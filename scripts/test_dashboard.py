"""Exercise the real Streamlit app and its filters against PostgreSQL."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


def check(app):
    assert not app.exception, [str(item.value) for item in app.exception]
    assert not app.error, [item.value for item in app.error]
    assert len(app.metric) >= 4, "Dashboard did not render its metrics"


def main():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "web" / "app.py"))
    app.run(timeout=60)
    check(app)
    assert int(app.metric[0].value.replace(",", "")) >= 100
    assert len(app.dataframe) >= 1
    assert len(app.get("plotly_chart")) >= 3
    print("Dashboard: real database, metrics, charts and tables rendered")
    for widget in app.sidebar.multiselect:
        if widget.options:
            widget.set_value([widget.options[0]]).run(timeout=60)
            check(app)
            widget.set_value([]).run(timeout=60)
    app.sidebar.text_input[0].set_value("zzzz_no_matching_game_6621601255").run(timeout=60)
    check(app)
    assert app.metric[0].value == "0"
    app.sidebar.text_input[0].set_value("").run(timeout=60)
    check(app)
    if app.sidebar.slider:
        slider = app.sidebar.slider[0]
        slider.set_range(slider.min, (slider.min + slider.max) / 2).run(timeout=60)
        check(app)
    print("Dashboard: genre, source, search, empty results and price filters OK")


if __name__ == "__main__":
    main()
