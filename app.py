"""
app.py
======
Mandi-to-Market Supply Chain Optimizer — Executive Dashboard + Agentic AI chat.

Run:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from agent import MandiData, answer, CROPS
from theme import inject_css, styled_fig, INTENT_ACCENT, INTENT_LABEL, GOLD, TEAL, RUST
from ml_insights import forecast_series, cluster_mandis

st.set_page_config(page_title="Mandi-to-Market Optimizer", layout="wide", page_icon="\U0001F33E")
st.markdown(inject_css(), unsafe_allow_html=True)


@st.cache_resource
def load_data():
    return MandiData("data_clean")


data = load_data()

total_arrivals_all = data.arrivals["arrival_qty_qtl"].sum()
mandi_count = data.master["mandi_id"].nunique()

st.markdown(f"""
<div class="ledger-hero">
    <h1>{total_arrivals_all:,.0f} quintals <span class="stat">moved</span> through {mandi_count} mandis this season</h1>
    <p>Mandi-to-Market Supply Chain Optimizer &mdash; TransOrg AgentIQ Datathon, Track 3 (AgriTech)</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar filters — shared across the Executive Dashboard tab
# ---------------------------------------------------------------------------
st.sidebar.markdown("### Filters")
crop_filter = st.sidebar.selectbox("Crop", ["All"] + CROPS)

district_options = ["All"] + sorted(data.master["district"].dropna().unique().tolist())
district_filter = st.sidebar.selectbox("District", district_options)

mandi_name_options = ["All"] + sorted(data.master["mandi_name"].dropna().unique().tolist())
mandi_filter = st.sidebar.selectbox("Mandi", mandi_name_options)
mandi_id_filter = data.name_to_id.get(mandi_filter.lower()) if mandi_filter != "All" else None

data_min_date = data.arrivals["date"].min().date()
data_max_date = data.arrivals["date"].max().date()
picked_range = st.sidebar.date_input(
    "Date Range",
    value=(data_min_date, data_max_date),
    min_value=data_min_date,
    max_value=data_max_date,
)
if isinstance(picked_range, tuple) and len(picked_range) == 2:
    range_start, range_end = picked_range
else:
    # Streamlit returns a single date while the user is mid-pick; fall back
    # to the full range rather than erroring on an incomplete selection.
    range_start, range_end = data_min_date, data_max_date
range_start, range_end = pd.Timestamp(range_start), pd.Timestamp(range_end)


def apply_filters(arr_df, prc_df, start, end):
    a, p = arr_df.copy(), prc_df.copy()
    if crop_filter != "All":
        a = a[a["crop_name"] == crop_filter]
        p = p[p["crop_name"] == crop_filter]
    if district_filter != "All":
        a = a[a["district"] == district_filter]
        p = p[p["district"] == district_filter]
    if mandi_id_filter:
        a = a[a["mandi_id"] == mandi_id_filter]
        p = p[p["mandi_id"] == mandi_id_filter]
    a = a[(a["date"] >= start) & (a["date"] <= end)]
    p = p[(p["date"] >= start) & (p["date"] <= end)]
    return a, p


def compute_kpis(a, p):
    return {
        "arrivals": a["arrival_qty_qtl"].sum(),
        "avg_price": p["modal_price"].mean(),
        "avg_msp": p["msp"].mean(),
        "crash_rate": p["below_msp"].mean() * 100 if len(p) else float("nan"),
    }


def delta_html(current, previous, higher_is_better=True):
    """Small HTML snippet: up/down arrow + % change vs the prior period of
    equal length. Shows 'n/a' when there's nothing to compare against."""
    if pd.isna(current) or pd.isna(previous) or previous == 0:
        return '<div class="kpi-delta flat">vs prior period: n/a</div>'
    change = (current - previous) / abs(previous) * 100
    good = (change >= 0) == higher_is_better
    cls = "flat" if abs(change) < 0.5 else ("up" if good else "down")
    arrow_sym = "\u2013" if cls == "flat" else ("\u25b2" if change >= 0 else "\u25bc")
    return f'<div class="kpi-delta {cls}">{arrow_sym} {abs(change):.1f}% vs prior period</div>'


tab_dashboard, tab_compare, tab_insights, tab_agent = st.tabs(
    ["Executive Dashboard", "Compare Mandis", "Advanced Insights", "Ask the Field Agent"]
)

# ---------------------------------------------------------------------------
# TAB 1 — Executive Dashboard
# ---------------------------------------------------------------------------
with tab_dashboard:
    arr, prc = apply_filters(data.arrivals, data.prices, range_start, range_end)

    # Previous period = same length, immediately preceding the selected window.
    window_len = range_end - range_start
    prev_end = range_start - pd.Timedelta(days=1)
    prev_start = prev_end - window_len
    prev_arr, prev_prc = apply_filters(data.arrivals, data.prices, prev_start, prev_end)

    cur = compute_kpis(arr, prc)
    prev = compute_kpis(prev_arr, prev_prc)
    crash_class = "alert" if pd.notna(cur["crash_rate"]) and cur["crash_rate"] > 15 else ""

    st.markdown(f"""
    <div class="kpi-strip">
        <div class="kpi-item">
            <div class="kpi-label">TOTAL ARRIVALS</div>
            <div class="kpi-value">{cur['arrivals']:,.0f} <span style="font-size:1rem;color:{TEAL};">Qtl</span></div>
            {delta_html(cur['arrivals'], prev['arrivals'], higher_is_better=True)}
        </div>
        <div class="kpi-item">
            <div class="kpi-label">AVG MODAL PRICE</div>
            <div class="kpi-value">{'₹' + format(cur['avg_price'], ',.0f') if pd.notna(cur['avg_price']) else '—'}</div>
            {delta_html(cur['avg_price'], prev['avg_price'], higher_is_better=True)}
        </div>
        <div class="kpi-item">
            <div class="kpi-label">AVG MSP</div>
            <div class="kpi-value">{'₹' + format(cur['avg_msp'], ',.0f') if pd.notna(cur['avg_msp']) else '—'}</div>
            {delta_html(cur['avg_msp'], prev['avg_msp'], higher_is_better=True)}
        </div>
        <div class="kpi-item">
            <div class="kpi-label">PRICE-CRASH RATE</div>
            <div class="kpi-value {crash_class}">{cur['crash_rate']:.1f}%</div>
            {delta_html(cur['crash_rate'], prev['crash_rate'], higher_is_better=False)}
        </div>
    </div>
    <p style="font-size:0.78rem;color:#B8AA9C;margin-top:-0.6rem;">
        vs. prior {window_len.days + 1}-day period ({prev_start.date()} to {prev_end.date()})
    </p>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="ledger-section-title">Daily arrival trend</div>', unsafe_allow_html=True)
        daily_arr = arr.groupby("date", as_index=False)["arrival_qty_qtl"].sum()
        fig = px.line(daily_arr, x="date", y="arrival_qty_qtl",
                       labels={"arrival_qty_qtl": "Quintals"})
        fig.update_traces(line_color=GOLD)
        st.plotly_chart(styled_fig(fig), use_container_width=True)

    with col2:
        st.markdown('<div class="ledger-section-title">Crop-wise arrival distribution</div>', unsafe_allow_html=True)
        # Uses the same filtered `arr` as the rest of the tab (previously this
        # chart silently ignored the sidebar filters and always showed
        # everything — fixed so every chart on the tab tells one consistent
        # story for the selected filters).
        crop_totals = arr.groupby("crop_name", as_index=False)["arrival_qty_qtl"].sum()
        fig = px.pie(crop_totals, names="crop_name", values="arrival_qty_qtl", hole=0.45)
        st.plotly_chart(styled_fig(fig), use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown('<div class="ledger-section-title">Top 10 mandis by arrival volume</div>', unsafe_allow_html=True)
        top_mandis = arr.groupby("mandi_id", as_index=False)["arrival_qty_qtl"].sum()
        top_mandis["mandi_name"] = top_mandis["mandi_id"].map(data.mandi_names)
        top_mandis = top_mandis.sort_values("arrival_qty_qtl", ascending=False).head(10)
        fig = px.bar(top_mandis, x="mandi_name", y="arrival_qty_qtl")
        fig.update_traces(marker_color=TEAL)
        fig.update_xaxes(tickangle=30, title=None)
        fig.update_yaxes(title="Quintals")
        st.plotly_chart(styled_fig(fig), use_container_width=True)

    with col4:
        st.markdown('<div class="ledger-section-title">Avg transit time by warehouse</div>', unsafe_allow_html=True)
        transport_f = data.transport.copy()
        if mandi_id_filter:
            transport_f = transport_f[transport_f["mandi_id"] == mandi_id_filter]
        wh = transport_f.groupby("destination_warehouse", as_index=False)["transit_hours"].mean()
        fig = px.bar(wh, x="destination_warehouse", y="transit_hours")
        fig.update_traces(marker_color=GOLD)
        fig.update_xaxes(title=None)
        fig.update_yaxes(title="Hours")
        st.plotly_chart(styled_fig(fig), use_container_width=True)

    st.markdown('<div class="ledger-section-title">Road connectivity — transit delay rate</div>', unsafe_allow_html=True)
    transport_delay = data.transport.copy()
    if mandi_id_filter:
        transport_delay = transport_delay[transport_delay["mandi_id"] == mandi_id_filter]
    delay_threshold = transport_delay["transit_hours"].quantile(0.75)
    delay_rate = (transport_delay["transit_hours"] > delay_threshold).mean() * 100 if len(transport_delay) else 0
    st.progress(min(delay_rate / 100, 1.0))
    st.caption(f"{delay_rate:.1f}% of trips exceed the 75th-percentile transit time "
               f"({delay_threshold:.1f} hrs) — flagged as delayed for emergency-response prioritisation.")

# ---------------------------------------------------------------------------
# TAB 2 — Compare Mandis (side-by-side)
# ---------------------------------------------------------------------------
with tab_compare:
    st.markdown('<div class="ledger-section-title">Pick two mandis to compare side by side</div>', unsafe_allow_html=True)
    all_mandi_names = sorted(data.master["mandi_name"].dropna().unique().tolist())

    cpick1, cpick2 = st.columns(2)
    with cpick1:
        mandi_a_name = st.selectbox("Mandi A", all_mandi_names, index=0, key="mandi_a")
    with cpick2:
        default_b = 1 if len(all_mandi_names) > 1 else 0
        mandi_b_name = st.selectbox("Mandi B", all_mandi_names, index=default_b, key="mandi_b")

    mandi_a_id = data.name_to_id.get(mandi_a_name.lower())
    mandi_b_id = data.name_to_id.get(mandi_b_name.lower())

    def mandi_summary(mandi_id):
        a = data.arrivals[data.arrivals["mandi_id"] == mandi_id]
        p = data.prices[data.prices["mandi_id"] == mandi_id]
        t = data.transport[data.transport["mandi_id"] == mandi_id]
        return {
            "arrivals": a["arrival_qty_qtl"].sum(),
            "avg_price": p["modal_price"].mean(),
            "crash_rate": p["below_msp"].mean() * 100 if len(p) else float("nan"),
            "avg_transit": t["transit_hours"].mean(),
            "top_crop": (a.groupby("crop_name")["arrival_qty_qtl"].sum().idxmax()
                         if len(a) else "\u2014"),
            "daily": a.groupby("date", as_index=False)["arrival_qty_qtl"].sum(),
        }

    summary_a = mandi_summary(mandi_a_id) if mandi_a_id else None
    summary_b = mandi_summary(mandi_b_id) if mandi_b_id else None

    ccol1, ccol2 = st.columns(2)
    for col, name, s in [(ccol1, mandi_a_name, summary_a), (ccol2, mandi_b_name, summary_b)]:
        with col:
            if s is None:
                st.warning("No data available for this mandi.")
                continue
            avg_price_disp = f"\u20b9{s['avg_price']:,.0f}" if pd.notna(s["avg_price"]) else "\u2014"
            avg_transit_disp = f"{s['avg_transit']:.1f} hrs" if pd.notna(s["avg_transit"]) else "\u2014"
            st.markdown(f"""
            <div class="compare-card">
                <h3>{name}</h3>
                <div class="compare-row"><span class="label">Total Arrivals</span><span class="value">{s['arrivals']:,.0f} Qtl</span></div>
                <div class="compare-row"><span class="label">Avg Modal Price</span><span class="value">{avg_price_disp}</span></div>
                <div class="compare-row"><span class="label">Price-Crash Rate</span><span class="value">{s['crash_rate']:.1f}%</span></div>
                <div class="compare-row"><span class="label">Avg Transit Time</span><span class="value">{avg_transit_disp}</span></div>
                <div class="compare-row"><span class="label">Top Crop</span><span class="value">{s['top_crop']}</span></div>
            </div>
            """, unsafe_allow_html=True)

    if summary_a is not None and summary_b is not None:
        st.markdown('<div class="ledger-section-title">Arrival trend — side by side</div>', unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=summary_a["daily"]["date"], y=summary_a["daily"]["arrival_qty_qtl"],
                                  mode="lines+markers", name=mandi_a_name, line=dict(color=GOLD)))
        fig.add_trace(go.Scatter(x=summary_b["daily"]["date"], y=summary_b["daily"]["arrival_qty_qtl"],
                                  mode="lines+markers", name=mandi_b_name, line=dict(color=TEAL)))
        fig.update_layout(yaxis_title="Arrivals (Quintals)", xaxis_title="Date")
        st.plotly_chart(styled_fig(fig), use_container_width=True)

# ---------------------------------------------------------------------------
# TAB 3 — Advanced Insights: forecasting + mandi clustering (Gate 4)
# ---------------------------------------------------------------------------
with tab_insights:
    st.markdown('<div class="ledger-section-title">Price / arrival forecast</div>', unsafe_allow_html=True)
    st.caption("A 7-day-ahead forecast — linear trend plus day-of-week seasonality, "
               "fit fresh on whatever crop/mandi you pick below.")

    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        forecast_crop = st.selectbox("Crop", CROPS, key="forecast_crop")
    with fc2:
        forecast_metric = st.selectbox("Metric", ["Arrivals (Qtl)", "Modal Price (\u20b9)"], key="forecast_metric")
    with fc3:
        forecast_mandi_name = st.selectbox("Mandi (optional)", ["All mandis"] + all_mandi_names, key="forecast_mandi")

    forecast_mandi_id = (data.name_to_id.get(forecast_mandi_name.lower())
                          if forecast_mandi_name != "All mandis" else None)

    if forecast_metric == "Arrivals (Qtl)":
        base = data.arrivals[data.arrivals["crop_name"] == forecast_crop]
        if forecast_mandi_id:
            base = base[base["mandi_id"] == forecast_mandi_id]
        daily = base.groupby("date", as_index=False)["arrival_qty_qtl"].sum().rename(
            columns={"arrival_qty_qtl": "value"})
        y_label = "Arrivals (Quintals)"
    else:
        base = data.prices[data.prices["crop_name"] == forecast_crop]
        if forecast_mandi_id:
            base = base[base["mandi_id"] == forecast_mandi_id]
        daily = base.groupby("date", as_index=False)["modal_price"].mean().rename(
            columns={"modal_price": "value"})
        y_label = "Modal Price (\u20b9)"

    hist, fcst, note = forecast_series(daily, value_col="value", horizon_days=7)
    st.caption(f"\U0001F4CA {note}")

    if len(hist) and len(fcst):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist["date"], y=hist["value"], mode="lines",
                                  name="Actual", line=dict(color=TEAL)))
        fig.add_trace(go.Scatter(x=fcst["date"], y=fcst["value"], mode="lines+markers",
                                  name="Forecast (next 7 days)", line=dict(color=GOLD, dash="dash")))
        fig.update_layout(yaxis_title=y_label, xaxis_title="Date")
        st.plotly_chart(styled_fig(fig), use_container_width=True)
    else:
        st.info("Not enough data to forecast this selection.")

    st.markdown('<div class="ledger-section-title" style="margin-top:1.4rem;">Mandi clusters \u2014 by volume &amp; price stability</div>', unsafe_allow_html=True)
    st.caption("KMeans grouping of mandis into behavioural clusters (avg arrival volume, "
               "arrival volatility, avg price, price volatility) \u2014 useful for spotting "
               "which mandis need closer monitoring vs. which are predictable suppliers.")

    cluster_feat, cluster_note = cluster_mandis(data.arrivals, data.prices, n_clusters=3)
    if cluster_note:
        st.info(cluster_note)
    else:
        cluster_feat = cluster_feat.merge(data.master[["mandi_id", "mandi_name"]], on="mandi_id", how="left")
        fig = px.scatter(
            cluster_feat, x="avg_arrival", y="price_volatility",
            color="cluster_label", hover_name="mandi_name",
            labels={"avg_arrival": "Avg Daily Arrivals (Qtl)", "price_volatility": "Price Volatility (\u20b9 std dev)"},
            color_discrete_sequence=[GOLD, TEAL, RUST, "#8C6E4A"],
        )
        st.plotly_chart(styled_fig(fig), use_container_width=True)

        summary_tbl = cluster_feat.groupby("cluster_label").agg(
            mandis=("mandi_id", "count"),
            avg_arrival=("avg_arrival", "mean"),
            avg_price=("avg_price", "mean"),
            avg_crash_rate=("crash_rate", "mean"),
        ).round(1).reset_index()
        st.dataframe(summary_tbl, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# TAB 4 — Agentic Graph AI chatbot ("Field Agent" ledger log)
# ---------------------------------------------------------------------------
with tab_agent:
    st.markdown('<div class="ledger-section-title">Ask a question — the agent picks the right chart and explains it</div>', unsafe_allow_html=True)
    st.caption("Try: \u201cPlot the daily arrival trend of Wheat in Amritsar for the last 30 days\u201d \u00b7 "
               "\u201cWhich mandis are experiencing prices below MSP?\u201d \u00b7 "
               "\u201cTop 5 mandis by arrival volume\u201d \u00b7 \u201cWhich warehouse receives the highest volume?\u201d")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    query = st.chat_input("Ask about arrivals, prices, transit, or weather...")

    if query:
        fig, summary, intent = answer(query, data)
        st.session_state.chat_history.append((query, fig, summary, intent))

    for i, (q, fig, summary, intent) in enumerate(reversed(st.session_state.chat_history)):
        accent = INTENT_ACCENT.get(intent, GOLD)
        label = INTENT_LABEL.get(intent, "Query")
        st.markdown(f"""
        <div class="ledger-entry" style="--accent: {accent};">
            <span class="tag">{label}</span>
            <div class="query">&ldquo;{q}&rdquo;</div>
        </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(styled_fig(fig), use_container_width=True, key=f"chart_{i}_{intent}")
        st.markdown(f'<div class="ledger-entry" style="--accent:{accent}; margin-top:-0.9rem;"><div class="summary">{summary}</div></div>', unsafe_allow_html=True)
