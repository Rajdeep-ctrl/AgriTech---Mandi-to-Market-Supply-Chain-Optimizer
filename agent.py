"""
agent.py
========
Graph-first Agentic AI for the Mandi-to-Market dashboard.

Design choice: a deterministic, rule-based NL -> (intent, entities) parser
instead of a paid LLM API. Why:
  - The datathon rules explicitly say NOT to spend money on LLM API credits.
  - It has zero network dependency, so it never breaks during a live demo/judging.
  - For a bounded domain (6 crops, ~60 mandis, a handful of question types)
    a rule-based parser is *more* reliable than a general LLM, and is fully
    explainable to judges.

Swap-in note: if you want a true LLM in the loop, replace `extract_entities()`
below with a call to a local model via Ollama (e.g. `llama3`) using the same
prompt->JSON contract. The rest of the pipeline (query -> chart) is unchanged.
"""

import re
import calendar
from datetime import timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

CROPS = ["Wheat", "Maize", "Mustard", "Cotton", "Rice", "Sugarcane"]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

class MandiData:
    def __init__(self, clean_dir="data_clean"):
        self.arrivals = pd.read_csv(f"{clean_dir}/mandi_arrivals.csv", parse_dates=["date"], encoding="utf-8")
        self.prices = pd.read_csv(f"{clean_dir}/price_and_msp.csv", parse_dates=["date"], encoding="utf-8")
        self.transport = pd.read_csv(
            f"{clean_dir}/transport_logistics.csv",
            parse_dates=["departure_time", "arrival_time"],
            encoding="utf-8",
        )
        self.weather = pd.read_csv(f"{clean_dir}/weather_sensors.csv", parse_dates=["date"], encoding="utf-8")
        self.master = pd.read_csv(f"{clean_dir}/mandi_master.csv", encoding="utf-8")

        # Each source file has its own date coverage in the synthetic data,
        # so windows are computed relative to *that table's* latest date —
        # not a single global date — otherwise a 'last 30 days' filter on a
        # table that ends earlier than the others silently returns nothing.
        self.max_date = self.arrivals["date"].max()
        self.max_date_prices = self.prices["date"].max()
        self.max_date_weather = self.weather["date"].max()
        self.mandi_names = dict(zip(self.master["mandi_id"], self.master["mandi_name"]))
        self.name_to_id = {v.lower(): k for k, v in self.mandi_names.items()}
        self.districts = set(self.master["district"].dropna().str.lower())


# ---------------------------------------------------------------------------
# Entity extraction
# ---------------------------------------------------------------------------

def extract_entities(query, data: MandiData):
    q = query.lower()
    ent = {"crop": None, "mandi_id": None, "district": None, "warehouse": None,
           "days": None, "months": None}

    for crop in CROPS:
        if crop.lower() in q:
            ent["crop"] = crop
            break

    for name_lower, mandi_id in data.name_to_id.items():
        if name_lower in q:
            ent["mandi_id"] = mandi_id
            break
    m = re.search(r"\b(mandi\s?-?\s?\d{1,3})\b", q)
    if m and not ent["mandi_id"]:
        digits = re.sub(r"\D", "", m.group(1))
        ent["mandi_id"] = f"MANDI{int(digits):03d}"

    for district in data.districts:
        if district in q:
            ent["district"] = district.title()
            break

    wh = re.search(r"\bwh-?(north|south|east|west|central)\b", q)
    if wh:
        ent["warehouse"] = f"WH-{wh.group(1).title()}"
    if "export" in q and "terminal" in q:
        ent["warehouse"] = "Export-Terminal"

    m = re.search(r"last (\d+)\s*day", q)
    if m:
        ent["days"] = int(m.group(1))
    m = re.search(r"last (\d+)\s*month", q)
    if m:
        ent["months"] = int(m.group(1))
    if ent["days"] is None and ent["months"] is None:
        ent["days"] = 30  # sensible default window

    return ent


def date_window(data: MandiData, ent, end=None):
    end = end if end is not None else data.max_date
    if ent["months"]:
        start = end - pd.DateOffset(months=ent["months"])
    else:
        start = end - timedelta(days=ent["days"] or 30)
    return start, end


# ---------------------------------------------------------------------------
# Intent routing -> each returns (plotly_figure, summary_text)
# ---------------------------------------------------------------------------

def _apply_filters(df, ent, mandi_col="mandi_id", district_col="district", crop_col="crop_name"):
    if ent.get("crop"):
        df = df[df[crop_col] == ent["crop"]]
    if ent.get("mandi_id"):
        df = df[df[mandi_col] == ent["mandi_id"]]
    if ent.get("district"):
        df = df[df[district_col].str.lower() == ent["district"].lower()]
    return df


def intent_arrival_trend(query, data, ent):
    start, end = date_window(data, ent)
    filtered_all = _apply_filters(data.arrivals, ent)
    df = filtered_all[(filtered_all["date"] >= start) & (filtered_all["date"] <= end)]
    widened = False
    if df.empty and not filtered_all.empty:
        df = filtered_all
        start, end = df["date"].min(), df["date"].max()
        widened = True

    daily = df.groupby("date", as_index=False)["arrival_qty_qtl"].sum()
    title_bits = [b for b in [ent["crop"], data.mandi_names.get(ent["mandi_id"]), ent["district"]] if b]
    title = "Daily arrivals" + (f" — {', '.join(title_bits)}" if title_bits else "")

    fig = px.line(daily, x="date", y="arrival_qty_qtl", markers=True, title=title,
                   labels={"arrival_qty_qtl": "Arrivals (Quintals)", "date": "Date"})

    total = daily["arrival_qty_qtl"].sum()
    avg = daily["arrival_qty_qtl"].mean() if len(daily) else 0
    note = " (no data in the requested window — showing the full range available for this filter instead.)" if widened else ""
    summary = (f"Over {len(daily)} days ({start.date()} to {end.date()}), total arrivals were "
               f"{total:,.1f} quintals, averaging {avg:,.1f} quintals/day.{note}"
               if len(daily) else "No matching arrival data found for this filter.")
    return fig, summary


def intent_price_vs_msp(query, data, ent):
    start, end = date_window(data, ent, end=data.max_date_prices)
    filtered_all = _apply_filters(data.prices, ent)
    df = filtered_all[(filtered_all["date"] >= start) & (filtered_all["date"] <= end)]
    widened = False
    if df.empty and not filtered_all.empty:
        df = filtered_all
        start, end = df["date"].min(), df["date"].max()
        widened = True

    daily = df.groupby("date", as_index=False)[["modal_price", "msp"]].mean()
    title_bits = [b for b in [ent["crop"], data.mandi_names.get(ent["mandi_id"]), ent["district"]] if b]
    title = "Modal price vs MSP" + (f" — {', '.join(title_bits)}" if title_bits else "")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily["date"], y=daily["modal_price"], mode="lines+markers",
                              name="Modal Price"))
    fig.add_trace(go.Scatter(x=daily["date"], y=daily["msp"], mode="lines", name="MSP",
                              line=dict(dash="dash")))
    fig.update_layout(title=title, xaxis_title="Date", yaxis_title="Price (₹/Quintal)")

    below = (daily["modal_price"] < daily["msp"]).sum()
    note = " (no data in the requested window — showing the full range available for this filter instead.)" if widened else ""
    summary = (f"Across {len(daily)} days, price was below MSP on {below} day(s). "
               f"Average modal price: ₹{daily['modal_price'].mean():,.0f}, average MSP: "
               f"₹{daily['msp'].mean():,.0f}.{note}" if len(daily) else "No matching price data found for this filter.")
    return fig, summary


def intent_below_msp(query, data, ent):
    start, end = date_window(data, ent, end=data.max_date_prices)
    df = data.prices[(data.prices["date"] >= start) & (data.prices["date"] <= end)]
    if ent["crop"]:
        df = df[df["crop_name"] == ent["crop"]]
    # below_msp round-trips through CSV as float (1.0 / 0.0 / NaN, since NaN
    # means "MSP unknown" — see clean_data.py). Compare to 1 rather than using
    # it directly as a boolean mask: NaN would otherwise make pandas treat
    # this as column selection instead of row filtering.
    crashes = df[df["below_msp"] == 1]
    by_mandi = crashes.groupby("mandi_id", as_index=False).size().sort_values("size", ascending=False).head(15)
    by_mandi["mandi_name"] = by_mandi["mandi_id"].map(data.mandi_names)

    fig = px.bar(by_mandi, x="mandi_name", y="size", title="Mandis with price-crash instances (Price < MSP)",
                 labels={"size": "Number of below-MSP records", "mandi_name": "Mandi"})
    fig.update_xaxes(tickangle=45)

    summary = (f"{len(crashes)} price-crash records found (modal price below MSP) "
               f"across {by_mandi.shape[0]} mandis in the selected window."
               if len(crashes) else "No price-crash instances found for this filter.")
    return fig, summary


def intent_transit_delay(query, data, ent):
    df = data.transport.copy()
    if ent["mandi_id"]:
        df = df[df["mandi_id"] == ent["mandi_id"]]
    if ent["warehouse"]:
        df = df[df["destination_warehouse"] == ent["warehouse"]]

    if "warehouse" in query.lower() or ent["warehouse"] or not ent["mandi_id"]:
        grp = df.groupby("destination_warehouse", as_index=False)["transit_hours"].mean()
        fig = px.bar(grp, x="destination_warehouse", y="transit_hours",
                     title="Average transit time by warehouse",
                     labels={"transit_hours": "Avg transit time (hrs)", "destination_warehouse": "Warehouse"})
        summary = (f"Average transit time ranges from {grp['transit_hours'].min():,.1f} to "
                   f"{grp['transit_hours'].max():,.1f} hours across warehouses."
                   if len(grp) else "No transport data found.")
    else:
        grp = df.groupby("mandi_id", as_index=False)["transit_hours"].mean()
        grp["mandi_name"] = grp["mandi_id"].map(data.mandi_names)
        fig = px.bar(grp.sort_values("transit_hours", ascending=False).head(15),
                     x="mandi_name", y="transit_hours", title="Average transit time by mandi",
                     labels={"transit_hours": "Avg transit time (hrs)", "mandi_name": "Mandi"})
        fig.update_xaxes(tickangle=45)
        summary = f"Average transit time computed across {len(grp)} mandis."
    return fig, summary


def intent_rainfall_correlation(query, data, ent):
    common_end = min(data.max_date, data.max_date_weather)
    start, end = date_window(data, ent, end=common_end)
    arr = data.arrivals[(data.arrivals["date"] >= start) & (data.arrivals["date"] <= end)]
    daily_arr = arr.groupby("date", as_index=False)["arrival_qty_qtl"].sum()

    rain = data.weather[(data.weather["date"] >= start) & (data.weather["date"] <= end)]
    daily_rain = rain.groupby("date", as_index=False)["rainfall_mm"].sum()

    merged = pd.merge(daily_arr, daily_rain, on="date", how="inner")
    corr = merged["arrival_qty_qtl"].corr(merged["rainfall_mm"]) if len(merged) > 2 else None

    fig = px.scatter(merged, x="rainfall_mm", y="arrival_qty_qtl", trendline="ols" if len(merged) > 2 else None,
                      title="Rainfall vs crop arrivals",
                      labels={"rainfall_mm": "Total daily rainfall (mm)", "arrival_qty_qtl": "Arrivals (Quintals)"})

    if corr is not None:
        direction = "negative (more rain, fewer arrivals)" if corr < 0 else "positive (more rain, more arrivals)"
        summary = f"Correlation coefficient between rainfall and arrivals is {corr:.2f} — a {direction} relationship."
    else:
        summary = "Not enough overlapping data points to compute a reliable correlation."
    return fig, summary


def intent_rainfall_trend(query, data, ent):
    """Weather sensors aren't individually mapped to a district in the source
    data, so a true 'by district' breakdown isn't recoverable — the agent is
    explicit about that instead of fabricating a mapping, and shows the
    overall rainfall trend for the requested window."""
    start, end = date_window(data, ent, end=data.max_date_weather)
    df = data.weather[(data.weather["date"] >= start) & (data.weather["date"] <= end)]
    daily = df.groupby("date", as_index=False)["rainfall_mm"].sum()

    fig = px.line(daily, x="date", y="rainfall_mm", markers=True, title="Total daily rainfall (all sensors)",
                   labels={"rainfall_mm": "Rainfall (mm)", "date": "Date"})

    summary = ("Note: sensors aren't individually mapped to districts in the source data, "
               "so this shows the aggregate rainfall trend across all sensors. "
               f"Total rainfall over {len(daily)} days: {daily['rainfall_mm'].sum():,.0f} mm."
               if len(daily) else "No matching weather data found.")
    return fig, summary


def intent_top_mandis(query, data, ent):
    start, end = date_window(data, ent)
    df = data.arrivals[(data.arrivals["date"] >= start) & (data.arrivals["date"] <= end)]
    if ent["crop"]:
        df = df[df["crop_name"] == ent["crop"]]
    grp = df.groupby("mandi_id", as_index=False)["arrival_qty_qtl"].sum()
    grp["mandi_name"] = grp["mandi_id"].map(data.mandi_names)
    grp = grp.sort_values("arrival_qty_qtl", ascending=False).head(5)

    fig = px.bar(grp, x="mandi_name", y="arrival_qty_qtl", title="Top 5 mandis by arrival volume",
                 labels={"arrival_qty_qtl": "Total arrivals (Quintals)", "mandi_name": "Mandi"})
    fig.update_xaxes(tickangle=30)

    summary = (f"Top mandi is {grp.iloc[0]['mandi_name']} with {grp.iloc[0]['arrival_qty_qtl']:,.0f} quintals."
               if len(grp) else "No arrival data found.")
    return fig, summary


def intent_arrivals_by_crop(query, data, ent):
    start, end = date_window(data, ent)
    df = data.arrivals[(data.arrivals["date"] >= start) & (data.arrivals["date"] <= end)]
    grp = df.groupby("crop_name", as_index=False)["arrival_qty_qtl"].sum().sort_values(
        "arrival_qty_qtl", ascending=False)

    fig = px.bar(grp, x="crop_name", y="arrival_qty_qtl", title="Total arrivals by crop",
                 labels={"arrival_qty_qtl": "Total arrivals (Quintals)", "crop_name": "Crop"})

    summary = (f"{grp.iloc[0]['crop_name']} leads with {grp.iloc[0]['arrival_qty_qtl']:,.0f} quintals."
               if len(grp) else "No arrival data found.")
    return fig, summary


def intent_price_distribution(query, data, ent):
    start, end = date_window(data, ent, end=data.max_date_prices)
    df = data.prices[(data.prices["date"] >= start) & (data.prices["date"] <= end)]
    if ent["crop"]:
        df = df[df["crop_name"] == ent["crop"]]

    fig = px.histogram(df, x="modal_price", nbins=30,
                        title=f"Distribution of wholesale (modal) prices"
                              + (f" — {ent['crop']}" if ent["crop"] else ""),
                        labels={"modal_price": "Modal price (₹/Quintal)"})

    summary = (f"Prices range from ₹{df['modal_price'].min():,.0f} to ₹{df['modal_price'].max():,.0f}, "
               f"median ₹{df['modal_price'].median():,.0f}." if len(df) else "No matching price data found.")
    return fig, summary


def intent_warehouse_volume(query, data, ent):
    df = data.transport.copy()
    grp = df.groupby("destination_warehouse", as_index=False).size().sort_values("size", ascending=False)
    fig = px.bar(grp, x="destination_warehouse", y="size", title="Trips received by warehouse",
                 labels={"size": "Number of trips", "destination_warehouse": "Warehouse"})
    summary = (f"{grp.iloc[0]['destination_warehouse']} receives the most trips ({grp.iloc[0]['size']})."
               if len(grp) else "No transport data found.")
    return fig, summary


# ---------------------------------------------------------------------------
# Intent detection (ordered — first match wins)
# ---------------------------------------------------------------------------

INTENTS = [
    (r"below\s*msp|price\s*crash", intent_below_msp),
    (r"\bvs\b.*msp|price.*msp|msp.*price", intent_price_vs_msp),
    (r"distribut", intent_price_distribution),
    (r"rainfall.*correlat|correlat.*rainfall|weather.*(impact|arrival)|rain.*arrival", intent_rainfall_correlation),
    (r"rainfall.*district|compare.*rainfall|total\s*rainfall", intent_rainfall_trend),
    (r"top\s*\d*\s*mandi", intent_top_mandis),
    (r"arrivals?\s*by\s*crop|total\s*arrivals?.*crop|crop.?wise", intent_arrivals_by_crop),
    (r"warehouse.*(receiv|volume|highest)", intent_warehouse_volume),
    (r"transit|delay", intent_transit_delay),
    (r"arrival.*trend|daily\s*arrival|plot.*arrival|arrival.*plot", intent_arrival_trend),
]


def answer(query: str, data: MandiData):
    """Main agent entrypoint: NL query -> (plotly figure, text summary, intent name)."""
    q = query.lower().strip()
    ent = extract_entities(q, data)

    for pattern, fn in INTENTS:
        if re.search(pattern, q):
            fig, summary = fn(q, data, ent)
            return fig, summary, fn.__name__

    # fallback: default to arrival trend so the agent always returns *something*
    fig, summary = intent_arrival_trend(q, data, ent)
    summary = ("I wasn't fully sure what you meant, so here's the arrival trend "
               "for your filters as a default view. Try asking about price vs MSP, "
               "top mandis, transit delays, or rainfall correlation.") + " " + summary
    return fig, summary, "fallback_arrival_trend"
