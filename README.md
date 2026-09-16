# 🌾 Mandi-to-Market Supply Chain Optimizer

**TransOrg AgentIQ Datathon · Track 3 — AgriTech**

An executive dashboard + graph-first AI agent for a State Agriculture Board to
monitor daily mandi crop arrivals, track modal price vs MSP, and correlate
arrivals with weather.

## What's inside

```
├── data_raw/                 # original messy source files (untouched)
├── data_clean/                # cleaned, standardized CSVs (generated)
├── clean_data.py               # Data Rescue script — run this first
├── agent.py                    # Graph-first Agentic AI (rule-based NL → chart)
├── ml_insights.py               # Forecasting + mandi clustering (Advanced Insights tab)
├── app.py                      # Streamlit dashboard + chat UI
├── DATA_DICTIONARY.md          # column-by-column documentation
└── requirements.txt
```

## How to run

```bash
pip install -r requirements.txt
python clean_data.py      # rescues the 5 raw files into data_clean/
streamlit run app.py      # opens the dashboard at localhost:8501
```

## Data Rescue — what was fixed

- **Crop names**: English / Hindi / Punjabi spellings and case variants merged
  into 6 canonical crops (Wheat, Maize, Mustard, Cotton, Rice, Sugarcane).
- **Mandi IDs**: `MANDI001`, `MANDI-001`, `mandi_001`, `M001`, bare `"003"` →
  all standardized to `MANDI001` format.
- **Quantities**: Tonnes / Quintals / KG (including units embedded inside the
  value string itself) → converted to a single unit, Quintals.
- **Prices**: `₹`, `Rs.`, `INR`, commas, `/-` suffixes stripped → clean floats.
- **Distances**: miles → km.
- **Weather**: Fahrenheit → Celsius, inches → mm, UTC → IST.
- **Transit times**: recomputed from departure/arrival timestamps where
  possible; impossible (negative) values nulled rather than kept wrong.
- Full details + row-drop counts: see `DATA_DICTIONARY.md`.

## The Agentic Graph AI

The bonus chatbot is a **rule-based NL → chart engine**, not a paid LLM API call.
This was a deliberate choice:

1. The datathon FAQ explicitly says not to spend money on LLM API credits and
   points toward free/local options.
2. It has **zero network dependency** — it can't fail or time out live in front
   of judges.
3. For a bounded domain (6 crops, ~60 mandis, ~10 question types) a rule-based
   parser is more reliable and more explainable than a general LLM.

It extracts entities (crop, mandi, district, warehouse, date window) from the
question, routes to one of 9 intent handlers, and returns the right chart type
(line for trends, bar for rankings/comparisons, scatter for correlations,
histogram for distributions) plus a one-line text summary — satisfying the
"understands NL → picks correct chart → explains it" bonus criteria.

If a filtered date window has no matching rows (a real possibility on sparse
synthetic data), the agent automatically widens to the full available range
for that filter and says so, rather than silently returning an empty chart.

To swap in a real local LLM (e.g. Llama 3 via Ollama) instead of the rule-based
parser, replace `extract_entities()` in `agent.py` — the rest of the
query → chart pipeline is unchanged.

## Business metrics computed

- Total crop arrivals (Quintals)
- Average modal price vs MSP, and price-crash rate (modal price < MSP)
- Top mandis by arrival volume
- Average transit time by warehouse / mandi, and delay rate
- Crop-wise arrival distribution
- Rainfall–arrival correlation

## Advanced Insights — forecasting & clustering (`ml_insights.py`)

The **Advanced Insights** dashboard tab adds two real (fitted, not
hand-picked) models on top of the descriptive analytics above:

- **7-day forecast** (arrivals or modal price, any crop/mandi combo) — a
  linear trend + day-of-week seasonal adjustment, fit fresh on whichever
  filter you pick. Falls back to a flat recent-average forecast when a
  filter has too little history (< 10 days) for a trend to be meaningful,
  rather than fitting a model on 3 points and returning nonsense.
- **Mandi clustering** — KMeans (k=3) groups all mandis by average arrival
  volume, arrival volatility, average price, and price volatility, then
  labels each cluster in plain language (e.g. *"High-Volume · Volatile"*)
  instead of a bare cluster number, and shows a per-cluster summary table.

**Why scikit-learn (`LinearRegression` + `KMeans`) instead of
Prophet/ARIMA:** Prophet needs a C++ build toolchain to install — a real
risk to hit hours before a deadline, especially on Windows. ARIMA can fail
to converge (or throw convergence warnings) on the short, noisy
per-mandi-per-crop series in this dataset. scikit-learn was already a
dependency for clustering either way, so this adds zero new install risk
and is guaranteed to run the same way on every machine.

