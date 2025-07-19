import os
import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# --------------- CONFIG -----------------
FIG_DPI = 300
sns.set(style="whitegrid", palette="deep", font_scale=1.1)

# --------------- HELPERS ----------------

def load_results(results_root: Path, pipeline_csv: str) -> pd.DataFrame:
    """Load and concatenate CSVs for one pipeline across all run folders"""
    frames = []
    for run_dir in results_root.glob("*run-*/"):
        csv_path = run_dir / pipeline_csv
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def aggregate(df: pd.DataFrame) -> pd.DataFrame:
    """Group by experiment keys and compute mean/std/sem"""
    if df.empty:
        return df
    group_cols = [
        "pipeline_type",
        "dataset_type",
        "dataset_size",
        "anonymization_method",
        "anonymization_params",
    ]
    numeric_cols = [c for c in df.columns if df[c].dtype != object and c not in group_cols]

    agg = (
        df.groupby(group_cols)[numeric_cols]
        .agg(["mean", "std", "sem"])
        .reset_index()
    )
    # flatten multi-index columns
    agg.columns = ["_".join(filter(None, col)).rstrip("_") for col in agg.columns]
    return agg

# --------------- PLOTS ------------------

def throughput_vs_size(all_agg: pd.DataFrame, fig_dir: Path):
    plt.figure(figsize=(8,6))
    for p in ["batch", "stream_optimized", "hybrid_adaptive"]:
        subset = all_agg[all_agg["pipeline_type"]==p]
        plt.errorbar(subset["dataset_size"], subset["records_per_second_mean"], 
                     yerr=subset["records_per_second_sem"], marker='o', label=p)
    plt.xscale('log'); plt.yscale('log')
    plt.xlabel("Dataset Size (records)"); plt.ylabel("Throughput (records/s)")
    plt.title("Throughput scaling by pipeline")
    plt.legend(); plt.tight_layout()
    plt.savefig(fig_dir/"throughput_scaling.png", dpi=FIG_DPI)
    plt.close()


def privacy_utility_spider(all_agg: pd.DataFrame, fig_dir: Path):
    # radar chart per anonymization method (mean across pipelines & sizes)
    from math import pi
    metrics = ["information_loss_score_mean", "utility_preservation_score_mean", "privacy_level_score_mean"]
    labels_map = {
        "information_loss_score_mean":"InfoLoss",
        "utility_preservation_score_mean":"Utility",
        "privacy_level_score_mean":"Privacy",
    }
    methods = all_agg["anonymization_method"].unique()
    N = len(metrics)
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1]

    plt.figure(figsize=(7,7))
    ax = plt.subplot(111, polar=True)
    for m in methods:
        tmp = all_agg[all_agg["anonymization_method"]==m]
        vals = [tmp[k].mean() for k in metrics]
        vals += vals[:1]
        ax.plot(angles, vals, label=m)
        ax.fill(angles, vals, alpha=0.1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([labels_map[k] for k in metrics])
    ax.set_yticklabels([])
    plt.title("Privacy–Utility radar per method")
    plt.legend(loc="upper right", bbox_to_anchor=(1.3,1.1))
    plt.tight_layout()
    plt.savefig(fig_dir/"privacy_utility_radar.png", dpi=FIG_DPI, bbox_inches='tight')
    plt.close()

# --------------- MAIN -------------------

def main():
    parser = argparse.ArgumentParser(description="Clean analysis pipeline")
    parser.add_argument("--results-root", default="results-duplicate", help="Root dir with run folders")
    parser.add_argument("--out", default="clean_analysis", help="Output directory for analysis artefacts")
    args = parser.parse_args()

    results_root = Path(args.results_root)
    out_dir = Path(args.out)
    fig_dir = out_dir/"figures"; table_dir = out_dir/"tables"
    fig_dir.mkdir(parents=True, exist_ok=True); table_dir.mkdir(exist_ok=True)

    # Load
    batch = load_results(results_root, "batch_pipeline_results.csv")
    stream = load_results(results_root, "stream_pipeline_results.csv")
    hybrid = load_results(results_root, "hybrid_router_results.csv")
    for df, name in [(batch,"batch"),(stream,"stream"),(hybrid,"hybrid")]:
        if not df.empty:
            df["pipeline_type"] = name if name!="stream" else "stream_optimized" if name else name
    raw_all = pd.concat([batch, stream, hybrid], ignore_index=True)
    raw_all.to_csv(out_dir/"raw_combined.csv", index=False)

    # Aggregate across runs
    all_agg = aggregate(raw_all)
    all_agg.to_csv(out_dir/"aggregated_metrics.csv", index=False)

    # Simple plots
    throughput_vs_size(all_agg, fig_dir)
    privacy_utility_spider(all_agg, fig_dir)

    print(f"Clean analysis complete. Outputs in {out_dir}")

if __name__ == "__main__":
    main() 