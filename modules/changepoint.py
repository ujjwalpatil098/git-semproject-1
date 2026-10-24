"""
Electricity Consumption Change-Point Detection.
Detects sustained structural shifts in consumption level and variability over time,
distinct from point anomaly detection. Implements Offline Cumulative Sum (CUSUM)
and Binary Segmentation. Includes synthetic data benchmark validation.
"""
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from scipy import stats


def detect_cusum_changepoints(
    series: pd.Series,
    threshold: float = 1.35,  # Standard critical value multiplier for Kolmogorov-Smirnov / CUSUM range
    min_segment_length: int = 14,
) -> Tuple[List[int], pd.DataFrame]:
    """
    Offline Cumulative Sum (CUSUM) change-point detection.
    Computes S_k = sum_{i=1}^k (x_i - mean(x)).
    Identifies significant structural regime shifts recursively where range(S) exceeds threshold * sigma * sqrt(n).
    """
    values = series.values.astype(float)
    n = len(values)
    if n < 2 * min_segment_length:
        return [], pd.DataFrame()

    mean_val = np.mean(values)
    std_val = np.std(values, ddof=1)
    if std_val < 1e-6:
        return [], pd.DataFrame()

    # Full series CUSUM trajectory
    full_cusum = np.cumsum(values - mean_val)

    changepoints: List[int] = []

    def recursive_cusum(start: int, end: int, depth: int = 0):
        seg_len = end - start
        if seg_len < 2 * min_segment_length or len(changepoints) >= 10:
            return

        seg_vals = values[start:end]
        seg_mean = np.mean(seg_vals)
        seg_std = np.std(seg_vals, ddof=1)
        if seg_std < 1e-6:
            return

        # S_k within segment
        s_k = np.cumsum(seg_vals - seg_mean)
        s_max = np.max(s_k)
        s_min = np.min(s_k)
        s_range = s_max - s_min

        # Critical boundary based on Brownian bridge maximum
        critical_value = threshold * seg_std * np.sqrt(seg_len)

        if s_range > critical_value:
            # Candidate change point is the point of maximal absolute deviation
            local_tau = int(np.argmax(np.abs(s_k)))
            global_tau = start + local_tau

            if (global_tau - start >= min_segment_length) and (end - global_tau >= min_segment_length):
                changepoints.append(global_tau)
                recursive_cusum(start, global_tau, depth + 1)
                recursive_cusum(global_tau, end, depth + 1)

    recursive_cusum(0, n)
    changepoints = sorted(changepoints)

    diag_df = pd.DataFrame({
        "Date": series.index,
        "Consumption": values,
        "Cumulative_Sum_Deviations": full_cusum,
    }, index=series.index)

    return changepoints, diag_df


def detect_binary_segmentation_changepoints(
    series: pd.Series,
    min_segment_length: int = 14,
    significance_alpha: float = 0.01,
    max_changepoints: int = 8,
) -> List[int]:
    """
    Offline change-point detection using recursive Binary Segmentation
    based on sum of squared errors minimization with two-sample statistical testing.
    """
    values = series.values.astype(float)
    n = len(values)
    if n < 2 * min_segment_length:
        return []

    changepoints: List[int] = []

    def segment(start: int, end: int, depth: int = 0):
        if (end - start) < (2 * min_segment_length) or len(changepoints) >= max_changepoints:
            return

        best_cost_reduction = -np.inf
        best_tau = -1

        sub = values[start:end]
        total_var = np.var(sub) * len(sub)

        for tau in range(start + min_segment_length, end - min_segment_length):
            left = values[start:tau]
            right = values[tau:end]
            cost_left = np.var(left) * len(left)
            cost_right = np.var(right) * len(right)
            reduction = total_var - (cost_left + cost_right)

            if reduction > best_cost_reduction:
                best_cost_reduction = reduction
                best_tau = tau

        if best_tau != -1:
            left_segment = values[start:best_tau]
            right_segment = values[best_tau:end]
            t_stat, p_val = stats.ttest_ind(left_segment, right_segment, equal_var=False)

            if p_val < significance_alpha:
                changepoints.append(best_tau)
                segment(start, best_tau, depth + 1)
                segment(best_tau, end, depth + 1)

    segment(0, n)
    return sorted(changepoints)


def summarize_changepoints(
    series: pd.Series,
    changepoint_indices: List[int],
    window_days: int = 30,
) -> pd.DataFrame:
    """
    Generate a detailed summary table comparing consumption before and after each detected change point.
    """
    if not changepoint_indices or series.empty:
        return pd.DataFrame()

    results = []
    n = len(series)
    dates = series.index

    for idx in changepoint_indices:
        if idx <= 0 or idx >= n:
            continue

        cp_date = dates[idx]
        start_pre = max(0, idx - window_days)
        end_post = min(n, idx + window_days)

        pre_series = series.iloc[start_pre:idx]
        post_series = series.iloc[idx:end_post]

        pre_mean = float(pre_series.mean()) if not pre_series.empty else np.nan
        post_mean = float(post_series.mean()) if not post_series.empty else np.nan
        pre_std = float(pre_series.std()) if not pre_series.empty else np.nan
        post_std = float(post_series.std()) if not post_series.empty else np.nan

        abs_diff = post_mean - pre_mean
        pct_diff = ((post_mean - pre_mean) / pre_mean * 100.0) if (pre_mean and pre_mean > 0) else np.nan

        direction = "Sustained Increase (▲)" if abs_diff > 0 else "Sustained Decrease (▼)"

        results.append({
            "Change-point Date": cp_date.strftime("%d-%m-%Y") if hasattr(cp_date, "strftime") else str(cp_date),
            "Direction": direction,
            "Pre-Shift Mean (kWh)": round(pre_mean, 2),
            "Post-Shift Mean (kWh)": round(post_mean, 2),
            "Absolute Shift (kWh)": round(abs_diff, 2),
            "Relative Shift (%)": round(pct_diff, 1) if pd.notna(pct_diff) else "N/A",
            "Pre-Shift Std (kWh)": round(pre_std, 2),
            "Post-Shift Std (kWh)": round(post_std, 2),
            "Pre Days": len(pre_series),
            "Post Days": len(post_series),
        })

    return pd.DataFrame(results)


def generate_synthetic_validation_series(
    n_days: int = 120,
    base_mean: float = 15.0,
    shift_size: float = 12.0,
    noise_std: float = 2.5,
    changepoint_day: int = 60,
    seed: int = 42,
) -> Tuple[pd.Series, int]:
    """
    Generate a known synthetic time series with an injected step shift
    for rigorous statistical algorithm validation.
    """
    rng = np.random.default_rng(seed)
    t = pd.date_range("2024-01-01", periods=n_days, freq="D")
    values = np.zeros(n_days)

    values[:changepoint_day] = rng.normal(loc=base_mean, scale=noise_std, size=changepoint_day)
    values[changepoint_day:] = rng.normal(loc=base_mean + shift_size, scale=noise_std, size=n_days - changepoint_day)

    values = np.clip(values, 0.0, None)
    synth_series = pd.Series(values, index=t, name="Synthetic Consumption (kWh)")
    return synth_series, changepoint_day
