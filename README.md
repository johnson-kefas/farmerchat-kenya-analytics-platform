# FarmerChat Kenya Analytics Platform

Version 4.0.0 is a unified Streamlit and Plotly application with two modules:

- Crop Query Analytics
- Livestock Query Analytics

The Livestock module extends the approved Crop Dashboard v3.0.1 design system.
Both modules use the same layout, responsive behavior, typography, color
palette, KPI cards, filters, chart styling, spacing, navigation, and export
patterns.

## Approved analytical sources

The packaged CSV files are the only analytical sources:

- `farmerchat_kenya_crop_intent_labelled_deduplicated_asset_standardized_v_4.0.0.csv`
- `farmerchat_kenya_livestock_intent_labelled_deduplicated_asset_standardized_v_4.0.0.csv`

The application excludes every 2024 test record before any KPI, visualization,
table, global filter, or download is calculated.

## Module navigation

Use the **Analytics module** control at the top of the sidebar to move between
Crop and Livestock. Each module remembers its own page and filter selections.
Selections from one module never leak into the other module.

Both modules contain six pages:

1. Data Quality
2. Crop Asset Type Analysis or Livestock Value Chain Analysis
3. Agricultural Domains
4. Subdomain Analysis
5. Geographic Analysis
6. Time Trends

## Global filters

The Crop module retains its approved global filters:

- Year
- County
- Asset Type
- Value Chain
- Domain
- Subdomain

The Livestock module uses the same filter design and adds the two requested
livestock classification filters:

- Year
- County
- Livestock Type
- Value Chain
- Domain
- Subdomain
- Intent
- Confidence Level

Every chart, KPI, table, and filtered-data download responds to the active
module's global filters.

## Livestock module coverage

### Data Quality

Shows reconstructed source occurrences, retained unique queries, exact
duplicates removed, potential near duplicates, incomplete core records,
unintelligible records, missing metadata, missing county, unclear asset names,
and review flags.

### Livestock Value Chain Analysis

Shows single-livestock and mixed-livestock distribution, approved value-chain
rankings, the long tail, a value-chain hierarchy, and co-occurring livestock
within approved mixed-livestock questions.

### Agricultural Domains

Uses the approved `primary_domain` values without inventing a new crosswalk.
Detailed topics such as feeding, disease management, vaccination, breeding,
housing, welfare, weather, and markets remain visible through approved
subdomains and farmer intents.

### Subdomain Analysis

Provides an interactive Domain to Subdomain to Farmer Intent drill-down,
ranked topics, and searchable tables.

### Geographic Analysis

Compares county representation, value chains, domain mix, and classification
coverage while keeping missing county information visible.

### Time Trends

Uses only 2025 and 2026. It shows monthly volume, monthly intensity, domain mix,
and approved livestock planning, livestock management, and weather-risk
signals. MAM and OND are calendar reference windows. Observed patterns are
descriptive and are not presented as proof of rainfall, disease outbreaks, or
climate causation.

## Responsive interface

The application preserves the approved v3.0.1 responsive interface:

- KPI cards use a container-aware grid and move to a new row before text
  becomes cramped.
- Main chart columns wrap when the sidebar opens or the browser becomes
  narrower.
- Plotly figures use responsive widths, adaptive title wrapping, automatic
  margins, and word-safe category labels.
- Streamlit Material Symbols retain their native icon font.
- Custom cards and layout elements use Streamlit's dedicated HTML renderer, so
  raw HTML or CSS cannot be exposed as Markdown code.
- Cards, controls, tables, notes, and charts share one neutral visual system
  based on Inter and native system fonts.
- The interface favors vertical reflow instead of horizontal compression.

## Project structure

```text
farmerchat_kenya_analytics_platform_v4.0.0/
├── app.py
├── requirements.txt
├── README.md
├── .streamlit/
│   └── config.toml
├── assets/
│   └── styles.css
├── data/
│   ├── farmerchat_kenya_crop_intent_labelled_deduplicated_asset_standardized_v_4.0.0.csv
│   └── farmerchat_kenya_livestock_intent_labelled_deduplicated_asset_standardized_v_4.0.0.csv
├── docs/
│   └── CHART_MAP.md
├── src/
│   ├── charts.py
│   ├── components.py
│   ├── config.py
│   ├── data.py
│   ├── filters.py
│   ├── formatting.py
│   ├── metrics.py
│   └── pages/
│       ├── assets.py
│       ├── data_quality.py
│       ├── domains.py
│       ├── geography.py
│       ├── subdomains.py
│       └── time_trends.py
└── tests/
    ├── test_app_integration.py
    ├── test_core.py
    └── test_ui_contract.py
```

## Windows installation and execution

### 1. Extract the ZIP

Extract the downloaded ZIP to a normal folder, for example:

```text
C:\Users\USER 1\Documents\farmerchat_kenya_analytics_platform_v4.0.0
```

Moving the complete extracted folder later is safe. Keep `app.py`, `src`,
`assets`, `.streamlit`, and `data` together.

### 2. Open PowerShell in the project folder

Open the extracted folder in File Explorer. Click the address bar, type:

```text
powershell
```

Press Enter. Confirm that the prompt ends with the project folder name.

### 3. Create a virtual environment

```powershell
python -m venv .venv
```

If `python` is not recognized, install Python 3.11 or 3.12 from
https://www.python.org/downloads/ and select **Add Python to PATH** during
installation.

### 4. Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

The prompt should now begin with `(.venv)`.

### 5. Install the required packages

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

No new application dependency was added for the Livestock module.

### 6. Start the platform

```powershell
python -m streamlit run app.py
```

Streamlit should open the platform in the default browser. If it does not,
copy the Local URL shown in PowerShell, usually
`http://localhost:8501`, and open it in a browser.

### 7. Stop and restart later

Press `Ctrl+C` in PowerShell to stop the app.

To run it later:

```powershell
cd "C:\Users\USER 1\Documents\farmerchat_kenya_analytics_platform_v4.0.0"
.\.venv\Scripts\Activate.ps1
python -m streamlit run app.py
```

## macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Optional external source paths

The packaged data works without configuration. If either approved CSV is
stored elsewhere, set its module-specific environment variable before starting
the application.

Crop:

```powershell
$env:FARMERCHAT_CROP_DATA_PATH = "C:\path\to\approved_crop_file.csv"
```

Livestock:

```powershell
$env:FARMERCHAT_LIVESTOCK_DATA_PATH = "C:\path\to\approved_livestock_file.csv"
```

Then run:

```powershell
python -m streamlit run app.py
```

`FARMERCHAT_DATA_PATH` remains supported as a legacy Crop-only override.

## Validation

Run the packaged automated checks from the activated virtual environment:

```powershell
python -m unittest discover -s tests -v
```

The integration checks execute all six pages in both modules against the full
packaged sources. They also check the module switch, livestock filters,
responsive UI contract, Plotly rendering paths, date exclusion, and raw-markup
regressions.

## Metric notes

- Total source occurrences are reconstructed from `query_duplicate_count`.
- Exact duplicates removed equal reconstructed occurrences minus retained
  approved query rows.
- Potential near duplicates are a conservative proxy based on case,
  punctuation, and whitespace normalization. They are review candidates, not
  confirmed duplicates.
- Incomplete records refer only to missing required core fields.
- Primary taxonomy blanks measure classification coverage and are not treated
  as missing core data.
- Livestock categories are not inferred. For example, cattle is not relabelled
  as dairy unless the approved source explicitly provides that value.
- The geographic page does not fabricate a choropleth. No authoritative Kenya
  county boundary file was supplied, and county metadata is incomplete.
- MAM and OND are calendar reference windows. External rainfall, outbreak,
  production, or market data would be required for causal conclusions.

## Troubleshooting

### `streamlit` is not recognized

Use:

```powershell
python -m streamlit run app.py
```

Confirm that `(.venv)` appears at the beginning of the PowerShell prompt.

### Dataset not found

Confirm that both approved CSV files remain inside the `data` folder and that
their names have not changed. Alternatively, use the module-specific
environment variables described above.

### The first load takes time

Both approved datasets are large. The first load of each module can take
several seconds. Streamlit caches deterministic preparation, so later filter
changes and module visits are faster.

### Port 8501 is already in use

```powershell
python -m streamlit run app.py --server.port 8502
```

Then open `http://localhost:8502`.
