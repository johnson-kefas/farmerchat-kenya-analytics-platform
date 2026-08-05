# Dashboard Chart Map

This chart map records the shared analytical contract for the Crop and
Livestock modules. Both modules use the same Plotly builders and palette.

| Section | Question | Chart form | Fields | Supported interpretation |
| --- | --- | --- | --- | --- |
| Data Quality | How much of the reconstructed source is unique? | Donut | Unique rows, duplicates removed | Deduplication composition |
| Data Quality | Which monitored fields have the most missing values? | Ranked horizontal bar | Field, missing count | Missingness concentration |
| Data Quality | Does missingness differ by production year? | Heatmap | Field, year, missing rate | Coverage pattern by year |
| Value Chains | What asset-type mix is represented? | Donut | Asset type, query count | Single versus mixed composition |
| Value Chains | Which value chains receive the most queries? | Ranked horizontal bar | Value chain, query count | Volume ranking and long tail |
| Value Chains | How is query volume distributed through the hierarchy? | Treemap | Asset type, value chain, query count | Hierarchical composition |
| Value Chains | Which approved mixed components co-occur? | Sankey | Source, target, query count | Frequent component pairs |
| Domains | Which approved primary domains dominate? | Ranked horizontal bar | Domain, query count | Knowledge-demand ranking |
| Domains | How complete is primary-domain classification? | Donut | Classified, unclassified | Classification coverage |
| Domains | Which subdomains sit within each domain? | Treemap | Domain, subdomain, query count | Taxonomy composition |
| Subdomains | Which topics lead within the selected domain? | Ranked horizontal bar | Subdomain, query count | Topic ranking |
| Subdomains | How do domain, subdomain, and intent connect? | Sunburst | Domain, subdomain, intent, query count | Interactive taxonomy drill-down |
| Geography | How complete is county metadata? | Donut | County present, county missing | Geographic coverage |
| Geography | Which counties are most represented? | Ranked horizontal bar | County, query count | Representation ranking |
| Geography | How does domain mix vary by county? | Heatmap | County, domain, count or within-county share | Regional demand composition |
| Time Trends | How does query volume move month to month? | Line | Month, query count | Production-period movement |
| Time Trends | Where are high- and low-volume months? | Heatmap | Year, month, query count | Monthly intensity |
| Time Trends | How does domain composition change over time? | Stacked area | Month, domain, query count | Mix over time |
| Time Trends | How do approved seasonal signals change? | Multi-line | Month, signal, monthly share | Descriptive calendar-aligned patterns |

## Visual policy

- Single-series charts use one approved accent color.
- Composition charts use no more than five approved category colors.
- Long labels use horizontal bars or word-safe wrapping.
- Standard count axes begin at zero.
- All charts use responsive width, compact number formatting, and informative
  hover labels.
- MAM and OND bands provide calendar context only.
