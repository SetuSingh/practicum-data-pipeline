import os
import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from math import pi
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# --------------- CONFIG -----------------
FIG_DPI = 300
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("deep")
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 12
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['xtick.labelsize'] = 11
plt.rcParams['ytick.labelsize'] = 11
plt.rcParams['legend.fontsize'] = 11

# ---------- COLOR MAPS ----------
PIPELINE_COLORS = {
    "batch": "#1f77b4",  # blue
    "stream": "#ff7f0e",  # orange  
    "adaptive_hybrid": "#2ca02c",  # green
}

ANONYMIZATION_COLORS = {
    "k_anonymity": "#9467bd",  # purple
    "differential_privacy": "#8c564b",  # brown
    "tokenization": "#e377c2",  # pink
}

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


def rename_pipelines(df: pd.DataFrame) -> pd.DataFrame:
    """Rename pipeline types as requested"""
    df = df.copy()
    df["pipeline_type"] = df["pipeline_type"].replace({
        "stream_optimized": "stream",
        "hybrid_adaptive": "adaptive_hybrid"
    })
    return df


def safe_plot_save(fig_path: Path):
    """Safely save plot with error handling"""
    try:
        plt.tight_layout()
        plt.savefig(fig_path, dpi=FIG_DPI, bbox_inches='tight')
        plt.close()
    except Exception as e:
        print(f"Warning: Could not save plot {fig_path}: {e}")
        plt.close()


def format_dataset_size_axis(ax, sizes):
    """Format dataset size axis with actual numbers instead of scientific notation"""
    # Convert to integers for cleaner display
    size_labels = [f"{int(size):,}" for size in sorted(sizes)]
    ax.set_xticks(sorted(sizes))
    ax.set_xticklabels(size_labels)
    ax.set_xscale('linear')  # Use linear scale for cleaner labels


# =========================================================================
#                           RQ-1: ARCHITECTURE EFFECTIVENESS  
# =========================================================================

def rq1_dataset_size_vs_latency(all_agg: pd.DataFrame, fig_dir: Path):
    """RQ-1: Dataset Size vs Detection Latency"""
    plt.figure(figsize=(10, 6))
    
    # Average across anonymization methods for cleaner visualization
    agg_latency = all_agg.groupby(['pipeline_type', 'dataset_size'], as_index=False).agg({
        'avg_latency_ms_mean': 'mean',
        'avg_latency_ms_sem': 'mean'
    })
    agg_latency['dataset_size'] = pd.to_numeric(agg_latency['dataset_size'])
    
    for pipeline in ['batch', 'stream', 'adaptive_hybrid']:
        data = agg_latency[agg_latency['pipeline_type'] == pipeline]
        if not data.empty:
            plt.errorbar(data['dataset_size'], data['avg_latency_ms_mean'], 
                        yerr=data['avg_latency_ms_sem'], 
                        marker='o', linewidth=2, markersize=8,
                        label=pipeline.replace('_', ' ').title(),
                        color=PIPELINE_COLORS[pipeline])
    
    plt.xlabel('Dataset Size (records)')
    plt.ylabel('Average Latency (ms)')
    plt.title('Violation Detection Latency by Architecture\n(Lower is Better)')
    plt.legend()
    
    # Format x-axis with actual dataset sizes
    unique_sizes = agg_latency['dataset_size'].unique()
    format_dataset_size_axis(plt.gca(), unique_sizes)
    plt.yscale('log')
    plt.grid(True, alpha=0.3)
    safe_plot_save(fig_dir / "dataset_size_vs_latency.png")


def rq1_dataset_size_vs_throughput(all_agg: pd.DataFrame, fig_dir: Path):
    """RQ-1: Dataset Size vs Throughput"""
    plt.figure(figsize=(10, 6))
    
    # Average across anonymization methods
    agg_throughput = all_agg.groupby(['pipeline_type', 'dataset_size'], as_index=False).agg({
        'records_per_second_mean': 'mean',
        'records_per_second_sem': 'mean'
    })
    agg_throughput['dataset_size'] = pd.to_numeric(agg_throughput['dataset_size'])
    
    for pipeline in ['batch', 'stream', 'adaptive_hybrid']:
        data = agg_throughput[agg_throughput['pipeline_type'] == pipeline]
        if not data.empty:
            line = plt.errorbar(data['dataset_size'], data['records_per_second_mean'],
                        yerr=data['records_per_second_sem'],
                        marker='s', linewidth=2, markersize=8,
                        label=pipeline.replace('_', ' ').title(),
                        color=PIPELINE_COLORS[pipeline])
            
            # Add throughput values as annotations
            for x, y in zip(data['dataset_size'], data['records_per_second_mean']):
                plt.annotate(f'{y:.0f}', (x, y), textcoords="offset points", 
                           xytext=(0,10), ha='center', fontsize=9, 
                           color=PIPELINE_COLORS[pipeline], fontweight='bold')
    
    plt.xlabel('Dataset Size (records)')
    plt.ylabel('Throughput (records/second)')
    plt.title('Processing Throughput by Architecture\n(Higher is Better)')
    plt.legend()
    
    # Format x-axis with actual dataset sizes
    unique_sizes = agg_throughput['dataset_size'].unique()
    format_dataset_size_axis(plt.gca(), unique_sizes)
    plt.yscale('log') 
    plt.grid(True, alpha=0.3)
    safe_plot_save(fig_dir / "dataset_size_vs_throughput.png")


def rq1_dataset_size_vs_total_time(all_agg: pd.DataFrame, fig_dir: Path):
    """RQ-1: Dataset Size vs Total Processing Time"""
    plt.figure(figsize=(10, 6))
    
    agg_time = all_agg.groupby(['pipeline_type', 'dataset_size'], as_index=False).agg({
        'total_time_seconds_mean': 'mean',
        'total_time_seconds_sem': 'mean'
    })
    agg_time['dataset_size'] = pd.to_numeric(agg_time['dataset_size'])
    
    for pipeline in ['batch', 'stream', 'adaptive_hybrid']:
        data = agg_time[agg_time['pipeline_type'] == pipeline]
        if not data.empty:
            plt.errorbar(data['dataset_size'], data['total_time_seconds_mean'],
                        yerr=data['total_time_seconds_sem'],
                        marker='^', linewidth=2, markersize=8,
                        label=pipeline.replace('_', ' ').title(),
                        color=PIPELINE_COLORS[pipeline])
            
            # Add actual time values as annotations
            for x, y in zip(data['dataset_size'], data['total_time_seconds_mean']):
                plt.annotate(f'{y:.2f}s', (x, y), textcoords="offset points", 
                           xytext=(0,10), ha='center', fontsize=9,
                           color=PIPELINE_COLORS[pipeline], fontweight='bold')
    
    plt.xlabel('Dataset Size (records)')
    plt.ylabel('Total Processing Time (seconds)')
    plt.title('End-to-End Processing Time by Architecture\n(Lower is Better)')
    plt.legend()
    
    # Format x-axis with actual dataset sizes - NO LOG SCALE for Y
    unique_sizes = agg_time['dataset_size'].unique()
    format_dataset_size_axis(plt.gca(), unique_sizes)
    plt.grid(True, alpha=0.3)
    safe_plot_save(fig_dir / "dataset_size_vs_total_time.png")


def rq1_dataset_size_vs_violations_detected(all_agg: pd.DataFrame, fig_dir: Path):
    """RQ-1: Dataset Size vs Violations Detected"""
    plt.figure(figsize=(10, 6))
    
    agg_violations = all_agg.groupby(['pipeline_type', 'dataset_size'], as_index=False).agg({
        'violations_detected_mean': 'mean',
        'violations_detected_sem': 'mean'
    })
    agg_violations['dataset_size'] = pd.to_numeric(agg_violations['dataset_size'])
    
    for pipeline in ['batch', 'stream', 'adaptive_hybrid']:
        data = agg_violations[agg_violations['pipeline_type'] == pipeline]
        if not data.empty:
            plt.errorbar(data['dataset_size'], data['violations_detected_mean'],
                        yerr=data['violations_detected_sem'],
                        marker='D', linewidth=2, markersize=8,
                        label=pipeline.replace('_', ' ').title(),
                        color=PIPELINE_COLORS[pipeline])
    
    plt.xlabel('Dataset Size (records)')
    plt.ylabel('Violations Detected')
    plt.title('Compliance Violation Detection by Architecture\n(Higher Detection Rate is Better)')
    plt.legend()
    
    # Format x-axis with actual dataset sizes
    unique_sizes = agg_violations['dataset_size'].unique()
    format_dataset_size_axis(plt.gca(), unique_sizes)
    plt.grid(True, alpha=0.3)
    safe_plot_save(fig_dir / "dataset_size_vs_violations_detected.png")


def rq1_latency_boxplot(raw_df: pd.DataFrame, fig_dir: Path):
    """RQ-1: Latency Distribution Boxplot"""
    plt.figure(figsize=(8, 6))
    
    # Create proper mapping
    pipeline_order = ['batch', 'stream', 'adaptive_hybrid']
    available_pipelines = [p for p in pipeline_order if p in raw_df['pipeline_type'].unique()]
    
    sns.boxplot(data=raw_df, x="pipeline_type", y="avg_latency_ms", 
                order=available_pipelines, palette=[PIPELINE_COLORS[p] for p in available_pipelines])
    plt.xlabel('Pipeline Architecture')
    plt.ylabel('Average Latency (ms)')
    plt.title('Latency Distribution by Architecture\n(Lower is Better, Dots = Outliers)')
    plt.yscale('log')
    
    # Set proper tick labels
    plt.xticks(range(len(available_pipelines)), 
               [p.replace('_', ' ').title() for p in available_pipelines])
    
    safe_plot_save(fig_dir / "latency_boxplot.png")


def rq1_resource_utilization(all_agg: pd.DataFrame, fig_dir: Path):
    """RQ-1: Resource Utilization Comparison"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Average resource usage across all experiments
    resource_data = all_agg.groupby('pipeline_type', as_index=False).agg({
        'memory_usage_mb_mean': 'mean',
        'cpu_usage_percent_mean': 'mean'
    })
    
    pipeline_order = ['batch', 'stream', 'adaptive_hybrid']
    available_pipelines = [p for p in pipeline_order if p in resource_data['pipeline_type'].unique()]
    
    # Memory usage
    memory_values = [resource_data[resource_data['pipeline_type'] == p]['memory_usage_mb_mean'].iloc[0] for p in available_pipelines]
    bars1 = ax1.bar(range(len(available_pipelines)), memory_values,
                    color=[PIPELINE_COLORS[p] for p in available_pipelines])
    ax1.set_xlabel('Pipeline Architecture')
    ax1.set_ylabel('Memory Usage (MB)')
    ax1.set_title('Memory Utilization\n(Lower is Better)')
    ax1.set_xticks(range(len(available_pipelines)))
    ax1.set_xticklabels([p.replace('_', ' ').title() for p in available_pipelines])
    
    # Add value labels on top of bars
    for i, (bar, val) in enumerate(zip(bars1, memory_values)):
        ax1.text(i, val + val*0.01, f'{val:.0f}', ha='center', va='bottom', fontweight='bold')
    
    # CPU usage
    cpu_values = [resource_data[resource_data['pipeline_type'] == p]['cpu_usage_percent_mean'].iloc[0] for p in available_pipelines]
    bars2 = ax2.bar(range(len(available_pipelines)), cpu_values,
                    color=[PIPELINE_COLORS[p] for p in available_pipelines])
    ax2.set_xlabel('Pipeline Architecture')
    ax2.set_ylabel('CPU Usage (%)')
    ax2.set_title('CPU Utilization\n(Lower is Better)')
    ax2.set_xticks(range(len(available_pipelines)))
    ax2.set_xticklabels([p.replace('_', ' ').title() for p in available_pipelines])
    
    # Add value labels on top of bars
    for i, (bar, val) in enumerate(zip(bars2, cpu_values)):
        ax2.text(i, val + val*0.01, f'{val:.0f}', ha='center', va='bottom', fontweight='bold')
    
    safe_plot_save(fig_dir / "resource_utilization.png")


# =========================================================================
#                      RQ-2: ANONYMIZATION TRADE-OFFS
# =========================================================================

def rq2_dataset_size_vs_information_loss(all_agg: pd.DataFrame, fig_dir: Path):
    """RQ-2: Dataset Size vs Information Loss"""
    plt.figure(figsize=(10, 6))
    
    for method in ['k_anonymity', 'differential_privacy', 'tokenization']:
        method_data = all_agg[all_agg['anonymization_method'] == method]
        if not method_data.empty:
            # Average across pipelines for cleaner plot
            agg_data = method_data.groupby('dataset_size', as_index=False).agg({
                'information_loss_score_mean': 'mean',
                'information_loss_score_sem': 'mean'
            })
            agg_data['dataset_size'] = pd.to_numeric(agg_data['dataset_size'])
            
            plt.errorbar(agg_data['dataset_size'], agg_data['information_loss_score_mean'],
                        yerr=agg_data['information_loss_score_sem'],
                        marker='o', linewidth=2, markersize=8,
                        label=method.replace('_', ' ').title(),
                        color=ANONYMIZATION_COLORS[method])
    
    plt.xlabel('Dataset Size (records)')
    plt.ylabel('Information Loss Score')
    plt.title('Information Loss by Anonymization Method\n(Lower is Better)')
    plt.legend()
    
    # Format x-axis with actual dataset sizes
    unique_sizes = all_agg['dataset_size'].unique()
    format_dataset_size_axis(plt.gca(), [pd.to_numeric(s) for s in unique_sizes])
    plt.grid(True, alpha=0.3)
    plt.ylim(0, 1)
    safe_plot_save(fig_dir / "dataset_size_vs_information_loss.png")


def rq2_dataset_size_vs_privacy_level(all_agg: pd.DataFrame, fig_dir: Path):
    """RQ-2: Dataset Size vs Privacy Level"""
    plt.figure(figsize=(10, 6))
    
    for method in ['k_anonymity', 'differential_privacy', 'tokenization']:
        method_data = all_agg[all_agg['anonymization_method'] == method]
        if not method_data.empty:
            agg_data = method_data.groupby('dataset_size', as_index=False).agg({
                'privacy_level_score_mean': 'mean',
                'privacy_level_score_sem': 'mean'
            })
            agg_data['dataset_size'] = pd.to_numeric(agg_data['dataset_size'])
            
            plt.errorbar(agg_data['dataset_size'], agg_data['privacy_level_score_mean'],
                        yerr=agg_data['privacy_level_score_sem'],
                        marker='s', linewidth=2, markersize=8,
                        label=method.replace('_', ' ').title(),
                        color=ANONYMIZATION_COLORS[method])
    
    plt.xlabel('Dataset Size (records)')
    plt.ylabel('Privacy Level Score')
    plt.title('Privacy Protection by Anonymization Method\n(Higher is More Secure)')
    plt.legend()
    
    # Format x-axis with actual dataset sizes
    unique_sizes = all_agg['dataset_size'].unique()
    format_dataset_size_axis(plt.gca(), [pd.to_numeric(s) for s in unique_sizes])
    plt.grid(True, alpha=0.3)
    plt.ylim(0, 1)
    safe_plot_save(fig_dir / "dataset_size_vs_privacy_level.png")


def rq2_dataset_size_vs_anonymization_overhead(all_agg: pd.DataFrame, fig_dir: Path):
    """RQ-2: Dataset Size vs Anonymization Overhead"""
    plt.figure(figsize=(10, 6))
    
    for method in ['k_anonymity', 'differential_privacy', 'tokenization']:
        method_data = all_agg[all_agg['anonymization_method'] == method]
        if not method_data.empty:
            agg_data = method_data.groupby('dataset_size', as_index=False).agg({
                'anonymization_overhead_seconds_mean': 'mean',
                'anonymization_overhead_seconds_sem': 'mean'
            })
            agg_data['dataset_size'] = pd.to_numeric(agg_data['dataset_size'])
            
            plt.errorbar(agg_data['dataset_size'], agg_data['anonymization_overhead_seconds_mean'],
                        yerr=agg_data['anonymization_overhead_seconds_sem'],
                        marker='^', linewidth=2, markersize=8,
                        label=method.replace('_', ' ').title(),
                        color=ANONYMIZATION_COLORS[method])
    
    plt.xlabel('Dataset Size (records)')
    plt.ylabel('Anonymization Overhead (seconds)')
    plt.title('Computational Overhead by Anonymization Method\n(Lower is Better)')
    plt.legend()
    
    # Format x-axis with actual dataset sizes - Clean Y-axis without annotations
    unique_sizes = all_agg['dataset_size'].unique()
    format_dataset_size_axis(plt.gca(), [pd.to_numeric(s) for s in unique_sizes])
    plt.grid(True, alpha=0.3)
    safe_plot_save(fig_dir / "dataset_size_vs_anonymization_overhead.png")


def rq2_dataset_size_vs_utility_score(all_agg: pd.DataFrame, fig_dir: Path):
    """RQ-2: Dataset Size vs Utility Preservation"""
    plt.figure(figsize=(10, 6))
    
    for method in ['k_anonymity', 'differential_privacy', 'tokenization']:
        method_data = all_agg[all_agg['anonymization_method'] == method]
        if not method_data.empty:
            agg_data = method_data.groupby('dataset_size', as_index=False).agg({
                'utility_preservation_score_mean': 'mean',
                'utility_preservation_score_sem': 'mean'
            })
            agg_data['dataset_size'] = pd.to_numeric(agg_data['dataset_size'])
            
            plt.errorbar(agg_data['dataset_size'], agg_data['utility_preservation_score_mean'],
                        yerr=agg_data['utility_preservation_score_sem'],
                        marker='D', linewidth=2, markersize=8,
                        label=method.replace('_', ' ').title(),
                        color=ANONYMIZATION_COLORS[method])
    
    plt.xlabel('Dataset Size (records)')
    plt.ylabel('Utility Preservation Score')
    plt.title('Data Utility by Anonymization Method\n(Higher is Better)')
    plt.legend()
    
    # Format x-axis with actual dataset sizes
    unique_sizes = all_agg['dataset_size'].unique()
    format_dataset_size_axis(plt.gca(), [pd.to_numeric(s) for s in unique_sizes])
    plt.grid(True, alpha=0.3)
    plt.ylim(0, 1)
    safe_plot_save(fig_dir / "dataset_size_vs_utility_score.png")


def rq2_privacy_utility_radar(all_agg: pd.DataFrame, fig_dir: Path):
    """RQ-2: Privacy-Utility Radar Charts with Better Colors"""
    metrics = ["information_loss_score_mean", "utility_preservation_score_mean", "privacy_level_score_mean"]
    methods = ["k_anonymity", "differential_privacy", "tokenization"]
    
    # Better color scheme
    RADAR_COLORS = {
        "k_anonymity": "#2E86AB",      # Blue  
        "differential_privacy": "#A23B72", # Magenta
        "tokenization": "#F18F01",     # Orange
    }
    
    N = len(metrics)
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1]

    # Combined radar
    plt.figure(figsize=(8, 8))
    ax = plt.subplot(111, polar=True)
    
    for method in methods:
        method_data = all_agg[all_agg["anonymization_method"] == method]
        if not method_data.empty:
            # Note: for information_loss, lower is better, so we invert it for visualization
            vals = []
            for metric in metrics:
                if metric == "information_loss_score_mean":
                    vals.append(1 - method_data[metric].mean())  # Invert information loss
                else:
                    vals.append(method_data[metric].mean())
            vals += vals[:1]
            
            ax.plot(angles, vals, label=method.replace('_', ' ').title(),
                   linewidth=3, color=RADAR_COLORS[method])
            ax.fill(angles, vals, alpha=0.15, color=RADAR_COLORS[method])
    
    ax.set_xticks(angles[:-1])
    # Adjust label for inverted information loss
    radar_labels = ["Low Information Loss", "Utility Preservation", "Privacy Level"]
    ax.set_xticklabels(radar_labels, fontsize=12)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'])
    ax.grid(True)
    
    plt.title("Privacy-Utility Trade-off Comparison\n(Larger Area = Better Overall Performance)", 
              y=1.08, fontsize=14, fontweight='bold')
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    safe_plot_save(fig_dir / "privacy_utility_radar_all.png")


def rq2_anonymization_overhead_heatmap(all_agg: pd.DataFrame, fig_dir: Path):
    """RQ-2: Anonymization Overhead Heatmap"""
    plt.figure(figsize=(10, 6))
    
    # Create pivot table
    pivot = all_agg.pivot_table(
        index="anonymization_method", 
        columns="pipeline_type",
        values="anonymization_overhead_seconds_mean", 
        aggfunc="mean"
    )
    
    # Rename columns and index for better display
    pivot.columns = [col.replace('_', ' ').title() for col in pivot.columns]
    pivot.index = [idx.replace('_', ' ').title() for idx in pivot.index]
    
    sns.heatmap(pivot, annot=True, fmt=".3f", cmap="YlOrRd", 
                cbar_kws={'label': 'Overhead (seconds)'})
    plt.title("Anonymization Overhead by Method and Architecture\n(Lower Values are Better)", y=1.08)
    plt.xlabel("Pipeline Architecture")
    plt.ylabel("Anonymization Method")
    safe_plot_save(fig_dir / "anonymization_overhead_heatmap.png")


def rq2_privacy_utility_scatter(all_agg: pd.DataFrame, fig_dir: Path):
    """RQ-2: Privacy-Utility Scatter with Throughput Bubbles"""
    plt.figure(figsize=(10, 8))
    
    # Create scatter plot with bubble size representing throughput
    for method in ['k_anonymity', 'differential_privacy', 'tokenization']:
        method_data = all_agg[all_agg['anonymization_method'] == method]
        if not method_data.empty:
            plt.scatter(method_data['utility_preservation_score_mean'],
                       method_data['privacy_level_score_mean'],
                       s=method_data['records_per_second_mean'] / 10,  # Scale bubble size
                       alpha=0.6,
                       label=method.replace('_', ' ').title(),
                       color=ANONYMIZATION_COLORS[method])
    
    plt.xlabel('Utility Preservation Score')
    plt.ylabel('Privacy Level Score')
    plt.title('Privacy-Utility Trade-off\n(Bubble size = Throughput, Upper Right = Ideal)', y=1.08)
    plt.xlim(0, 1)
    plt.ylim(0, 1)
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Add ideal region annotation
    plt.axvline(x=0.8, color='green', linestyle='--', alpha=0.5)
    plt.axhline(y=0.8, color='green', linestyle='--', alpha=0.5)
    plt.text(0.82, 0.82, 'Ideal\nRegion', fontsize=10, alpha=0.7, 
             bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.3))
    
    safe_plot_save(fig_dir / "privacy_utility_scatter.png")


def rq2_privacy_utility_effectiveness_matrix(all_agg: pd.DataFrame, fig_dir: Path):
    """RQ-2: Simplified Privacy-Utility Effectiveness Matrix"""
    plt.figure(figsize=(10, 6))
    
    # Aggregate by anonymization method
    effectiveness = all_agg.groupby('anonymization_method', as_index=False).agg({
        'utility_preservation_score_mean': 'mean',
        'privacy_level_score_mean': 'mean',
        'records_per_second_mean': 'mean'
    })
    
    methods = ['k_anonymity', 'differential_privacy', 'tokenization']
    method_labels = ['K-Anonymity', 'Differential Privacy', 'Tokenization']
    
    x_pos = np.arange(len(methods))
    
    # Create grouped bar chart
    width = 0.25
    
    utility_bars = plt.bar(x_pos - width, 
                          [effectiveness[effectiveness['anonymization_method'] == m]['utility_preservation_score_mean'].iloc[0] for m in methods],
                          width, label='Utility Preservation', color='#2E86AB', alpha=0.8)
    
    privacy_bars = plt.bar(x_pos, 
                          [effectiveness[effectiveness['anonymization_method'] == m]['privacy_level_score_mean'].iloc[0] for m in methods],
                          width, label='Privacy Level', color='#A23B72', alpha=0.8)
    
    # Normalize throughput to 0-1 scale for comparison
    throughput_vals = [effectiveness[effectiveness['anonymization_method'] == m]['records_per_second_mean'].iloc[0] for m in methods]
    max_throughput = max(throughput_vals)
    normalized_throughput = [t/max_throughput for t in throughput_vals]
    
    efficiency_bars = plt.bar(x_pos + width, normalized_throughput,
                             width, label='Processing Efficiency', color='#F18F01', alpha=0.8)
    
    # Add value labels on bars
    for bars in [utility_bars, privacy_bars, efficiency_bars]:
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                    f'{height:.2f}', ha='center', va='bottom', fontsize=9)
    
    plt.xlabel('Anonymization Method')
    plt.ylabel('Performance Score (0-1)')
    plt.title('Anonymization Method Effectiveness Comparison\n(Higher is Better for All Metrics)')
    plt.xticks(x_pos, method_labels)
    plt.legend()
    plt.ylim(0, 1.1)
    plt.grid(True, alpha=0.3)
    safe_plot_save(fig_dir / "privacy_utility_effectiveness_matrix.png")


# =========================================================================
#                        RQ-3: HYBRID ROUTER EFFECTIVENESS
# =========================================================================

def rq3_performance_scalability_analysis(all_agg: pd.DataFrame, fig_dir: Path):
    """RQ-3: Performance Scalability Analysis"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Scalability metric: throughput per dataset size
    scalability_data = all_agg.groupby(['pipeline_type', 'dataset_size'], as_index=False).agg({
        'records_per_second_mean': 'mean',
        'total_time_seconds_mean': 'mean'
    })
    scalability_data['dataset_size'] = pd.to_numeric(scalability_data['dataset_size'])
    scalability_data['efficiency_ratio'] = scalability_data['records_per_second_mean'] / scalability_data['dataset_size'] * 1000
    
    # Plot 1: Efficiency Ratio (Throughput per 1K records)
    for pipeline in ['batch', 'stream', 'adaptive_hybrid']:
        data = scalability_data[scalability_data['pipeline_type'] == pipeline]
        if not data.empty:
            ax1.plot(data['dataset_size'], data['efficiency_ratio'],
                    marker='o', linewidth=2, markersize=8,
                    label=pipeline.replace('_', ' ').title(),
                    color=PIPELINE_COLORS[pipeline])
    
    ax1.set_xlabel('Dataset Size (records)')
    ax1.set_ylabel('Efficiency Ratio (records/second per 1K)')
    ax1.set_title('Processing Efficiency Scalability\n(Higher = Better Scalability)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Format x-axis
    unique_sizes = scalability_data['dataset_size'].unique()
    ax1.set_xticks(sorted(unique_sizes))
    ax1.set_xticklabels([f"{int(size):,}" for size in sorted(unique_sizes)])
    
    # Plot 2: Processing Time Growth Rate
    for pipeline in ['batch', 'stream', 'adaptive_hybrid']:
        data = scalability_data[scalability_data['pipeline_type'] == pipeline]
        if not data.empty:
            ax2.plot(data['dataset_size'], data['total_time_seconds_mean'],
                    marker='s', linewidth=2, markersize=8,
                    label=pipeline.replace('_', ' ').title(),
                    color=PIPELINE_COLORS[pipeline])
    
    ax2.set_xlabel('Dataset Size (records)')
    ax2.set_ylabel('Total Processing Time (seconds)')
    ax2.set_title('Processing Time Growth\n(Lower Growth = Better)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Format x-axis
    ax2.set_xticks(sorted(unique_sizes))
    ax2.set_xticklabels([f"{int(size):,}" for size in sorted(unique_sizes)])
    
    safe_plot_save(fig_dir / "performance_scalability_analysis.png")


def rq3_hybrid_effectiveness_summary(all_agg: pd.DataFrame, fig_dir: Path):
    """RQ-3: Hybrid Router Effectiveness Summary"""
    plt.figure(figsize=(12, 8))
    
    # Create comprehensive comparison metrics
    comparison_data = all_agg.groupby('pipeline_type', as_index=False).agg({
        'avg_latency_ms_mean': 'mean',
        'records_per_second_mean': 'mean', 
        'total_time_seconds_mean': 'mean',
        'memory_usage_mb_mean': 'mean',
        'cpu_usage_percent_mean': 'mean'
    })
    
    pipelines = ['batch', 'stream', 'adaptive_hybrid']
    metrics = ['Latency (ms)', 'Throughput (rps)', 'Processing Time (s)', 'Memory (MB)', 'CPU (%)']
    
    # Normalize all metrics to 0-1 scale (with appropriate direction)
    normalized_data = []
    for pipeline in pipelines:
        if pipeline in comparison_data['pipeline_type'].values:
            row_data = comparison_data[comparison_data['pipeline_type'] == pipeline].iloc[0]
            normalized_row = []
            
            # Latency (lower is better)
            latency_vals = comparison_data['avg_latency_ms_mean'].values
            normalized_row.append(1 - (row_data['avg_latency_ms_mean'] - min(latency_vals)) / 
                                (max(latency_vals) - min(latency_vals)))
            
            # Throughput (higher is better)  
            throughput_vals = comparison_data['records_per_second_mean'].values
            normalized_row.append((row_data['records_per_second_mean'] - min(throughput_vals)) / 
                                (max(throughput_vals) - min(throughput_vals)))
            
            # Processing time (lower is better)
            time_vals = comparison_data['total_time_seconds_mean'].values
            normalized_row.append(1 - (row_data['total_time_seconds_mean'] - min(time_vals)) / 
                                (max(time_vals) - min(time_vals)))
            
            # Memory (lower is better)
            memory_vals = comparison_data['memory_usage_mb_mean'].values
            normalized_row.append(1 - (row_data['memory_usage_mb_mean'] - min(memory_vals)) / 
                                (max(memory_vals) - min(memory_vals)))
            
            # CPU (lower is better)
            cpu_vals = comparison_data['cpu_usage_percent_mean'].values
            normalized_row.append(1 - (row_data['cpu_usage_percent_mean'] - min(cpu_vals)) / 
                                (max(cpu_vals) - min(cpu_vals)))
            
            normalized_data.append(normalized_row)
    
    # Create heatmap
    normalized_data = np.array(normalized_data)
    
    im = plt.imshow(normalized_data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
    
    # Set ticks and labels
    plt.xticks(range(len(metrics)), metrics, rotation=45)
    plt.yticks(range(len(pipelines)), [p.replace('_', ' ').title() for p in pipelines])
    
    # Add text annotations
    for i in range(len(pipelines)):
        for j in range(len(metrics)):
            text = plt.text(j, i, f'{normalized_data[i, j]:.2f}',
                           ha="center", va="center", color="black", fontweight='bold')
    
    plt.title('Architecture Performance Comparison Matrix\n(Green = Better, Red = Worse)')
    plt.colorbar(im, label='Normalized Performance Score')
    safe_plot_save(fig_dir / "hybrid_effectiveness_summary.png")


def rq3_decision_distribution_analysis(all_agg: pd.DataFrame, fig_dir: Path):
    """RQ-3: Router Decision Distribution by Dataset Characteristics"""
    hybrid_data = all_agg[all_agg['pipeline_type'] == 'adaptive_hybrid']
    if hybrid_data.empty:
        print("No hybrid data found for decision distribution analysis")
        return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Plot 1: Decision distribution by dataset size
    decision_by_size = hybrid_data.groupby('dataset_size', as_index=False).agg({
        'stream_percentage_mean': 'mean',
        'batch_percentage_mean': 'mean'
    })
    decision_by_size['dataset_size'] = pd.to_numeric(decision_by_size['dataset_size'])
    
    width = 0.35
    sizes = sorted(decision_by_size['dataset_size'].unique())
    x_pos = np.arange(len(sizes))
    
    stream_pcts = [decision_by_size[decision_by_size['dataset_size'] == s]['stream_percentage_mean'].iloc[0] for s in sizes]
    batch_pcts = [decision_by_size[decision_by_size['dataset_size'] == s]['batch_percentage_mean'].iloc[0] for s in sizes]
    
    bars1 = ax1.bar(x_pos, stream_pcts, width, label='Stream Processing', 
                    color=PIPELINE_COLORS['stream'], alpha=0.8)
    bars2 = ax1.bar(x_pos, batch_pcts, width, bottom=stream_pcts, 
                    label='Batch Processing', color=PIPELINE_COLORS['batch'], alpha=0.8)
    
    ax1.set_xlabel('Dataset Size (records)')
    ax1.set_ylabel('Routing Percentage (%)')
    ax1.set_title('Router Decision Distribution by Dataset Size')
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels([f"{int(s):,}" for s in sizes])
    ax1.legend()
    ax1.set_ylim(0, 100)
    
    # Add percentage labels
    for i, (s_pct, b_pct) in enumerate(zip(stream_pcts, batch_pcts)):
        ax1.text(i, s_pct/2, f'{s_pct:.1f}%', ha='center', va='center', fontweight='bold')
        ax1.text(i, s_pct + b_pct/2, f'{b_pct:.1f}%', ha='center', va='center', fontweight='bold')
    
    # Plot 2: Decision effectiveness (latency achieved vs pure approaches)
    effectiveness_data = []
    
    batch_latencies = all_agg[all_agg['pipeline_type'] == 'batch'].groupby('dataset_size')['avg_latency_ms_mean'].mean()
    stream_latencies = all_agg[all_agg['pipeline_type'] == 'stream'].groupby('dataset_size')['avg_latency_ms_mean'].mean()  
    hybrid_latencies = all_agg[all_agg['pipeline_type'] == 'adaptive_hybrid'].groupby('dataset_size')['avg_latency_ms_mean'].mean()
    
    for size in sizes:
        size_str = str(int(size))
        if size_str in batch_latencies.index and size_str in stream_latencies.index and size_str in hybrid_latencies.index:
            batch_lat = batch_latencies[size_str]
            stream_lat = stream_latencies[size_str] 
            hybrid_lat = hybrid_latencies[size_str]
            
            # Calculate how much better hybrid is vs the best pure approach
            best_pure = min(batch_lat, stream_lat)
            improvement = (best_pure - hybrid_lat) / best_pure * 100
            effectiveness_data.append(improvement)
        else:
            effectiveness_data.append(0)
    
    bars3 = ax2.bar(x_pos, effectiveness_data, color=PIPELINE_COLORS['adaptive_hybrid'], alpha=0.8)
    ax2.set_xlabel('Dataset Size (records)')
    ax2.set_ylabel('Latency Improvement (%)')
    ax2.set_title('Hybrid Router Latency Improvement\nvs Best Pure Architecture')
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels([f"{int(s):,}" for s in sizes])
    ax2.axhline(y=0, color='black', linestyle='--', alpha=0.5)
    ax2.grid(True, alpha=0.3)
    
    # Add improvement labels
    for i, improvement in enumerate(effectiveness_data):
        ax2.text(i, improvement + (max(effectiveness_data) * 0.05), 
                f'{improvement:.1f}%', ha='center', va='bottom', fontweight='bold')
    
    safe_plot_save(fig_dir / "decision_distribution_analysis.png")


def rq3_workload_adaptation_analysis(all_agg: pd.DataFrame, fig_dir: Path):
    """RQ-3: Workload Adaptation Analysis"""
    plt.figure(figsize=(12, 8))
    
    # Analyze how hybrid adapts across different conditions
    hybrid_data = all_agg[all_agg['pipeline_type'] == 'adaptive_hybrid']
    if hybrid_data.empty:
        print("No hybrid data found for workload adaptation analysis")
        return
    
    # Group by dataset type and anonymization method
    adaptation_analysis = hybrid_data.groupby(['dataset_type', 'anonymization_method'], as_index=False).agg({
        'stream_percentage_mean': 'mean',
        'avg_latency_ms_mean': 'mean',
        'records_per_second_mean': 'mean'
    })
    
    # Create subplot for each dataset type
    dataset_types = adaptation_analysis['dataset_type'].unique()
    fig, axes = plt.subplots(1, len(dataset_types), figsize=(5*len(dataset_types), 6))
    if len(dataset_types) == 1:
        axes = [axes]
    
    for i, dataset_type in enumerate(dataset_types):
        data = adaptation_analysis[adaptation_analysis['dataset_type'] == dataset_type]
        
        methods = data['anonymization_method'].unique()
        stream_pcts = data['stream_percentage_mean'].values
        
        bars = axes[i].bar(range(len(methods)), stream_pcts,
                          color=[ANONYMIZATION_COLORS.get(m, '#666666') for m in methods],
                          alpha=0.8)
        
        axes[i].set_xlabel('Anonymization Method')
        axes[i].set_ylabel('Stream Processing Percentage (%)')
        axes[i].set_title(f'Routing Adaptation\n{dataset_type.title()} Dataset')
        axes[i].set_xticks(range(len(methods)))
        axes[i].set_xticklabels([m.replace('_', ' ').title() for m in methods], rotation=45)
        axes[i].set_ylim(0, 100)
        
        # Add percentage labels
        for j, (bar, pct) in enumerate(zip(bars, stream_pcts)):
            axes[i].text(j, pct + 2, f'{pct:.1f}%', ha='center', va='bottom', fontweight='bold')
    
    plt.suptitle('Adaptive Router Workload-Specific Decision Patterns', fontsize=16, fontweight='bold')
    safe_plot_save(fig_dir / "workload_adaptation_analysis.png")


def rq3_hybrid_vs_pure_performance(all_agg: pd.DataFrame, fig_dir: Path):
    """RQ-3: Hybrid vs Pure Architecture Performance"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Performance metrics by pipeline
    perf_data = all_agg.groupby('pipeline_type', as_index=False).agg({
        'records_per_second_mean': 'mean',
        'avg_latency_ms_mean': 'mean'
    })
    
    pipeline_order = ['batch', 'stream', 'adaptive_hybrid']
    available_pipelines = [p for p in pipeline_order if p in perf_data['pipeline_type'].unique()]
    
    # Throughput comparison
    throughput_values = [perf_data[perf_data['pipeline_type'] == p]['records_per_second_mean'].iloc[0] 
                        for p in available_pipelines]
    bars1 = ax1.bar(range(len(available_pipelines)), throughput_values,
                    color=[PIPELINE_COLORS[p] for p in available_pipelines])
    ax1.set_xlabel('Pipeline Architecture')
    ax1.set_ylabel('Throughput (records/second)')
    ax1.set_title('Throughput Comparison\n(Higher is Better)')
    ax1.set_xticks(range(len(available_pipelines)))
    ax1.set_xticklabels([p.replace('_', ' ').title() for p in available_pipelines])
    
    # Add value labels on bars with better precision
    for i, (bar, val) in enumerate(zip(bars1, throughput_values)):
        ax1.text(i, val, f'{val:.1f}', ha='center', va='bottom', fontweight='bold')
    
    # Latency comparison
    latency_values = [perf_data[perf_data['pipeline_type'] == p]['avg_latency_ms_mean'].iloc[0] 
                     for p in available_pipelines]
    bars2 = ax2.bar(range(len(available_pipelines)), latency_values,
                    color=[PIPELINE_COLORS[p] for p in available_pipelines])
    ax2.set_xlabel('Pipeline Architecture')
    ax2.set_ylabel('Average Latency (ms)')
    ax2.set_title('Latency Comparison\n(Lower is Better)')
    ax2.set_xticks(range(len(available_pipelines)))
    ax2.set_xticklabels([p.replace('_', ' ').title() for p in available_pipelines])
    
    # Add value labels on bars with better precision
    for i, (bar, val) in enumerate(zip(bars2, latency_values)):
        ax2.text(i, val, f'{val:.3f}', ha='center', va='bottom', fontweight='bold')
    
    safe_plot_save(fig_dir / "hybrid_vs_pure_performance.png")


def rq3_routing_split_pie(all_agg: pd.DataFrame, fig_dir: Path):
    """RQ-3: Routing Decision Split"""
    hybrid_data = all_agg[all_agg['pipeline_type'] == 'adaptive_hybrid']
    if hybrid_data.empty:
        print("No hybrid data found for routing pie chart")
        return
    
    # Average routing percentages
    stream_pct = hybrid_data['stream_percentage_mean'].mean()
    batch_pct = hybrid_data['batch_percentage_mean'].mean()
    
    # Handle case where percentages might not sum to 100
    total = stream_pct + batch_pct
    if total > 0:
        stream_pct = stream_pct / total * 100
        batch_pct = batch_pct / total * 100
    
    plt.figure(figsize=(8, 6))
    sizes = [stream_pct, batch_pct]
    labels = ['Stream Processing', 'Batch Processing']
    colors = [PIPELINE_COLORS['stream'], PIPELINE_COLORS['batch']]
    
    wedges, texts, autotexts = plt.pie(sizes, labels=labels, autopct='%1.1f%%', 
                                      colors=colors, startangle=90,
                                      textprops={'fontsize': 12})
    
    plt.title('Adaptive Hybrid Router Decision Distribution', fontsize=14)
    plt.axis('equal')
    safe_plot_save(fig_dir / "routing_split_pie.png")


def rq3_latency_reduction_scatter(all_agg: pd.DataFrame, fig_dir: Path):
    """RQ-3: Latency Reduction Analysis - Simplified"""
    try:
        plt.figure(figsize=(8, 8))
        
        # Get data for each pipeline type by dataset size
        batch_data = all_agg[all_agg['pipeline_type'] == 'batch'][['dataset_size', 'avg_latency_ms_mean']]
        stream_data = all_agg[all_agg['pipeline_type'] == 'stream'][['dataset_size', 'avg_latency_ms_mean']]
        hybrid_data = all_agg[all_agg['pipeline_type'] == 'adaptive_hybrid'][['dataset_size', 'avg_latency_ms_mean']]
        
        if any(df.empty for df in [batch_data, stream_data, hybrid_data]):
            print("Insufficient data for latency reduction analysis")
            return
        
        # Merge data for comparison
        merged = batch_data.merge(stream_data, on='dataset_size', suffixes=('_batch', '_stream'))
        merged = merged.merge(hybrid_data, on='dataset_size')
        merged.rename(columns={'avg_latency_ms_mean': 'avg_latency_ms_mean_hybrid'}, inplace=True)
        
        if merged.empty:
            print("No matching data found for latency reduction analysis")
            return
        
        # Calculate latency reductions
        merged['batch_reduction'] = merged['avg_latency_ms_mean_batch'] - merged['avg_latency_ms_mean_hybrid']
        merged['stream_reduction'] = merged['avg_latency_ms_mean_stream'] - merged['avg_latency_ms_mean_hybrid']
        
        # Create scatter plot
        plt.scatter(merged['batch_reduction'], merged['stream_reduction'], 
                   s=100, alpha=0.7, color=PIPELINE_COLORS['adaptive_hybrid'])
        
        # Simple annotations without complex text positioning
        for _, row in merged.iterrows():
            size_k = int(row['dataset_size']) // 1000
            plt.annotate(f"{size_k}K", 
                        (row['batch_reduction'], row['stream_reduction']),
                        xytext=(5, 5), textcoords='offset points', fontsize=9)
        
        # Add reference lines
        plt.axhline(0, color='grey', linestyle='--', alpha=0.5)
        plt.axvline(0, color='grey', linestyle='--', alpha=0.5)
        
        plt.xlabel('Batch Latency - Hybrid Latency (ms)')
        plt.ylabel('Stream Latency - Hybrid Latency (ms)')
        plt.title('Latency Reduction: Hybrid vs Pure Architectures\n(Upper Right Quadrant = Hybrid Beats Both)')
        plt.grid(True, alpha=0.3)
        safe_plot_save(fig_dir / "latency_reduction_scatter.png")
        
    except Exception as e:
        print(f"Error in latency reduction scatter: {e}")
        plt.close()


def rq3_router_overhead_analysis(all_agg: pd.DataFrame, fig_dir: Path):
    """RQ-3: Router Overhead Analysis"""
    hybrid_data = all_agg[all_agg['pipeline_type'] == 'adaptive_hybrid']
    if hybrid_data.empty or 'router_time_ms_mean' not in hybrid_data.columns:
        print("No router overhead data found")
        return
    
    plt.figure(figsize=(10, 6))
    
    # Convert dataset_size to numeric
    hybrid_data_plot = hybrid_data.copy()
    hybrid_data_plot['dataset_size'] = pd.to_numeric(hybrid_data_plot['dataset_size'])
    
    # Plot router overhead vs dataset size
    plt.errorbar(hybrid_data_plot['dataset_size'], 
                hybrid_data_plot['router_time_ms_mean'],
                yerr=hybrid_data_plot.get('router_time_ms_sem', 0),
                marker='o', linewidth=2, markersize=8,
                color=PIPELINE_COLORS['adaptive_hybrid'])
    
    plt.xlabel('Dataset Size (records)')
    plt.ylabel('Router Decision Time (ms)')
    plt.title('Adaptive Router Overhead Analysis\n(Lower is Better)', y=1.08)
    
    # Format x-axis with actual dataset sizes
    unique_sizes = hybrid_data_plot['dataset_size'].unique()
    format_dataset_size_axis(plt.gca(), unique_sizes)
    plt.yscale('log')
    plt.grid(True, alpha=0.3)
    safe_plot_save(fig_dir / "router_overhead_analysis.png")


# =========================================================================
#                            ADDITIONAL ANALYSES
# =========================================================================

def additional_time_breakdown_stacked(all_agg: pd.DataFrame, fig_dir: Path):
    """Additional: Time Breakdown by Anonymization Method"""
    plt.figure(figsize=(10, 6))
    
    # Aggregate time components by anonymization method
    time_data = all_agg.groupby('anonymization_method', as_index=False).agg({
        'compliance_check_time_seconds_mean': 'mean',
        'anonymization_overhead_seconds_mean': 'mean', 
        'pure_processing_time_seconds_mean': 'mean'
    })
    
    # Rename for better labels
    time_data.rename(columns={
        'compliance_check_time_seconds_mean': 'Compliance Check',
        'anonymization_overhead_seconds_mean': 'Anonymization',
        'pure_processing_time_seconds_mean': 'Core Processing'
    }, inplace=True)
    
    # Create percentage breakdown
    time_cols = ['Compliance Check', 'Anonymization', 'Core Processing']
    time_data[time_cols] = time_data[time_cols].div(time_data[time_cols].sum(axis=1), axis=0)
    
    # Plot stacked bar
    ax = time_data.set_index('anonymization_method')[time_cols].plot(
        kind='bar', stacked=True, figsize=(10, 6), 
        color=['#ff9999', '#66b3ff', '#99ff99'])
    
    plt.title('Processing Time Breakdown by Anonymization Method\n(Shows Relative Time Distribution)', y=1.08)
    plt.xlabel('Anonymization Method')
    plt.ylabel('Fraction of Total Time')
    plt.legend(title='Processing Component', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.xticks(rotation=45)
    safe_plot_save(fig_dir / "time_breakdown_stacked.png")


# --------------- MAIN -------------------

def main():
    parser = argparse.ArgumentParser(description="Enhanced clean analysis pipeline")
    parser.add_argument("--results-root", default="results-duplicate", help="Root dir with run folders")
    parser.add_argument("--out", default="clean_analysis", help="Output directory for analysis artefacts")
    args = parser.parse_args()

    results_root = Path(args.results_root)
    out_dir = Path(args.out)
    
    # Create organized directory structure
    rq1_dir = out_dir / "figures" / "rq-1"
    rq2_dir = out_dir / "figures" / "rq-2" 
    rq3_dir = out_dir / "figures" / "rq-3"
    tables_dir = out_dir / "tables"
    
    for dir_path in [rq1_dir, rq2_dir, rq3_dir, tables_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)

    print("Loading experimental results...")
    # Load data
    batch = load_results(results_root, "batch_pipeline_results.csv")
    stream = load_results(results_root, "stream_pipeline_results.csv")
    hybrid = load_results(results_root, "hybrid_router_results.csv")
    
    # Set pipeline types and rename
    for df, name in [(batch, "batch"), (stream, "stream_optimized"), (hybrid, "hybrid_adaptive")]:
        if not df.empty:
            df["pipeline_type"] = name
    
    raw_all = pd.concat([batch, stream, hybrid], ignore_index=True)
    raw_all = rename_pipelines(raw_all)
    raw_all.to_csv(out_dir / "raw_combined.csv", index=False)

    # Aggregate across runs
    all_agg = aggregate(raw_all)
    all_agg = rename_pipelines(all_agg)
    all_agg.to_csv(out_dir / "aggregated_metrics.csv", index=False)

    print("Generating RQ-1 plots (Architecture Effectiveness)...")
    # RQ-1: Architecture Effectiveness
    rq1_dataset_size_vs_latency(all_agg, rq1_dir)
    rq1_dataset_size_vs_throughput(all_agg, rq1_dir)
    rq1_dataset_size_vs_total_time(all_agg, rq1_dir)
    rq1_dataset_size_vs_violations_detected(all_agg, rq1_dir)
    rq1_latency_boxplot(raw_all, rq1_dir)
    rq1_resource_utilization(all_agg, rq1_dir)

    print("Generating RQ-2 plots (Anonymization Trade-offs)...")
    # RQ-2: Anonymization Trade-offs
    rq2_dataset_size_vs_information_loss(all_agg, rq2_dir)
    rq2_dataset_size_vs_privacy_level(all_agg, rq2_dir)
    rq2_dataset_size_vs_anonymization_overhead(all_agg, rq2_dir)
    rq2_dataset_size_vs_utility_score(all_agg, rq2_dir)
    rq2_privacy_utility_radar(all_agg, rq2_dir)
    rq2_anonymization_overhead_heatmap(all_agg, rq2_dir)
    rq2_privacy_utility_effectiveness_matrix(all_agg, rq2_dir)  # NEW: Simplified effectiveness matrix

    print("Generating RQ-3 plots (Hybrid Router Effectiveness)...")
    # RQ-3: Hybrid Router Effectiveness - EXPANDED SET
    rq3_performance_scalability_analysis(all_agg, rq3_dir)        # NEW: Scalability analysis
    rq3_hybrid_effectiveness_summary(all_agg, rq3_dir)           # NEW: Effectiveness summary matrix
    rq3_decision_distribution_analysis(all_agg, rq3_dir)         # NEW: Decision patterns analysis  
    rq3_workload_adaptation_analysis(all_agg, rq3_dir)           # NEW: Workload adaptation
    rq3_hybrid_vs_pure_performance(all_agg, rq3_dir)             # IMPROVED: Performance comparison
    rq3_routing_split_pie(all_agg, rq3_dir)                      # Original pie chart
    rq3_latency_reduction_scatter(all_agg, rq3_dir)              # Original scatter plot

    print("Generating additional analyses...")
    # Additional Analysis
    additional_time_breakdown_stacked(all_agg, out_dir / "figures")

    print(f"\n✅ Enhanced analysis complete with improved visualizations!")
    print(f"  📊 RQ-1 plots: {rq1_dir} (6 plots)")
    print(f"  📊 RQ-2 plots: {rq2_dir} (8 plots)")  
    print(f"  📊 RQ-3 plots: {rq3_dir} (7 plots)")
    print(f"  📋 Data tables: {tables_dir}")
    print(f"\n🔍 Key improvements:")
    print(f"  • Fixed axis formatting (actual values, no scientific notation)")
    print(f"  • Added value annotations on plots")
    print(f"  • Improved color schemes")
    print(f"  • Added 4 new comprehensive RQ-3 analysis plots")
    print(f"  • Replaced confusing scatter plot with effectiveness matrix")


if __name__ == "__main__":
    main() 