"""
Consumption Behaviour Profiling Using K-Means.
Extracts daily or weekly behavioural electricity consumption features, standardizes them,
applies K-Means clustering, evaluates silhouette score, projects to 2D PCA,
and generates data-driven behavioural profiles.
"""
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
import plotly.express as px
import plotly.graph_objects as go


FEATURE_NAMES = [
    "total_kwh",
    "peak_power_kw",
    "std_power_kw",
    "evening_kwh",
    "overnight_kwh",
    "peak_to_avg_ratio",
    "is_weekend",
]

FEATURE_DESCRIPTIONS = {
    "total_kwh": "Total consumption in the period (kWh)",
    "peak_power_kw": "Maximum peak power recorded (kW)",
    "std_power_kw": "Variability / standard deviation in power (kW)",
    "evening_kwh": "Evening consumption between 18:00 and 22:00 (kWh)",
    "overnight_kwh": "Overnight baseload consumption between 00:00 and 06:00 (kWh)",
    "peak_to_avg_ratio": "Ratio of peak power to average power",
    "is_weekend": "Proportion of weekend days in observation",
}


def extract_behavioural_features(
    df: pd.DataFrame,
    granularity: str = "Daily",
) -> pd.DataFrame:
    """
    Extract multi-dimensional behavioural features aggregated to Daily or Weekly.
    Performs fast vectorized calculations.
    """
    data = df.copy()
    if "DateTime" not in data.columns:
        raise ValueError("DataFrame must contain a DateTime column.")

    data["DateTime"] = pd.to_datetime(data["DateTime"])
    data = data.sort_values("DateTime")

    # Time components
    data["hour"] = data["DateTime"].dt.hour
    data["weekday"] = data["DateTime"].dt.weekday
    data["is_weekend_num"] = (data["weekday"] >= 5).astype(float)
    data["is_evening"] = ((data["hour"] >= 18) & (data["hour"] < 22)).astype(float)
    data["is_overnight"] = ((data["hour"] >= 0) & (data["hour"] < 6)).astype(float)

    # Power in kW to energy in kWh per ~1-min reading
    gap = data["Global_active_power"].clip(lower=0.0)
    data["energy_kwh"] = gap / 60.0
    data["evening_kwh"] = data["energy_kwh"] * data["is_evening"]
    data["overnight_kwh"] = data["energy_kwh"] * data["is_overnight"]

    if granularity == "Daily":
        data["period"] = data["DateTime"].dt.date
    else:
        # Weekly grouping ending on Sunday
        data["period"] = data["DateTime"].dt.to_period("W").apply(lambda r: r.start_time.date())

    grouped = data.groupby("period")
    agg_df = grouped.agg(
        total_kwh=("energy_kwh", "sum"),
        peak_power_kw=("Global_active_power", "max"),
        std_power_kw=("Global_active_power", "std"),
        mean_power_kw=("Global_active_power", "mean"),
        evening_kwh=("evening_kwh", "sum"),
        overnight_kwh=("overnight_kwh", "sum"),
        is_weekend=("is_weekend_num", "mean"),
        reading_count=("Global_active_power", "count"),
    ).reset_index()

    # Fill NaN std (e.g. single reading) with 0.0
    agg_df["std_power_kw"] = agg_df["std_power_kw"].fillna(0.0)
    # Peak to average ratio safely
    agg_df["peak_to_avg_ratio"] = np.where(
        agg_df["mean_power_kw"] > 0,
        agg_df["peak_power_kw"] / agg_df["mean_power_kw"],
        1.0
    )

    # Filter out periods with very few readings (e.g. less than 60 readings in a day)
    min_readings = 60 if granularity == "Daily" else 300
    agg_df = agg_df[agg_df["reading_count"] >= min_readings].copy()

    agg_df["period_str"] = pd.to_datetime(agg_df["period"]).dt.strftime("%Y-%m-%d")
    return agg_df


def run_kmeans_clustering(
    features_df: pd.DataFrame,
    n_clusters: int = 3,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Standardize features and execute K-Means clustering.
    Returns (annotated_df, metrics_and_models_dict).
    """
    if len(features_df) < n_clusters:
        raise ValueError(
            f"Not enough observations ({len(features_df)}) to form {n_clusters} clusters."
        )

    # Select numerical features for clustering
    available_features = [f for f in FEATURE_NAMES if f in features_df.columns]
    X_raw = features_df[available_features].values

    # Handle edge case: zero variance
    variances = np.var(X_raw, axis=0)
    valid_mask = variances > 1e-6
    if not np.any(valid_mask):
        raise ValueError("Features exhibit zero variance. Cannot perform clustering.")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)

    kmeans = KMeans(
        n_clusters=n_clusters,
        init="k-means++",
        n_init=10,
        max_iter=300,
        random_state=random_state,
    )
    cluster_labels = kmeans.fit_predict(X_scaled)

    # Calculate Silhouette score if valid
    sil_score = None
    if 2 <= n_clusters < len(X_scaled):
        try:
            sil_score = float(silhouette_score(X_scaled, cluster_labels))
        except Exception:
            sil_score = None

    # PCA 2D Projection
    pca = PCA(n_components=2, random_state=random_state)
    X_pca = pca.fit_transform(X_scaled)
    var_ratio = pca.explained_variance_ratio_

    result_df = features_df.copy()
    result_df["cluster"] = cluster_labels
    result_df["pca1"] = X_pca[:, 0]
    result_df["pca2"] = X_pca[:, 1]

    # Derive descriptive labels from cluster statistics
    overall_mean = result_df["total_kwh"].mean()
    cluster_profiles: Dict[int, Dict[str, Any]] = {}
    cluster_labels_map: Dict[int, str] = {}

    for c in range(n_clusters):
        c_subset = result_df[result_df["cluster"] == c]
        c_mean = c_subset["total_kwh"].mean()
        c_peak = c_subset["peak_power_kw"].mean()
        c_eve = c_subset["evening_kwh"].mean()
        c_night = c_subset["overnight_kwh"].mean()
        c_std = c_subset["std_power_kw"].mean()
        c_wknd = c_subset["is_weekend"].mean()

        # Dynamic heuristic labeling
        label_parts = []
        if c_mean < 0.75 * overall_mean:
            label_parts.append("Low Base")
        elif c_mean > 1.35 * overall_mean:
            label_parts.append("High Intensity")
        else:
            label_parts.append("Moderate")

        if c_eve > (0.35 * c_mean) and c_eve > result_df["evening_kwh"].mean():
            label_parts.append("Evening Peak")
        elif c_night > (0.35 * c_mean) and c_night > result_df["overnight_kwh"].mean():
            label_parts.append("Overnight Load")
        elif c_std > 1.25 * result_df["std_power_kw"].mean():
            label_parts.append("High Variability")
        elif c_wknd > 0.4:
            label_parts.append("Weekend Active")

        profile_title = " · ".join(label_parts) if label_parts else f"Profile {c + 1}"
        cluster_labels_map[c] = f"Cluster {c + 1}: {profile_title}"

        cluster_profiles[c] = {
            "name": cluster_labels_map[c],
            "count": len(c_subset),
            "percentage": (len(c_subset) / len(result_df)) * 100.0,
            "mean_kwh": float(c_mean),
            "peak_kw": float(c_peak),
            "std_kw": float(c_std),
            "evening_kwh": float(c_eve),
            "overnight_kwh": float(c_night),
            "weekend_ratio": float(c_wknd),
        }

    result_df["cluster_label"] = result_df["cluster"].map(cluster_labels_map)

    context = {
        "n_clusters": n_clusters,
        "silhouette_score": sil_score,
        "pca_variance_ratio": [float(v) for v in var_ratio],
        "cluster_profiles": cluster_profiles,
        "cluster_labels_map": cluster_labels_map,
        "feature_names": available_features,
        "scaler": scaler,
        "kmeans": kmeans,
    }
    return result_df, context
