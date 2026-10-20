# Data sources

## Main dataset
- **SignalConso** — DGCCRF (French Ministries of Economy and Finance)
- Page: <https://www.data.gouv.fr/datasets/signalconso>
- File: <https://www.data.gouv.fr/api/1/datasets/r/106add51-e925-4121-b0e4-81489c26a43f>
- Licence: Licence Ouverte / Open Licence (Etalab); reuse allowed with attribution.
- Columns used: `id`, `category`, `subcategories`, `Date`, `status`, `Signalement Transmis`,
  `Signalement Lu par l'entreprise`, `Signalement ayant reçu une réponse`, `dep_code`, `dep_name`.

## Reference files (hand-maintained)
- `data/reference/departments.csv`: 101 départements with region, approximate centroid and **approximate
  population in thousands**. Replace the population with the official INSEE legal population before
  publishing precise rates.
- `data/reference/labels_en.csv`: English labels for sector and status codes (our translation). Codes not
  listed get an automatic label and are flagged in the "Data & limits" tab.

## Cleaning rules
Unreadable dates, dates before Nov 2018 and future dates are removed; duplicated ids are removed (first
kept); blank sector becomes "Unspecified"; unknown département becomes "Unlocated".
