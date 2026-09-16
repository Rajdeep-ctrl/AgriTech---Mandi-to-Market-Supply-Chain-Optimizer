"""
theme.py
========
Design tokens for the Mandi-to-Market dashboard — a "market ledger" look
grounded in the subject (grain mandis, harvest, price registers) instead of
a generic SaaS dashboard palette.

Color:  charcoal-brown base, harvest-gold primary accent, crop-teal secondary,
        rust-red for price alerts, warm off-white text.
Type:   Fraunces (serif, editorial/ledger feel) for headings,
        IBM Plex Sans for body and data.
"""

import plotly.graph_objects as go
import plotly.io as pio

BG = "#1A1512"
SURFACE = "#241E1A"
SURFACE_HI = "#2E2621"
BORDER = "#3A3128"
GOLD = "#E8A33D"
TEAL = "#3E7C6D"
RUST = "#C1502E"
TEXT = "#F2EAE1"
TEXT_DIM = "#B8AA9C"


def inject_css():
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,500;0,600;0,700;1,500&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

    html, body, [class*="css"] {{
        font-family: 'IBM Plex Sans', sans-serif;
    }}

    .stApp {{
        background-color: {BG};
        color: {TEXT};
    }}

    section[data-testid="stSidebar"] {{
        background-color: {SURFACE};
        border-right: 1px solid {BORDER};
    }}

    /* ---- Hero band ---- */
    .ledger-hero {{
        background: linear-gradient(135deg, #241E1A 0%, #1E2B26 100%);
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 2.2rem 2.4rem;
        margin-bottom: 1.6rem;
    }}
    .ledger-hero h1 {{
        font-family: 'Fraunces', serif;
        font-weight: 600;
        font-size: 2.3rem;
        color: {TEXT};
        margin: 0 0 0.4rem 0;
        line-height: 1.15;
    }}
    .ledger-hero .stat {{
        font-style: italic;
        color: {GOLD};
    }}
    .ledger-hero p {{
        font-family: 'IBM Plex Sans', sans-serif;
        color: {TEXT_DIM};
        font-size: 1.02rem;
        margin: 0;
    }}

    /* ---- KPI strip: hairline-divided, not identical boxed cards ---- */
    .kpi-strip {{
        display: flex;
        border-top: 1px solid {BORDER};
        border-bottom: 1px solid {BORDER};
        padding: 1.1rem 0;
        margin-bottom: 1.6rem;
    }}
    .kpi-item {{
        flex: 1;
        padding: 0 1.6rem;
        border-right: 1px solid {BORDER};
    }}
    .kpi-item:last-child {{ border-right: none; }}
    .kpi-label {{
        font-size: 0.78rem;
        color: {TEXT_DIM};
        margin-bottom: 0.25rem;
    }}
    .kpi-value {{
        font-family: 'Fraunces', serif;
        font-size: 1.9rem;
        font-weight: 600;
        color: {TEXT};
    }}
    .kpi-value.alert {{ color: {RUST}; }}
    .kpi-value.positive {{ color: {TEAL}; }}
    .kpi-delta {{
        font-size: 0.82rem;
        margin-top: 0.15rem;
        font-family: 'IBM Plex Sans', sans-serif;
    }}
    .kpi-delta.up {{ color: {TEAL}; }}
    .kpi-delta.down {{ color: {RUST}; }}
    .kpi-delta.flat {{ color: {TEXT_DIM}; }}

    /* ---- Compare view ---- */
    .compare-card {{
        background: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 1.1rem 1.4rem;
        margin-bottom: 0.8rem;
    }}
    .compare-card h3 {{
        font-family: 'Fraunces', serif;
        color: {GOLD};
        font-size: 1.15rem;
        margin: 0 0 0.7rem 0;
    }}
    .compare-row {{
        display: flex;
        justify-content: space-between;
        padding: 0.4rem 0;
        border-bottom: 1px solid {BORDER};
        font-size: 0.92rem;
    }}
    .compare-row:last-child {{ border-bottom: none; }}
    .compare-row .label {{ color: {TEXT_DIM}; }}
    .compare-row .value {{ color: {TEXT}; font-weight: 600; }}

    /* ---- Section labels ---- */
    .ledger-section-title {{
        font-family: 'Fraunces', serif;
        font-size: 1.15rem;
        font-weight: 600;
        color: {TEXT};
        margin: 0.4rem 0 0.8rem 0;
    }}

    /* ---- Chart containers ---- */
    div[data-testid="stPlotlyChart"] {{
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 0.6rem;
    }}

    /* ---- Tabs ---- */
    button[data-baseweb="tab"] {{
        font-family: 'Fraunces', serif;
        font-size: 1.02rem;
        color: {TEXT_DIM};
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {GOLD};
    }}
    div[data-baseweb="tab-highlight"] {{
        background-color: {GOLD};
    }}

    /* ---- Ledger-entry chat (agent tab) ---- */
    .ledger-entry {{
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-left: 3px solid var(--accent, {GOLD});
        border-radius: 4px;
        padding: 0.9rem 1.2rem;
        margin-bottom: 0.9rem;
    }}
    .ledger-entry .query {{
        font-family: 'Fraunces', serif;
        font-style: italic;
        color: {TEXT_DIM};
        font-size: 0.95rem;
        margin-bottom: 0.5rem;
    }}
    .ledger-entry .tag {{
        display: inline-block;
        font-size: 0.7rem;
        letter-spacing: 0.03em;
        color: {BG};
        background-color: var(--accent, {GOLD});
        border-radius: 3px;
        padding: 0.12rem 0.5rem;
        margin-bottom: 0.6rem;
    }}
    .ledger-entry .summary {{
        color: {TEXT};
        font-size: 0.98rem;
        line-height: 1.5;
    }}

    /* ---- Progress bar (delay rate) ---- */
    div[data-testid="stProgress"] > div > div {{
        background-color: {RUST};
    }}

    /* ---- Selects ---- */
    div[data-baseweb="select"] > div {{
        background-color: {SURFACE_HI};
        border-color: {BORDER};
    }}

    /* ---- Chat input ---- */
    [data-testid="stChatInput"] textarea {{
        background-color: {SURFACE_HI} !important;
        color: {TEXT} !important;
    }}
    </style>
    """


def styled_fig(fig: go.Figure) -> go.Figure:
    """Apply the shared palette + font to any plotly figure, transparent
    background so the surrounding card color shows through."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Sans, sans-serif", color=TEXT, size=13),
        title_font=dict(family="Fraunces, serif", color=TEXT, size=17),
        colorway=[GOLD, TEAL, RUST, "#8C6E4A", "#6B8F86", "#9C6B4F"],
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=50, l=10, r=10, b=10),
    )
    fig.update_xaxes(gridcolor=BORDER, zerolinecolor=BORDER, color=TEXT_DIM)
    fig.update_yaxes(gridcolor=BORDER, zerolinecolor=BORDER, color=TEXT_DIM)
    return fig


INTENT_ACCENT = {
    "intent_arrival_trend": GOLD,
    "fallback_arrival_trend": GOLD,
    "intent_top_mandis": GOLD,
    "intent_arrivals_by_crop": GOLD,
    "intent_price_vs_msp": TEAL,
    "intent_price_distribution": TEAL,
    "intent_below_msp": RUST,
    "intent_transit_delay": "#8C6E4A",
    "intent_warehouse_volume": "#8C6E4A",
    "intent_rainfall_correlation": TEAL,
    "intent_rainfall_trend": TEAL,
}

INTENT_LABEL = {
    "intent_arrival_trend": "Arrivals",
    "fallback_arrival_trend": "Arrivals",
    "intent_top_mandis": "Ranking",
    "intent_arrivals_by_crop": "Crop mix",
    "intent_price_vs_msp": "Price vs MSP",
    "intent_price_distribution": "Price",
    "intent_below_msp": "Price alert",
    "intent_transit_delay": "Transit",
    "intent_warehouse_volume": "Transit",
    "intent_rainfall_correlation": "Weather",
    "intent_rainfall_trend": "Weather",
}
