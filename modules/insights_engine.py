"""
Confidence-Aware Intelligent Insights Engine.
Generates rigorous, data-grounded insights and actionable recommendations
accompanied by transparent evidence-quality grading and limitations.
"""
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from scipy import stats


class InsightCard:
    """Represents a structured analytical finding with confidence metrics."""

    def __init__(
        self,
        title: str,
        category: str,
        observation: str,
        date_range: str,
        supporting_stats: Dict[str, Any],
        rule_or_method: str,
        confidence_level: str,  # "HIGH", "MODERATE", "LOW"
        confidence_rationale: str,
        explanation: str,
        recommendation: str,
        limitations: List[str],
    ):
        self.title = title
        self.category = category
        self.observation = observation
        self.date_range = date_range
        self.supporting_stats = supporting_stats
        self.rule_or_method = rule_or_method
        self.confidence_level = confidence_level.upper()
        self.confidence_rationale = confidence_rationale
        self.explanation = explanation
        self.recommendation = recommendation
        self.limitations = limitations

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "category": self.category,
            "observation": self.observation,
            "date_range": self.date_range,
            "supporting_stats": self.supporting_stats,
            "rule_or_method": self.rule_or_method,
            "confidence_level": self.confidence_level,
            "confidence_rationale": self.confidence_rationale,
            "explanation": self.explanation,
            "recommendation": self.recommendation,
            "limitations": self.limitations,
        }


def generate_intelligent_insights(
    df: pd.DataFrame,
    daily_series: pd.Series,
    min_observations: int = 7,
) -> List[InsightCard]:
    """
    Evaluate statistical properties of the active dataset and produce structured,
    confidence-scored insights.
    """
    insights: List[InsightCard] = []

    if df.empty or daily_series.empty or len(daily_series) < min_observations:
        return [
            InsightCard(
                title="Insufficient Data Coverage",
                category="Data Quality",
                observation=f"Dataset contains only {len(daily_series)} daily observation(s).",
                date_range="N/A",
                supporting_stats={"Total Days": len(daily_series)},
                rule_or_method="Minimum sample threshold (N >= 7 days)",
                confidence_level="LOW",
                confidence_rationale="Sample size is too small to derive statistically stable behavioral patterns.",
                explanation="Statistical tests and behavioral profiling require at least one to two weeks of consistent readings.",
                recommendation="Provide a dataset spanning at least 30 consecutive days for reliable consumption insights.",
                limitations=["No inferences can be drawn reliably from sparse or truncated records."],
            )
        ]

    n_days = len(daily_series)
    start_str = daily_series.index.min().strftime("%d %b %Y")
    end_str = daily_series.index.max().strftime("%d %b %Y")
    date_range_str = f"{start_str} to {end_str}"

    # -------------------------------------------------------------
    # 1. Weekday vs. Weekend Consumption Disparity (Two-Sample t-test)
    # -------------------------------------------------------------
    daily_df = daily_series.rename("kwh").to_frame()
    daily_df["weekday"] = daily_df.index.weekday
    daily_df["is_weekend"] = daily_df["weekday"] >= 5

    weekdays = daily_df[~daily_df["is_weekend"]]["kwh"].dropna()
    weekends = daily_df[daily_df["is_weekend"]]["kwh"].dropna()

    if len(weekdays) >= 5 and len(weekends) >= 4:
        mean_wkday = float(weekdays.mean())
        mean_wknd = float(weekends.mean())
        std_wkday = float(weekdays.std(ddof=1)) if len(weekdays) > 1 else 0.0
        std_wknd = float(weekends.std(ddof=1)) if len(weekends) > 1 else 0.0

        # Welch's t-test (unequal variances)
        t_stat, p_val = stats.ttest_ind(weekdays, weekends, equal_var=False)

        # Cohen's d effect size
        pooled_std = np.sqrt(((len(weekdays) - 1) * (std_wkday**2) + (len(weekends) - 1) * (std_wknd**2)) / (len(weekdays) + len(weekends) - 2)) if (len(weekdays) + len(weekends) > 2) else 1.0
        cohens_d = (mean_wknd - mean_wkday) / pooled_std if pooled_std > 0 else 0.0
        diff_pct = ((mean_wknd - mean_wkday) / mean_wkday * 100.0) if mean_wkday > 0 else 0.0

        if p_val < 0.05 and abs(diff_pct) >= 10.0:
            if n_days >= 60 and p_val < 0.001:
                conf = "HIGH"
                conf_rat = f"Strong statistical significance (p={p_val:.2e} < 0.001) over {n_days} days with Cohen's d={cohens_d:.2f}."
            else:
                conf = "MODERATE"
                conf_rat = f"Statistically significant (p={p_val:.3f} < 0.05) with moderate sample size ({len(weekdays)} weekdays, {len(weekends)} weekend days)."

            trend_word = "higher" if diff_pct > 0 else "lower"
            obs = f"Weekend consumption averages {mean_wknd:.2f} kWh/day, which is {abs(diff_pct):.1f}% {trend_word} than weekday consumption ({mean_wkday:.2f} kWh/day)."
            rec = (
                f"Examine weekend routines and high-draw household devices active on Saturdays and Sundays. Consider scheduling heavy tasks (e.g. laundry, dishwashing) during non-peak utility hours if time-of-use tariffs apply."
                if diff_pct > 0 else
                f"Weekday consumption is notably higher. Review daytime active loads (such as home office equipment, continuous cooling/heating, or daytime standby)."
            )

            insights.append(
                InsightCard(
                    title="Weekend vs. Weekday Consumption Pattern",
                    category="Behavioral Dynamics",
                    observation=obs,
                    date_range=date_range_str,
                    supporting_stats={
                        "Weekday Mean": f"{mean_wkday:.2f} kWh/day",
                        "Weekend Mean": f"{mean_wknd:.2f} kWh/day",
                        "Difference (%)": f"{diff_pct:+.1f}%",
                        "Welch t-stat": f"{t_stat:.2f}",
                        "p-value": f"{p_val:.4f}",
                        "Cohen's d": f"{cohens_d:.2f}",
                        "Weekday Sample": len(weekdays),
                        "Weekend Sample": len(weekends),
                    },
                    rule_or_method="Welch's two-sample t-test (two-tailed, unequal variance) with Cohen's d effect size",
                    confidence_level=conf,
                    confidence_rationale=conf_rat,
                    explanation="Household occupancy and appliance schedules naturally shift between workdays and weekends, causing distinct daily energy profiles.",
                    recommendation=rec,
                    limitations=[
                        "Does not account for external holiday calendars or temporary resident absences.",
                        "Sub-circuit data is needed to verify which specific appliances drive the weekend variance.",
                    ],
                )
            )

    # -------------------------------------------------------------
    # 2. Standby / Baseload Power (Overnight Vampire Draw)
    # -------------------------------------------------------------
    if "DateTime" in df.columns and "Global_active_power" in df.columns:
        overnight_df = df[df["DateTime"].dt.hour.between(1, 4)]
        if not overnight_df.empty:
            baseload_kw = float(overnight_df["Global_active_power"].quantile(0.10))
            median_kw = float(df["Global_active_power"].median())
            baseload_ratio = (baseload_kw / median_kw) if median_kw > 0 else 0.0

            # Basal load in kWh per day
            daily_baseload_kwh = baseload_kw * 24.0
            total_avg_kwh = float(daily_series.mean())
            baseload_share_pct = (daily_baseload_kwh / total_avg_kwh * 100.0) if total_avg_kwh > 0 else 0.0

            conf = "HIGH" if len(overnight_df) > 5000 else "MODERATE"
            conf_rat = f"Evaluated from {len(overnight_df):,} overnight 1-4 AM minute readings with 10th-percentile filtering to eliminate sporadic spikes."

            obs = f"Continuous baseline power draw is estimated at {baseload_kw:.2f} kW ({daily_baseload_kwh:.1f} kWh/day), representing ~{baseload_share_pct:.1f}% of total daily electricity usage."

            if baseload_kw > 0.4:
                rec = "Continuous baseload appears elevated. Inspect continuously plugged appliances (refrigerators, Wi-Fi routers, entertainment centers, standby electronics, and water heaters) using smart plugs or power strips."
            else:
                rec = "Continuous baseload is within a healthy low range (<0.4 kW). Continue turning off standby power switches when appliances are not in active use."

            insights.append(
                InsightCard(
                    title="Continuous Baseload & Standby Power",
                    category="Energy Efficiency",
                    observation=obs,
                    date_range=date_range_str,
                    supporting_stats={
                        "Estimated Baseload Power": f"{baseload_kw:.3f} kW",
                        "Equivalent 24h Baseload": f"{daily_baseload_kwh:.2f} kWh/day",
                        "Share of Daily Usage": f"{baseload_share_pct:.1f}%",
                        "Overnight Samples": len(overnight_df),
                    },
                    rule_or_method="10th percentile of active power between 01:00 AM and 04:00 AM",
                    confidence_level=conf,
                    confidence_rationale=conf_rat,
                    explanation="Baseload represents phantom/standby power and constantly running equipment that draws power 24 hours a day even when occupants are asleep.",
                    recommendation=rec,
                    limitations=[
                        "Assumes 1-4 AM reflects purely non-interactive base loads; nocturnal occupant activity may elevate this estimate.",
                    ],
                )
            )

    # -------------------------------------------------------------
    # 3. Peak Hour Concentration (Evening Peak)
    # -------------------------------------------------------------
    if "DateTime" in df.columns and "Global_active_power" in df.columns:
        hourly_mean = df.groupby(df["DateTime"].dt.hour)["Global_active_power"].mean()
        peak_hour = int(hourly_mean.idxmax())
        peak_mean_kw = float(hourly_mean.max())
        overall_mean_kw = float(df["Global_active_power"].mean())
        ratio_peak = (peak_mean_kw / overall_mean_kw) if overall_mean_kw > 0 else 1.0

        if ratio_peak >= 1.3:
            obs = f"Electricity demand consistently peaks at {peak_hour:02d}:00 with an average draw of {peak_mean_kw:.2f} kW, which is {ratio_peak:.1f}× higher than the daily average."
            rec = f"Stagger power-intensive activities away from {peak_hour:02d}:00–{(peak_hour+2)%24:02d}:00 (e.g. run laundry, dishwashers, or water heaters earlier in the day or after 22:00)."

            insights.append(
                InsightCard(
                    title="Diurnal Peak Demand Concentration",
                    category="Load Shifting",
                    observation=obs,
                    date_range=date_range_str,
                    supporting_stats={
                        "Peak Hour": f"{peak_hour:02d}:00",
                        "Peak Hour Average": f"{peak_mean_kw:.2f} kW",
                        "Overall Mean Power": f"{overall_mean_kw:.2f} kW",
                        "Peak / Average Ratio": f"{ratio_peak:.2f}×",
                    },
                    rule_or_method="Hourly mean active power aggregation across the entire observation window",
                    confidence_level="HIGH" if n_days >= 30 else "MODERATE",
                    confidence_rationale=f"Derived from {len(df):,} granular readings across {n_days} days.",
                    explanation="Simultaneous operation of kitchen appliances, entertainment systems, and climate controls in the evening hours produces sharp demand peaks.",
                    recommendation=rec,
                    limitations=[
                        "Load shifting benefits depend on whether the consumer's utility tariff includes Time-of-Day (ToD) pricing.",
                    ],
                )
            )

    # -------------------------------------------------------------
    # 4. Sub-Meter Energy Breakdown (if present)
    # -------------------------------------------------------------
    sub_cols = [c for c in ["Sub_metering_1", "Sub_metering_2", "Sub_metering_3"] if c in df.columns]
    if len(sub_cols) == 3:
        sub_sums = {
            "Kitchen (Sub 1)": float(df["Sub_metering_1"].sum() / 1000.0),
            "Laundry (Sub 2)": float(df["Sub_metering_2"].sum() / 1000.0),
            "Water Heater & AC (Sub 3)": float(df["Sub_metering_3"].sum() / 1000.0),
        }
        total_sub_kwh = sum(sub_sums.values())
        if total_sub_kwh > 0:
            dominant_sub = max(sub_sums, key=sub_sums.get)
            dom_val = sub_sums[dominant_sub]
            dom_pct = (dom_val / total_sub_kwh) * 100.0

            obs = f"{dominant_sub} constitutes the single largest measured sub-meter load, accounting for {dom_pct:.1f}% ({dom_val:,.1f} kWh) of all sub-metered energy."
            rec = f"Prioritize efficiency measures on {dominant_sub.lower()}. Even modest improvements (e.g. raising AC setpoint by 1-2°C, regular filter cleaning, or washing clothes at 30°C) will yield the largest observed energy impact."

            insights.append(
                InsightCard(
                    title="Dominant Sub-Meter Energy Driver",
                    category="End-Use Allocation",
                    observation=obs,
                    date_range=date_range_str,
                    supporting_stats={
                        "Sub 1 - Kitchen": f"{sub_sums['Kitchen (Sub 1)']:,.1f} kWh",
                        "Sub 2 - Laundry": f"{sub_sums['Laundry (Sub 2)']:,.1f} kWh",
                        "Sub 3 - Water Heater & AC": f"{sub_sums['Water Heater & AC (Sub 3)']:,.1f} kWh",
                        "Dominant Share": f"{dom_pct:.1f}%",
                    },
                    rule_or_method="Relative share of sub-meter sum (Wh converted to kWh)",
                    confidence_level="HIGH",
                    confidence_rationale="Direct sub-meter hardware integration with zero estimation ambiguity for the monitored circuits.",
                    explanation="High-power thermal appliances (compressors, resistive heating elements) consume significantly more electrical energy per cycle than electronic devices.",
                    recommendation=rec,
                    limitations=[
                        "Sub-metering does not cover general lighting, wall sockets, or unmetered utility circuits.",
                    ],
                )
            )

    # -------------------------------------------------------------
    # 5. Volatility & Extreme Daily Outliers (IQR)
    # -------------------------------------------------------------
    q1 = float(daily_series.quantile(0.25))
    q3 = float(daily_series.quantile(0.75))
    iqr = q3 - q1
    upper_fence = q3 + 1.5 * iqr
    outliers = daily_series[daily_series > upper_fence]

    if len(outliers) > 0:
        outlier_pct = (len(outliers) / n_days) * 100.0
        max_day = outliers.idxmax()
        max_val = float(outliers.max())

        obs = f"{len(outliers)} day(s) ({outlier_pct:.1f}% of observations) substantially exceeded the upper statistical threshold ({upper_fence:.2f} kWh/day). Peak day reached {max_val:.2f} kWh on {max_day.strftime('%d %b %Y')}."
        rec = "Audit high-consumption dates against exceptional household events, guest visits, HVAC intensive heatwaves/cold snaps, or faulty equipment left operating continuously."

        insights.append(
            InsightCard(
                title="Consumption Volatility & Extreme Spike Days",
                category="Outlier Detection",
                observation=obs,
                date_range=date_range_str,
                supporting_stats={
                    "Flagged High Days": len(outliers),
                    "Percentage of Days": f"{outlier_pct:.1f}%",
                    "IQR Upper Threshold": f"{upper_fence:.2f} kWh/day",
                    "Historical Maximum": f"{max_val:.2f} kWh",
                    "Peak Spike Date": max_day.strftime("%d-%m-%Y"),
                },
                rule_or_method="Interquartile Range (IQR) fence: Q3 + 1.5 × (Q3 - Q1)",
                confidence_level="HIGH" if n_days >= 30 else "MODERATE",
                confidence_rationale=f"IQR is robust against extreme values. Evaluated across {n_days} calendar days.",
                explanation="Outlier days represent non-routine electricity usage episodes that disproportionately inflate monthly billing totals.",
                recommendation=rec,
                limitations=[
                    "Outlier identification is statistical and does not indicate whether the spike was legitimate necessary usage or preventable waste.",
                ],
            )
        )

    return insights
