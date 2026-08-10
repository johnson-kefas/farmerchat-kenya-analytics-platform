# County map revision: v4.2.0

## v4.1.0 failure diagnosis

Version 4.1.0 contained 47 county features, and the normalized county join
matched the production data. The national boundary was a separate line trace
and was not intentionally used as the data fill.

The failure occurred in Plotly's geographic SVG path conversion. The ADM1
exterior-ring direction was interpreted as the complement of each county.
Rendered county paths began with the full map rectangle and then cut out the
county as a hole. Repeated choropleth traces therefore painted almost the whole
viewport in one pale colour. The separate national line remained visible,
which made the result resemble a single filled Kenya polygon.

The v4.1.0 tests counted Plotly trace types and GeoJSON features, but did not
inspect the generated paths or rendered pixels. They could therefore pass while
the visible map remained wrong.

Version 4.2.0 starts from the v4.0.0 dashboard and replaces the horizontal
county bar chart with a new MapLibre-based Plotly implementation. The v4.1.0
map code was not used as the implementation baseline.

## Boundary inspection

### User-supplied `Admo.zip`

- National layer: `KEN_adm0`, 1 feature
- County layer: `KEN_adm1`, 47 features
- County name field: `NAME_1`
- County geometry: 36 Polygon and 11 MultiPolygon features
- CRS: WGS 84 geographic coordinates
- Licence: no source or licence document was included

The supplied archive was suitable technically, but absence of a licence file
was not treated as proof of redistribution permission.

### Bundled boundary source

The release uses the geoBoundaries `gbOpen` Kenya ADM1 and ADM0 layers. The
official API reports 47 county units, one national unit, 2020 represented year,
and Public Domain status. Both local files use CRS84 longitude/latitude
coordinates. Full source details are in `assets/geo/BOUNDARY_SOURCE.md`.

## Map design

- County ADM1 polygons are the only filled data geometry.
- All 47 counties remain present after every filter change.
- Counties with zero queries use neutral grey.
- Counties with data use `log(1 + query count)` for colour placement.
- The colourbar and tooltips show actual query counts.
- County borders use a visible 1.15 px line.
- The national ADM0 layer is a separate 2.2 px line-only trace.
- Hover shows county, exact query count, share, and rank.
- MapLibre provides pan, zoom, scroll zoom, and reset-view interaction.
- Boundary files are local and cached. No live map service or token is needed.

The logarithmic range is justified by the real production distributions. Crop
has a 65.9× maximum-to-median county ratio and Livestock has a 61.4× ratio.
The transformation preserves counts while making lower-volume differences
visible.

## Validation result

- 22 automated tests passed.
- Crop: 47 polygons, 18 counties with queries, 29 neutral counties.
- Livestock: 47 polygons, 18 counties with queries, 29 neutral counties.
- Nyeri is the highest-volume and darkest county in both default views.
- Independent rendered-image review confirmed visible internal borders,
  multiple colour intensities, neutral zero counties, and a separate national
  outline.
- The regression suite fails if the county fill is replaced with one
  Kenya-wide feature.
