import streamlit as st
import pandas as pd
from pathlib import Path
from io import StringIO

# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="Electricity Consumption Analysis Dashboard",
    page_icon="⚡",
    layout="wide"
)

DATA_FILE = Path("cleaned_householddata.csv")


# ---------------------------------------------------------
# LOAD AND PREPARE DATA
# ---------------------------------------------------------
@st.cache_data
def load_data(file_path):
    data = pd.read_csv(file_path)
    data.columns = data.columns.str.strip()

    if "DateTime" not in data.columns:
        if "Date" not in data.columns or "Time" not in data.columns:
            raise ValueError("The dataset must contain DateTime or both Date and Time columns.")
        data["DateTime"] = pd.to_datetime(
            data["Date"].astype(str) + " " + data["Time"].astype(str),
            dayfirst=True,
            errors="coerce"
        )
    else:
        data["DateTime"] = pd.to_datetime(data["DateTime"], errors="coerce")

    numeric_columns = [
        "Global_active_power",
        "Global_reactive_power",
        "Voltage",
        "Global_intensity",
        "Sub_metering_1",
        "Sub_metering_2",
        "Sub_metering_3",
    ]

    for column in numeric_columns:
        if column in data.columns:
            data[column] = pd.to_numeric(data[column], errors="coerce")

    data = data.dropna(subset=["DateTime", "Global_active_power"])
    data = data.sort_values("DateTime").reset_index(drop=True)
    return data


st.sidebar.title("⚡ Energy Dashboard")
st.sidebar.caption("Electricity Consumption Analysis")
page = st.sidebar.radio(
    "Go to",
    [
        "🏠 Overview",
        "📊 Consumption Analysis",
        "🚨 Anomaly Detection",
        "⭐ Energy Efficiency",
        "💡 Insights & Recommendations",
        "🗄️ SQL Analytics",
    ],
)

st.sidebar.divider()
st.sidebar.caption("Data source: cleaned household electricity dataset")

if not DATA_FILE.exists():
    st.error(
        f"Could not find `{DATA_FILE.name}`. Place it in the same folder as "
        "this Python file, then run the dashboard again."
    )
    st.stop()

try:
    df = load_data(str(DATA_FILE))
except Exception as error:
    st.error(f"Could not load the dataset: {error}")
    st.stop()

if df.empty:
    st.error("The dataset contains no usable rows after loading.")
    st.stop()

# Daily electricity energy estimate:
# Global_active_power is in kW and observations are approximately one minute apart.
# Dividing the sum by 60 converts observed minute-level kW readings to kWh.
daily = (
    df.set_index("DateTime")["Global_active_power"]
    .resample("D")
    .sum()
    .div(60)
    .rename("Consumption (kWh)")
)
daily = daily.dropna()

# Reusable statistics
total_kwh = float(daily.sum())
average_daily_kwh = float(daily.mean()) if not daily.empty else 0.0
peak_date = daily.idxmax() if not daily.empty else None
peak_kwh = float(daily.max()) if not daily.empty else 0.0
start_date = df["DateTime"].min()
end_date = df["DateTime"].max()

st.sidebar.write(f"**Records:** {len(df):,}")
st.sidebar.write(f"**Period:** {start_date:%d %b %Y} – {end_date:%d %b %Y}")


# ---------------------------------------------------------
# OVERVIEW
# ---------------------------------------------------------
if page == "🏠 Overview":
    st.title("⚡ Electricity Consumption Analysis Dashboard")
    st.write(
        "Explore household electricity usage using the cleaned dataset "
        "and calculated consumption statistics."
    )
    st.caption(
        "Daily energy is estimated from the available one-minute readings. "
        "Because preprocessing removed rows with missing values, totals may be underestimated."
    )
    st.divider()
    st.subheader("📌 Consumption Overview")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Observed Consumption", f"{total_kwh:,.2f} kWh")
    col2.metric("Average Daily Consumption", f"{average_daily_kwh:,.2f} kWh")
    col3.metric("Highest Daily Consumption", f"{peak_kwh:,.2f} kWh")
    col4.metric("Usable Records", f"{len(df):,}")

    st.divider()
    st.subheader("📈 Daily Consumption Trend")
    st.line_chart(daily)

    monthly = daily.resample("MS").sum().dropna()
    if not monthly.empty:
        st.subheader("🗓️ Monthly Consumption")
        monthly.index = monthly.index.strftime("%b %Y")
        st.bar_chart(monthly)

    st.subheader("📋 Dataset Preview")
    st.dataframe(df.head(10), use_container_width=True)

    st.info(
        "Cost and an official efficiency score are not displayed yet because "
        "a tariff and a validated scoring method have not been configured."
    )


# ---------------------------------------------------------
# CONSUMPTION ANALYSIS
# ---------------------------------------------------------
elif page == "📊 Consumption Analysis":
    st.title("📊 Consumption Analysis")
    st.write("Select a time scale and date range to explore consumption.")

    min_date = df["DateTime"].min().date()
    max_date = df["DateTime"].max().date()

    date_col1, date_col2 = st.columns(2)
    with date_col1:
        from_date = st.date_input("Start date", value=min_date, min_value=min_date, max_value=max_date)
    with date_col2:
        to_date = st.date_input("End date", value=max_date, min_value=min_date, max_value=max_date)

    period = st.selectbox("Analysis period", ["Daily", "Weekly", "Monthly"])

    if from_date > to_date:
        st.warning("Start date must be on or before the end date.")
        st.stop()

    filtered = df[
        (df["DateTime"].dt.date >= from_date)
        & (df["DateTime"].dt.date <= to_date)
    ].copy()

    if filtered.empty:
        st.warning("No records were found for the selected date range.")
        st.stop()

    selected_daily = (
        filtered.set_index("DateTime")["Global_active_power"]
        .resample("D").sum().div(60).rename("Consumption (kWh)")
    ).dropna()

    if period == "Daily":
        chart_series = selected_daily
    elif period == "Weekly":
        chart_series = selected_daily.resample("W").sum().dropna()
    else:
        chart_series = selected_daily.resample("MS").sum().dropna()

    st.subheader(f"{period} Consumption Trend")
    st.line_chart(chart_series)

    if not selected_daily.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Consumption in Selected Period", f"{selected_daily.sum():,.2f} kWh")
        c2.metric("Average Daily Consumption", f"{selected_daily.mean():,.2f} kWh")
        c3.metric("Peak Day", f"{selected_daily.max():,.2f} kWh")
        st.write(f"**Peak date:** {selected_daily.idxmax():%d %b %Y}")

    st.divider()
    st.subheader("🔌 Sub-Metering Comparison")

    submeter_columns = [
        "Sub_metering_1",
        "Sub_metering_2",
        "Sub_metering_3",
    ]
    available_submeters = [c for c in submeter_columns if c in filtered.columns]

    if available_submeters:
        # Sub-meter readings are Wh per one-minute interval; sum / 1000 gives kWh.
        submeter_totals = (filtered[available_submeters].sum() / 1000).rename("Observed energy (kWh)")
        submeter_totals.index = [
            {
                "Sub_metering_1": "Kitchen appliances",
                "Sub_metering_2": "Laundry appliances",
                "Sub_metering_3": "Water heater / AC",
            }.get(name, name)
            for name in submeter_totals.index
        ]
        st.bar_chart(submeter_totals)
        st.dataframe(
            submeter_totals.rename_axis("Sub-meter category").reset_index(),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("Sub-metering columns were not found in the dataset.")


# ---------------------------------------------------------
# ANOMALY DETECTION
# ---------------------------------------------------------
elif page == "🚨 Anomaly Detection":
    st.title("🚨 Unusually High Daily Consumption")
    st.write(
        "This page flags daily consumption values outside the IQR range. "
        "These are statistical outliers and are not automatically errors."
    )

    q1 = daily.quantile(0.25)
    q3 = daily.quantile(0.75)
    iqr = q3 - q1
    lower_limit = q1 - 1.5 * iqr
    upper_limit = q3 + 1.5 * iqr

    # Daily energy cannot be negative; high-use flags are based on the upper IQR threshold.
    unusual_days = daily[daily > upper_limit].sort_values(ascending=False)

    c1, c2, c3 = st.columns(3)
    c1.metric("High-Consumption Days Flagged", f"{len(unusual_days):,}")
    c2.metric("Upper IQR Threshold", f"{upper_limit:.2f} kWh/day")
    c3.metric(
        "Highest Flagged Day",
        f"{unusual_days.max():.2f} kWh" if not unusual_days.empty else "None"
    )

    chart = daily.rename("Daily consumption (kWh)").to_frame()
    chart["Upper IQR threshold"] = upper_limit
    st.subheader("Daily Consumption and Outlier Threshold")
    st.line_chart(chart)

    st.subheader("Flagged Days")
    if unusual_days.empty:
        st.success("No days exceeded the current upper IQR threshold.")
    else:
        outlier_table = unusual_days.rename("Consumption (kWh)").to_frame()
        outlier_table.index.name = "Date"
        st.dataframe(outlier_table, use_container_width=True)

    st.caption(
        f"IQR lower limit: {lower_limit:.2f} kWh/day. "
        f"IQR upper limit: {upper_limit:.2f} kWh/day. "
        "This dashboard flags high daily values only."
    )


# ---------------------------------------------------------
# ENERGY EFFICIENCY
# ---------------------------------------------------------
elif page == "⭐ Energy Efficiency":
    st.title("⭐ Energy Usage Review")
    st.write(
        "This page summarizes consumption patterns that may help users "
        "investigate energy-saving opportunities."
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Average Daily Consumption", f"{average_daily_kwh:.2f} kWh")
    c2.metric("Highest Daily Consumption", f"{peak_kwh:.2f} kWh")
    c3.metric(
        "Peak Day Compared with Average",
        f"{(peak_kwh / average_daily_kwh):.1f}×" if average_daily_kwh > 0 else "N/A"
    )

    st.subheader("Daily Consumption Distribution")
    st.bar_chart(daily)

    st.subheader("Practical Recommendations")
    st.write("- Review days that exceed the usual consumption range.")
    st.write("- Compare monthly usage to identify periods with increased consumption.")
    st.write("- Investigate which sub-meter categories account for more observed energy.")
    st.warning(
        "A formal efficiency score, percentage savings, and estimated bill require "
        "a defined scoring method, comparison baseline, and electricity tariff. "
        "They are intentionally not guessed here."
    )


# ---------------------------------------------------------
# INSIGHTS AND RECOMMENDATIONS
# ---------------------------------------------------------
elif page == "💡 Insights & Recommendations":
    st.title("💡 Insights & Recommendations")

    st.subheader("📌 Data-Based Findings")
    st.write(f"- The cleaned dataset contains **{len(df):,} usable records**.")
    st.write(
        f"- The available timestamps range from **{start_date:%d %b %Y}** "
        f"to **{end_date:%d %b %Y}**."
    )
    st.write(f"- Average observed daily consumption is **{average_daily_kwh:.2f} kWh**.")
    if peak_date is not None:
        st.write(
            f"- The highest observed daily consumption is **{peak_kwh:.2f} kWh**, "
            f"on **{peak_date:%d %b %Y}**."
        )

    monthly = daily.resample("MS").sum().dropna()
    if not monthly.empty:
        highest_month = monthly.idxmax()
        lowest_month = monthly.idxmin()
        st.write(
            f"- Highest total month in the available data: **{highest_month:%B %Y}** "
            f"({monthly.max():.2f} kWh)."
        )
        st.write(
            f"- Lowest total month in the available data: **{lowest_month:%B %Y}** "
            f"({monthly.min():.2f} kWh)."
        )
        st.subheader("Monthly Consumption")
        monthly.index = monthly.index.strftime("%b %Y")
        st.bar_chart(monthly)

    st.subheader("🎯 Recommendations")
    st.write("- Inspect unusually high daily consumption before deciding whether it is an error.")
    st.write("- Compare monthly totals and investigate large increases.")
    st.write("- Review the three sub-meter categories to understand their contribution.")
    st.write("- Keep missing-data limitations in mind when interpreting totals.")

    peak_date_text = peak_date.strftime("%Y-%m-%d") if peak_date is not None else "N/A"
    report = f"""Electricity Consumption Analysis Report

Data source: {DATA_FILE.name}
Records used: {len(df):,}
Date range: {start_date:%Y-%m-%d} to {end_date:%Y-%m-%d}
Estimated observed consumption total: {total_kwh:.2f} kWh
Average daily consumption: {average_daily_kwh:.2f} kWh
Highest daily consumption: {peak_kwh:.2f} kWh
Peak date: {peak_date_text}

Note: Daily energy is calculated from available minute-level active-power readings.
Rows removed during preprocessing may cause consumption totals to be underestimated.
Cost and efficiency score are not calculated because tariff and scoring assumptions
have not been provided.
"""
    st.download_button(
        "📥 Download Analysis Report",
        data=report,
        file_name="electricity_analysis_report.txt",
        mime="text/plain",
    )


# ---------------------------------------------------------
# SQL ANALYTICS
# ---------------------------------------------------------
elif page == "🗄️ SQL Analytics":
    st.title("🗄️ Structured Consumption Summary")
    st.write(
        "This page currently uses Pandas to summarize the loaded CSV. "
        "A live SQL database connection has not been configured yet."
    )

    submeter_columns = [
        "Sub_metering_1",
        "Sub_metering_2",
        "Sub_metering_3",
    ]
    available_submeters = [c for c in submeter_columns if c in df.columns]

    if available_submeters:
        summary = (df[available_submeters].sum() / 1000).rename("Observed energy (kWh)")
        summary.index.name = "Sub-meter"
        st.dataframe(summary.reset_index(), use_container_width=True, hide_index=True)
        st.bar_chart(summary)

    st.subheader("Example SQL query for a future database connection")
    st.code(
        "SELECT DATE(DateTime) AS usage_date, "
        "SUM(Global_active_power) / 60 AS consumption_kwh "
        "FROM electricity_data "
        "GROUP BY DATE(DateTime) "
        "ORDER BY usage_date;",
        language="sql",
    )
    st.caption("The SQL statement is an example; it is not executed by this version.")
