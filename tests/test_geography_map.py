"""County geometry, join, map-layer, and regression tests."""

from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import CROP_MODULE, LIVESTOCK_MODULE
from src.geography_map import (
    COUNTY_BORDER_COLOR,
    NATIONAL_BORDER_COLOR,
    county_choropleth,
    load_kenya_boundaries,
    normalise_county_name,
    prepare_county_map_data,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _geometry_bbox(geometry: dict) -> tuple[float, float, float, float]:
    """Return a bounding box for Polygon or MultiPolygon GeoJSON geometry."""
    geometry_type = geometry["type"]
    polygons = (
        [geometry["coordinates"]]
        if geometry_type == "Polygon"
        else geometry["coordinates"]
    )
    points = [point for polygon in polygons for ring in polygon for point in ring]
    longitudes = [float(point[0]) for point in points]
    latitudes = [float(point[1]) for point in points]
    return min(longitudes), min(latitudes), max(longitudes), max(latitudes)


class KenyaCountyMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.counties, cls.national = load_kenya_boundaries()

    def _sample_map_data(self) -> pd.DataFrame:
        ranking = pd.DataFrame(
            {
                "County": [
                    "Nyeri County",
                    "HomaBay",
                    "Murang’a",
                    "Taita-Taveta",
                    "Tharaka-Nithi",
                ],
                "Queries": [36_052, 2_600, 700, 338, 387],
            }
        )
        mapped, unmatched = prepare_county_map_data(ranking, self.counties)
        self.assertEqual(unmatched, ())
        return mapped

    def test_boundary_inventory_is_47_adm1_counties_and_one_adm0_feature(self) -> None:
        county_features = self.counties["features"]
        national_features = self.national["features"]
        self.assertEqual(len(county_features), 47)
        self.assertEqual(len(national_features), 1)
        self.assertEqual(
            {feature["geometry"]["type"] for feature in county_features},
            {"Polygon", "MultiPolygon"},
        )
        self.assertEqual(national_features[0]["geometry"]["type"], "MultiPolygon")
        self.assertTrue(
            self.counties["crs"]["properties"]["name"].endswith("CRS84")
        )
        self.assertTrue(
            self.national["crs"]["properties"]["name"].endswith("CRS84")
        )
        names = [
            feature["properties"]["dashboard_county"]
            for feature in county_features
        ]
        self.assertEqual(len(set(names)), 47)
        self.assertIn("Tharaka-Nithi", names)

    def test_regression_fails_for_a_single_kenya_wide_polygon(self) -> None:
        """Prove that 47 distinct county geometries, not ADM0, drive the fill."""
        county_bboxes = {
            _geometry_bbox(feature["geometry"])
            for feature in self.counties["features"]
        }
        national_bbox = _geometry_bbox(self.national["features"][0]["geometry"])
        self.assertEqual(len(county_bboxes), 47)
        self.assertNotIn(national_bbox, county_bboxes)

        mapped = self._sample_map_data()
        figure = county_choropleth(
            mapped,
            self.counties,
            self.national,
            "County representation",
            "Geotagged query volume by county",
        )
        fill_traces = [trace for trace in figure.data if trace.type == "choroplethmap"]
        self.assertEqual(sum(len(trace.locations) for trace in fill_traces), 47)
        self.assertTrue(
            all(len(trace.geojson["features"]) == 47 for trace in fill_traces)
        )
        self.assertTrue(
            all(
                trace.featureidkey == "properties.dashboard_county"
                for trace in fill_traces
            )
        )
        self.assertFalse(any(trace.type == "choropleth" for trace in figure.data))

    def test_join_is_robust_numeric_and_retains_zero_counties(self) -> None:
        mapped = self._sample_map_data()
        self.assertEqual(len(mapped), 47)
        self.assertTrue(pd.api.types.is_integer_dtype(mapped["Queries"]))
        self.assertEqual(int(mapped["Has data"].sum()), 5)
        self.assertEqual(int((mapped["Queries"] == 0).sum()), 42)
        self.assertEqual(
            int(mapped.loc[mapped["County"].eq("Nyeri"), "Queries"].iloc[0]),
            36_052,
        )
        self.assertEqual(normalise_county_name("County of HomaBay"), "homa bay")
        self.assertEqual(normalise_county_name("Murang’a County"), "muranga")

    def test_all_counties_remain_when_filtered_selection_has_no_geotagged_rows(self) -> None:
        mapped, unmatched = prepare_county_map_data(
            pd.DataFrame(columns=["County", "Queries"]),
            self.counties,
        )
        self.assertEqual(unmatched, ())
        self.assertEqual(len(mapped), 47)
        self.assertEqual(int(mapped["Has data"].sum()), 0)
        figure = county_choropleth(
            mapped,
            self.counties,
            self.national,
            "County representation",
            "No geotagged rows",
        )
        fill_traces = [trace for trace in figure.data if trace.type == "choroplethmap"]
        self.assertEqual(len(fill_traces), 1)
        self.assertEqual(len(fill_traces[0].locations), 47)

    def test_colour_values_vary_and_highest_volume_is_darkest(self) -> None:
        mapped = self._sample_map_data()
        figure = county_choropleth(
            mapped,
            self.counties,
            self.national,
            "County representation",
            "Geotagged query volume by county",
        )
        data_trace = next(
            trace
            for trace in figure.data
            if trace.type == "choroplethmap" and trace.name == "Query volume"
        )
        zero_trace = next(
            trace
            for trace in figure.data
            if trace.type == "choroplethmap" and trace.name == "No queries"
        )
        self.assertGreater(len(np.unique(np.asarray(data_trace.z, dtype=float))), 1)
        maximum_index = int(np.argmax(np.asarray(data_trace.z, dtype=float)))
        self.assertEqual(data_trace.locations[maximum_index], "Nyeri")
        self.assertEqual(len(zero_trace.locations), 42)
        self.assertEqual(len(set(np.asarray(zero_trace.z, dtype=float))), 1)
        self.assertEqual(data_trace.marker.line.color, COUNTY_BORDER_COLOR)
        self.assertGreaterEqual(float(data_trace.marker.line.width), 1.0)
        self.assertIn("log scale", data_trace.colorbar.title.text)
        self.assertIn("Queries: %{customdata[1]}", data_trace.hovertemplate)
        self.assertIn("Share: %{customdata[2]}", data_trace.hovertemplate)
        self.assertIn("Rank: %{customdata[3]}", data_trace.hovertemplate)
        self.assertIn("No geotagged queries", zero_trace.hovertemplate)

    def test_national_outline_is_separate_and_does_not_fill_counties(self) -> None:
        figure = county_choropleth(
            self._sample_map_data(),
            self.counties,
            self.national,
            "County representation",
            "Geotagged query volume by county",
        )
        outline = next(trace for trace in figure.data if trace.type == "scattermap")
        self.assertEqual(outline.mode, "lines")
        self.assertEqual(outline.line.color, NATIONAL_BORDER_COLOR)
        self.assertGreater(float(outline.line.width), 1.15)
        self.assertIsNone(outline.fill)
        self.assertEqual(figure.layout.map.style, "white-bg")
        self.assertGreater(float(figure.layout.map.zoom), 0)
        self.assertEqual(figure.layout.map.uirevision, "kenya-county-map-v4.2.0")

    def test_filtered_crop_and_livestock_sources_build_dynamic_maps(self) -> None:
        for module in (CROP_MODULE, LIVESTOCK_MODULE):
            path = PROJECT_ROOT / "data" / module.dataset_filename
            frame = pd.read_csv(
                path,
                usecols=["user_geo_level2", "query_year_month"],
                low_memory=False,
            )
            years = pd.to_numeric(
                frame["query_year_month"].astype("string").str[:4],
                errors="coerce",
            )
            production = frame.loc[years.isin([2025, 2026])]
            county = production["user_geo_level2"].astype("string").str.strip()
            ranking = (
                county.loc[county.notna() & county.ne("")]
                .value_counts()
                .rename_axis("County")
                .reset_index(name="Queries")
            )
            mapped, unmatched = prepare_county_map_data(ranking, self.counties)
            self.assertEqual(unmatched, (), module.label)
            self.assertEqual(int(mapped["Queries"].sum()), int(ranking["Queries"].sum()))
            self.assertEqual(len(mapped), 47)

            # Simulate the existing County filter by passing its filtered ranking.
            selected = ranking.loc[ranking["County"].eq("Nyeri")]
            filtered_map, unmatched = prepare_county_map_data(selected, self.counties)
            self.assertEqual(unmatched, ())
            self.assertEqual(int(filtered_map["Has data"].sum()), 1)
            self.assertEqual(
                int(filtered_map.loc[filtered_map["County"].eq("Nyeri"), "Queries"].iloc[0]),
                int(selected["Queries"].iloc[0]),
            )
            figure = county_choropleth(
                filtered_map,
                self.counties,
                self.national,
                "County representation",
                f"{module.label} filtered query volume",
            )
            self.assertEqual(
                sum(
                    len(trace.locations)
                    for trace in figure.data
                    if trace.type == "choroplethmap"
                ),
                47,
            )


if __name__ == "__main__":
    unittest.main()
