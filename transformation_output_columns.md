# Transformation Output Files — Column Reference

All files saved to `transformed/{dev|full}/`.

---

## 1. `transformed_cems.csv` — Main Enriched Dataset
**Rules:** T0 + T1 + T2 + T3 + T4 + T5 + T9 + T10 + T11

The original cleaned CEMS data with **30+ new columns** added on top.

| Column | Source | Description |
|--------|--------|-------------|
| Plant_ID, Stack_ID | Original | Factory and stack identifier |
| TS | Original | Timestamp (datetime) |
| PM2.5, SO2, NOx | Original | Pollutant concentrations (µg/m³) |
| Flow_Rate_m3_hr | Original | Stack gas flow rate |
| Unit | Original | Always `ug/m3` after cleaning |
| Status | Original | OK, FAULT, MAINT, GAP_FILLED, UNKNOWN |
| Source_Type | Original | `Stack` or `Ambient` |
| Exceedance_Flag | Original | Legacy flag from cleaning |
| Audit_Hash | Original | SHA-256 integrity hash |
| **Latitude** | **T0** | Split from Lat_Lon → float |
| **Longitude** | **T0** | Split from Lat_Lon → float |
| **Sector** | **Prep** | Joined from sensor_master (Cement/Steel/Power) |
| **Exceed_PM25** | **T1** | True if PM2.5 > CPCB limit for that source type |
| **Exceed_SO2** | **T1** | True if SO2 > CPCB limit |
| **Exceed_NOx** | **T1** | True if NOx > CPCB limit |
| **Any_Exceedance** | **T1** | True if ANY pollutant exceeds |
| **AQI_PM25** | **T2** | AQI sub-index for PM2.5 (0–500 scale) |
| **AQI_SO2** | **T2** | AQI sub-index for SO2 |
| **AQI_NOx** | **T2** | AQI sub-index for NOx |
| **AQI_Overall** | **T2** | Max of the 3 sub-indices (worst pollutant wins) |
| **AQI_Category** | **T2** | Good / Satisfactory / Moderate / Poor / Very Poor / Severe |
| **Load_PM25_kg_day** | **T3** | Emission load = conc × flow × 24 / 1e9 (stack only) |
| **Load_SO2_kg_day** | **T3** | Same for SO2 |
| **Load_NOx_kg_day** | **T3** | Same for NOx |
| **PM25_24h_avg** | **T4** | Rolling 24-hour mean (window=96 readings) |
| **PM25_24h_p95** | **T4** | Rolling 24-hour 95th percentile |
| **SO2_24h_avg, NOx_24h_avg** | **T4** | Same for other pollutants |
| **Wind_Contribution_Score** | **T5** | 0–1 score: is wind blowing from a factory toward this sensor? |
| **Health_Risk_Score** | **T9** | AQI_PM25 × 0.25 (cumulative exposure per 15-min reading) |
| **Date** | **T9** | Date extracted from TS |
| **Hour** | **T10** | Hour of day (0–23) |
| **DayOfWeek** | **T10** | Monday, Tuesday, etc. |
| **Location_ID** | **T11** | Mapped to nearest meteorology station |
| **Wind_Speed_kmh** | **T11** | Joined from meteorology (km/h) |
| **Wind_Dir_deg** | **T11** | Wind direction (degrees, 0=North) |
| **Temp_C** | **T11** | Temperature (°C) |
| **Humidity_RH** | **T11** | Relative humidity (%) |

---

## 2. `compliance_report.csv` — Rule T6 (Overall)

One row per **plant**. Shows how often they stay within legal limits across the full time period.

| Column | Description |
|--------|-------------|
| Plant_ID | Factory identifier |
| Total_Readings | Number of 15-min readings for that plant |
| Exceedances | How many readings broke the law |
| Compliance_Rate_Pct | `(Total - Exceedances) / Total × 100` |

---

## 3. `compliance_report_monthly.csv` — Rule T6 (Monthly)

Same as above but **broken down by month**. Tracks whether a plant is improving or worsening over time.

| Column | Description |
|--------|-------------|
| Plant_ID | Factory identifier |
| Month | Year-Month period (e.g., `2025-01`) |
| Total_Readings | Readings in that month |
| Exceedances | Exceedances in that month |
| Compliance_Rate_Pct | Monthly compliance percentage |

---

## 4. `penalty_estimate.csv` — Rule T19

Financial penalties based on how badly and how long each plant exceeded limits.

| Column | Description |
|--------|-------------|
| Plant_ID | Factory |
| Pollutant | Which pollutant (PM2.5 / SO2 / NOx) |
| Hours | Total hours of exceedance |
| Pct_Over | Average % over the legal limit |
| Severity | Minor (0–50% over) / Moderate (50–100%) / Major (100%+) |
| Fine_INR | `Hours × Fine_Rate` from compliance_penalty_rules.csv |

---

## 5. `episodes.csv` — Rule T7

Sustained high-pollution events (readings > 2× legal limit for at least 1 hour).

| Column | Description |
|--------|-------------|
| Plant_ID, Stack_ID | Where it happened |
| Pollutant | Which pollutant |
| Episode_Start | When the episode began |
| Episode_End | When it ended |
| Duration_Hours | How long (hours) |
| Peak_Value | Worst reading during the episode (µg/m³) |

---

## 6. `hotspot_ranking.csv` — Rule T17

Ranks ALL locations by pollution intensity and persistence.

| Column | Description |
|--------|-------------|
| Plant_ID | Location |
| Days | Total days with data |
| Exc_Days | Days with at least one exceedance |
| Avg_PM25 | Average PM2.5 across all days |
| Persist_Pct | `Exc_Days / Days × 100` |
| Score | `Persist_Pct × Avg_PM25 / 100` (higher = worse) |
| Rank | 1 = worst polluter |

---

## 7. `drift_alarms.csv` — Rule T13

Sensors that show suspicious data drift (CUSUM change-point detection).

| Column | Description |
|--------|-------------|
| Plant_ID, Stack_ID | Which sensor |
| Pollutant | Which pollutant drifted |
| Alarm_Count | Number of drift alarm points |
| Drift_Score | How severe the drift (multiples of threshold) |

---

## 8. `spatial_grid.csv` — Rule T8

A 10×10 lat/lon grid with estimated PM2.5 values (for map visualization).

| Column | Description |
|--------|-------------|
| Grid_Lat | Latitude of grid point |
| Grid_Lon | Longitude of grid point |
| PM25_IDW | Estimated PM2.5 via Inverse Distance Weighting |

---

## 9. `hourly_profile.csv` — Rule T10

Average pollutant levels by hour-of-day (0–23). Shows daily pollution rhythm.

| Column | Description |
|--------|-------------|
| Hour | Hour of day (0–23) |
| PM2.5 | Average PM2.5 at that hour |
| SO2 | Average SO2 at that hour |
| NOx | Average NOx at that hour |

---

## 10. `model_features.csv` — Rule T16

ML-ready feature table for PM2.5 forecasting.

| Column | Description |
|--------|-------------|
| PM25_lag_15m/1h/6h/24h | Lagged PM2.5 values |
| PM25_roll_mean_6h | Rolling 6-hour average |
| PM25_roll_std_6h | Rolling 6-hour standard deviation |
| IsWeekend | Boolean: is it Saturday/Sunday? |
| HourSin, HourCos | Cyclical time encoding |
| Wind_Speed, Temp_C | Weather features from T11 |

---

## 11 & 12. `regulatory_report_stack.csv` & `regulatory_report_ambient.csv` — Rule T15

CPCB-format daily summary reports, split by source type.

| Column | Description |
|--------|-------------|
| Plant_ID | Factory/location |
| Date | Day |
| PM25_Avg, SO2_Avg, NOx_Avg | Daily averages |
| Readings | Number of readings that day |
| Exceedances | How many exceeded limits |
| AQI_Avg | Average AQI for the day |

---

## 13. `emission_factor_comparison.csv` — Rule T12

Compares actual measured emissions vs expected from AP-42 emission factors.

| Column | Description |
|--------|-------------|
| Sector | Cement / Steel / Power |
| Pollutant | PM2.5 / SO2 / NOx |
| EF_kg_per_ton | Expected emission factor |
| Avg_Measured_Load | Actual measured emissions (kg/day avg) |

---

## 14. `control_impact.csv` — Rule T18

Pre/post analysis of pollution control equipment installations.

| Column | Description |
|--------|-------------|
| Plant_ID, Stack_ID | Which sensor |
| Measure | Equipment type (Wet Scrubber, Baghouse, etc.) |
| Pollutant | Which pollutant |
| Pre_Avg | Average before installation |
| Post_Avg | Average after installation |
| Reduction_Pct | `(Pre - Post) / Pre × 100` (negative = got worse) |

---

## 15. `gap_analysis.csv` — Rule T14

Data availability analysis per sensor.

| Column | Description |
|--------|-------------|
| Plant_ID, Stack_ID | Sensor identifier |
| Original_Readings | How many readings we actually received |
| OK_Readings | Readings with Status = OK |
| Faults | Readings with Status = FAULT |
| Maint | Readings with Status = MAINT |
| Unknown | Readings with Status = UNKNOWN |
| Expected_Readings | How many we *should* have (based on time window ÷ 15 min) |
| Missing_Readings | Expected - Original |
| Data_Availability_Pct | `Original / Expected × 100` |
| **ORPHANED_GAPS row** | 489 gap-filled rows from cleaning that have no Plant_ID |

---

## 16. `open_data_extract.csv` — Rule T20

Privacy-safe public version of the dataset.

| Column | Description |
|--------|-------------|
| Same as transformed_cems but... | |
| ❌ Audit_Hash | Removed (internal) |
| ❌ Record_ID | Removed (internal) |
| ❌ Location_ID | Removed (internal) |
| Latitude, Longitude | Rounded to 2 decimal places |
