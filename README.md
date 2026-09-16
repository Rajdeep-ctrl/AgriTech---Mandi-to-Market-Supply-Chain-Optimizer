
## 📌 Overview

**Agritech - Mandi-to-Market Supply Chain Optimizer** is a data-driven AgriTech solution designed to help Agriculture Boards monitor mandi-level crop prices, arrivals, MSP deviations, and weather-related patterns from a single platform.

The project transforms messy agricultural data into a clean, structured analytics layer and presents actionable insights through an interactive **Tableau dashboard**. Advanced analytics such as **price forecasting, mandi clustering, and anomaly detection** can further help identify hidden patterns in agricultural markets.

The core idea is simple:

**Raw Data → Data Cleaning → Analytics → Dashboard → Advanced Insights → AI Agent**

---

## 🎯 Problem Statement

Agriculture Boards may not have a unified view of:

- Which crops are being sold in which mandis
- How actual market prices compare with MSP
- Which mandis are experiencing unusual price fluctuations
- How crop arrivals change over time
- Whether rainfall or temperature affects arrivals
- Where potential supply shortages, excess arrivals, or unusual price movements are occurring

Our solution brings these signals together so that market conditions can be monitored and analyzed more efficiently.

---

## 💡 What We Built

The project follows a **4-layer architecture**:

### 1. Data Rescue & Cleaning
Raw and messy agricultural datasets are processed using Python and Pandas.

The cleaning pipeline handles:

- Crop-name standardization
- Hindi-to-English crop mapping
- Unit conversion to KG
- Date and timezone standardization
- Missing-value handling
- Duplicate removal
- Cleaning proof through before/after row counts

### 2. Analytics Layer
Clean data is converted into query-ready structured tables using SQL/Pandas.

Key metrics include:

- **Price Deviation %**
- **Daily Arrival Volume**
- **7-day / 30-day Moving Average**
- **Price Volatility**
- **Weather Correlation**

### 3. Interactive Tableau Dashboard
The analytics layer powers an executive-style Tableau dashboard containing:

- KPI cards
- Price vs MSP trend charts
- Mandi-wise arrival volume
- Weather vs arrival-volume scatter plots
- Crop filters
- Mandi filters
- Date-range filters
- Advanced insights such as forecasting and clustering

### 4. AI Text-to-Chart Agent *(Bonus)*
An optional AI layer allows users to ask questions in natural language.

Example:

> "Show me the wheat price trend in a mandi for the last 30 days."

The agent can:

1. Understand the user's query
2. Extract crop, mandi, metric, and time range
3. Generate/run an SQL query
4. Select an appropriate chart type
5. Render the visualization
6. Provide a short natural-language summary

---

## 📊 Key Analytics

### Price Deviation

```text
Price Deviation % = ((Actual Price - MSP) / MSP) × 100
```

This helps identify whether the actual market price is above or below MSP.

### Daily Arrival Volume

```text
Daily Arrival Volume = SUM(quantity_kg)
GROUP BY mandi, crop, date
```

### Moving Average

7-day and 30-day rolling averages are used to identify smoother price and arrival trends.

### Price Volatility

Rolling standard deviation is used to identify crops/mandis with greater price fluctuations.

### Weather Correlation

Correlation between arrival volume and weather variables such as rainfall and temperature is analyzed to identify potential relationships.

---

## 🔍 Advanced Insights

To move beyond basic descriptive analytics, the project includes/targets:

### 📈 Price Forecasting

Forecasting the next 7 days of crop prices for individual crops and mandis using approaches such as:

- Prophet
- ARIMA / statsmodels

### 🏪 Mandi Clustering

Mandis can be grouped based on their:

- Average price
- Price volatility
- Arrival volume

**K-Means clustering** can be used to identify groups such as stable or high-volatility market patterns.

### 🚨 Anomaly Detection

Unusual price spikes or drops can be flagged using a statistical rule based on:

```text
Mean ± 2 × Standard Deviation
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Data Cleaning | Python, Pandas, Jupyter Notebook |
| Data Storage | SQLite / DuckDB |
| Analytics | SQL, Pandas |
| Forecasting | Prophet / statsmodels |
| Clustering | scikit-learn K-Means |
| Dashboard | Tableau Desktop, Tableau Public |
| AI Agent | Python, LangChain, Groq / Ollama |
| Visualization | Plotly / Matplotlib |
| Version Control | Git & GitHub |
| Documentation | Markdown |

---

## 🗂️ Data Model

The analytics layer follows a simple fact/dimension model.

### `fact_arrivals`

| Column | Description |
|---|---|
| `date` | Date of crop arrival |
| `mandi_id` | Unique mandi identifier |
| `crop_id` | Unique crop identifier |
| `quantity_kg` | Arrival quantity in KG |
| `price` | Actual market price |
| `msp` | Minimum Support Price |

### `dim_mandi`

| Column | Description |
|---|---|
| `mandi_id` | Unique mandi identifier |
| `mandi_name` | Name of mandi |
| `state` | State |
| `district` | District |

### `dim_crop`

| Column | Description |
|---|---|
| `crop_id` | Unique crop identifier |
| `crop_name_en` | Crop name in English |
| `crop_name_hi` | Crop name in Hindi |

### `fact_weather`

| Column | Description |
|---|---|
| `date` | Weather observation date |
| `mandi_id` | Related mandi |
| `rainfall` | Rainfall measurement |
| `temp` | Temperature |
| `humidity` | Humidity |

For complete field-level definitions, see **`data_dictionary.md`**.

---

## 🧹 Data Cleaning Pipeline

The pipeline follows:

```text
Raw CSV
   ↓
Explore & Profile
   ↓
Standardize Crop Names
   ↓
Convert Units
   ↓
Fix Dates / Timezone
   ↓
Handle Missing Values
   ↓
Remove Duplicates
   ↓
Validate
   ↓
Clean Data
   ↓
SQLite / DuckDB
```

### Cleaning Principles

- Crop names are standardized using a mapping dictionary.
- Quantities are converted to KG.
- Original units can be retained for traceability.
- Dates are standardized to IST where applicable.
- Missing prices are handled through forward-fill as specified by the project pipeline.
- Missing arrivals are flagged rather than blindly dropped.
- Duplicate records are removed using mandi, crop, and date identifiers.
- Row counts are recorded to provide cleaning proof.

---

## 📁 Repository Structure

```text
agritech-datathon/
│
├── README.md
├── data_dictionary.md
│
├── data/
│   ├── raw/
│   └── cleaned/
│
├── notebooks/
│   └── data_cleaning.ipynb
│
├── src/
│   ├── clean_pipeline.py
│   ├── metrics.py
│   ├── forecasting.py
│   └── agent.py
│
├── dashboard/
│   └── tableau_workbook.twbx
│
└── demo/
    └── demo_video.mp4
```

---

## 🧩 Code Architecture

The project is designed to stay modular rather than putting everything into one large script.

### `clean_pipeline.py`
Handles data cleaning and preprocessing.

### `metrics.py`
Contains business metrics and analytical calculations.

### `forecasting.py`
Contains forecasting and advanced analytical models.

### `agent.py`
Handles the natural-language AI agent workflow.

### `notebooks/data_cleaning.ipynb`
Used for exploration, experimentation, validation, and demonstrating the cleaning process.

---

## 📈 Dashboard

The Tableau dashboard is designed as an executive monitoring interface.

### Main Dashboard Components

**KPIs**
- Average Price
- Total Arrivals
- MSP Deviation

**Visualizations**
- Price vs MSP over time
- Arrival volume by mandi
- Rainfall/temperature vs arrival volume
- Forecasted price trends
- Mandi clusters

**Filters**
- Crop
- Mandi
- Date Range

### Tableau Public

🔗 **Live Dashboard:** `ADD_TABLEAU_PUBLIC_LINK_HERE`

> Replace the placeholder above with the final Tableau Public URL before submission.

---

## 🤖 AI Agent Workflow

```text
User Question
     ↓
Natural Language Understanding
     ↓
Extract:
Crop + Mandi + Metric + Time Range
     ↓
Generate SQL
     ↓
Execute Query
     ↓
Choose Chart Type
     ↓
Render Chart
     ↓
Generate Text Summary
```

### Chart Selection Logic

| Query Type | Chart |
|---|---|
| Trend / Time Series | Line Chart |
| Category Comparison | Bar Chart |
| Correlation | Scatter Plot |

---

## 👥 Team Roles

| Role | Responsibility |
|---|---|
| Data Engineer | Data cleaning pipeline, data dictionary, cleaning proof |
| Analytics Lead | Metrics, SQL model, analytical layer |
| Dashboard Developer | Tableau dashboard and Tableau Public publishing |
| AI Agent + Documentation | AI agent, README, demo and documentation |

The team should cross-check the complete project before submission, especially the README and data dictionary.

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd agritech-datathon
```

### 2. Install Dependencies

```bash
pip install pandas jupyter scikit-learn statsmodels prophet
```

For the optional AI agent, install the required LangChain, LLM-provider, and visualization packages used by the implementation.

### 3. Add Data

Place source datasets inside:

```text
data/raw/
```

### 4. Run the Cleaning Pipeline

```bash
python src/clean_pipeline.py
```

### 5. Run Analytics

```bash
python src/metrics.py
```

### 6. Run Forecasting / Clustering

```bash
python src/forecasting.py
```

### 7. Open the Dashboard

Open the Tableau workbook from:

```text
dashboard/
```

Then publish the final dashboard to **Tableau Public**.

> Update the commands above if the final repository implementation uses different filenames or entry points.

---

## 📌 Expected Impact

The solution is intended to provide a unified view of mandi-level agricultural market conditions.

It can help users:

- Monitor crop prices against MSP
- Track crop arrival patterns
- Identify unusual price movements
- Compare mandi behavior
- Explore weather-arrival relationships
- Discover market clusters
- View short-term price forecasts
- Ask questions through a natural-language interface

---

## 🏆 Submission Checklist

- [ ] Public GitHub repository
- [ ] Clear `README.md`
- [ ] `data_dictionary.md`
- [ ] Cleaning proof with raw vs cleaned row counts
- [ ] Forecasting / clustering results
- [ ] Live Tableau Public dashboard
- [ ] Final presentation in PDF format
- [ ] 3–5 minute demo video
- [ ] Notebook comments/documentation

---

## 👨‍💻 Project

**AgriTech — Mandi-to-Market Supply Chain Optimizer**

**TransOrg AgentIQ Datathon 2026**

Built with Python, Pandas, SQL, Tableau and AI-assisted analytics.
"""

path = Path("/mnt/data/README.md")
path.write_text(readme, encoding="utf-8")
print(f"Created: {path}")
print(f"Size: {path.stat().st_size} bytes")
