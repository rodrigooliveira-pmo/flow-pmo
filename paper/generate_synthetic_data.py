"""
generate_synthetic_data.py
==========================
Generates a reproducible synthetic dataset of developer productivity metrics
for Q3 2024 (2024-07-01 to 2024-09-30).

Usage:
    python paper/generate_synthetic_data.py

Output:
    paper/data/developers_q3_2024.csv
    paper/data/summary_by_team.csv
    paper/data/summary_by_role.csv
"""

import os
import math
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SEED = 42
rng = np.random.default_rng(SEED)

TEAMS = {
    "W1NNER":    {"n_devs": 9, "n_tl": 2},
    "S1NC":      {"n_devs": 7, "n_tl": 2},
    "BeFinance": {"n_devs": 5, "n_tl": 1},
    "Data":      {"n_devs": 4, "n_tl": 1},
    "Infra":     {"n_devs": 3, "n_tl": 1},
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Helper generators
# ---------------------------------------------------------------------------

def normal_clip(mean, std, low, high, size, rng):
    return np.clip(rng.normal(mean, std, size), low, high)


def lognormal_clip(mean, sigma, low, high, size, rng):
    """
    Draw from a log-normal such that the *median* of the underlying normal
    corresponds to `mean` (i.e., mu = log(mean)).
    """
    mu = math.log(mean)
    return np.clip(rng.lognormal(mu, sigma, size), low, high)


# ---------------------------------------------------------------------------
# Build developer records
# ---------------------------------------------------------------------------

records = []
dev_id = 1

for team, cfg in TEAMS.items():
    n_total = cfg["n_devs"]
    n_tl    = cfg["n_tl"]
    n_dev   = n_total - n_tl

    for role, count in [("Tech Lead", n_tl), ("Dev", n_dev)]:
        for _ in range(count):
            rec = {}
            rec["developer_id"] = f"DEV{dev_id:03d}"
            rec["team"]         = team
            rec["role"]         = role

            # -- Items pulled --------------------------------------------------
            if role == "Tech Lead":
                items_pulled = int(round(normal_clip(10, 3, 4, 18, 1, rng)[0]))
            else:
                items_pulled = int(round(normal_clip(15, 5, 5, 28, 1, rng)[0]))

            # -- Flow efficiency -----------------------------------------------
            flow_eff = normal_clip(68, 15, 30, 100, 1, rng)[0]

            # -- Delivery counts -----------------------------------------------
            items_delivered = int(math.floor(items_pulled * flow_eff / 100))
            items_delivered = max(items_delivered, 1)       # at least 1
            wip_residual    = items_pulled - items_delivered

            rec["items_pulled"]        = items_pulled
            rec["items_delivered"]     = items_delivered
            rec["wip_residual"]        = wip_residual
            rec["flow_efficiency_pct"] = round(flow_eff, 2)

            # -- Story-point delivery ------------------------------------------
            sp_per_item = normal_clip(3.5, 1.5, 1, 8, items_delivered, rng)
            sp_delivered = int(round(sp_per_item.sum()))
            rec["sp_delivered"] = sp_delivered

            # -- Score complexity (SP-bucket weighted) -------------------------
            # Assign each delivered item a bucket weight based on its SP
            score_complexity = 0.0
            for sp in sp_per_item:
                if sp < 1:
                    score_complexity += 0.5        # no/trivial estimate
                elif sp <= 3:
                    score_complexity += 1.0        # small
                elif sp <= 8:
                    score_complexity += 2.0        # medium
                else:
                    score_complexity += 3.0        # large / 13+
            rec["score_complexity"] = round(score_complexity, 2)

            # -- Defects -------------------------------------------------------
            defects = int(rng.poisson(items_delivered * 0.18))
            rec["defects_delivered"]  = defects
            rec["pct_failure_demand"] = round(
                defects / items_delivered * 100 if items_delivered > 0 else 0.0, 2
            )

            # -- Lead time (median days) ---------------------------------------
            rec["lead_time_median_days"] = round(
                lognormal_clip(8, 0.7, 1, 35, 1, rng)[0], 2
            )

            # -- Engineering activity ------------------------------------------
            if role == "Tech Lead":
                commits = int(round(normal_clip(35, 15, 8, 80, 1, rng)[0]))
            else:
                commits = int(round(normal_clip(65, 25, 15, 150, 1, rng)[0]))

            prs_merged = int(round(normal_clip(10, 4, 2, 25, 1, rng)[0]))

            rec["commits"]    = commits
            rec["prs_merged"] = prs_merged

            # -- Quality metrics -----------------------------------------------
            review_quality = normal_clip(72, 15, 30, 100, 1, rng)[0]
            if role == "Tech Lead":
                review_quality = min(review_quality + 10, 100)
            rec["review_quality_pct"] = round(review_quality, 2)

            rec["pipeline_success_rate_pct"] = round(
                normal_clip(74, 18, 20, 100, 1, rng)[0], 2
            )
            rec["conformance_quality_pct"] = round(
                normal_clip(71, 14, 35, 98, 1, rng)[0], 2
            )
            rec["rework_rate_pct"] = round(
                normal_clip(19, 9, 2, 50, 1, rng)[0], 2
            )
            rec["qa_return_rate_pct"] = round(
                normal_clip(14, 8, 0, 40, 1, rng)[0], 2
            )

            # -- Process / flow complexity ------------------------------------
            rec["variant_complexity"] = round(
                normal_clip(3.2, 1.1, 1, 6, 1, rng)[0], 2
            )
            rec["bottleneck_hours"] = round(
                float(np.clip(rng.exponential(12, 1)[0], 0, 80)), 2
            )

            records.append(rec)
            dev_id += 1

# ---------------------------------------------------------------------------
# Build DataFrame
# ---------------------------------------------------------------------------

df = pd.DataFrame(records)

# ---------------------------------------------------------------------------
# Radar / benchmark scores
# ---------------------------------------------------------------------------

p75_score_complexity = df["score_complexity"].quantile(0.75)

df["_rb_entrega"]      = (df["score_complexity"] / p75_score_complexity * 100).clip(0, 100)
df["_rb_flow"]         = (df["flow_efficiency_pct"] / 80 * 100).clip(0, 100)
df["_rb_revisao"]      = (df["review_quality_pct"] / 70 * 100).clip(0, 100)
df["_rb_conformance"]  = (df["conformance_quality_pct"] / 75 * 100).clip(0, 100)
df["_rb_anti_rework"]  = ((100 - df["rework_rate_pct"]) / 80 * 100).clip(0, 100)

ideal = np.array([100, 100, 100, 100, 100])
radar_cols = ["_rb_entrega", "_rb_flow", "_rb_revisao", "_rb_conformance", "_rb_anti_rework"]

distances = df[radar_cols].apply(
    lambda row: np.linalg.norm(row.values - ideal), axis=1
)

# Max possible euclidean distance: sqrt(5) * 100
max_dist = math.sqrt(5) * 100
df["distance_to_ideal"] = (distances / max_dist * 100).clip(0, 100)
df["score_benchmark"]   = (100 - df["distance_to_ideal"]).round(2)

df["score_integrated"] = (
    df["score_complexity"]
    + df["prs_merged"]
    + df["commits"] / 5
).round(2)

# Round radar columns
for col in radar_cols + ["distance_to_ideal"]:
    df[col] = df[col].round(2)

# ---------------------------------------------------------------------------
# Save full table
# ---------------------------------------------------------------------------

out_full = os.path.join(OUTPUT_DIR, "developers_q3_2024.csv")
df.to_csv(out_full, index=False)
print(f"[OK] Saved full developer table → {out_full}")

# ---------------------------------------------------------------------------
# Summary by team
# ---------------------------------------------------------------------------

numeric_cols = df.select_dtypes(include="number").columns.tolist()
summary_team = df.groupby("team")[numeric_cols].median().round(2).reset_index()
out_team = os.path.join(OUTPUT_DIR, "summary_by_team.csv")
summary_team.to_csv(out_team, index=False)
print(f"[OK] Saved team summary       → {out_team}")

# ---------------------------------------------------------------------------
# Summary by role
# ---------------------------------------------------------------------------

summary_role = df.groupby("role")[numeric_cols].median().round(2).reset_index()
out_role = os.path.join(OUTPUT_DIR, "summary_by_role.csv")
summary_role.to_csv(out_role, index=False)
print(f"[OK] Saved role summary       → {out_role}")

# ---------------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------------

print("\n" + "=" * 70)
print("SYNTHETIC DATA SUMMARY — FlowPMO Q3 2024 (seed=42)")
print("=" * 70)
print(f"  Developers : {len(df)}")
print(f"  Teams      : {df['team'].nunique()}")
print(f"  Period     : 2024-07-01 → 2024-09-30  (92 days)")
print(f"  Roles      : {dict(df['role'].value_counts())}")
print()

key_metrics = [
    "items_delivered", "flow_efficiency_pct", "score_complexity",
    "review_quality_pct", "conformance_quality_pct", "rework_rate_pct",
    "score_benchmark", "score_integrated",
]

print(f"{'Metric':<30} {'Mean':>8} {'Median':>8} {'Std':>8} {'Min':>8} {'Max':>8}")
print("-" * 70)
for col in key_metrics:
    s = df[col]
    print(
        f"{col:<30} {s.mean():>8.2f} {s.median():>8.2f} "
        f"{s.std():>8.2f} {s.min():>8.2f} {s.max():>8.2f}"
    )

print()
print("--- By Role (medians) ---")
print(summary_role[["role"] + [c for c in key_metrics if c in summary_role.columns]].to_string(index=False))

print()
print("--- By Team (medians) ---")
print(summary_team[["team"] + [c for c in key_metrics if c in summary_team.columns]].to_string(index=False))
print("=" * 70)
