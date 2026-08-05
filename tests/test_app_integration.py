"""Full-source Streamlit execution tests for both analytics modules."""

from __future__ import annotations

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DashboardIntegrationTests(unittest.TestCase):
    """Execute every navigation state against the packaged approved data."""

    def _app(self) -> AppTest:
        return AppTest.from_file(
            PROJECT_ROOT / "app.py",
            default_timeout=90,
        ).run(timeout=90)

    def _assert_pages(self, app: AppTest) -> None:
        page_selector = next(radio for radio in app.radio if radio.label == "Explore")
        pages = list(page_selector.options)
        self.assertEqual(len(pages), 6)

        for page in pages:
            next(
                radio for radio in app.radio if radio.label == "Explore"
            ).set_value(page).run(timeout=90)
            self.assertEqual(
                len(app.exception),
                0,
                f"{page} raised: {[item.message for item in app.exception]}",
            )
            self.assertGreaterEqual(len(app.get("plotly_chart")), 2)
            self.assertEqual(len(app.code), 0)
            leaked = [
                str(block.value)
                for block in app.markdown
                if any(
                    marker in str(block.value)
                    for marker in ("<style", "<article", ".metric-grid")
                )
            ]
            self.assertEqual(leaked, [])

    def test_crop_module_all_pages(self) -> None:
        app = self._app()
        self._assert_pages(app)

    def test_livestock_module_all_pages(self) -> None:
        app = self._app()
        next(
            radio for radio in app.radio if radio.label == "Analytics module"
        ).set_value("livestock").run(timeout=90)
        self.assertIn(
            "2. Livestock value chain",
            next(radio for radio in app.radio if radio.label == "Explore").options,
        )
        labels = {widget.label for widget in app.multiselect}
        self.assertIn("Livestock Type", labels)
        self.assertIn("Intent", labels)
        self.assertIn("Confidence Level", labels)
        self._assert_pages(app)


if __name__ == "__main__":
    unittest.main()
