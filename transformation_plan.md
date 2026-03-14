# Transformation Plan — All 20 Rules

## Overview

Transform cleaned CEMS data into analysis-ready outputs. Each rule produces a new column, derived table, or analytical output.

**Input:** Cleaned datasets from Phase 2 + 5 new reference/lookup datasets (Nodes 6–10).

---

## New Datasets to Generate (All Clean — No Messiness)

### Node 6: `meteorology_data.csv` (~2,880 rows for dev)
Hourly weather data for 4 ambient locations, Jan 1–7 2025.

| Column | Type | Example |
|--------|------|---------|
| Location_ID | string | `LOC-DEL-01` |
| TS | datetime | `2025-01-01 01:00` |
| Wind_Speed_kmh | float | `15.5` |
| Wind_Dir_deg | int | `180` (South) |
| Temp_C | float | `12.5` |
| Humidity_RH | float | `65.0` |

### Node 7: `aqi_standards_cpcb.csv` (15 rows, static)
CPCB National Ambient AQI breakpoint table.

| Column | Type | Example |
|--------|------|---------|
| Pollutant | string | `PM2.5` |
| Conc_Low | float | `0.0` |
| Conc_High | float | `30.0` |
| AQI_Low | int | `0` |
| AQI_High | int | `50` |
| Category | string | `Good` |

### Node 8: `emission_factors.csv` (9 rows, static)
AP-42 style emission factors by sector.

| Column | Type | Example |
|--------|------|---------|
| Sector | string | `Cement` |
| Pollutant | string | `PM2.5` |
| Emission_Factor_kg_per_ton | float | `0.85` |

### Node 9: `industry_control_measures.csv` (5 rows, static)
Filter/scrubber installation log for plants.

| Column | Type | Example |
|--------|------|---------|
| Plant_ID | string | `PL-01` |
| Stack_ID | string | `S-01` |
| Measure_Type | string | `Wet Scrubber` |
| Install_Date | datetime | `2025-01-04` |

### Node 10: `compliance_penalty_rules.csv` (9 rows, static)
Fine schedule per pollutant by severity.

| Column | Type | Example |
|--------|------|---------|
| Pollutant | string | `PM2.5` |
| Severity | string | `Minor` |
| Threshold_Pct_Over | float | `0` |
| Fine_INR_per_Hour | int | `10000` |

---

## Transformation Rules — Execution Order

### Phase A: Structural Transforms (Foundation)

#### T0: Lat/Lon Split *(Prerequisite — not in the 20 rules but needed)*
- **Input:** `Lat_Lon` column (`"13.08,80.27"`)
- **Output:** `Latitude` (float), `Longitude` (float) columns
- **Logic:** `df[['Latitude','Longitude']] = df['Lat_Lon'].str.split(',', expand=True).astype(float)`
- Drop original `Lat_Lon` column

---

### Phase B: Time-Series Aggregation (T1, T4, T10)

#### T1: Exceedance flags vs daily/hourly standards
- **Input:** Cleaned data + `regulatory_thresholds`
- **Output:** `Hourly_Exceedance` flag, `Daily_Exceedance` flag
- **Logic:** Resample to hourly/daily averages → compare against limits → flag

#### T4: Rolling 24-hour averages and percentiles
- **Input:** Cleaned data (15-min readings)
- **Output:** `PM25_24h_avg`, `SO2_24h_avg`, `NOx_24h_avg`, `PM25_24h_p95`
- **Logic:** `df.rolling(window=96)` (96 × 15min = 24h) → mean/percentile

#### T10: Diurnal and weekly seasonality profiles
- **Input:** Cleaned data with `TS`
- **Output:** `hourly_profile.csv` — average pollutant levels by hour-of-day
- **Logic:** Extract `Hour`, `DayOfWeek` → group → mean

---

### Phase C: AQI & Health (T2, T9)

#### T2: Pollutant AQI sub-index computation and overall AQI
- **Input:** Cleaned data + `aqi_standards_cpcb.csv`
- **Output:** `AQI_PM25`, `AQI_SO2`, `AQI_NOx`, `AQI_Overall`, `AQI_Category`
- **Logic:** For each pollutant, find which breakpoint row the concentration falls in → linear interpolation → `AQI = ((AQI_High - AQI_Low) / (Conc_High - Conc_Low)) × (Conc - Conc_Low) + AQI_Low` → overall = max of sub-indices

#### T9: Health risk proxy index (PM2.5 exposure)
- **Input:** AQI values from T2
- **Output:** `Health_Risk_Score` (cumulative PM2.5 exposure index)
- **Logic:** `AQI_PM25 × hours_exposed` → daily cumulative score per location

---

### Phase D: Emission & Load Calculations (T3, T12)

#### T3: Emission load (kg/day) from concentration and flow
- **Input:** Cleaned data (`PM2.5` in µg/m³, `Flow_Rate_m3_hr`)
- **Output:** `Load_PM25_kg_day`, `Load_SO2_kg_day`, `Load_NOx_kg_day`
- **Logic:** `Load = concentration(µg/m³) × flow(m³/hr) × 24hr / 1e9` → kg/day
- Only for Stack sensors (ambient has no flow)

#### T12: Emission factor application for sectors
- **Input:** `emission_factors.csv` + `sensor_master` (Sector)
- **Output:** `Estimated_Emission_kg_ton` per plant
- **Logic:** Join sector → multiply factor × estimated production → compare with actual measured load

---

### Phase E: Weather & Source Analysis (T5, T11)

#### T11: Meteorology joins (wind, temp, RH)
- **Input:** Cleaned data + `meteorology_data.csv`
- **Output:** `Wind_Speed`, `Wind_Dir`, `Temp_C`, `Humidity_RH` columns merged
- **Logic:** Left join on nearest `Location_ID` + hourly `TS`

#### T5: Source contribution indicators (wind-weighted)
- **Input:** T11 output (wind + pollution data) + Lat/Lon
- **Output:** `Wind_Contribution_Score` per stack
- **Logic:** If wind blows FROM factory TOWARD ambient sensor + ambient reading is high → score contribution

---

### Phase F: Compliance & Regulatory (T6, T15, T19)

#### T6: Compliance rate per plant/month
- **Input:** Exceedance flags from T1
- **Output:** `compliance_report.csv` — `Plant_ID`, `Compliance_Rate_%`, `Total_Readings`, `Exceedances`
- **Logic:** `(total_readings - exceedances) / total_readings × 100`

#### T15: Regulatory reporting tables (Stack, Ambient)
- **Input:** Aggregated data + `Source_Type`
- **Output:** `regulatory_report_stack.csv`, `regulatory_report_ambient.csv`
- **Logic:** Daily/monthly averages by plant, formatted per CPCB reporting requirements

#### T19: Compliance penalty estimation
- **Input:** Exceedance data + `compliance_penalty_rules.csv`
- **Output:** `penalty_estimate.csv` — `Plant_ID`, `Pollutant`, `Exceedance_Hours`, `Severity`, `Estimated_Fine_INR`
- **Logic:** Count exceedance hours → classify severity (Minor/Moderate/Major based on % over limit) → multiply by fine rate

---

### Phase G: Anomaly & Event Detection (T7, T13)

#### T7: Episode detection (high pollution events)
- **Input:** Cleaned data + thresholds
- **Output:** `episodes.csv` — `Plant_ID`, `Episode_Start`, `Episode_End`, `Duration_Hours`, `Peak_Value`, `Pollutant`
- **Logic:** Consecutive readings above 2× threshold → group into episodes

#### T13: Change-point detection for drift alarms
- **Input:** Cleaned time-series per sensor
- **Output:** `drift_alarms.csv` — `Plant_ID`, `Stack_ID`, `Alarm_TS`, `Drift_Score`
- **Logic:** Rolling z-score or CUSUM → flag if mean shifts beyond 2σ

---

### Phase H: Spatial Analysis (T8, T17)

#### T8: Spatial interpolation grids for maps
- **Input:** Lat/Lon (from T0) + daily average pollutant values
- **Output:** `spatial_grid.csv` — interpolated PM2.5 values on a lat/lon grid
- **Logic:** Inverse Distance Weighting (IDW) from known sensor locations → grid of estimated values

#### T17: Hotspot ranking by persistence and intensity
- **Input:** Exceedance data + Lat/Lon
- **Output:** `hotspot_ranking.csv` — `Location`, `Persistence_Days`, `Avg_Exceedance_Pct`, `Rank`
- **Logic:** Days with exceedance × average % over limit → rank

---

### Phase I: Forecasting & Modeling (T16)

#### T16: Model features for forecasting PM2.5
- **Input:** All transformed data
- **Output:** `model_features.csv` with ML-ready columns
- **Features:**
  - Lag features: `PM25_lag_1h`, `PM25_lag_6h`, `PM25_lag_24h`
  - Rolling stats: `PM25_rolling_mean_6h`, `PM25_rolling_std_6h`
  - Time features: `Hour`, `DayOfWeek`, `IsWeekend`
  - Weather: `Wind_Speed`, `Temp_C`, `Humidity_RH`
  - Category: `Source_Type`, `Sector`

---

### Phase J: Impact & Privacy (T18, T14, T20)

#### T18: Control measure impact evaluation (pre/post)
- **Input:** Cleaned data + `industry_control_measures.csv`
- **Output:** `control_impact.csv` — `Plant_ID`, `Pre_Avg_PM25`, `Post_Avg_PM25`, `Reduction_Pct`
- **Logic:** Split data by `Install_Date` → compare averages before vs after

#### T14: Gap-filled vs raw comparison metrics
- **Input:** Cleaned data (GAP_FILLED status) + audit log
- **Output:** `gap_analysis.csv` — `Gap_Count`, `Gap_Duration`, `Data_Availability_Pct` per sensor
- **Logic:** Count GAP_FILLED rows per sensor, calculate % of expected readings received

#### T20: Open data extract with privacy safeguards
- **Input:** All transformed data
- **Output:** `open_data_extract.csv` — public-safe version
- **Logic:** Remove `Audit_Hash`, round Lat/Lon to 2 decimals, drop internal IDs, keep only aggregate metrics

---

## Output Files Summary

| Output File | Rules | Description |
|-------------|-------|-------------|
| `transformed_cems.csv` | T0,T1,T2,T3,T4,T9 | Main enriched dataset with all new columns |
| `hourly_profile.csv` | T10 | Average pollutant by hour-of-day |
| `compliance_report.csv` | T6 | Compliance rate per plant |
| `regulatory_report_*.csv` | T15 | CPCB-format reporting tables |
| `penalty_estimate.csv` | T19 | Financial penalty estimates |
| `episodes.csv` | T7 | High pollution event log |
| `drift_alarms.csv` | T13 | Sensor drift warnings |
| `spatial_grid.csv` | T8 | Interpolated map data |
| `hotspot_ranking.csv` | T17 | Worst polluters ranked |
| `model_features.csv` | T16 | ML-ready feature table |
| `control_impact.csv` | T18 | Before/after filter analysis |
| `gap_analysis.csv` | T14 | Data completeness metrics |
| `open_data_extract.csv` | T20 | Public-safe data release |
