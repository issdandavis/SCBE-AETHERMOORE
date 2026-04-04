#!/usr/bin/env python3
"""Energy-Aware Compute Simulation
====================================

Simulates 24 hours of workload requests against the SCBE /v1/compute/authorize
endpoint logic, using real microgrid data from Kaggle (or synthetic fallback).

Produces concrete metrics:
  - Total kWh consumed vs baseline (if everything ran on FULL tier)
  - Number of DENY decisions (thermal/energy prevention)
  - Tier distribution (TINY vs MEDIUM vs FULL)
  - Energy savings percentage
  - Peak demand reduction

Usage:
    python scripts/energy_compute_simulation.py
"""

from __future__ import annotations

import json
import math
import random
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Ensure repo root is on sys.path so imports resolve
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.api.compute_routes import (
    EnergySource,
    EnergyState,
    InferenceTier,
    TIER_PROFILES,
    _estimate_workload_energy,
    _select_tier,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
HOURS = 24
NUM_WORKLOADS = 1000
ARTIFACTS_DIR = REPO_ROOT / "artifacts" / "energy_sim"
REPORT_PATH = ARTIFACTS_DIR / "simulation_24h_report.json"
KAGGLE_OWNER = "programmer3"
KAGGLE_DATASET = "renewable-energy-microgrid-dataset"
KAGGLE_FILE = "Renewable_energy_dataset.csv"

random.seed(42)


# ---------------------------------------------------------------------------
# Data loading: Kaggle download or synthetic fallback
# ---------------------------------------------------------------------------

def _try_download_kaggle() -> Optional[Any]:
    """Attempt to download the Kaggle microgrid dataset via kagglehub or kaggle API.

    Returns a pandas DataFrame if successful, None otherwise.
    """
    try:
        import pandas as pd
    except ImportError:
        print("[INFO] pandas not installed -- using synthetic data")
        return None

    # Strategy 1: kagglehub (newest recommended approach)
    try:
        import kagglehub
        path = kagglehub.dataset_download(f"{KAGGLE_OWNER}/{KAGGLE_DATASET}")
        csv_path = Path(path) / KAGGLE_FILE
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            print(f"[OK] Loaded Kaggle dataset via kagglehub: {len(df)} rows")
            return df
    except Exception as e:
        print(f"[INFO] kagglehub download failed: {e}")

    # Strategy 2: kaggle CLI / API
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
        with tempfile.TemporaryDirectory() as tmpdir:
            api.dataset_download_files(
                f"{KAGGLE_OWNER}/{KAGGLE_DATASET}",
                path=tmpdir,
                unzip=True,
            )
            csv_path = Path(tmpdir) / KAGGLE_FILE
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                print(f"[OK] Loaded Kaggle dataset via kaggle API: {len(df)} rows")
                return df
    except Exception as e:
        print(f"[INFO] kaggle API download failed: {e}")

    # Strategy 3: direct URL (public datasets sometimes accessible)
    try:
        import urllib.request
        url = (
            f"https://www.kaggle.com/api/v1/datasets/download/"
            f"{KAGGLE_OWNER}/{KAGGLE_DATASET}/{KAGGLE_FILE}"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "dataset.zip"
            urllib.request.urlretrieve(url, zip_path)
            if zipfile.is_zipfile(zip_path):
                with zipfile.ZipFile(zip_path) as zf:
                    zf.extractall(tmpdir)
                csv_path = Path(tmpdir) / KAGGLE_FILE
                if csv_path.exists():
                    df = pd.read_csv(csv_path)
                    print(f"[OK] Loaded Kaggle dataset via direct URL: {len(df)} rows")
                    return df
    except Exception as e:
        print(f"[INFO] direct URL download failed: {e}")

    return None


def _extract_hourly_profiles_from_kaggle(df: Any) -> List[Dict[str, float]]:
    """Extract 24 hourly energy profiles from the Kaggle microgrid data.

    The Kaggle dataset (programmer3/renewable-energy-microgrid-dataset) has
    3546 hourly rows with columns including:
      - solar_pv_output (0-100 normalized), wind_power_output (0-100)
      - battery_state_of_charge (0-100%), temperature (C)
      - solar_irradiance (W/m2), grid_load_demand, hour_of_day (0-23)

    Because solar_pv_output in the dataset is uniformly distributed (not
    time-of-day correlated), we use the real battery/temperature/irradiance
    averages per hour but apply a realistic solar envelope so nighttime
    solar is zero and daytime peaks at noon.
    """
    import pandas as pd

    # Use the built-in hour_of_day column if present, else parse timestamp
    if "hour_of_day" in df.columns:
        df["_hour"] = df["hour_of_day"].astype(int)
    else:
        dt_col = _find_col(df, ["timestamp", "date", "time"])
        if dt_col:
            df["_hour"] = pd.to_datetime(df[dt_col], errors="coerce").dt.hour
        else:
            df["_hour"] = df.index % 24

    # Map column names flexibly
    solar_col = _find_col(df, ["solar_pv_output", "solar_power", "pv_power"])
    battery_col = _find_col(df, ["battery_state_of_charge", "battery_soc", "soc"])
    temp_col = _find_col(df, ["temperature", "temp", "ambient_temp"])
    irradiance_col = _find_col(df, ["solar_irradiance", "irradiance", "ghi"])
    load_col = _find_col(df, ["grid_load_demand", "load_demand", "demand"])

    # Global averages for scaling
    solar_global_mean = df[solar_col].mean() if solar_col else 50.0

    profiles = []
    for hour in range(24):
        hour_data = df[df["_hour"] == hour]
        if len(hour_data) == 0:
            hour_data = df  # fallback to global average

        # Raw aggregates from Kaggle
        solar_raw = float(hour_data[solar_col].mean()) if solar_col else 50.0
        battery_pct = float(hour_data[battery_col].mean()) if battery_col else 50.0
        temp_c = float(hour_data[temp_col].mean()) if temp_col else 25.0
        irradiance = float(hour_data[irradiance_col].mean()) if irradiance_col else 0.0
        load_demand = float(hour_data[load_col].mean()) if load_col else 250.0

        # Sanitize NaN
        if math.isnan(solar_raw):
            solar_raw = 50.0
        if math.isnan(battery_pct):
            battery_pct = 50.0
        if math.isnan(temp_c):
            temp_c = 25.0
        if math.isnan(irradiance):
            irradiance = 0.0
        if math.isnan(load_demand):
            load_demand = 250.0

        # Apply realistic solar envelope: zero at night, bell curve 6am-6pm.
        # Scale the Kaggle normalized value (0-100) by the envelope and convert
        # to a representative kW output for a ~5kW peak array.
        if 6 <= hour <= 18:
            solar_envelope = math.sin(math.pi * (hour - 6) / 12)
        else:
            solar_envelope = 0.0

        # solar_raw/100 * 5kW * envelope => realistic kW
        solar_kw = (solar_raw / 100.0) * 5.0 * solar_envelope

        profiles.append({
            "hour": hour,
            "solar_kw": round(solar_kw, 3),
            "battery_pct": round(battery_pct, 1),
            "temperature_c": round(temp_c, 1),
            "irradiance_wm2": round(irradiance, 1),
            "load_demand": round(load_demand, 1),
        })

    return profiles


def _find_col(df: Any, candidates: List[str]) -> Optional[str]:
    """Find a DataFrame column matching any of the candidate substrings (case-insensitive)."""
    for col in df.columns:
        for cand in candidates:
            if cand.lower() in col.lower():
                return col
    return None


def _generate_synthetic_profiles() -> List[Dict[str, float]]:
    """Generate synthetic 24-hour energy profiles when Kaggle data is unavailable."""
    print("[INFO] Generating synthetic 24-hour energy profiles")
    profiles = []
    for hour in range(24):
        # Solar: bell curve peaking at noon
        if 6 <= hour <= 18:
            solar_kw = 5.0 * math.sin(math.pi * (hour - 6) / 12)
        else:
            solar_kw = 0.0

        # Battery: starts at 80%, charges during solar, discharges otherwise
        if 6 <= hour <= 14:
            battery_pct = 80.0 + (hour - 6) * 2.0  # Charges up to ~96%
        elif hour < 6:
            battery_pct = 80.0 - (6 - hour) * 3.0  # Discharges overnight
        else:
            battery_pct = 96.0 - (hour - 14) * 3.0  # Discharges afternoon/evening

        battery_pct = max(10.0, min(100.0, battery_pct))

        # Temperature
        temperature_c = 20.0 + 10.0 * math.sin(math.pi * (hour - 4) / 16) if 4 <= hour <= 20 else 15.0

        # Irradiance
        if 6 <= hour <= 18:
            irradiance = 800.0 * math.sin(math.pi * (hour - 6) / 12)
        else:
            irradiance = 0.0

        profiles.append({
            "hour": hour,
            "solar_kw": round(solar_kw, 2),
            "battery_pct": round(battery_pct, 1),
            "temperature_c": round(temperature_c, 1),
            "irradiance_wm2": round(irradiance, 1),
        })

    return profiles


# ---------------------------------------------------------------------------
# Grid price model
# ---------------------------------------------------------------------------

def _grid_price_for_hour(hour: int) -> float:
    """Simulate time-of-use grid pricing ($/kWh).

    - Off-peak (11pm-6am): $0.06/kWh
    - Mid-peak (6am-2pm, 6pm-11pm): $0.12/kWh
    - Peak (2pm-6pm): $0.25/kWh
    """
    if 23 <= hour or hour < 6:
        return 0.06
    elif 14 <= hour < 18:
        return 0.25
    else:
        return 0.12


# ---------------------------------------------------------------------------
# Workload generator
# ---------------------------------------------------------------------------

def _generate_workloads(n: int) -> List[Dict[str, Any]]:
    """Generate n simulated workloads distributed across 24 hours.

    Workload characteristics:
      - Model sizes: 0.01B to 70B (log-distributed)
      - Token counts: 100 to 10000
      - Priorities: 1-10
      - Arrival hour: distributed with peaks during business hours
    """
    workloads = []
    for i in range(n):
        # Arrival hour: weighted toward business hours (8am-6pm)
        if random.random() < 0.7:
            hour = random.randint(8, 17)
        else:
            hour = random.randint(0, 23)

        # Model size: log-uniform between 0.01B and 70B
        log_min = math.log(0.01)
        log_max = math.log(70.0)
        model_size = math.exp(random.uniform(log_min, log_max))

        # Token count: 100 to 10000
        tokens = random.randint(100, 10000)

        # Priority: 1-10 (slight bias toward middle)
        priority = max(1, min(10, int(random.gauss(5.5, 2.0))))

        # Latency requirement: 0 (no constraint) or 100-10000ms
        if random.random() < 0.3:
            latency_req_ms = 0.0
        else:
            latency_req_ms = random.uniform(100, 10000)

        # Cloud escalation: most allow it
        allow_cloud = random.random() < 0.85

        workloads.append({
            "id": f"wl-{i:04d}",
            "hour": hour,
            "model_size_b": round(model_size, 3),
            "tokens": tokens,
            "priority": priority,
            "latency_req_ms": round(latency_req_ms, 1),
            "allow_cloud": allow_cloud,
        })

    return workloads


# ---------------------------------------------------------------------------
# Simulation engine
# ---------------------------------------------------------------------------

def run_simulation(profiles: List[Dict[str, float]], workloads: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Run the 24-hour simulation.

    For each hour:
      1. Build the EnergyState from the profile
      2. Process all workloads arriving in that hour
      3. Track energy consumed, tier decisions, denials
    """
    # Group workloads by hour
    by_hour: Dict[int, List[Dict[str, Any]]] = {h: [] for h in range(24)}
    for wl in workloads:
        by_hour[wl["hour"]].append(wl)

    # Tracking
    tier_counts = {t.value: 0 for t in InferenceTier}
    total_energy_wh = 0.0
    baseline_energy_wh = 0.0  # Everything on FULL tier
    deny_count = 0
    hourly_results: List[Dict[str, Any]] = []
    peak_demand_w_actual = 0.0
    peak_demand_w_baseline = 0.0
    cooling_failures = 0

    # Running battery state -- use Kaggle profile as starting point but
    # evolve it dynamically based on solar charging vs compute discharge.
    battery_capacity_wh = 10000.0  # 10 kWh battery
    running_battery_pct = profiles[0]["battery_pct"]

    for hour in range(HOURS):
        profile = profiles[hour]
        hour_workloads = by_hour[hour]

        # Determine cooling availability (5% random failure per hour)
        # Use a deterministic seed per hour for reproducibility
        cooling_ok = random.random() > 0.05
        if not cooling_ok:
            cooling_failures += 1

        # Solar contribution to available energy (kW * 1h = kWh -> Wh)
        solar_wh = profile["solar_kw"] * 1000.0  # kW to Wh for 1 hour

        # Battery available energy
        battery_available_wh = (running_battery_pct / 100.0) * battery_capacity_wh

        # Grid always available (but priced)
        grid_price = _grid_price_for_hour(hour)

        # Total available energy = solar + battery + modest grid backstop
        # Grid backstop is intentionally limited to force tier selection pressure
        grid_backstop_wh = 2000.0  # 2 kWh grid budget per hour
        available_wh = solar_wh + battery_available_wh + grid_backstop_wh

        # Determine primary source
        if solar_wh > 200:
            source = EnergySource.SOLAR
        elif running_battery_pct > 30:
            source = EnergySource.BATTERY
        else:
            source = EnergySource.GRID

        # Solar forecast for next hour
        next_hour = (hour + 1) % 24
        solar_forecast_wh = profiles[next_hour]["solar_kw"] * 1000.0

        # Build energy state
        energy_state = EnergyState(
            available_wh=available_wh,
            source=source,
            battery_pct=running_battery_pct,
            solar_forecast_wh=solar_forecast_wh,
            grid_price_per_kwh=grid_price,
            cooling_available=cooling_ok,
        )

        hour_energy_consumed = 0.0
        hour_baseline_consumed = 0.0
        hour_power_actual = 0.0
        hour_power_baseline = 0.0
        hour_tier_counts = {t.value: 0 for t in InferenceTier}

        for wl in hour_workloads:
            # Call _select_tier with current energy state
            tier, harmonic_cost, signals = _select_tier(
                model_size_b=wl["model_size_b"],
                tokens=wl["tokens"],
                latency_req_ms=wl["latency_req_ms"],
                priority=wl["priority"],
                energy=energy_state,
                allow_cloud=wl["allow_cloud"],
            )

            tier_counts[tier.value] += 1
            hour_tier_counts[tier.value] += 1

            if tier == InferenceTier.DENY:
                deny_count += 1
                # Baseline still counts as if it ran on FULL
                baseline_e = _estimate_workload_energy(wl["tokens"], InferenceTier.FULL)
                baseline_energy_wh += baseline_e
                hour_baseline_consumed += baseline_e
                hour_power_baseline += TIER_PROFILES[InferenceTier.FULL]["power_w"]
            else:
                # Actual energy consumed
                actual_e = _estimate_workload_energy(wl["tokens"], tier)
                total_energy_wh += actual_e
                hour_energy_consumed += actual_e
                hour_power_actual += TIER_PROFILES[tier]["power_w"]

                # Baseline: if this ran on FULL
                baseline_e = _estimate_workload_energy(wl["tokens"], InferenceTier.FULL)
                baseline_energy_wh += baseline_e
                hour_baseline_consumed += baseline_e
                hour_power_baseline += TIER_PROFILES[InferenceTier.FULL]["power_w"]

                # Reduce available energy for next workload this hour
                energy_state.available_wh = max(0, energy_state.available_wh - actual_e)

        # Update battery: charge from solar, discharge from compute
        solar_charge_wh = solar_wh * 0.3  # 30% of solar goes to battery
        battery_delta_pct = ((solar_charge_wh - hour_energy_consumed) / battery_capacity_wh) * 100.0
        running_battery_pct = max(5.0, min(100.0, running_battery_pct + battery_delta_pct))

        # Track peak demand
        peak_demand_w_actual = max(peak_demand_w_actual, hour_power_actual)
        peak_demand_w_baseline = max(peak_demand_w_baseline, hour_power_baseline)

        hourly_results.append({
            "hour": hour,
            "workloads_processed": len(hour_workloads),
            "tier_distribution": hour_tier_counts,
            "energy_consumed_wh": round(hour_energy_consumed, 4),
            "baseline_energy_wh": round(hour_baseline_consumed, 4),
            "battery_pct_end": round(running_battery_pct, 1),
            "solar_available_wh": round(solar_wh, 1),
            "grid_price_per_kwh": grid_price,
            "cooling_available": cooling_ok,
            "source": source.value,
            "peak_power_w": round(hour_power_actual, 1),
        })

    # Compute summary metrics
    total_kwh = total_energy_wh / 1000.0
    baseline_kwh = baseline_energy_wh / 1000.0
    savings_pct = ((baseline_kwh - total_kwh) / baseline_kwh * 100.0) if baseline_kwh > 0 else 0.0
    peak_reduction_pct = (
        ((peak_demand_w_baseline - peak_demand_w_actual) / peak_demand_w_baseline * 100.0)
        if peak_demand_w_baseline > 0 else 0.0
    )

    # Grid cost estimate
    actual_grid_cost = sum(
        (hr["energy_consumed_wh"] / 1000.0) * hr["grid_price_per_kwh"]
        for hr in hourly_results
    )
    baseline_grid_cost = sum(
        (hr["baseline_energy_wh"] / 1000.0) * hr["grid_price_per_kwh"]
        for hr in hourly_results
    )

    summary = {
        "simulation_timestamp": datetime.now(timezone.utc).isoformat(),
        "simulation_params": {
            "hours": HOURS,
            "total_workloads": NUM_WORKLOADS,
            "cooling_failure_rate": 0.05,
            "battery_capacity_kwh": 10.0,
            "grid_backstop_kwh_per_hour": 5.0,
        },
        "energy_metrics": {
            "total_kwh_consumed": round(total_kwh, 4),
            "baseline_kwh_if_all_full": round(baseline_kwh, 4),
            "energy_savings_kwh": round(baseline_kwh - total_kwh, 4),
            "energy_savings_pct": round(savings_pct, 2),
        },
        "demand_metrics": {
            "peak_demand_w_actual": round(peak_demand_w_actual, 1),
            "peak_demand_w_baseline": round(peak_demand_w_baseline, 1),
            "peak_demand_reduction_pct": round(peak_reduction_pct, 2),
        },
        "decision_metrics": {
            "tier_distribution": tier_counts,
            "deny_count": deny_count,
            "deny_rate_pct": round(deny_count / NUM_WORKLOADS * 100.0, 2),
            "authorized_count": NUM_WORKLOADS - deny_count,
        },
        "cost_metrics": {
            "actual_grid_cost_usd": round(actual_grid_cost, 4),
            "baseline_grid_cost_usd": round(baseline_grid_cost, 4),
            "cost_savings_usd": round(baseline_grid_cost - actual_grid_cost, 4),
            "cost_savings_pct": round(
                ((baseline_grid_cost - actual_grid_cost) / baseline_grid_cost * 100.0)
                if baseline_grid_cost > 0 else 0.0,
                2,
            ),
        },
        "infrastructure_metrics": {
            "cooling_failure_hours": cooling_failures,
            "data_source": "unknown",  # Updated below
        },
        "hourly_breakdown": hourly_results,
    }

    return summary


# ---------------------------------------------------------------------------
# Report output
# ---------------------------------------------------------------------------

def _print_report(summary: Dict[str, Any]) -> None:
    """Print a human-readable summary to stdout."""
    print("\n" + "=" * 70)
    print("  SCBE Energy-Aware Compute Simulation -- 24-Hour Report")
    print("=" * 70)

    em = summary["energy_metrics"]
    dm = summary["demand_metrics"]
    dec = summary["decision_metrics"]
    cm = summary["cost_metrics"]
    infra = summary["infrastructure_metrics"]

    print(f"\n  Data source: {infra['data_source']}")
    print(f"  Workloads simulated: {summary['simulation_params']['total_workloads']}")
    print(f"  Simulation time: {summary['simulation_timestamp']}")

    print(f"\n--- Energy ---")
    print(f"  Total consumed:        {em['total_kwh_consumed']:.4f} kWh")
    print(f"  Baseline (all FULL):   {em['baseline_kwh_if_all_full']:.4f} kWh")
    print(f"  Energy saved:          {em['energy_savings_kwh']:.4f} kWh ({em['energy_savings_pct']:.1f}%)")

    print(f"\n--- Peak Demand ---")
    print(f"  Actual peak:           {dm['peak_demand_w_actual']:.1f} W")
    print(f"  Baseline peak:         {dm['peak_demand_w_baseline']:.1f} W")
    print(f"  Peak reduction:        {dm['peak_demand_reduction_pct']:.1f}%")

    print(f"\n--- Tier Distribution ---")
    td = dec["tier_distribution"]
    total = sum(td.values())
    for tier_name in ["TINY", "MEDIUM", "FULL", "DENY"]:
        count = td.get(tier_name, 0)
        pct = (count / total * 100.0) if total > 0 else 0.0
        bar = "#" * int(pct / 2)
        print(f"  {tier_name:8s}: {count:5d} ({pct:5.1f}%)  {bar}")

    print(f"\n--- Decisions ---")
    print(f"  Authorized:            {dec['authorized_count']}")
    print(f"  Denied:                {dec['deny_count']} ({dec['deny_rate_pct']:.1f}%)")
    print(f"  Cooling failures:      {infra['cooling_failure_hours']} hours")

    print(f"\n--- Grid Cost ---")
    print(f"  Actual cost:           ${cm['actual_grid_cost_usd']:.4f}")
    print(f"  Baseline cost:         ${cm['baseline_grid_cost_usd']:.4f}")
    print(f"  Cost savings:          ${cm['cost_savings_usd']:.4f} ({cm['cost_savings_pct']:.1f}%)")

    print(f"\n--- Hourly Snapshot (energy consumed Wh) ---")
    print(f"  {'Hour':>4s}  {'Wklds':>5s}  {'ActualWh':>9s}  {'BaseWh':>9s}  {'Batt%':>5s}  {'Solar':>6s}  {'$/kWh':>6s}  {'Cool':>4s}")
    print(f"  {'----':>4s}  {'-----':>5s}  {'---------':>9s}  {'------':>9s}  {'-----':>5s}  {'------':>6s}  {'------':>6s}  {'----':>4s}")
    for hr in summary["hourly_breakdown"]:
        cool_str = "OK" if hr["cooling_available"] else "FAIL"
        print(
            f"  {hr['hour']:4d}  {hr['workloads_processed']:5d}  "
            f"{hr['energy_consumed_wh']:9.4f}  {hr['baseline_energy_wh']:9.4f}  "
            f"{hr['battery_pct_end']:5.1f}  {hr['solar_available_wh']:6.0f}  "
            f"${hr['grid_price_per_kwh']:.2f}   {cool_str}"
        )

    print("\n" + "=" * 70)
    print(f"  Report saved to: {REPORT_PATH}")
    print("=" * 70 + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load energy data
    print("[1/4] Loading energy data...")
    kaggle_df = _try_download_kaggle()

    if kaggle_df is not None:
        profiles = _extract_hourly_profiles_from_kaggle(kaggle_df)
        data_source = f"kaggle:{KAGGLE_OWNER}/{KAGGLE_DATASET} ({len(kaggle_df)} rows)"
    else:
        profiles = _generate_synthetic_profiles()
        data_source = "synthetic (Kaggle unavailable)"

    print(f"  Data source: {data_source}")
    print(f"  Profile hours: {len(profiles)}")

    # 2. Generate workloads
    print(f"\n[2/4] Generating {NUM_WORKLOADS} simulated workloads across 24 hours...")
    workloads = _generate_workloads(NUM_WORKLOADS)

    # Show workload distribution
    size_buckets = {"tiny(<0.1B)": 0, "medium(0.1-3B)": 0, "large(3-70B)": 0}
    for wl in workloads:
        if wl["model_size_b"] < 0.1:
            size_buckets["tiny(<0.1B)"] += 1
        elif wl["model_size_b"] <= 3.0:
            size_buckets["medium(0.1-3B)"] += 1
        else:
            size_buckets["large(3-70B)"] += 1
    print(f"  Model size distribution: {size_buckets}")
    print(f"  Token range: {min(w['tokens'] for w in workloads)}-{max(w['tokens'] for w in workloads)}")
    print(f"  Priority range: {min(w['priority'] for w in workloads)}-{max(w['priority'] for w in workloads)}")

    # 3. Run simulation
    print(f"\n[3/4] Running 24-hour simulation...")
    summary = run_simulation(profiles, workloads)
    summary["infrastructure_metrics"]["data_source"] = data_source

    # 4. Output
    print(f"\n[4/4] Writing report...")

    # Save JSON
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    # Print human-readable report
    _print_report(summary)


if __name__ == "__main__":
    main()
