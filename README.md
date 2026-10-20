# SignalConso — What happens when consumers report a problem?

**#EFREIDataStories2026 · Individual Streamlit data-storytelling project**
Author: Fares Mimita · Student ID: 20231244 · Class: ING2 BIA

An interactive dashboard on **SignalConso**, the French platform where consumers report problems with
businesses (scams, unfair practices, poor service). It follows a story: *hook → context → key insights →
implications and next steps*, and adds two interactive features built from the analysis.

## The story (8 tabs)

| Tab | Role in the narrative | What it answers |
|---|---|---|
| 1 · Context | Hook and framing | Why this matters, who it is for, key definitions |
| 2 · What | Insight | Which sectors dominate? Is volume growing? Drill-down into one sector and its reasons |
| 3 · When | Insight | Is there seasonality? Which sectors peak in which month? |
| 4 · Where | Insight | Which départements report most, per 100,000 residents? |
| 5 · Then what? | Insight + **Extra 1** | How many reports are forwarded, read, answered? What if more got an answer? |
| 6 · Your check | **Extra 2** | A personal view: compare your département and sector with France |
| 7 · Data & limits | Transparency | Cleaning steps, validation checks, biases and limits |
| 8 · Takeaways | Implications | Computed conclusions, recommendations, next steps, downloadable summary |

### The two extras
1. **Reply-gap simulator** (tab 5): set a target for each funnel step (forwarded → read → answered) and see
   how many more reports per year would end with a reply.
2. **"Your check"** (tab 6): pick a département and a sector and see the local rank per head of population,
   the local reply rate against France, the local sector mix and the best period to be vigilant.

## Data

- **Dataset:** SignalConso — DGCCRF, French Ministries of Economy and Finance
- **Portal:** data.gouv.fr — <https://www.data.gouv.fr/datasets/signalconso>
- **Licence:** Licence Ouverte / Open Licence (Etalab)
- **Coverage:** consumer reports since November 2018, updated daily.
- **Reference files** (in `data/reference/`): `departments.csv` (names, regions, approximate centroids and
  rounded population) and `labels_en.csv` (English labels for source codes). See `docs/DATA_SOURCES.md`.

Only aggregates (month × sector × département) are kept by the app: no personal data, no company names.

## Run it locally

Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/download_data.py      # or copy the CSV to data/raw/signalconso.csv
python scripts/build_data.py         # cleans the CSV, writes data/processed/ (a few minutes)
streamlit run app.py
```
macOS/Linux: same commands, with `source .venv/bin/activate`. Shortcuts are in the `Makefile`.

`build_data.py` prints the columns it found, the cleaning summary and the category codes that still lack
an English label (add them to `data/reference/labels_en.csv`).

## Deploy (Streamlit Community Cloud)

1. Run `build_data.py` locally, then commit **`data/processed/`** (a few hundred KB). The raw CSV stays out
   of the repository (`.gitignore`).
2. Push to GitHub, create a new app on <https://share.streamlit.io>, main file `app.py`.
3. The deployed app starts from the processed files only; it never needs the 280 MB CSV.

## Project layout

```
app.py                 page layout, sidebar filters, KPIs, tabs
core/                  logic (no Streamlit code except in ui/store helpers)
  config.py            constants and paths        schema.py   column detection
  pipeline.py          chunked cleaning + aggregation   labels.py / geo.py   English labels, départements
  store.py             download, parquet files    metrics.py  all computations
  charts.py            Plotly figures             ui.py / context.py   formatting, shared state
sections/              one file per tab
scripts/               download_data.py, build_data.py
data/reference/        small hand-maintained lookups     data/processed/   generated, committed
tests/                 pytest + Streamlit AppTest (synthetic data)
docs/                  STORYBOARD.md, DEMO_SCRIPT.md, DATA_SOURCES.md
```

Run the tests with `pip install -r requirements-dev.txt` then `python -m pytest`.

## How it maps to the grading criteria

| Criterion | Where |
|---|---|
| Narrative & framing | Tabs 1 and 8, "key message" line under every tab title, `docs/STORYBOARD.md` |
| Data work | Chunked cleaning (invalid, future, pre-launch dates, duplicates, blanks), validation table, seasonality on complete years only, per-capita rates |
| Visualization & UX | Colour-blind-safe palette, titled axes with units, text description under each chart, sidebar filters, two interactive extras |
| Engineering | Modular code, cached loading, runs from small processed files, automated tests |
| Communication | This README, in-app "Data & limits", `docs/DEMO_SCRIPT.md` |

## Limitations (also shown in the app)

- A report is a claim, not proven fraud; more reports can also mean a better-known platform.
- Reporters are not a random sample of consumers.
- Sector classification changed over time, which affects year-to-year comparisons by sector.
- Per-capita rates use rounded population figures; map bubbles use approximate centroids.
- English labels for source codes are our own translations; reasons are left in French.
- Nothing here establishes causes.
