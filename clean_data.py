"""
clean_data.py
=============
Data Rescue script for the "Mandi-to-Market Supply Chain Optimizer" (Track 3).

Takes the 5 raw, messy source files and produces clean, standardized CSVs
in data_clean/, ready to be queried by the dashboard and the AI agent.

Run:  python clean_data.py
"""

import re
import json
import pandas as pd
import numpy as np
from pathlib import Path

RAW = Path("data_raw")
CLEAN = Path("data_clean")
CLEAN.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Shared helpers
# ---------------------------------------------------------------------------

# Canonical crop name lookup: every messy variant (English / Hindi / Punjabi
# spelling, different case) maps to one clean English crop name.
CROP_MAP = {
    "wheat": "Wheat", "gehun": "Wheat", "kanak": "Wheat", "गेहूं": "Wheat",
    "maize": "Maize", "corn": "Maize", "makka": "Maize", "makki": "Maize", "मक्का": "Maize",
    "mustard": "Mustard", "sarson": "Mustard", "sarso": "Mustard", "सरसों": "Mustard",
    "cotton": "Cotton", "kapas": "Cotton", "narma": "Cotton", "कपास": "Cotton",
    "paddy": "Rice", "chawal": "Rice", "dhaan": "Rice", "धान": "Rice", "basmati": "Rice",
    "rice": "Rice", "चावल": "Rice",
    "sugarcane": "Sugarcane", "ganne": "Sugarcane", "ganna": "Sugarcane", "गन्ना": "Sugarcane",
}


def standardize_crop(name):
    if pd.isna(name):
        return np.nan
    key = str(name).strip().lower()
    return CROP_MAP.get(key, str(name).strip().title())


def standardize_mandi_id(raw_id):
    """MANDI001, MANDI-001, mandi_001, M001, '003', 'mandi041' -> 'MANDI001'."""
    if pd.isna(raw_id):
        return np.nan
    digits = re.sub(r"\D", "", str(raw_id))
    if not digits:
        return np.nan
    return f"MANDI{int(digits):03d}"


def clean_price(val):
    """Strip currency symbols / text / commas / trailing '/-' -> float."""
    if pd.isna(val) or str(val).strip() == "":
        return np.nan
    s = str(val)
    s = re.sub(r"[₹]|Rs\.?|INR", "", s, flags=re.IGNORECASE)
    s = s.replace(",", "").replace("/-", "").strip()
    try:
        return float(s)
    except ValueError:
        return np.nan


def _try_date(val):
    """Robust date/datetime parser.

    IMPORTANT: a single dayfirst=True/False dateutil guess is NOT safe on
    this dataset. Auditing data_raw showed the ambiguous numeric formats
    follow two DIFFERENT conventions:
        - '/'-separated (DD/MM/YYYY) and '.'-separated (DD.MM.YYYY)  -> day-first
        - '-'-separated numeric (MM-DD-YYYY, incl. 12-hr AM/PM)      -> month-first
    A blind dayfirst=True guess silently mis-parses ~40% of the '-'-separated
    rows (swaps day/month). It also corrupts *unambiguous* ISO strings like
    '2026-01-12T02:03:26' -> mis-parsed as Dec 1 instead of Jan 12 (a known
    dateutil quirk when dayfirst=True is forced). Explicit formats, tried in
    order, avoid both problems.
    """
    return parse_flexible_datetime(val)


def parse_flexible_datetime(val):
    if pd.isna(val):
        return pd.NaT
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return pd.NaT

    explicit_formats = [
        "%Y-%m-%dT%H:%M:%S",    # ISO w/ T                 - unambiguous
        "%Y-%m-%d %H:%M:%S",    # ISO w/ space              - unambiguous
        "%Y-%m-%d",             # ISO date only             - unambiguous
        "%Y/%m/%d",             # YYYY/MM/DD                - unambiguous (year first)
        "%d/%m/%Y %H:%M",       # DD/MM/YYYY HH:MM          - day-first (confirmed in data)
        "%d/%m/%Y",             # DD/MM/YYYY                - day-first (confirmed in data)
        "%d.%m.%Y",             # DD.MM.YYYY                - day-first (confirmed in data)
        "%m-%d-%Y %I:%M %p",    # MM-DD-YYYY hh:mm AM/PM    - month-first (confirmed in data)
        "%m-%d-%Y",             # MM-DD-YYYY                - month-first (confirmed in data)
        "%d-%b-%Y %H:%M:%S",    # DD-Mon-YYYY HH:MM:SS      - unambiguous (month name)
        "%d-%b-%Y",             # DD-Mon-YYYY               - unambiguous (month name)
    ]
    for fmt in explicit_formats:
        try:
            return pd.to_datetime(s, format=fmt)
        except (ValueError, TypeError):
            continue
    # last resort for anything unexpected — should rarely fire given the list above
    return pd.to_datetime(s, errors="coerce", dayfirst=True)


# ---------------------------------------------------------------------------
# 2. Mandi master (clean first — everything else joins against it)
# ---------------------------------------------------------------------------

def clean_master():
    df = pd.read_csv(RAW / "track3_mandi_master.csv", encoding="utf-8")
    df["mandi_id"] = df["mandi_id"].apply(standardize_mandi_id)
    df["district"] = df["district"].astype(str).str.strip().str.title().replace(
        {"Nan": np.nan, "": np.nan}
    )
    df["mandi_type"] = df["mandi_type"].astype(str).str.strip().str.upper().replace(
        {"NAN": np.nan, "": np.nan}
    )
    df["total_area_acres"] = pd.to_numeric(df["total_area_acres"], errors="coerce")
    df = df.drop_duplicates(subset="mandi_id", keep="first")
    df = df.dropna(subset=["mandi_id"])
    df.to_csv(CLEAN / "mandi_master.csv", index=False, encoding="utf-8")
    return df


# ---------------------------------------------------------------------------
# 3. Mandi arrivals
# ---------------------------------------------------------------------------

UNIT_TO_QTL = {
    "t": 10, "tonnes": 10, "tonne": 10, "mt": 10,
    "qtl": 1, "q": 1, "quintal": 1, "quintals": 1,
    "kg": 0.01, "kgs": 0.01, "kilo": 0.01,
}


def parse_quantity_unit(qty_raw, unit_raw):
    """Some rows embed the unit inside the quantity string itself
    (e.g. '415.88 qtl') when the unit column is blank. Some also use
    thousands-separator commas (e.g. '36,654.0 KG') which must be
    stripped before the numeric regex, otherwise it only matches the
    digits before the comma and the row is lost."""
    qty_str = str(qty_raw).strip().lower() if pd.notna(qty_raw) else ""
    qty_str = qty_str.replace(",", "")
    unit = str(unit_raw).strip().lower() if pd.notna(unit_raw) else ""

    embedded_match = re.match(r"([\d.\-]+)\s*([a-z]+)?", qty_str)
    number = np.nan
    if embedded_match:
        try:
            number = float(embedded_match.group(1))
        except ValueError:
            number = np.nan
        if not unit and embedded_match.group(2):
            unit = embedded_match.group(2)

    factor = UNIT_TO_QTL.get(unit, np.nan)
    if pd.isna(number) or pd.isna(factor):
        return np.nan
    if number < 0:  # impossible negative arrival quantity
        return np.nan
    return round(number * factor, 3)


def clean_arrivals(master):
    df = pd.read_csv(RAW / "track3_mandi_arrivals.csv", encoding="utf-8")
    df["mandi_id"] = df["mandi_id"].apply(standardize_mandi_id)
    df["date"] = df["date"].apply(_try_date)
    df["crop_name"] = df["crop_name"].apply(standardize_crop)
    df["arrival_qty_qtl"] = df.apply(
        lambda r: parse_quantity_unit(r["arrival_quantity"], r["unit"]), axis=1
    )
    df["farmer_count"] = pd.to_numeric(df["farmer_count"], errors="coerce")

    df = df.merge(master[["mandi_id", "district", "state"]], on="mandi_id", how="left")

    before = len(df)
    df = df.dropna(subset=["mandi_id", "date", "crop_name", "arrival_qty_qtl"])
    after = len(df)
    print(f"[arrivals] rows {before} -> {after} after dropping unrecoverable rows")

    df = df[["arrival_id", "date", "mandi_id", "district", "state", "crop_name",
             "variety", "arrival_qty_qtl", "farmer_count"]]
    df.to_csv(CLEAN / "mandi_arrivals.csv", index=False, encoding="utf-8")
    return df


# ---------------------------------------------------------------------------
# 4. Price & MSP
# ---------------------------------------------------------------------------

def clean_prices(master):
    with open(RAW / "track3_price_and_msp.json", encoding="utf-8") as f:
        raw = json.load(f)
    df = pd.DataFrame(raw)

    df["mandi_id"] = df["mandi_id"].apply(standardize_mandi_id)
    df["date"] = df["date"].apply(_try_date)
    df["crop_name"] = df["crop_name"].apply(standardize_crop)
    for col in ["min_price", "max_price", "modal_price", "msp"]:
        df[col] = df[col].apply(clean_price)

    # fill missing district from master via mandi_id
    df = df.drop(columns=["district"]).merge(
        master[["mandi_id", "district", "state"]], on="mandi_id", how="left"
    )

    before = len(df)
    df = df.dropna(subset=["mandi_id", "date", "crop_name", "modal_price"])
    after = len(df)
    print(f"[prices] rows {before} -> {after} after dropping unrecoverable rows")

    # NOTE: plain `modal_price < msp` silently evaluates to False whenever msp
    # is NaN (numpy/pandas comparison quirk), which would misreport ~2,000
    # "unknown MSP" rows as "not a price crash" instead of "unknown" — a real
    # bias in a core business KPI. Keep it explicitly null when MSP is missing.
    df["below_msp"] = np.where(df["msp"].notna(), df["modal_price"] < df["msp"], np.nan)

    df = df[["record_id", "date", "mandi_id", "district", "state", "crop_name",
             "min_price", "max_price", "modal_price", "msp", "below_msp"]]
    df.to_csv(CLEAN / "price_and_msp.csv", index=False, encoding="utf-8")
    return df


# ---------------------------------------------------------------------------
# 5. Transport / logistics
# ---------------------------------------------------------------------------

def clean_distance(dist_raw, unit_raw):
    s = str(dist_raw).strip().lower() if pd.notna(dist_raw) else ""
    unit = str(unit_raw).strip().lower() if pd.notna(unit_raw) else ""
    m = re.match(r"([\d.]+)\s*([a-z]+)?", s)
    if not m:
        return np.nan
    try:
        val = float(m.group(1))
    except ValueError:
        return np.nan
    if not unit and m.group(2):
        unit = m.group(2)
    if unit.startswith("mile"):
        return round(val * 1.60934, 2)
    return round(val, 2)  # already km (or unit missing -> assume km)


def clean_vehicle_no(v):
    if pd.isna(v) or str(v).strip() == "":
        return np.nan
    s = re.sub(r"[\s\-]", "", str(v)).upper()
    m = re.match(r"^([A-Z]{2})(\d{2})([A-Z]{1,2})(\d{4})$", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}-{m.group(4)}"
    return str(v).strip().upper()


def clean_transport(master):
    df = pd.read_csv(RAW / "track3_transport_logistics.csv", encoding="utf-8")
    df["mandi_id"] = df["mandi_id"].apply(standardize_mandi_id)
    df["departure_time"] = df["departure_time"].apply(parse_flexible_datetime)
    df["arrival_time"] = df["arrival_time"].apply(parse_flexible_datetime)
    df["distance_km"] = df.apply(
        lambda r: clean_distance(r["distance"], r["distance_unit"]), axis=1
    )
    df["vehicle_no"] = df["vehicle_no"].apply(clean_vehicle_no)

    # recompute transit_hours from timestamps where possible; fall back to given value
    computed = (df["arrival_time"] - df["departure_time"]).dt.total_seconds() / 3600
    given = pd.to_numeric(df["transit_hours"], errors="coerce")
    df["transit_hours_clean"] = np.where(
        computed.notna() & (computed > 0), computed, given
    )
    # impossible / negative transit times -> NaN (can't recover)
    df.loc[df["transit_hours_clean"] <= 0, "transit_hours_clean"] = np.nan

    df = df.merge(master[["mandi_id", "district"]], on="mandi_id", how="left")

    before = len(df)
    df = df.dropna(subset=["mandi_id", "destination_warehouse", "distance_km"])
    after = len(df)
    print(f"[transport] rows {before} -> {after} after dropping unrecoverable rows")

    df = df[["trip_id", "mandi_id", "district", "destination_warehouse",
             "departure_time", "arrival_time", "transit_hours_clean",
             "distance_km", "vehicle_no", "driver_id"]]
    df = df.rename(columns={"transit_hours_clean": "transit_hours"})
    df.to_csv(CLEAN / "transport_logistics.csv", index=False, encoding="utf-8")
    return df


# ---------------------------------------------------------------------------
# 6. Weather sensors
# ---------------------------------------------------------------------------

def parse_temperature_c(temp_raw, unit_raw):
    """Handles '68', '85.3', '39.8°C', '18.9' + unit column, F->C conversion."""
    if pd.isna(temp_raw):
        return np.nan
    s = str(temp_raw).strip()
    m = re.match(r"([\d.\-]+)\s*°?\s*([A-Za-z]*)", s)
    if not m:
        return np.nan
    try:
        val = float(m.group(1))
    except ValueError:
        return np.nan
    raw_unit = m.group(2) if m.group(2) else (str(unit_raw) if pd.notna(unit_raw) else "")
    unit = re.sub(r"[^a-zA-Z]", "", raw_unit).strip().lower()
    if unit.startswith("f"):
        return round((val - 32) * 5 / 9, 2)
    return round(val, 2)  # already Celsius


def parse_rainfall_mm(val, unit):
    if pd.isna(val):
        return np.nan
    val = float(val)
    if val < 0:
        return np.nan
    u = str(unit).strip().lower() if pd.notna(unit) else "mm"
    if u.startswith("in"):
        return round(val * 25.4, 2)
    return round(val, 2)


def parse_weather_timestamp(ts):
    """Convert UTC -> IST (+5:30); IST timestamps and bare dates pass through."""
    if pd.isna(ts):
        return pd.NaT
    s = str(ts).strip()
    is_utc = s.upper().endswith("UTC")
    s_clean = re.sub(r"\s*(UTC|IST)\s*$", "", s, flags=re.IGNORECASE)
    dt = parse_flexible_datetime(s_clean)
    if pd.isna(dt):
        return pd.NaT
    if is_utc:
        dt = dt + pd.Timedelta(hours=5, minutes=30)
    return dt


def clean_weather():
    df = pd.read_excel(RAW / "track3_weather_sensors.xlsx")
    df["timestamp_ist"] = df["timestamp"].apply(parse_weather_timestamp)
    df["temperature_c"] = df.apply(
        lambda r: parse_temperature_c(r["temperature"], r["temp_unit"]), axis=1
    )
    df["rainfall_mm"] = df.apply(
        lambda r: parse_rainfall_mm(r["rainfall"], r["rain_unit"]), axis=1
    )
    df["humidity_percent"] = pd.to_numeric(df["humidity_percent"], errors="coerce")

    before = len(df)
    df = df.dropna(subset=["timestamp_ist"])
    after = len(df)
    print(f"[weather] rows {before} -> {after} after dropping rows with unparseable timestamps")

    df["date"] = df["timestamp_ist"].dt.date
    df = df[["sensor_id", "timestamp_ist", "date", "temperature_c",
             "rainfall_mm", "humidity_percent"]]
    df.to_csv(CLEAN / "weather_sensors.csv", index=False, encoding="utf-8")
    return df


# ---------------------------------------------------------------------------
# 7. Run everything
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Cleaning mandi_master...")
    master = clean_master()

    print("Cleaning mandi_arrivals...")
    arrivals = clean_arrivals(master)

    print("Cleaning price_and_msp...")
    prices = clean_prices(master)

    print("Cleaning transport_logistics...")
    transport = clean_transport(master)

    print("Cleaning weather_sensors...")
    weather = clean_weather()

    print("\nAll clean files written to data_clean/:")
    for f in sorted(CLEAN.glob("*.csv")):
        print(" -", f.name)
