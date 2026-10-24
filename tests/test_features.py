"""
Comprehensive test suite for WattWise Electricity Analytics.
Validates all six advanced features, calculation correctness, edge cases,
data upload safety, and database persistence using Python's standard unittest.
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import date, timedelta
import sqlite3
import numpy as np
import pandas as pd

from modules.db import (
    init_db,
    add_saving_action,
    get_all_saving_actions,
    update_saving_action,
    delete_saving_action,
    run_readonly_query,
)
from modules.dataset_manager import (
    detect_candidate_columns,
    validate_and_transform_uploaded_csv,
)
from modules.savings_tracker import evaluate_action_impact
from modules.profiling import (
    extract_behavioural_features,
    run_kmeans_clustering,
)
from modules.changepoint import (
    detect_cusum_changepoints,
    detect_binary_segmentation_changepoints,
    generate_synthetic_validation_series,
    summarize_changepoints,
)
from modules.carbon import (
    calculate_emissions,
    compute_daily_emissions,
    compute_monthly_emissions,
    find_highest_emission_days,
    CEA_NATIONAL_GRID_FACTOR,
)
from modules.insights_engine import (
    generate_intelligent_insights,
    InsightCard,
)


class TestWattWiseFeatures(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_db = Path(self.temp_dir) / "test_electricity.db"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # =====================================================================
    # 1. DATABASE & PERSISTENCE TESTS (FEATURE 1)
    # =====================================================================

    def test_db_init_and_crud(self):
        init_db(self.test_db)

        # Verify table created
        conn = sqlite3.connect(self.test_db)
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
        conn.close()
        self.assertIn("energy_saving_actions", tables)

        # Insert action
        act_id = add_saving_action(
            action_name="LED Bulb Upgrade",
            action_category="Reducing unnecessary lighting",
            action_date="2008-05-15",
            baseline_days=14,
            followup_days=14,
            tariff_inr=8.0,
            notes="Replaced all 60W bulbs with 9W LEDs",
            db_path=self.test_db,
        )
        self.assertGreater(act_id, 0)

        # Retrieve all
        df_actions = get_all_saving_actions(self.test_db)
        self.assertEqual(len(df_actions), 1)
        self.assertEqual(df_actions.iloc[0]["action_name"], "LED Bulb Upgrade")
        self.assertEqual(df_actions.iloc[0]["tariff_inr"], 8.0)

        # Update action
        updated = update_saving_action(
            action_id=act_id,
            action_name="LED Bulb Upgrade V2",
            action_category="Reducing unnecessary lighting",
            action_date="2008-05-15",
            baseline_days=21,
            followup_days=21,
            tariff_inr=8.5,
            notes="Updated notes",
            db_path=self.test_db,
        )
        self.assertTrue(updated)
        df_after_update = get_all_saving_actions(self.test_db)
        self.assertEqual(df_after_update.iloc[0]["action_name"], "LED Bulb Upgrade V2")
        self.assertEqual(df_after_update.iloc[0]["baseline_days"], 21)

        # Delete action
        deleted = delete_saving_action(act_id, self.test_db)
        self.assertTrue(deleted)
        df_after_delete = get_all_saving_actions(self.test_db)
        self.assertEqual(len(df_after_delete), 0)

    def test_db_readonly_query_security(self):
        init_db(self.test_db)

        # Allowed query
        res = run_readonly_query("SELECT count(*) as cnt FROM energy_saving_actions", db_path=self.test_db)
        self.assertIn("cnt", res.columns)

        # Disallowed queries
        with self.assertRaises(ValueError):
            run_readonly_query("DROP TABLE energy_saving_actions", db_path=self.test_db)

        with self.assertRaises(ValueError):
            run_readonly_query("INSERT INTO energy_saving_actions (action_name) VALUES ('hack')", db_path=self.test_db)

    # =====================================================================
    # 2. SAVINGS TRACKER IMPACT EVALUATION TESTS (FEATURE 1)
    # =====================================================================

    def test_savings_tracker_math(self):
        dates = pd.date_range("2024-01-01", periods=60, freq="D")
        values = [20.0] * 30 + [15.0] * 30
        daily_series = pd.Series(values, index=dates)

        action_d = date(2024, 1, 31)
        res = evaluate_action_impact(
            daily_series=daily_series,
            action_date=action_d,
            baseline_days=14,
            followup_days=14,
            tariff_inr=10.0,
        )

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["baseline_mean_kwh"], 20.0)
        self.assertEqual(res["followup_mean_kwh"], 15.0)
        self.assertEqual(res["absolute_daily_diff_kwh"], 5.0)
        self.assertEqual(res["percentage_change"], 25.0)
        self.assertEqual(res["estimated_daily_cost_diff"], 50.0)
        self.assertEqual(res["estimated_period_cost_diff"], 700.0)

    def test_savings_tracker_edge_cases(self):
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        daily_series = pd.Series([10.0] * 10, index=dates)

        # Action date out of range
        res = evaluate_action_impact(daily_series, date(2025, 1, 1), 14, 14, 7.5)
        self.assertEqual(res["status"], "insufficient_data")

        # Zero baseline
        zero_series = pd.Series([0.0] * 10 + [5.0] * 10, index=pd.date_range("2024-01-01", periods=20, freq="D"))
        res_zero = evaluate_action_impact(zero_series, date(2024, 1, 11), 7, 7, 7.5)
        self.assertEqual(res_zero["status"], "success")
        self.assertEqual(res_zero["percentage_change"], 0.0)

        # Negative tariff
        res_neg_tariff = evaluate_action_impact(daily_series, date(2024, 1, 6), 3, 3, -5.0)
        self.assertEqual(res_neg_tariff["tariff_inr"], 0.0)
        self.assertEqual(res_neg_tariff["estimated_daily_cost_diff"], 0.0)

    # =====================================================================
    # 3. K-MEANS PROFILING & PCA TESTS (FEATURE 2)
    # =====================================================================

    def test_behavioural_profiling(self):
        dt_range = pd.date_range("2024-01-01 00:00:00", periods=14 * 1440, freq="min")
        rng = np.random.default_rng(42)
        power_vals = rng.uniform(0.5, 3.5, size=len(dt_range))
        mock_df = pd.DataFrame({
            "DateTime": dt_range,
            "Global_active_power": power_vals,
        })

        feat_df = extract_behavioural_features(mock_df, granularity="Daily")
        self.assertEqual(len(feat_df), 14)
        for expected_col in ["total_kwh", "peak_power_kw", "std_power_kw", "evening_kwh", "overnight_kwh"]:
            self.assertIn(expected_col, feat_df.columns)

        clustered_df, ctx = run_kmeans_clustering(feat_df, n_clusters=3, random_state=42)
        self.assertIn("cluster", clustered_df.columns)
        self.assertIn("cluster_label", clustered_df.columns)
        self.assertIn("pca1", clustered_df.columns)
        self.assertIn("pca2", clustered_df.columns)
        self.assertEqual(ctx["n_clusters"], 3)
        self.assertEqual(len(ctx["pca_variance_ratio"]), 2)

    def test_kmeans_insufficient_data(self):
        small_df = pd.DataFrame({
            "period": [date(2024, 1, 1)],
            "total_kwh": [15.0],
            "peak_power_kw": [2.5],
            "std_power_kw": [0.5],
            "evening_kwh": [3.0],
            "overnight_kwh": [2.0],
            "peak_to_avg_ratio": [1.5],
            "is_weekend": [0.0],
        })
        with self.assertRaises(ValueError):
            run_kmeans_clustering(small_df, n_clusters=3)

    # =====================================================================
    # 4. CHANGE-POINT DETECTION TESTS (FEATURE 3)
    # =====================================================================

    def test_synthetic_validation_and_cusum(self):
        synth_series, true_cp = generate_synthetic_validation_series(
            n_days=100, base_mean=10.0, shift_size=15.0, noise_std=1.0, changepoint_day=50, seed=42
        )
        self.assertEqual(len(synth_series), 100)
        self.assertEqual(true_cp, 50)

        cp_indices, diag = detect_cusum_changepoints(synth_series, threshold=1.2, min_segment_length=14)
        self.assertGreater(len(cp_indices), 0)
        self.assertLessEqual(abs(cp_indices[0] - true_cp), 5)

        summary = summarize_changepoints(synth_series, cp_indices, window_days=20)
        self.assertFalse(summary.empty)
        self.assertIn("Pre-Shift Mean (kWh)", summary.columns)
        self.assertIn("Post-Shift Mean (kWh)", summary.columns)
        self.assertIn("Absolute Shift (kWh)", summary.columns)

    def test_binary_segmentation_changepoints(self):
        synth_series, _ = generate_synthetic_validation_series(
            n_days=80, base_mean=10.0, shift_size=20.0, noise_std=1.2, changepoint_day=40, seed=123
        )
        cps = detect_binary_segmentation_changepoints(synth_series, min_segment_length=10, significance_alpha=0.01)
        self.assertGreaterEqual(len(cps), 1)
        self.assertLessEqual(abs(cps[0] - 40), 4)

    # =====================================================================
    # 5. CARBON FOOTPRINT INTELLIGENCE TESTS (FEATURE 4)
    # =====================================================================

    def test_carbon_emissions_calculations(self):
        res = calculate_emissions(1000.0, emission_factor=CEA_NATIONAL_GRID_FACTOR)
        self.assertEqual(res["consumption_kwh"], 1000.0)
        self.assertEqual(round(res["emissions_kg"], 1), 716.0)
        self.assertEqual(round(res["emissions_tonnes"], 3), 0.716)

        res_zero = calculate_emissions(0.0)
        self.assertEqual(res_zero["emissions_kg"], 0.0)

        res_neg = calculate_emissions(-50.0)
        self.assertEqual(res_neg["emissions_kg"], 0.0)

        daily_s = pd.Series([10.0, 20.0, 30.0], index=pd.date_range("2024-01-01", periods=3, freq="D"))
        daily_em = compute_daily_emissions(daily_s, emission_factor=0.8)
        self.assertEqual(len(daily_em), 3)
        self.assertEqual(daily_em.iloc[0]["Emissions (kg CO2e)"], 8.0)

        top_days = find_highest_emission_days(daily_s, emission_factor=0.8, top_n=2)
        self.assertEqual(len(top_days), 2)
        self.assertEqual(top_days.iloc[0]["Consumption (kWh)"], 30.0)

    # =====================================================================
    # 6. CUSTOM DATASET UPLOAD TESTS (FEATURE 5)
    # =====================================================================

    def test_custom_dataset_upload_and_mapping(self):
        csv_text = """Date,Time,Active_Power_kW,Kitchen_Wh
2024-01-01,00:00:00,1.25,10
2024-01-01,00:01:00,1.30,12
2024-01-01,00:02:00,invalid,15
2024-01-01,00:03:00,1.40,18
"""
        cleaned, report, issues = validate_and_transform_uploaded_csv(
            file_bytes=csv_text.encode("utf-8"),
            date_col="Date",
            time_col="Time",
            power_col="Active_Power_kW",
            sub1_col="Kitchen_Wh",
        )

        self.assertIsNotNone(cleaned)
        self.assertEqual(report["total_rows"], 4)
        self.assertEqual(report["usable_rows"], 3)
        self.assertIn("DateTime", cleaned.columns)
        self.assertIn("Global_active_power", cleaned.columns)
        self.assertIn("Sub_metering_1", cleaned.columns)
        self.assertTrue(any("invalid or missing power" in issue for issue in issues))

    def test_column_candidate_auto_detection(self):
        cols = ["timestamp", "power_kw", "sub_metering_1", "voltage_v"]
        mapping = detect_candidate_columns(cols)
        self.assertEqual(mapping["datetime"], "timestamp")
        self.assertEqual(mapping["power"], "power_kw")
        self.assertEqual(mapping["sub1"], "sub_metering_1")

    # =====================================================================
    # 7. CONFIDENCE-AWARE INTELLIGENT INSIGHTS TESTS (FEATURE 6)
    # =====================================================================

    def test_intelligent_insights_generation(self):
        dates = pd.date_range("2024-01-01 00:00:00", periods=60 * 1440, freq="min")
        df_raw = pd.DataFrame({"DateTime": dates})
        is_weekend = df_raw["DateTime"].dt.weekday >= 5
        df_raw["Global_active_power"] = np.where(is_weekend, 2.5, 1.0)
        df_raw["Sub_metering_1"] = 100.0
        df_raw["Sub_metering_2"] = 200.0
        df_raw["Sub_metering_3"] = 800.0

        daily = df_raw.set_index("DateTime")["Global_active_power"].resample("D").sum().div(60)

        insights = generate_intelligent_insights(df_raw, daily)
        self.assertGreaterEqual(len(insights), 3)

        categories = [i.category for i in insights]
        self.assertIn("Behavioral Dynamics", categories)
        self.assertIn("Energy Efficiency", categories)

        for ins in insights:
            self.assertIn(ins.confidence_level, ["HIGH", "MODERATE", "LOW"])
            self.assertGreater(len(ins.limitations), 0)
            self.assertNotEqual(ins.recommendation, "")

    def test_changepoint_constant_and_empty(self):
        empty_s = pd.Series(dtype=float)
        cps, diag = detect_cusum_changepoints(empty_s)
        self.assertEqual(len(cps), 0)
        self.assertTrue(diag.empty)

        const_s = pd.Series([10.0] * 50, index=pd.date_range("2024-01-01", periods=50, freq="D"))
        cps_const, diag_const = detect_cusum_changepoints(const_s)
        self.assertEqual(len(cps_const), 0)

    def test_pdf_report_generation(self):
        dt_range = pd.date_range("2024-01-01 00:00:00", periods=5 * 1440, freq="min")
        rng = np.random.default_rng(42)
        mock_df = pd.DataFrame({
            "DateTime": dt_range,
            "Global_active_power": rng.uniform(0.5, 2.5, size=len(dt_range)),
            "Global_reactive_power": rng.uniform(0.1, 0.4, size=len(dt_range)),
            "Voltage": rng.uniform(230, 245, size=len(dt_range)),
            "Global_intensity": rng.uniform(2.0, 10.0, size=len(dt_range)),
            "Sub_metering_1": rng.integers(0, 50, size=len(dt_range)).astype(float),
            "Sub_metering_2": rng.integers(0, 50, size=len(dt_range)).astype(float),
            "Sub_metering_3": rng.integers(0, 50, size=len(dt_range)).astype(float),
        })
        daily_s = mock_df.set_index("DateTime")["Global_active_power"].resample("D").sum().div(60)

        import sys, os
        sys.path.insert(0, os.getcwd())
        from dashboard import make_pdf_report

        pdf_bytes = make_pdf_report(mock_df, daily_s, "test_dataset.csv")
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()

