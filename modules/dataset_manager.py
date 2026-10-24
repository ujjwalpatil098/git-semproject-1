"""
Custom dataset upload, schema detection, validation, and session management.
Ensures uploaded user datasets never overwrite or alter original files or database tables.
"""
from typing import Dict, List, Optional, Tuple, Any
from io import BytesIO, StringIO
import pandas as pd
import numpy as np


LIKELY_DATETIME_COLS = [
    "datetime", "date_time", "timestamp", "time_stamp", "ts", "date", "time", "reading_time"
]

LIKELY_POWER_COLS = [
    "global_active_power", "active_power", "power", "kw", "kwh",
    "consumption", "energy", "value", "meter_reading", "energy_kwh"
]


def detect_candidate_columns(columns: List[str]) -> Dict[str, Optional[str]]:
    """Automatically identify the most probable datetime, date, time, and power columns."""
    mapping: Dict[str, Optional[str]] = {
        "datetime": None,
        "date": None,
        "time": None,
        "power": None,
        "sub1": None,
        "sub2": None,
        "sub3": None,
        "reactive": None,
        "voltage": None,
        "intensity": None,
    }
    cols_lower = {c: str(c).strip().lower() for c in columns}

    for orig, low in cols_lower.items():
        if low in ["datetime", "date_time", "timestamp"]:
            mapping["datetime"] = orig
        elif low in ["date", "reading_date"]:
            mapping["date"] = orig
        elif low in ["time", "reading_time"]:
            mapping["time"] = orig
        elif low in ["global_active_power", "active_power", "power", "power_kw", "consumption_kwh", "energy_kwh"]:
            mapping["power"] = orig
        elif "sub_metering_1" in low or low == "sub1":
            mapping["sub1"] = orig
        elif "sub_metering_2" in low or low == "sub2":
            mapping["sub2"] = orig
        elif "sub_metering_3" in low or low == "sub3":
            mapping["sub3"] = orig
        elif "reactive" in low:
            mapping["reactive"] = orig
        elif "voltage" in low:
            mapping["voltage"] = orig
        elif "intensity" in low or "current" in low:
            mapping["intensity"] = orig

    # Fallback if no exact power found
    if not mapping["power"]:
        for orig, low in cols_lower.items():
            if any(term in low for term in ["power", "kwh", "watt", "energy", "consumption"]):
                mapping["power"] = orig
                break

    return mapping


def validate_and_transform_uploaded_csv(
    file_bytes: bytes,
    datetime_col: Optional[str] = None,
    date_col: Optional[str] = None,
    time_col: Optional[str] = None,
    power_col: Optional[str] = None,
    power_unit: str = "kW (approx. 1-minute interval)",
    sub1_col: Optional[str] = None,
    sub2_col: Optional[str] = None,
    sub3_col: Optional[str] = None,
) -> Tuple[Optional[pd.DataFrame], Dict[str, Any], List[str]]:
    """
    Validate and transform an uploaded CSV file into standard WattWise format.
    Returns (cleaned_dataframe, data_quality_report, list_of_warnings_or_errors).
    """
    issues: List[str] = []
    report: Dict[str, Any] = {}

    try:
        raw_df = pd.read_csv(BytesIO(file_bytes), nrows=500000)
    except Exception as exc:
        return None, {}, [f"Could not parse CSV file: {exc}"]

    total_rows = len(raw_df)
    report["total_rows"] = total_rows
    report["raw_columns"] = list(raw_df.columns)

    if total_rows == 0:
        return None, {}, ["The uploaded CSV file is empty."]

    working_df = raw_df.copy()
    working_df.columns = [str(c).strip() for c in working_df.columns]

    # 1. Parse Datetime
    dt_series = None
    if datetime_col and datetime_col in working_df.columns:
        dt_series = pd.to_datetime(working_df[datetime_col], dayfirst=True, errors="coerce")
    elif date_col and time_col and date_col in working_df.columns and time_col in working_df.columns:
        dt_series = pd.to_datetime(
            working_df[date_col].astype(str) + " " + working_df[time_col].astype(str),
            dayfirst=True,
            errors="coerce"
        )
    elif date_col and date_col in working_df.columns:
        dt_series = pd.to_datetime(working_df[date_col], dayfirst=True, errors="coerce")
    else:
        # Try automatic discovery
        for col in working_df.columns:
            low = col.lower()
            if low in ["datetime", "date_time", "timestamp"]:
                dt_series = pd.to_datetime(working_df[col], dayfirst=True, errors="coerce")
                break
        if dt_series is None and "Date" in working_df.columns and "Time" in working_df.columns:
            dt_series = pd.to_datetime(
                working_df["Date"].astype(str) + " " + working_df["Time"].astype(str),
                dayfirst=True,
                errors="coerce"
            )

    if dt_series is None or dt_series.notna().sum() == 0:
        return None, report, ["Could not parse valid timestamps. Please select appropriate date/datetime columns."]

    working_df["DateTime"] = dt_series
    missing_dates = int(dt_series.isna().sum())
    report["missing_timestamps"] = missing_dates
    if missing_dates > 0:
        issues.append(f"{missing_dates:,} row(s) had unparseable timestamps and will be excluded.")

    # 2. Parse Power / Consumption column
    chosen_power = power_col
    if not chosen_power or chosen_power not in working_df.columns:
        # Try default
        if "Global_active_power" in working_df.columns:
            chosen_power = "Global_active_power"
        else:
            for col in working_df.columns:
                if any(k in col.lower() for k in ["power", "kwh", "consumption", "energy"]):
                    chosen_power = col
                    break

    if not chosen_power or chosen_power not in working_df.columns:
        return None, report, ["No valid electricity consumption or power column was selected or found."]

    power_numeric = pd.to_numeric(working_df[chosen_power], errors="coerce")
    missing_power = int(power_numeric.isna().sum())
    report["missing_power_values"] = missing_power
    if missing_power > 0:
        issues.append(f"{missing_power:,} row(s) contained invalid or missing power readings and will be dropped.")

    # Convert to standard kW if specified as Watts or kWh direct
    if power_unit == "Watts (W)":
        power_numeric = power_numeric / 1000.0
    elif power_unit == "Daily kWh (pre-aggregated)":
        # If daily kWh, each row represents daily total
        pass

    working_df["Global_active_power"] = power_numeric

    # 3. Clean and filter
    cleaned = working_df.dropna(subset=["DateTime", "Global_active_power"]).copy()

    # Deduplicate timestamps
    dup_count = int(cleaned.duplicated(subset=["DateTime"]).sum())
    report["duplicate_timestamps"] = dup_count
    if dup_count > 0:
        issues.append(f"{dup_count:,} duplicate timestamp(s) detected and averaged.")
        cleaned = cleaned.groupby("DateTime", as_index=False).mean(numeric_only=True)

    cleaned = cleaned.sort_values("DateTime").reset_index(drop=True)
    report["usable_rows"] = len(cleaned)

    if len(cleaned) == 0:
        return None, report, ["No usable rows remain after dropping null timestamps and readings."]

    # Check for negative power
    neg_power = int((cleaned["Global_active_power"] < 0).sum())
    report["negative_power_rows"] = neg_power
    if neg_power > 0:
        issues.append(f"{neg_power:,} row(s) had negative power readings; clipped to 0.0.")
        cleaned["Global_active_power"] = cleaned["Global_active_power"].clip(lower=0.0)

    # Optional sub-metering columns
    for orig, target in [
        (sub1_col, "Sub_metering_1"),
        (sub2_col, "Sub_metering_2"),
        (sub3_col, "Sub_metering_3"),
    ]:
        if orig and orig in cleaned.columns and orig != target:
            cleaned[target] = pd.to_numeric(cleaned[orig], errors="coerce").fillna(0.0)
        elif target not in cleaned.columns:
            cleaned[target] = 0.0

    # Ensure other numeric columns exist with default 0 if absent to protect legacy views
    for optional_col in ["Global_reactive_power", "Voltage", "Global_intensity"]:
        if optional_col not in cleaned.columns:
            cleaned[optional_col] = 0.0
        else:
            cleaned[optional_col] = pd.to_numeric(cleaned[optional_col], errors="coerce").fillna(0.0)

    # Summary statistics
    report["start_date"] = cleaned["DateTime"].min().strftime("%Y-%m-%d %H:%M")
    report["end_date"] = cleaned["DateTime"].max().strftime("%Y-%m-%d %H:%M")
    report["mean_power"] = float(cleaned["Global_active_power"].mean())
    report["max_power"] = float(cleaned["Global_active_power"].max())
    report["min_power"] = float(cleaned["Global_active_power"].min())

    return cleaned, report, issues
