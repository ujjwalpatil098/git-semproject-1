import os
import pandas as pd
import matplotlib.pyplot as plt

# 1. LOAD CLEANED DATA
df = pd.read_csv("cleaned_householddata.csv")

df["DateTime"] = pd.to_datetime(df["DateTime"])
df = df.sort_values("DateTime")

# 2. CREATE OUTPUT FOLDER
os.makedirs("EDA_Results", exist_ok=True)

# 3. DAILY ELECTRICITY CONSUMPTION
daily = df.set_index("DateTime")["Global_active_power"].resample("D").sum() / 60

daily = daily.dropna()

print("\nDaily Consumption Summary (kWh)")
print(daily.describe().round(2))

plt.figure(figsize=(12, 5))
daily.plot()
plt.title("Daily Electricity Consumption")
plt.xlabel("Date")
plt.ylabel("Energy Consumption (kWh)")
plt.tight_layout()
plt.savefig("EDA_Results/daily_consumption.png")
plt.show()

# 4. CONSUMPTION DISTRIBUTION
plt.figure(figsize=(10, 5))
df["Global_active_power"].hist(bins=50)
plt.title("Global Active Power Distribution")
plt.xlabel("Global Active Power (kW)")
plt.ylabel("Frequency")
plt.tight_layout()
plt.savefig("EDA_Results/consumption_distribution.png")
plt.show()

# 5. MONTHLY CONSUMPTION
monthly = daily.resample("MS").sum().dropna()
monthly.index = monthly.index.strftime("%b %Y")

plt.figure(figsize=(12, 5))
monthly.plot(kind="bar")
plt.title("Monthly Electricity Consumption")
plt.xlabel("Month")
plt.ylabel("Energy Consumption (kWh)")
plt.tight_layout()
plt.savefig("EDA_Results/monthly_consumption.png")
plt.show()

# 6. SUB-METERING COMPARISON
submeter_columns = [
    "Sub_metering_1",
    "Sub_metering_2",
    "Sub_metering_3"
]

submeter_means = df[submeter_columns].mean()

print("\nAverage Sub-Metering Readings")
print(submeter_means.round(2))

plt.figure(figsize=(8, 5))
submeter_means.plot(kind="bar")
plt.title("Average Sub-Metering Readings")
plt.xlabel("Sub-Meter")
plt.ylabel("Average Reading (Wh per minute)")
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig("EDA_Results/submeter_comparison.png")
plt.show()

print("\nEDA visualizations completed.")
print("Charts saved in the EDA_Results folder.")


# 7. CORRELATION ANALYSIS

correlation_columns = [
    "Global_active_power",
    "Global_reactive_power",
    "Voltage",
    "Global_intensity",
    "Sub_metering_1",
    "Sub_metering_2",
    "Sub_metering_3"
]

correlation_matrix = df[correlation_columns].corr()

print("\nCorrelation Matrix")
print(correlation_matrix.round(2))

plt.figure(figsize=(10, 8))

plt.imshow(correlation_matrix, cmap="coolwarm", vmin=-1, vmax=1)

plt.colorbar(label="Correlation Coefficient")
plt.xticks(
    range(len(correlation_columns)),
    correlation_columns,
    rotation=45,
    ha="right"
)
plt.yticks(range(len(correlation_columns)), correlation_columns)

for i in range(len(correlation_columns)):
    for j in range(len(correlation_columns)):
        plt.text(
            j, i,
            f"{correlation_matrix.iloc[i, j]:.2f}",
            ha="center",
            va="center",
            fontsize=8
        )

plt.title("Correlation Between Electricity Measurements")
plt.tight_layout()
plt.savefig("EDA_Results/correlation_heatmap.png")
plt.show()


# 8. OUTLIER ANALYSIS USING IQR

outlier_columns = [
    "Global_active_power",
    "Global_intensity",
    "Voltage"
]

print("\nOutlier Analysis (IQR Method)")

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

for i, column in enumerate(outlier_columns):
    q1 = df[column].quantile(0.25)
    q3 = df[column].quantile(0.75)
    iqr = q3 - q1

    lower_limit = q1 - 1.5 * iqr
    upper_limit = q3 + 1.5 * iqr

    outliers = df[
        (df[column] < lower_limit) |
        (df[column] > upper_limit)
    ]

    print(f"\n{column}")
    print(f"Lower limit: {lower_limit:.2f}")
    print(f"Upper limit: {upper_limit:.2f}")
    print(f"Outlier count: {len(outliers)}")
    print(f"Outlier percentage: {len(outliers) / len(df) * 100:.2f}%")

    axes[i].boxplot(df[column].dropna())
    axes[i].set_title(column)
    axes[i].set_ylabel("Reading")

plt.suptitle("Outlier Analysis of Electricity Measurements")
plt.tight_layout()
plt.savefig("EDA_Results/outlier_analysis.png")
plt.show()