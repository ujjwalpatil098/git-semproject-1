# ⚡ WattWise: Electricity Consumption Analysis & Environmental Intelligence Dashboard

> **A comprehensive, data-driven analytical dashboard and machine-learning intelligence platform for household electricity consumption patterns, behavioral clustering, structural change detection, carbon auditing, and intervention tracking.**

---

## 📌 Project Overview

**WattWise** is an advanced electricity analytics platform designed to analyze high-frequency minute-level household consumption data (over 2 million observations), extract behavioral patterns, identify structural shifts, estimate associated greenhouse gas emissions, and empower consumers to track the financial and energetic impact of energy-saving interventions.

The application is built on top of **Streamlit**, **Pandas**, **NumPy**, **Plotly**, **Scikit-Learn**, **SciPy**, **ReportLab**, and **SQLite**, combining interactive visual exploration with rigorous statistical tests.

---

## 🚀 Key Features

### 1. ⚡ Original Core Features (Preserved & Optimized)
- **Overview Dashboard**: High-level KPI summaries, dynamic daily area trend charts, monthly bar charts, and data previews.
- **Consumption Analysis**: Multi-granularity exploration (Daily, Weekly, Monthly), date range filtering, and sub-meter energy breakdowns (Kitchen, Laundry, Climate/Water Heating).
- **Anomaly Detection**: Interquartile Range (IQR) fence-based outlier flagging to detect unusually high daily consumption days with Excel export.
- **Energy Usage Review**: Daily consumption distribution histograms and heuristic recommendations based on observed usage.
- **Findings & Report Generation**: Multi-page formal PDF export via ReportLab and styled Excel metric downloads.
- **SQL Analytics**: Live, interactive SQLite query console connected directly to `electricity.db` with pre-built query templates and read-only parameterized security.

---

### 2. ⚡ Six Advanced Implemented Features

#### Feature 1: Smart Energy Savings Tracker
- **Empirical Before-and-After Comparison**: Compare consumption between equivalent baseline and follow-up observation periods (e.g. 7, 14, 21, or 30 days) before and after a recorded intervention date.
- **Key Metrics Displayed**:
  - Baseline daily mean (kWh/day) & total (kWh)
  - Follow-up daily mean (kWh/day) & total (kWh)
  - Absolute consumption difference ($\text{Baseline} - \text{Follow-up}$) in kWh
  - Percentage change ($\%$) relative to baseline
  - Estimated daily cost difference ($\Delta\text{kWh} \times \text{Tariff}$)
  - Estimated period cost difference ($\Delta\text{kWh} \times N_{\text{follow-up}} \times \text{Tariff}$)
- **Configurable Electricity Tariff**: Configurable in ₹/kWh (default ₹7.50/kWh).
- **SQLite Persistence**: Interventions are saved persistently in `electricity.db` (`energy_saving_actions` table) with full CRUD support (create, view, update, delete with explicit confirmation).
- **Timeline Comparison Visualization**: Time-series chart centered on the action date with shaded baseline/follow-up regimes and horizontal average reference lines.
- **Scientific Integrity**: Results are explicitly labeled as *observed consumption changes* rather than guaranteed causal savings, discussing weather and occupancy influences.

#### Feature 2: Consumption Behaviour Profiling (K-Means & PCA)
- **Vectorized Behavioural Feature Extraction**: Aggregates high-frequency data into Daily or Weekly observations and constructs 7 behavioural features:
  1. `total_kwh`: Total period consumption
  2. `peak_power_kw`: Maximum recorded active power
  3. `std_power_kw`: Power variability / standard deviation
  4. `evening_kwh`: Evening consumption (18:00 – 22:00)
  5. `overnight_kwh`: Overnight baseload consumption (00:00 – 06:00)
  6. `peak_to_avg_ratio`: Demand ratio ($\text{Peak} / \text{Mean}$)
  7. `is_weekend`: Weekend observation indicator
- **Standardization & Clustering**: Features are standardized with `StandardScaler` and clustered with `KMeans(random_state=42)`.
- **Clustering Evaluation**: Computes the **Silhouette Score** to evaluate cluster cohesion and separation.
- **Dimensionality Reduction (2D PCA)**: Projects the 7-dimensional feature space onto 2 principal components with explained variance percentages.
- **Data-Driven Cluster Labels**: Derives dynamic, statistics-grounded labels (e.g., *"Low Base · Evening Peak"*, *"High Intensity · Weekend Active"*, *"Moderate Usage"*).
- **Cluster Data Explorer**: Allows users to filter and inspect specific calendar dates assigned to each cluster and export to Excel.

#### Feature 3: Electricity Consumption Change-Point Detection
- **Structural Shifts vs. Point Anomalies**: Unlike anomaly detection (which flags isolated extreme days), change-point detection identifies sustained step shifts in the underlying baseline consumption or variance.
- **Dual Statistical Algorithms**:
  - **Offline CUSUM (Taylor)**: Evaluates cumulative sum deviations $S_k = \sum_{i=1}^k (x_i - \bar{x})$ against a Brownian bridge threshold ($h \cdot \sigma \sqrt{n}$) to identify structural change boundaries.
  - **Binary Segmentation**: Recursive partition search that minimizes sum-of-squares cost and validates step changes using Welch's two-sample t-test.
- **Adjustable Sensitivity & Granularity**: Configurable sensitivity threshold and minimum segment separation.
- **Interactive Visualization**: Marks detected change points with vertical markers and plots horizontal regime averages across consecutive periods.
- **Summary Table**: Tabulates change-point date, shift direction (▲ Step Up / ▼ Step Down), pre-shift mean, post-shift mean, absolute difference (kWh), and percentage difference (%).
- **Isolated Synthetic Benchmark Bench**: Built-in validation test bench with an injected, known step shift to prove algorithm sensitivity without touching the dashboard dataset.

#### Feature 4: Carbon Footprint Intelligence
- **Verified Greenhouse Gas Accounting**: Computes carbon emissions associated with electricity usage using documented grid emission factors:
  $$\text{Emissions (kg CO}_2\text{e)} = \text{Consumption (kWh)} \times \text{Factor (kg CO}_2\text{e/kWh)}$$
  $$\text{Emissions (Tonnes CO}_2\text{e)} = \frac{\text{Emissions (kg CO}_2\text{e)}}{1000}$$
- **Documented Emission Factors**:
  - **Central Electricity Authority (CEA) of India, CO2 Baseline Database (Version 19.0, 2023-24)**: National grid weighted average of **0.716 kg CO₂e/kWh**.
  - **CEA Thermal Generation Margin**: **0.820 kg CO₂e/kWh**.
  - **Renewable Hybrid Scenario**: **0.450 kg CO₂e/kWh**.
  - **Custom Factor**: Fully customizable for user-specified grid grids.
- **Interactive Visualizations**: Daily carbon emissions area charts, monthly total emissions bar charts, top 10 highest emitting calendar days, and date range filtering.
- **PDF Report Integration**: Carbon emission metrics and CEA methodology are automatically integrated into the downloadable formal PDF report.

#### Feature 5: Custom Dataset Upload & Data-Quality Audit
- **Zero-Overwrite Safety Guarantee**: Uploaded CSV files are processed in-memory for the active session. The primary dataset `cleaned_electricity_data.csv` and database `electricity.db` are never altered or overwritten.
- **Flexible Schema Mapping**:
  - Auto-detects combined DateTime or separate Date and Time columns.
  - Auto-detects active power / energy columns.
  - Allows manual user overrides and unit selection (kW, Watts, or pre-aggregated kWh).
  - Supports optional sub-metering circuit mapping.
- **Data-Quality Audit Report**:
  - Audits raw row count vs usable clean rows.
  - Identifies unparseable timestamps and invalid numeric entries.
  - Detects duplicate timestamps and averages them.
  - Clips negative power readings with transparent warnings.
- **Session Dataset Switcher**: Prominent status pills indicate whether the dashboard is analyzing the default dataset or an uploaded CSV, with a one-click "Restore Default Dataset" button.

#### Feature 6: Confidence-Aware Intelligent Insights
- **Evidence-Graded Recommendations**: Discards arbitrary confidence scores in favor of transparent, defensible evidence grading:
  - 🟢 **HIGH EVIDENCE**: Sample size $N \ge 30$, $<5\%$ missingness, statistically significant effect ($p < 0.001$).
  - 🟡 **MODERATE EVIDENCE**: Moderate sample size ($10 \le N < 30$), or moderate variance ($p < 0.05$).
  - 🔴 **LOW EVIDENCE**: Sparse data ($N < 10$), or high uncertainty.
- **Statistical Analyses**:
  1. **Weekend vs. Weekday Disparity**: Two-sample Welch's t-test with Cohen's d effect size calculation.
  2. **Continuous Baseload & Standby Power**: 10th percentile active power draw between 01:00 AM and 04:00 AM to isolate phantom vampire loads.
  3. **Diurnal Peak Concentration**: Identification of the peak demand hour and peak-to-average ratio.
  4. **Dominant Sub-Circuit Load**: End-use breakdown of kitchen, laundry, and climate systems.
  5. **Consumption Volatility & Extreme Outliers**: Interquartile range (IQR) fences.
- **Actionable Advice**: Tailored, plain-language recommendations and explicitly stated analytical limitations.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend & UI** | Streamlit, Plotly Express, Plotly Graph Objects, Custom CSS (Space Grotesk & DM Sans) |
| **Data Processing** | Python 3.x, Pandas, NumPy |
| **Machine Learning & Stats** | Scikit-Learn (KMeans, StandardScaler, PCA, Silhouette Score), SciPy (stats, ttest, CUSUM) |
| **Persistence** | SQLite3 (`electricity.db`) with parameterized SQL queries |
| **Export & Reporting** | ReportLab (A4 PDF engine), OpenPyXL (formatted Excel spreadsheets) |
| **Testing** | Python `unittest` framework |

---

## 📂 Project Structure

```
Electricity_protocol/
├── dashboard.py                  # Main Streamlit dashboard application (orchestrator & views)
├── requirements.txt              # Production dependency specifications
├── cleaned_electricity_data.csv  # Cleaned household power dataset (~2.05M rows, 244 MB)
├── electricity.db                # SQLite database (tables: electricity_data, energy_saving_actions)
├── modules/                      # Modular backend packages
│   ├── __init__.py
│   ├── db.py                     # SQLite connection, CRUD queries, and parameterized runner
│   ├── dataset_manager.py        # Custom CSV upload, validation, and schema mapping engine
│   ├── savings_tracker.py        # Smart energy savings tracker math & impact evaluation
│   ├── profiling.py              # Behavioral feature engineering, K-Means & 2D PCA
│   ├── changepoint.py            # Offline CUSUM & Binary Segmentation change-point algorithms
│   ├── carbon.py                 # Carbon emissions calculation & CEA grid emission factors
│   └── insights_engine.py        # Confidence-aware evidence grading & statistical insights
├── tests/
│   └── test_features.py          # 14 comprehensive unit tests covering all features & edge cases
├── create_database.ipynb         # Database ingestion notebook
├── EDA.ipynb                     # Exploratory Data Analysis notebook
└── dataset.ipynb                 # Dataset cleaning and transformation notebook
```

---

## ⚙️ Installation & Setup

### 1. Clone or Open the Workspace
Ensure you are in the project root directory:
```bash
cd Electricity_protocol
```

### 2. Install Dependencies
Install all required packages using pip:
```bash
pip install -r requirements.txt
```

### 3. Verify SQLite Database
The SQLite database `electricity.db` is already initialized. The application will automatically verify and create the `energy_saving_actions` table upon launch.

---

## ▶️ How to Run the Application

Start the Streamlit dashboard by running:
```bash
streamlit run dashboard.py
```
The application will launch in your default web browser (typically at `http://localhost:8501`).

---

## 🧪 Running Automated Tests

Run the comprehensive unit test suite to verify calculation correctness, edge case handling, and persistence:
```bash
python -m unittest tests/test_features.py -v
```

---

## 📊 Dataset Schema

| Column | Type | Unit | Description |
| :--- | :--- | :--- | :--- |
| `Date` | string | `YYYY-MM-DD` | Date of reading |
| `Time` | string | `HH:MM:SS` | Time of reading (1-minute frequency) |
| `Global_active_power` | float | **kW** | Household global active power |
| `Global_reactive_power` | float | **kVAR** | Household global reactive power |
| `Voltage` | float | **V** | Minute-averaged line voltage |
| `Global_intensity` | float | **A** | Current intensity |
| `Sub_metering_1` | float | **Wh** | Kitchen appliances (dishwasher, microwave, oven) |
| `Sub_metering_2` | float | **Wh** | Laundry room appliances (washing machine, refrigerator) |
| `Sub_metering_3` | float | **Wh** | Climate control & electric water heater |
| `Datetime` | string | `YYYY-MM-DD HH:MM:SS` | Combined ISO timestamp |
| `Energy_kWh` | float | **kWh** | Derived 1-minute energy: `Global_active_power / 60` |

---

## 🧮 Mathematical Formulations

### 1. Energy Calculation
$$\text{Daily Consumption (kWh)} = \sum_{t=1}^{1440} \frac{\text{Global\_active\_power}_t \text{ (kW)}}{60}$$

### 2. Intervention Savings & Financial Impact
$$\Delta\text{kWh}_{\text{daily}} = \overline{\text{kWh}}_{\text{baseline}} - \overline{\text{kWh}}_{\text{followup}}$$
$$\text{Percentage Change (\%)} = \left(\frac{\Delta\text{kWh}_{\text{daily}}}{\overline{\text{kWh}}_{\text{baseline}}}\right) \times 100$$
$$\text{Estimated Period Cost Difference (₹)} = \Delta\text{kWh}_{\text{daily}} \times N_{\text{followup}} \times \text{Tariff (₹/kWh)}$$

### 3. Cumulative Sum (CUSUM) Formulation
$$S_k = \sum_{i=1}^k (x_i - \bar{x}), \quad k = 1, \dots, n$$
A structural change is flagged when the range exceeds the critical boundary:
$$\max(S_k) - \min(S_k) > h \cdot \sigma \sqrt{n}$$

---

## ⚠️ Academic Presentation Guidance & Limitations

When presenting this project in a college or technical seminar:
1. **Causation vs. Correlation**: Clearly disclose that before-and-after reductions observed in the Energy Savings Tracker indicate statistical shifts, not definitive causal proof. External variables such as seasonal temperature changes, appliance duty cycles, and resident travel also influence consumption.
2. **Static Grid Emission Factor**: Note that greenhouse gas calculations use the Central Electricity Authority (CEA) weighted average emission factor (0.716 kg CO₂e/kWh), which is an annual average rather than real-time marginal hourly emissions.
3. **Sub-Metering Coverage**: Sub-meters 1, 2, and 3 monitor specific high-draw circuits; unmonitored circuits (lighting, general wall sockets, entertainment devices) account for the difference between total active power and sub-meter sums.
