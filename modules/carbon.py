"""
Carbon Footprint Intelligence.
Calculates and visualizes estimated greenhouse gas emissions associated with electricity usage
based on documented grid emission factors (e.g., Central Electricity Authority of India).
"""
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np


# Central Electricity Authority (CEA), Government of India
# CO2 Baseline Database for the Indian Power Sector (Version 19, 2023/24)
CEA_NATIONAL_GRID_FACTOR = 0.716  # kg CO2e / kWh (Weighted average of Indian Grid)
CEA_THERMAL_WEIGHTED_FACTOR = 0.820  # kg CO2e / kWh (Thermal dominant mix)
RENEWABLE_HYBRID_FACTOR = 0.450  # kg CO2e / kWh (Solar/Wind integrated utility mix)


PRESET_EMISSION_FACTORS = {
    "India CEA National Grid Average (0.716 kg CO₂e/kWh)": {
        "factor": CEA_NATIONAL_GRID_FACTOR,
        "source": "Central Electricity Authority (CEA), Govt. of India (CO₂ Baseline Database Ver 19.0, 2023-24)",
        "scope": "All-India Grid Weighted Average (including hydro, renewables, thermal, nuclear)",
    },
    "India Thermal Generation Mix (0.820 kg CO₂e/kWh)": {
        "factor": CEA_THERMAL_WEIGHTED_FACTOR,
        "source": "CEA User Guide Ver 19.0 (Thermal Generation specific grid margin)",
        "scope": "Coal and gas dominant generation baseline",
    },
    "Clean Energy / Solar-Heavy Mix (0.450 kg CO₂e/kWh)": {
        "factor": RENEWABLE_HYBRID_FACTOR,
        "source": "Derived illustrative hybrid renewable/grid blend",
        "scope": "40%+ renewable integration scenario",
    },
}


def calculate_emissions(
    consumption_kwh: float,
    emission_factor: float = CEA_NATIONAL_GRID_FACTOR,
) -> Dict[str, float]:
    """
    Compute total carbon emissions from electricity consumption.
    Formula:
      Emissions (kg CO2e) = Consumption (kWh) * Emission Factor (kg CO2e/kWh)
      Emissions (Tonnes CO2e) = Emissions (kg CO2e) / 1000
    """
    if consumption_kwh < 0 or emission_factor < 0:
        return {"consumption_kwh": 0.0, "emissions_kg": 0.0, "emissions_tonnes": 0.0}

    kg_co2 = consumption_kwh * emission_factor
    tonnes_co2 = kg_co2 / 1000.0

    return {
        "consumption_kwh": float(consumption_kwh),
        "emissions_kg": float(kg_co2),
        "emissions_tonnes": float(tonnes_co2),
        "emission_factor": float(emission_factor),
    }


def compute_daily_emissions(
    daily_series: pd.Series,
    emission_factor: float = CEA_NATIONAL_GRID_FACTOR,
) -> pd.DataFrame:
    """
    Generate daily emissions time series with kilograms and cumulative tonnes.
    """
    if daily_series.empty:
        return pd.DataFrame(columns=["Date", "Consumption (kWh)", "Emissions (kg CO2e)", "Emissions (Tonnes CO2e)"])

    df = daily_series.rename("Consumption (kWh)").reset_index()
    date_col = "DateTime" if "DateTime" in df.columns else df.columns[0]
    df["Date"] = pd.to_datetime(df[date_col])
    df["Emissions (kg CO2e)"] = df["Consumption (kWh)"] * emission_factor
    df["Emissions (Tonnes CO2e)"] = df["Emissions (kg CO2e)"] / 1000.0
    return df.sort_values("Date").reset_index(drop=True)


def compute_monthly_emissions(
    daily_series: pd.Series,
    emission_factor: float = CEA_NATIONAL_GRID_FACTOR,
) -> pd.DataFrame:
    """
    Aggregate monthly carbon emissions.
    """
    if daily_series.empty:
        return pd.DataFrame()

    mon_kwh = daily_series.resample("MS").sum().dropna()
    mdf = mon_kwh.rename("Consumption (kWh)").reset_index()
    mdf["Month"] = pd.to_datetime(mdf.iloc[:, 0])
    mdf["Month_Label"] = mdf["Month"].dt.strftime("%b %Y")
    mdf["Emissions (kg CO2e)"] = mdf["Consumption (kWh)"] * emission_factor
    mdf["Emissions (Tonnes CO2e)"] = mdf["Emissions (kg CO2e)"] / 1000.0
    return mdf


def find_highest_emission_days(
    daily_series: pd.Series,
    emission_factor: float = CEA_NATIONAL_GRID_FACTOR,
    top_n: int = 10,
) -> pd.DataFrame:
    """
    Identify the highest carbon-emitting calendar days.
    """
    if daily_series.empty:
        return pd.DataFrame()

    top_days = daily_series.sort_values(ascending=False).head(top_n).reset_index()
    date_col = top_days.columns[0]
    top_days.columns = ["Date", "Consumption (kWh)"]
    top_days["Date"] = pd.to_datetime(top_days["Date"]).dt.strftime("%d-%m-%Y")
    top_days["Emissions (kg CO2e)"] = (top_days["Consumption (kWh)"] * emission_factor).round(2)
    top_days["Emissions (Tonnes CO2e)"] = (top_days["Emissions (kg CO2e)"] / 1000.0).round(4)
    top_days["Consumption (kWh)"] = top_days["Consumption (kWh)"].round(2)
    return top_days
