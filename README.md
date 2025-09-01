# WEFE Nexus DSS: Policy & Intervention Simulator

A modular Streamlit application for exploring water–energy–food–ecosystems (WEFE) policies and interventions on Living Labs.

## Project Structure

```
trans-sahara-prototype-deployment/
├── app.py                          # Main Streamlit entry point
├── requirements.txt                # Python dependencies
├── assets/                         # Images and static assets
│   └── *.jpg
├── data/
│   ├── policies.json               # Policy catalogue
│   ├── pillars.json                # Pillar/indicator definitions (names, units, bounds)
│   ├── livinglab.json              # Living Lab data (scores/values per indicator)
│   └── interventions/              # Intervention definitions used by simulation
│       └── *_intervention.json
└── src/
    ├── core/
    │   ├── data_loader.py          # Low-level data loading helpers
    │   ├── intervention_optimizer.py# Policy simulation / intervention selection
    │   └── wefe_calculations.py    # Scoring, normalization, utilities
    ├── pages/
    │   ├── initial_page.py         # Welcome view, Living Lab details, pillar visuals
    │   ├── policy_tab.py           # Policy list, selection, indicator search
    │   └── intervention_tab.py     # Selected interventions summary
    └── policy/
        ├── data.py                 # Policy data helpers and indicator utilities
        ├── ui.py                   # Policy UI widgets and indicator impact table
        └── visualization.py        # Heatmaps and scoring visuals
```

## Key Features

- Indicator numbering across the app:
  - Living Lab indicator lists (in `initial_page.py`)
  - Policy impact table (in `policy/ui.py`)
  - Policy search by indicator (in `pages/policy_tab.py`)
  - Heatmaps (in `policy/visualization.py`) show numbered rows and numbers in hover text
- Search by indicator (Policy tab):
  - Toggle "Search by Indicator" to switch from category filter to an indicator dropdown
  - Indicators are listed with numbers (e.g., `03. basic_drinking_water_services`)
  - Results show policies that improve the selected indicator
  - Policies are ordered by improvement magnitude (ascending)
- WEFE score comparison gauges and before/after heatmaps
- Simulation pipeline that maps policy choices to recommended interventions

## How Indicator Numbering Works

- Indicator metadata is sourced from `data/pillars.json`.
- A consistent numbering map is built at runtime and applied wherever indicators are displayed.
- Example display: `07. renewable_electricity_output`.

## Run Locally

1) Install dependencies:
```bash
pip install -r requirements.txt
```

2) Launch the app:
```bash
streamlit run app.py
```

## Usage Tips

- Start on the initial page: select a Living Lab and review pillar indicators (now numbered).
- Open the Policy tab:
  - Use category filter or enable "Search by Indicator" to find policies improving a specific indicator.
  - Add policies to your selection; the impact table shows numbered indicators with improvements.
  - Run the simulation to produce recommended interventions.
- Heatmaps: numbered indicator rows with hover text showing the indicator number and name.

## Code Pointers

- Indicator numbering utilities: `src/policy/data.py`
- Search-by-indicator logic and sorting: `src/policy/data.py` and `src/pages/policy_tab.py`
- Living Lab indicator display: `src/pages/initial_page.py`
- Policy impact table: `src/policy/ui.py`
- Heatmaps: `src/policy/visualization.py`

## Data Files

- `data/pillars.json`: Definitions for indicators (names, units, min/max), grouped by pillar and category
- `data/livinglab.json`: Living Lab entries and indicator values
- `data/policies.json`: Policies with synergies/trade-offs and affected indicators
- `data/interventions/*.json`: Intervention definitions used by the optimizer

## Requirements

- Python 3.10+
- Streamlit-compatible environment (browser access to the local server) 