# Transformation Phase — Walkthrough

## What Was Done
Built and executed the full transformation pipeline ([04_transformation.py](file:///s:/1.capg_case_Study/notebooks/04_transformation.py) → [.ipynb](file:///s:/1.capg_case_Study/notebooks/02_cleaning.ipynb)) applying all **20+1 transformation rules** (T0–T20) to the cleaned CEMS data.

## Input Data
| File | Source |
|------|--------|
| [cleaned/dev/raw_cems_data_cleaned.csv](file:///s:/1.capg_case_Study/cleaned/dev/raw_cems_data_cleaned.csv) | 6,000 rows, 14 cols — Phase 2 output |
| [datasets/dev/sensor_master.csv](file:///s:/1.capg_case_Study/datasets/dev/sensor_master.csv) | 10 sensors (5 stack + 5 ambient) |
| [datasets/dev/regulatory_thresholds.csv](file:///s:/1.capg_case_Study/datasets/dev/regulatory_thresholds.csv) | 6 CPCB legal limits |
| [datasets/dev/transformation/meteorology_data.csv](file:///s:/1.capg_case_Study/datasets/dev/transformation/meteorology_data.csv) | 672 hourly weather records |
| [datasets/dev/transformation/aqi_standards_cpcb.csv](file:///s:/1.capg_case_Study/datasets/dev/transformation/aqi_standards_cpcb.csv) | 15 breakpoint rows |
| [datasets/dev/transformation/emission_factors.csv](file:///s:/1.capg_case_Study/datasets/dev/transformation/emission_factors.csv) | 9 AP-42 factors |
| [datasets/dev/transformation/industry_control_measures.csv](file:///s:/1.capg_case_Study/datasets/dev/transformation/industry_control_measures.csv) | 5 filter installs |
| [datasets/dev/transformation/compliance_penalty_rules.csv](file:///s:/1.capg_case_Study/datasets/dev/transformation/compliance_penalty_rules.csv) | 9 fine schedule rows |

## Rules Applied

| Rule | What It Does | Output |
|------|-------------|--------|
| **T0** | Split `Lat_Lon` → `Latitude`, `Longitude` floats | Enriched main dataset |
| **T1** | Per-pollutant exceedance flags (PM2.5/SO2/NOx vs CPCB limits) | `Exceed_PM25`, `Exceed_SO2`, `Exceed_NOx`, `Any_Exceedance` |
| **T2** | AQI sub-index computation using CPCB breakpoints + linear interpolation | `AQI_PM25`, `AQI_SO2`, `AQI_NOx`, `AQI_Overall`, `AQI_Category` |
| **T3** | Emission load (kg/day) = concentration × flow × 24/1e9 (stack only) | `Load_PM25_kg_day`, `Load_SO2_kg_day`, `Load_NOx_kg_day` |
| **T4** | Rolling 24h moving averages and P95 percentiles (window=96) | `PM25_24h_avg`, `PM25_24h_p95`, etc. |
| **T5** | Wind-weighted source contribution score for ambient sensors | `Wind_Contribution_Score` |
| **T6** | Compliance rate per plant = (total - exceedances) / total × 100 | [compliance_report.csv](file:///s:/1.capg_case_Study/transformed/dev/compliance_report.csv) |
| **T7** | Episode detection: sustained periods > 2× threshold | [episodes.csv](file:///s:/1.capg_case_Study/transformed/dev/episodes.csv) |
| **T8** | Spatial IDW interpolation on 10×10 lat/lon grid | [spatial_grid.csv](file:///s:/1.capg_case_Study/transformed/dev/spatial_grid.csv) |
| **T9** | Health risk proxy = AQI_PM25 × 0.25 (per 15-min reading) | `Health_Risk_Score` |
| **T10** | Hourly diurnal profiles (avg pollution by hour-of-day) | [hourly_profile.csv](file:///s:/1.capg_case_Study/transformed/dev/hourly_profile.csv) |
| **T11** | Meteorology join (wind, temp, humidity) via Location_ID + hourly TS | `Wind_Speed_kmh`, `Wind_Dir_deg`, `Temp_C`, `Humidity_RH` |
| **T12** | Emission factor comparison (measured vs expected by sector) | [emission_factor_comparison.csv](file:///s:/1.capg_case_Study/transformed/dev/emission_factor_comparison.csv) |
| **T13** | CUSUM drift alarm detection per sensor | [drift_alarms.csv](file:///s:/1.capg_case_Study/transformed/dev/drift_alarms.csv) |
| **T14** | Gap-filled vs raw data availability per sensor | [gap_analysis.csv](file:///s:/1.capg_case_Study/transformed/dev/gap_analysis.csv) |
| **T15** | Regulatory reporting (daily stack + ambient summaries) | [regulatory_report_stack.csv](file:///s:/1.capg_case_Study/transformed/dev/regulatory_report_stack.csv), [regulatory_report_ambient.csv](file:///s:/1.capg_case_Study/transformed/dev/regulatory_report_ambient.csv) |
| **T16** | ML feature engineering (lags, rolling stats, time encoding, weather) | [model_features.csv](file:///s:/1.capg_case_Study/transformed/dev/model_features.csv) |
| **T17** | Hotspot ranking by persistence × intensity | [hotspot_ranking.csv](file:///s:/1.capg_case_Study/transformed/dev/hotspot_ranking.csv) |
| **T18** | Control measure pre/post impact analysis | [control_impact.csv](file:///s:/1.capg_case_Study/transformed/dev/control_impact.csv) |
| **T19** | Compliance penalty estimation (INR fines by severity) | [penalty_estimate.csv](file:///s:/1.capg_case_Study/transformed/dev/penalty_estimate.csv) |
| **T20** | Open data extract (privacy-safe, no hashes, rounded coords) | [open_data_extract.csv](file:///s:/1.capg_case_Study/transformed/dev/open_data_extract.csv) |

## Output Files Summary (13 files in `transformed/dev/`)
- **Main enriched dataset**: `transformed_cems.csv` — all new columns added to CEMS
- **12 derived tables**: compliance, episodes, spatial, drift, gap, regulatory, ML, hotspot, control impact, penalty, emission factors, open data

## Testing
- Script ran end-to-end without errors on dev dataset
- All 13 output CSV files generated and verified
- Converted to Jupyter notebook via `jupytext`

## Key Files
- [04_transformation.py](file:///s:/1.capg_case_Study/notebooks/04_transformation.py) — Main script
- [04_transformation.ipynb](file:///s:/1.capg_case_Study/notebooks/04_transformation.ipynb) — Notebook version
- [transformation_plan.md](file:///s:/1.capg_case_Study/transformation_plan.md) — Detailed plan
