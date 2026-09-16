# Data Dictionary — Cleaned Datasets (`data_clean/`)

## mandi_master.csv
| Column | Description |
|---|---|
| mandi_id | Canonical mandi ID, standardized to `MANDIxxx` (3-digit, zero-padded) |
| mandi_name | Name of the mandi |
| district | District, title-cased, trimmed |
| state | State the mandi is located in |
| mandi_type | APMC / Private / Direct, upper-cased for consistency |
| total_area_acres | Mandi's physical area in acres |

## mandi_arrivals.csv
| Column | Description |
|---|---|
| arrival_id | Unique arrival record ID |
| date | Parsed arrival date (multiple raw formats standardized) |
| mandi_id | Canonical mandi ID (joins to mandi_master) |
| district, state | Joined in from mandi_master |
| crop_name | Canonicalized crop name — English/Hindi/Punjabi variants merged (e.g. "गेहूं"/"Gehun"/"Kanak" → "Wheat") |
| variety | Crop variety, as given |
| arrival_qty_qtl | Arrival quantity converted to **Quintals** (1 Tonne = 10 Qtl, 1 Qtl = 100 Kg) |
| farmer_count | Number of farmers who brought produce that day |

## price_and_msp.csv
| Column | Description |
|---|---|
| record_id | Unique price record ID |
| date | Parsed date |
| mandi_id, district, state | Joined/standardized mandi reference |
| crop_name | Canonicalized crop name |
| min_price / max_price / modal_price | Prices in ₹/Quintal — currency symbols (₹, Rs., INR), commas, and "/-" suffixes stripped |
| msp | Minimum Support Price, ₹/Quintal, cleaned the same way |
| below_msp | Boolean — True when modal_price < msp (a "price crash") |

## transport_logistics.csv
| Column | Description |
|---|---|
| trip_id | Unique trip ID |
| mandi_id, district | Origin mandi (standardized) |
| destination_warehouse | Destination warehouse code |
| departure_time / arrival_time | Parsed timestamps (multiple raw formats standardized) |
| transit_hours | Recomputed from timestamps where possible, otherwise the given value; negative/impossible values set to null |
| distance_km | Distance converted to kilometers (1 mile = 1.60934 km) |
| vehicle_no | Vehicle registration, normalized to `XX-00-XX-0000` format where recognizable |
| driver_id | Driver identifier |

## weather_sensors.csv
| Column | Description |
|---|---|
| sensor_id | Sensor identifier |
| timestamp_ist | Timestamp converted to IST (UTC readings shifted +5:30) |
| date | Date derived from timestamp_ist |
| temperature_c | Temperature in Celsius (Fahrenheit readings converted) |
| rainfall_mm | Rainfall in millimeters (inches converted); negative values treated as invalid |
| humidity_percent | Relative humidity, % |

**Note:** weather sensors are not individually mapped to a district/mandi in the
source data (no lat/long or district column). The agent and dashboard are
explicit about this limitation rather than fabricating a mapping — see
`agent.py::intent_rainfall_trend`.

## Row counts (raw → clean)
| File | Raw rows | Clean rows | Dropped (unrecoverable) |
|---|---|---|---|
| mandi_arrivals | 25,750 | 24,489 | 1,261 |
| price_and_msp | 12,000 | 10,213 | 1,787 |
| transport_logistics | 10,400 | 10,400 | 0 |
| weather_sensors | 15,000 | 13,445 | 1,555 |

Rows are dropped only when a required field (id, date, crop, or the core
numeric measure) survives cleaning as unparseable/negative — e.g. a
transit time of -4 hours cannot be corrected, so that row is excluded
rather than silently kept wrong. The 1,261 dropped arrival rows are
genuinely-negative quantities (data entry errors) with no recoverable
correct value.

## Data-quality issues caught during review

A second pass over the cleaning logic (comparing script output against
the raw files directly, not just checking it "ran without errors") found
four real bugs, since fixed:

1. **Comma-formatted quantities were silently dropped.** ~2,593 arrival
   rows like `"36,654.0 KG"` failed the numeric regex because of the
   thousands-separator comma, so `arrival_qty_qtl` came out `NaN` and the
   whole row was excluded — a straightforward parsing fix instead of a
   real data-quality "unrecoverable" case. Fixed by stripping commas
   before parsing; ~2,600 rows recovered.
2. **Ambiguous dash-separated dates were parsed with the wrong
   day/month convention.** The raw data mixes `DD/MM/YYYY` (day-first)
   with `MM-DD-YYYY` (month-first, confirmed by checking which field
   position exceeds 12) under one blind `dayfirst=True` guess, silently
   swapping day and month for ~40% of the affected rows (~1,586 rows in
   arrivals, ~757 in prices). Fixed with an explicit, ordered list of
   formats instead of one global guess.
3. **Unambiguous ISO timestamps were still mis-parsed.** A `dayfirst=True`
   dateutil fallback applied to a string like `2026-01-12T02:03:26`
   returns **Dec 1**, not Jan 12 — a known dateutil quirk. This alone
   inflated transit-time calculations to an average of ~308 hours (max
   ~7,770 hours / 320+ days) in `transport_logistics`, corrupting the
   "average transit time by warehouse" KPI. Fixed by trying explicit ISO
   formats first; average transit time is now a realistic ~13.5 hours
   (max ~48 hours).
4. **`below_msp` mislabeled "MSP unknown" as "not a crash."** Plain
   `modal_price < msp` evaluates to `False` in pandas when `msp` is
   `NaN`, so ~2,042 records with no MSP on file were counted as *not*
   price crashes instead of *unknown* — silently biasing the price-crash
   KPI downward. Fixed to output `NaN` (not `False`) when MSP is missing;
   `agent.py`'s below-MSP intent updated to match (`== 1` instead of a
   direct boolean mask, since the column now round-trips through CSV as
   float with real `NaN`s).
