"""Thai-language Streamlit dashboard backed exclusively by PostgreSQL."""

import os
from html import escape

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
    :root {color-scheme: dark;}
    .stApp {background: radial-gradient(ellipse at 85% 0%, #182041 0%, #080D1A 48%); color: #F8FAFC;}
    html, body, [data-testid="stAppViewContainer"] {font-family: "Segoe UI", Tahoma, sans-serif; color: #F8FAFC;}
    [data-testid="stMainBlockContainer"] {max-width: 1800px; padding: 1.7rem 2.2rem 2rem;}
    [data-testid="stHeader"] {background: transparent;}
    [data-testid="stSidebar"] {background: #10192B; border-right: 1px solid #26344C;}
    [data-testid="stSidebar"] > div:first-child {padding-top: 1.6rem;}
    [data-testid="stSidebar"] h2 {font-size: 1.2rem;}
    [data-testid="stWidgetLabel"] p, [data-testid="stMarkdownContainer"] p,
    [data-testid="stMetricLabel"] p, h1, h2, h3 {color: #F8FAFC;}
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {color: #94A3B8;}
    [data-testid="stTextInput"] input {background: #151F34; color: #F8FAFC; caret-color: #22D3EE;}
    [data-testid="stTextInput"] input::placeholder {color: #94A3B8; opacity: 1;}
    [data-baseweb="select"] > div {background: #151F34; color: #F8FAFC; border-color: #34445E;}
    [data-baseweb="select"] input {color: #F8FAFC;}
    [data-baseweb="popover"], [role="listbox"], [role="option"] {background: #151F34; color: #F8FAFC;}
    [role="option"]:hover {background: #26344C;}
    [data-baseweb="tag"] {background: #263C56; color: #F8FAFC;}
    [data-testid="stSlider"] {color: #F8FAFC;}
    [data-testid="stMetric"] {background: linear-gradient(135deg, #151F34, #111B2F); border: 1px solid #293751;
        border-top: 3px solid #22D3EE; padding: 16px 19px; border-radius: 14px; box-shadow: 0 8px 24px #00000024;}
    [data-testid="stMetricValue"] {color: #F8FAFC; font-size: clamp(1.6rem, 2.6vw, 2.6rem); font-weight: 750; letter-spacing: -.04em;}
    [data-testid="stMetricLabel"] {color: #CBD5E1; font-size: .85rem;}
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) [data-testid="stMetric"] {border-top-color: #34D399;}
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) [data-testid="stMetric"] {border-top-color: #A78BFA;}
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(4) [data-testid="stMetric"] {border-top-color: #FB7185;}
    [data-testid="stPlotlyChart"], [data-testid="stDataFrame"] {border: 1px solid #26344C; border-radius: 14px; overflow: hidden; background: #151F34;}
    [data-testid="stVerticalBlock"] {gap: .8rem;}
    h3 {font-size: 1.02rem !important; letter-spacing: .01em; padding-top: .3rem !important;}
    a {color: #67E8F9;}
    .hero {position: relative; padding: 22px 26px; margin-bottom: 6px; border: 1px solid #2A3A58; border-radius: 18px;
        background: linear-gradient(110deg, #151F34 0%, #141F38 60%, #262044 100%); overflow: hidden;}
    .hero::after {content: ""; position: absolute; bottom: 0; left: 0; width: 100%; height: 3px;
        background: linear-gradient(90deg, #22D3EE, #A78BFA 65%, #FB7185);}
    .hero-kicker {font-size: .68rem; color: #67E8F9; letter-spacing: .2em; font-weight: 700; margin-bottom: 8px;}
    .hero h1 {font-size: clamp(1.55rem, 2.6vw, 2.6rem); line-height: 1.2; font-weight: 850; padding: 0; letter-spacing: -.03em;}
    .hero-subtitle {color: #C4B5FD; font-size: .92rem; letter-spacing: .06em; margin: 8px 0 5px;}
    .hero-description {color: #CBD5E1; font-size: .85rem;}
    .source-pills {display: flex; flex-wrap: wrap; gap: 8px; margin-top: 13px;}
    .source-pill {font-size: .7rem; color: #E2E8F0; background: #080D1A80; border: 1px solid #39435D; border-radius: 30px; padding: 4px 10px;}
    .sidebar-brand {font-size: .72rem; letter-spacing: .18em; color: #67E8F9; font-weight: 750; margin-bottom: 12px;}
    .section-label {color: #94A3B8; font-size: .68rem; letter-spacing: .18em; font-weight: 700; margin-top: 10px;}
    .pipeline-banner {border: 1px solid #34445E; border-left: 3px solid var(--status); background: #151F34;
        border-radius: 12px; padding: 12px 16px; color: #F8FAFC; font-size: .9rem; margin-bottom: 10px;}
    .pipeline-banner strong {color: var(--status);}
    @media (max-width: 800px) {
        [data-testid="stMainBlockContainer"] {padding: 1rem;}
        .hero {padding: 18px;}
        [data-testid="stMetric"] {padding: 12px;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """<div class="hero">
    <div class="hero-kicker">GAMING COMMAND CENTER / ANALYTICS</div>
    <h1>🎮 PC GAME ANALYTICS</h1>
    <div class="hero-subtitle">Multi-Source Gaming Intelligence</div>
    <div class="hero-description">สำรวจเกม PC ฟรี ติดตามดีล และวิเคราะห์ตลาดเกมจากข้อมูลจริงในที่เดียว</div>
    <div class="source-pills"><span class="source-pill">FreeToGame · FREE GAMES</span>
    <span class="source-pill">CheapShark · DEAL INTELLIGENCE</span>
    <span class="source-pill">Wikipedia · GAME LIBRARY</span></div></div>""",
    unsafe_allow_html=True,
)

PALETTE = ["#22D3EE", "#A78BFA", "#34D399", "#FB7185", "#FBBF24", "#60A5FA"]
SOURCE_NAMES = {"freetogame": "FreeToGame", "cheapshark": "CheapShark", "wikipedia": "Wikipedia"}
SOURCE_COLORS = {"FreeToGame": "#34D399", "CheapShark": "#22D3EE", "Wikipedia": "#A78BFA"}


def gaming_chart(fig, height=290):
    fig.update_layout(
        template="plotly_dark", height=height,
        paper_bgcolor="#151F34", plot_bgcolor="#151F34",
        font=dict(family="Segoe UI, Tahoma, sans-serif", color="#E2E8F0", size=12),
        margin=dict(l=16, r=20, t=30, b=38),
        colorway=PALETTE,
        legend=dict(font=dict(color="#E2E8F0"), bgcolor="#151F34"),
        hoverlabel=dict(bgcolor="#10192B", bordercolor="#64748B", font_color="#F8FAFC"),
    )
    fig.update_xaxes(gridcolor="#29354B", zerolinecolor="#34445E", tickfont_color="#CBD5E1", title_font_color="#CBD5E1")
    fig.update_yaxes(gridcolor="#29354B", zerolinecolor="#34445E", tickfont_color="#CBD5E1", title_font_color="#CBD5E1")
    return fig

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
    st.markdown('<div class="sidebar-brand">◈ PLAYER INTELLIGENCE</div>', unsafe_allow_html=True)
    st.header("สำรวจคลังเกม")
    st.caption("เลือกมุมมองที่สนใจ · ทุกกราฟปรับตามตัวกรอง")
    search = st.text_input("ค้นหาชื่อเกม", placeholder="พิมพ์ชื่อเกมที่ต้องการ…")
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
    st.caption("ช่วงราคาเริ่มต้นแสดงทุกเกม รวมเกมที่ไม่มีข้อมูลราคา")
    st.divider()
    st.caption("PC GAME ANALYTICS / 02739452")

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
st.markdown('<div class="section-label">OVERVIEW / ภาพรวมตามตัวกรอง</div>', unsafe_allow_html=True)
metric_columns = st.columns(4)
metric_columns[0].metric("🎮 เกมทั้งหมด", f"{int(row['games']):,}")
metric_columns[1].metric("✦ เกมฟรี", f"{int(row['free_games']):,}")
metric_columns[2].metric(
    "◈ ราคาเฉลี่ย (USD)",
    f"${row['average_price']:.2f}" if pd.notna(row["average_price"]) else "—",
)
metric_columns[3].metric("↘ เกมที่กำลังลดราคา", f"{int(row['discounted_games']):,}")

left, right = st.columns(2)
with left:
    st.subheader("ประเภทเกมยอดนิยม")
    if genres.empty:
        st.info("ไม่มีข้อมูลประเภทเกมตามตัวกรอง")
    else:
        st.plotly_chart(
            gaming_chart(px.bar(genres.sort_values("total"), x="total", y="genre", orientation="h",
                color_discrete_sequence=["#22D3EE"], labels={"total": "จำนวนเกม", "genre": ""})),
            use_container_width=True, config={"displayModeBar": False},
        )
with right:
    st.subheader("จำนวนเกมจากแต่ละแหล่ง")
    if source_counts.empty:
        st.info("ไม่มีข้อมูลแหล่งเกมตามตัวกรอง")
    else:
        source_display = source_counts.assign(source=source_counts["source"].map(SOURCE_NAMES))
        source_figure = px.bar(source_display, x="source", y="total", color="source", text="total",
            color_discrete_map=SOURCE_COLORS, labels={"source": "", "total": "เกมไม่ซ้ำ"})
        source_figure.update_layout(showlegend=False)
        source_figure.update_traces(textposition="outside", cliponaxis=False)
        st.plotly_chart(gaming_chart(source_figure), use_container_width=True, config={"displayModeBar": False})

price_panel, pipeline_panel = st.columns([1.25, 1])
with price_panel:
    st.subheader("ราคา × ส่วนลด / USD")
    if price_chart.empty:
        st.info("ไม่พบข้อมูลราคาและส่วนลดสำหรับตัวกรองนี้")
    else:
        st.plotly_chart(gaming_chart(px.scatter(
            price_chart,
            x="normal_price",
            y="sale_price",
            size="discount_percent",
            color="store_name",
            hover_name="title",
            hover_data=["discount_percent"],
            color_discrete_sequence=PALETTE,
            labels={"normal_price": "ราคาปกติ (USD)", "sale_price": "ราคาลด (USD)", "store_name": "ร้านค้า"},
        ), height=300), use_container_width=True, config={"displayModeBar": False})

st.subheader("Game Explorer / คลังเกม")
st.caption(f"พบ {len(games):,} เกมตามตัวกรอง · ค้นหาและกรองจากแถบด้านซ้าย · ราคาที่ไม่ระบุแสดงเป็นช่องว่าง")
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
    height=360,
    column_config={
        "ลิงก์": st.column_config.LinkColumn("ลิงก์", display_text="↗ เปิดเกม"),
        "ราคาปกติ (USD)": st.column_config.NumberColumn(format="$%.2f"),
        "ราคาลด (USD)": st.column_config.NumberColumn(format="$%.2f"),
        "ส่วนลด (%)": st.column_config.NumberColumn(format="%.1f%%"),
    },
)

with pipeline_panel:
    st.subheader("Pipeline / สถานะล่าสุด")
    if latest_runs.empty:
        st.info("ยังไม่มีประวัติ Pipeline — Trigger DAG ใน Airflow เพื่อเริ่มเก็บข้อมูล")
    else:
        latest = latest_runs.iloc[0]
        status_label = {"success": "สำเร็จ", "partial_success": "สำเร็จบางแหล่ง", "failed": "ล้มเหลว"}.get(latest["status"], latest["status"])
        status_color = {"success": "#34D399", "partial_success": "#FBBF24", "failed": "#FB7185"}.get(latest["status"], "#94A3B8")
        st.markdown(f'<div class="pipeline-banner" style="--status:{status_color}">'
            f'● PIPELINE STATUS &nbsp; <strong>{escape(str(status_label))}</strong></div>', unsafe_allow_html=True)
        status_columns = st.columns(3)
        status_columns[0].metric("Records Loaded", f"{int(latest['records_loaded']):,}")
        status_columns[1].metric("Failed Sources", int(latest["failed_sources"]))
        status_columns[2].metric("Quality Check", "ผ่าน ✓" if latest["quality_passed"] else "ไม่ผ่าน ✕")
        finished = pd.to_datetime(latest["finished_at"], utc=True).tz_convert("Asia/Bangkok")
        st.caption(f"อัปเดต {finished:%d/%m/%Y %H:%M} น. · Asia/Bangkok")
        if latest["error_summary"]:
            st.warning(latest["error_summary"])
        with st.expander("ดูประวัติ Pipeline"):
            st.dataframe(latest_runs, use_container_width=True, hide_index=True, height=180)
