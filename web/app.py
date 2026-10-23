"""Thai-language Streamlit dashboard backed exclusively by PostgreSQL."""

import os

import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st

st.set_page_config(
    page_title="PC Game Analytics",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(ttl=60)
def read_query(query, params=None):
    connection = psycopg2.connect(
        host=os.getenv("ANALYTICS_DB_HOST", "localhost"),
        port=int(os.getenv("ANALYTICS_DB_PORT", "5453")),
        dbname=os.getenv("ANALYTICS_DB_NAME", "game_analytics"),
        user=os.getenv("ANALYTICS_DB_USER", "game_analytics"),
        password=os.getenv("ANALYTICS_DB_PASSWORD", ""),
        connect_timeout=5,
        application_name="pc-game-analytics-dashboard",
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return pd.DataFrame.from_records(
                cursor.fetchall(),
                columns=[column.name for column in cursor.description],
                coerce_float=True,
            )
    finally:
        connection.close()


st.markdown(
    """
    <style>
    .stApp {background: linear-gradient(160deg, #101827 0%, #101827 40%, #172338 100%);}
    [data-testid="stMetric"] {background: #1d2b40; padding: 16px; border-radius: 12px;}
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("🎮 PC Game Analytics")
st.caption("แดชบอร์ดวิเคราะห์เกม PC ฟรีและดีลลดราคาจากข้อมูลจริง 3 แหล่ง")

try:
    filters = read_query(
        """
        SELECT DISTINCT genre FROM games
        WHERE genre IS NOT NULL AND BTRIM(genre) <> ''
        ORDER BY genre
        """
    )
    sources = read_query(
        "SELECT DISTINCT source FROM raw_games ORDER BY source"
    )
    price_bounds = read_query(
        """
        SELECT MIN(sale_price) AS min_price, MAX(sale_price) AS max_price
        FROM game_offers WHERE currency = 'USD' AND sale_price IS NOT NULL
        """
    )
except psycopg2.OperationalError as exc:
    st.error(f"เชื่อมต่อ PostgreSQL ไม่สำเร็จ: {exc}")
    st.info("ตรวจสอบว่า Game Analytics PostgreSQL healthy และตั้งค่าไฟล์ .env แล้ว")
    st.stop()

min_price = price_bounds.loc[0, "min_price"]
max_price = price_bounds.loc[0, "max_price"]
price_floor = float(min_price) if pd.notna(min_price) else 0.0
price_ceiling = float(max_price) if pd.notna(max_price) else 0.0

with st.sidebar:
    st.header("ตัวกรอง")
    selected_genres = st.multiselect("ประเภทเกม", filters["genre"].tolist())
    selected_sources = st.multiselect("แหล่งข้อมูล", sources["source"].tolist())
    if price_ceiling > price_floor:
        selected_price = st.slider(
            "ช่วงราคาลด (USD)",
            min_value=price_floor,
            max_value=price_ceiling,
            value=(price_floor, price_ceiling),
        )
    else:
        selected_price = (price_floor, price_ceiling)
        st.caption("ยังไม่มีช่วงราคาที่ใช้กรองได้")
    search = st.text_input("ค้นหาชื่อเกม")

conditions = []
params = []
if selected_genres:
    conditions.append("g.genre = ANY(%s)")
    params.append(selected_genres)
if search.strip():
    conditions.append("g.title ILIKE %s")
    params.append(f"%{search.strip()}%")
if selected_sources:
    conditions.append(
        "EXISTS (SELECT 1 FROM raw_games r WHERE r.canonical_key = g.canonical_key AND r.source = ANY(%s))"
    )
    params.append(selected_sources)
if price_ceiling > price_floor and tuple(selected_price) != (price_floor, price_ceiling):
    conditions.append(
        "EXISTS (SELECT 1 FROM game_offers p WHERE p.game_id = g.id AND p.currency = 'USD' AND p.sale_price BETWEEN %s AND %s)"
    )
    params.extend(selected_price)
where_clause = " AND ".join(conditions) if conditions else "TRUE"

try:
    games = read_query(
        f"""
        SELECT g.id, g.title, g.genre, g.developer, g.publisher, g.release_date,
               g.game_url,
               COALESCE(src.sources, ARRAY[]::text[]) AS sources,
               offer.store_name, offer.currency, offer.normal_price,
               offer.sale_price, offer.discount_percent, offer.deal_rating,
               offer.offer_url,
               (g.canonical_key IN (
                    SELECT canonical_key FROM raw_games WHERE source = 'freetogame'
               )) AS is_free
        FROM games g
        LEFT JOIN LATERAL (
            SELECT ARRAY_AGG(DISTINCT r.source ORDER BY r.source) AS sources
            FROM raw_games r WHERE r.canonical_key = g.canonical_key
        ) src ON TRUE
        LEFT JOIN LATERAL (
            SELECT o.store_name, o.currency, o.normal_price, o.sale_price,
                   o.discount_percent, o.deal_rating, o.offer_url
            FROM game_offers o
            WHERE o.game_id = g.id AND o.currency = 'USD'
            ORDER BY o.discount_percent DESC NULLS LAST, o.sale_price ASC NULLS LAST
            LIMIT 1
        ) offer ON TRUE
        WHERE {where_clause}
        ORDER BY g.title
        """,
        params or None,
    )
    totals = read_query(
        f"""
        WITH filtered_games AS (
          SELECT g.id, g.canonical_key
          FROM games g
          WHERE {where_clause}
        ),
        per_game_prices AS (
          SELECT f.id,
                 MIN(o.sale_price) FILTER (WHERE o.currency = 'USD') AS lowest_price,
                 BOOL_OR(o.discount_percent > 0 AND o.sale_price < o.normal_price) AS discounted
          FROM filtered_games f
          LEFT JOIN game_offers o ON o.game_id = f.id
          GROUP BY f.id
        )
        SELECT
          COUNT(*) AS games,
          COUNT(*) FILTER (
            WHERE EXISTS (
              SELECT 1 FROM raw_games r
              WHERE r.canonical_key = f.canonical_key AND r.source = 'freetogame'
            )
          ) AS free_games,
          ROUND(AVG(lowest_price), 2) AS average_price,
          COUNT(*) FILTER (WHERE discounted) AS discounted_games
        FROM filtered_games f
        JOIN per_game_prices p ON p.id = f.id
        """,
        params or None,
    )
    genres = read_query(
        f"""
        SELECT COALESCE(NULLIF(g.genre, ''), 'ไม่ระบุ') AS genre, COUNT(*) AS total
        FROM games g WHERE {where_clause}
        GROUP BY 1 ORDER BY total DESC LIMIT 12
        """,
        params or None,
    )
    source_counts = read_query(
        f"""
        SELECT r.source, COUNT(DISTINCT g.id) AS total
        FROM games g JOIN raw_games r ON r.canonical_key = g.canonical_key
        WHERE {where_clause}
        GROUP BY r.source ORDER BY total DESC
        """,
        params or None,
    )
    price_chart = read_query(
        f"""
        SELECT g.title, o.normal_price, o.sale_price, o.discount_percent, o.store_name
        FROM games g JOIN game_offers o ON o.game_id = g.id
        WHERE o.currency = 'USD' AND {where_clause}
        ORDER BY o.discount_percent DESC NULLS LAST LIMIT 25
        """,
        params or None,
    )
    latest_runs = read_query(
        """
        SELECT run_id, status, started_at, finished_at, records_extracted,
               records_loaded, failed_sources, quality_passed, error_summary
        FROM pipeline_runs ORDER BY finished_at DESC LIMIT 10
        """
    )
except (psycopg2.Error, ValueError) as exc:
    st.error(f"อ่านข้อมูลจาก PostgreSQL ไม่สำเร็จ: {exc}")
    st.stop()

row = totals.iloc[0]
metric_columns = st.columns(4)
metric_columns[0].metric("เกมทั้งหมด", f"{int(row['games']):,}")
metric_columns[1].metric("เกมฟรี", f"{int(row['free_games']):,}")
metric_columns[2].metric(
    "ราคาเฉลี่ย (USD)",
    f"${row['average_price']:.2f}" if pd.notna(row["average_price"]) else "—",
)
metric_columns[3].metric("เกมที่กำลังลดราคา", f"{int(row['discounted_games']):,}")

left, right = st.columns(2)
with left:
    st.subheader("ประเภทเกมยอดนิยม")
    if genres.empty:
        st.info("ไม่มีข้อมูลประเภทเกมตามตัวกรอง")
    else:
        st.plotly_chart(
            px.bar(genres, x="total", y="genre", orientation="h", labels={"total": "จำนวนเกม", "genre": "ประเภท"}),
            use_container_width=True,
        )
with right:
    st.subheader("จำนวนเกมจากแต่ละแหล่ง")
    if source_counts.empty:
        st.info("ไม่มีข้อมูลแหล่งเกมตามตัวกรอง")
    else:
        st.plotly_chart(
            px.bar(source_counts, x="source", y="total", color="source", labels={"source": "แหล่งข้อมูล", "total": "เกมไม่ซ้ำ"}),
            use_container_width=True,
        )

st.subheader("เปรียบเทียบราคาและส่วนลด (USD)")
if price_chart.empty:
    st.info("ไม่พบข้อมูลราคาและส่วนลดสำหรับตัวกรองนี้")
else:
    st.plotly_chart(
        px.scatter(
            price_chart,
            x="normal_price",
            y="sale_price",
            size="discount_percent",
            color="store_name",
            hover_name="title",
            hover_data=["discount_percent"],
            labels={"normal_price": "ราคาปกติ (USD)", "sale_price": "ราคาลด (USD)", "store_name": "ร้านค้า"},
        ),
        use_container_width=True,
    )

st.subheader("รายชื่อเกม")
display = games.rename(
    columns={
        "title": "ชื่อเกม",
        "genre": "ประเภท",
        "developer": "ผู้พัฒนา",
        "release_date": "วันเปิดตัว",
        "game_url": "ลิงก์",
        "sources": "แหล่งข้อมูล",
        "store_name": "ร้านค้า",
        "normal_price": "ราคาปกติ (USD)",
        "sale_price": "ราคาลด (USD)",
        "discount_percent": "ส่วนลด (%)",
        "is_free": "เกมฟรี",
    }
)
visible_columns = [
    column
    for column in (
        "ชื่อเกม",
        "ประเภท",
        "ผู้พัฒนา",
        "วันเปิดตัว",
        "ลิงก์",
        "แหล่งข้อมูล",
        "ร้านค้า",
        "ราคาปกติ (USD)",
        "ราคาลด (USD)",
        "ส่วนลด (%)",
        "เกมฟรี",
    )
    if column in display.columns
]
st.dataframe(
    display[visible_columns],
    use_container_width=True,
    hide_index=True,
    column_config={"ลิงก์": st.column_config.LinkColumn("ลิงก์", display_text="เปิดเกม")},
)

st.subheader("สถานะ Pipeline ล่าสุด")
if latest_runs.empty:
    st.info("ยังไม่มีประวัติ Pipeline — Trigger DAG ใน Airflow เพื่อเริ่มเก็บข้อมูล")
else:
    latest = latest_runs.iloc[0]
    status_label = {
        "success": "สำเร็จ",
        "partial_success": "สำเร็จบางแหล่ง",
        "failed": "ล้มเหลว",
    }.get(latest["status"], latest["status"])
    status_columns = st.columns(4)
    status_columns[0].metric("สถานะล่าสุด", status_label)
    status_columns[1].metric("ข้อมูลสำเร็จ", int(latest["records_loaded"]))
    status_columns[2].metric("แหล่งที่ล้มเหลว", int(latest["failed_sources"]))
    status_columns[3].metric("Quality Check", "ผ่าน" if latest["quality_passed"] else "ไม่ผ่าน")
    st.caption(f"เริ่ม {latest['started_at']} · เสร็จ {latest['finished_at']}")
    if latest["error_summary"]:
        st.warning(latest["error_summary"])
    st.dataframe(latest_runs, use_container_width=True, hide_index=True)
