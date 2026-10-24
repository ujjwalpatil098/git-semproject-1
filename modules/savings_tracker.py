"""
Smart Energy Savings Tracker.
Records user energy-saving interventions, computes empirical before-and-after
consumption differences, projects estimated financial impacts, and provides SQLite persistence.
"""
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
from modules.db import (
    add_saving_action,
    get_all_saving_actions,
    update_saving_action,
    delete_saving_action,
)


ACTION_PRESETS = [
    "Reducing unnecessary lighting",
    "Switching off unused appliances",
    "Reducing standby power (phantom loads)",
    "Improving air-conditioner / heating usage",
    "Moving high-energy activities away from peak hours",
    "Custom Action",
]


def evaluate_action_impact(
    daily_series: pd.Series,
    action_date: date,
    baseline_days: int = 14,
    followup_days: int = 14,
    tariff_inr: float = 7.50,
) -> Dict[str, Any]:
    """
    Empirically compare consumption in the baseline window preceding the action date
    with the follow-up window succeeding the action date.
    """
    if daily_series.empty:
        return {"status": "error", "message": "Daily consumption series is empty."}

    action_dt = pd.to_datetime(action_date)
    # Baseline window: [action_date - baseline_days, action_date - 1 day]
    baseline_start = action_dt - timedelta(days=baseline_days)
    baseline_end = action_dt - timedelta(days=1)

    # Follow-up window: [action_date, action_date + followup_days - 1 day]
    followup_start = action_dt
    followup_end = action_dt + timedelta(days=followup_days - 1)

    # Slice daily series
    # Ensure index is DatetimeIndex
    series_dt = daily_series.copy()
    series_dt.index = pd.to_datetime(series_dt.index)

    baseline_data = series_dt[(series_dt.index >= baseline_start) & (series_dt.index <= baseline_end)]
    followup_data = series_dt[(series_dt.index >= followup_start) & (series_dt.index <= followup_end)]

    actual_base_days = len(baseline_data)
    actual_follow_days = len(followup_data)

    if actual_base_days == 0 or actual_follow_days == 0:
        return {
            "status": "insufficient_data",
            "message": (
                f"Action date {action_date.strftime('%d-%m-%Y')} falls outside or near the edge of the dataset coverage "
                f"({series_dt.index.min().strftime('%d-%m-%Y')} to {series_dt.index.max().strftime('%d-%m-%Y')}). "
                f"Found {actual_base_days} baseline day(s) and {actual_follow_days} follow-up day(s)."
            ),
            "actual_base_days": actual_base_days,
            "actual_follow_days": actual_follow_days,
        }

    base_mean = float(baseline_data.mean())
    follow_mean = float(followup_data.mean())
    base_total = float(baseline_data.sum())
    follow_total = float(followup_data.sum())

    # Absolute difference in daily kWh (positive means consumption decreased)
    abs_diff = base_mean - follow_mean

    # Percentage change relative to baseline
    pct_change = (abs_diff / base_mean * 100.0) if base_mean > 0 else 0.0

    # Financial differences
    safe_tariff = max(0.0, float(tariff_inr))
    daily_cost_diff = abs_diff * safe_tariff
    period_cost_diff = daily_cost_diff * actual_follow_days

    return {
        "status": "success",
        "action_date": action_date.strftime("%d-%m-%Y"),
        "baseline_period": f"{baseline_start.strftime('%d-%m-%Y')} to {baseline_end.strftime('%d-%m-%Y')}",
        "followup_period": f"{followup_start.strftime('%d-%m-%Y')} to {followup_end.strftime('%d-%m-%Y')}",
        "baseline_days_requested": baseline_days,
        "followup_days_requested": followup_days,
        "baseline_days_evaluated": actual_base_days,
        "followup_days_evaluated": actual_follow_days,
        "baseline_mean_kwh": round(base_mean, 2),
        "followup_mean_kwh": round(follow_mean, 2),
        "baseline_total_kwh": round(base_total, 2),
        "followup_total_kwh": round(follow_total, 2),
        "absolute_daily_diff_kwh": round(abs_diff, 2),
        "percentage_change": round(pct_change, 1),
        "tariff_inr": safe_tariff,
        "estimated_daily_cost_diff": round(daily_cost_diff, 2),
        "estimated_period_cost_diff": round(period_cost_diff, 2),
        "baseline_data": baseline_data,
        "followup_data": followup_data,
    }
