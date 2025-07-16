# 🔬 Research Analysis Scripts

> **Comprehensive Pipeline Performance Analysis for Research Publication**

This directory contains research analysis scripts that provide **clean, research-grade metrics** for comparing batch, stream, and hybrid data processing pipelines with different anonymization configurations.

## 📋 **Overview**

The research analysis framework tests **3 pipeline types** × **11 anonymization configurations** × **5 dataset sizes** × **2 data types** = **330 total experiments** to generate comprehensive performance metrics for research publication.

### **🔧 What Gets Tested**

| Component         | Options                                                                                                   | Description                        |
| ----------------- | --------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| **Pipelines**     | Batch, Stream, Hybrid                                                                                     | All three processing architectures |
| **Anonymization** | K-anonymity (k=3,5,10,15)<br/>Differential Privacy (ε=0.1,0.5,1.0,2.0)<br/>Tokenization (128,256,512-bit) | All 11 configurations              |
| **Dataset Sizes** | 500, 1000, 2500, 5000, 10000                                                                              | Incremental scaling tests          |
| **Data Types**    | Healthcare (HIPAA), Financial (GDPR)                                                                      | Compliance-specific testing        |

### **⏱️ Clean Timing Architecture**

Each experiment measures **pure processing time** with clean separation:

```
PRE-PROCESSING (not timed)     PURE PROCESSING (timed)        POST-PROCESSING (not timed)
├─ Data loading               ├─ Compliance checking         ├─ CSV file creation
├─ Processor initialization   ├─ Anonymization              ├─ Database operations
├─ Connection setup           ├─ Core processing logic       ├─ Progress updates
└─ Memory measurement         └─ Violation detection         └─ Resource cleanup
```

## 🚀 **Quick Start**

### **Prerequisites**

```bash
# Required for all scripts
pip install pandas numpy faker psutil

# Required for stream/hybrid (if using Kafka)
pip install kafka-python

# Required for visualizations
pip install matplotlib seaborn

# Optional: Start Kafka for stream/hybrid testing
docker-compose up -d kafka
```

### **Run All Experiments**

```bash
# Run comprehensive analysis (all pipelines)
python run_all_research_analysis.py

# Run only batch analysis (no Kafka required)
python run_all_research_analysis.py --batch-only

# Run only stream analysis (requires Kafka)
python run_all_research_analysis.py --stream-only

# Run only hybrid analysis (requires Kafka)
python run_all_research_analysis.py --hybrid-only

# Skip Kafka connectivity check (fallback mode)
python run_all_research_analysis.py --skip-kafka-check
```

### **Run Individual Analyses**

```bash
# Individual pipeline analysis
python batch_pipeline_analysis.py    # Batch processing only
python stream_pipeline_analysis.py   # Stream processing only (requires Kafka)
python hybrid_pipeline_analysis.py   # Hybrid processing only (requires Kafka)

# Test utilities
python research_utils.py            # Test data generation and utilities
```

## 📊 **Generated Outputs**

### **File Structure**

```
research-analysis-scripts/
├── results/                           # All analysis results
│   ├── consolidated_research_results.csv     # All experiments consolidated
│   ├── batch_pipeline_results.csv           # Batch-specific results
│   ├── stream_pipeline_results.csv          # Stream-specific results
│   ├── hybrid_pipeline_results.csv          # Hybrid-specific results
│   ├── pipeline_comparison_report.json      # Comparative analysis
│   ├── research_summary.md                  # Research findings summary
│   └── performance_comparison.png           # Performance visualizations
├── test_data/                        # Generated test datasets
│   ├── healthcare_500_records.csv
│   ├── healthcare_1000_records.csv
│   ├── financial_500_records.csv
│   └── ...
├── logs/                             # Execution logs
└── temp/                             # Temporary processing files
```

### **Key Result Files**

| File                                | Description                                       | Usage                              |
| ----------------------------------- | ------------------------------------------------- | ---------------------------------- |
| `consolidated_research_results.csv` | **Master results file** with all experiments      | Primary data for research analysis |
| `pipeline_comparison_report.json`   | **Comparative analysis** with performance metrics | Pipeline comparison insights       |
| `research_summary.md`               | **Research findings** in Markdown format          | Research paper material            |
| `performance_comparison.png`        | **Performance visualizations**                    | Charts for publications            |

## 📈 **Results Schema**

### **CSV Output Columns**

| Column                         | Description                                   | Research Usage               |
| ------------------------------ | --------------------------------------------- | ---------------------------- |
| `experiment_id`                | Unique experiment identifier                  | Tracking and reproducibility |
| `pipeline_type`                | batch/stream/hybrid                           | Pipeline comparison          |
| `dataset_type`                 | healthcare/financial                          | Data type analysis           |
| `dataset_size`                 | Number of records                             | Scaling analysis             |
| `anonymization_method`         | k_anonymity/differential_privacy/tokenization | Method comparison            |
| `anonymization_params`         | JSON config (k_value, epsilon, key_length)    | Parameter optimization       |
| `pure_processing_time_seconds` | **Clean processing time**                     | Primary performance metric   |
| `records_per_second`           | **Throughput measurement**                    | Performance comparison       |
| `violations_detected`          | Compliance violations found                   | Effectiveness analysis       |
| `violation_rate`               | Percentage of violations                      | Compliance effectiveness     |
| `information_loss_score`       | Anonymization quality (0-1)                   | Privacy-utility tradeoff     |
| `utility_preservation_score`   | Data utility retained (0-1)                   | Utility analysis             |
| `memory_usage_mb`              | Memory consumption                            | Resource analysis            |
| `cpu_usage_percent`            | CPU utilization                               | Resource analysis            |

### **Research Metrics**

The framework provides **research-grade metrics** for:

1. **Performance Comparison**: Pure processing time without I/O contamination
2. **Scaling Analysis**: Throughput vs. dataset size relationships
3. **Anonymization Effectiveness**: Information loss vs. utility preservation
4. **Resource Utilization**: Memory and CPU consumption patterns
5. **Compliance Detection**: Violation detection rates by pipeline type

## 🔬 **Research Applications**

### **For Research Papers**

```python
# Example: Load consolidated results for analysis
import pandas as pd
import numpy as np

# Load consolidated results
df = pd.read_csv('results/consolidated_research_results.csv')

# Filter successful experiments
successful = df[df['success'] == True]

# Pipeline performance comparison
pipeline_performance = successful.groupby('pipeline_type').agg({
    'pure_processing_time_seconds': 'mean',
    'records_per_second': 'mean',
    'violation_rate': 'mean'
})

# Anonymization method effectiveness
method_effectiveness = successful.groupby('anonymization_method').agg({
    'information_loss_score': 'mean',
    'utility_preservation_score': 'mean',
    'records_per_second': 'mean'
})

# Scaling analysis
scaling_analysis = successful.groupby(['pipeline_type', 'dataset_size']).agg({
    'records_per_second': 'mean'
}).reset_index()
```

### **Statistical Analysis**

```python
# Example: Statistical significance testing
from scipy import stats

# Compare pipeline performance
batch_throughput = successful[successful['pipeline_type'] == 'batch']['records_per_second']
stream_throughput = successful[successful['pipeline_type'] == 'stream']['records_per_second']

# Perform t-test
t_stat, p_value = stats.ttest_ind(batch_throughput, stream_throughput)
print(f"Pipeline comparison: t={t_stat:.3f}, p={p_value:.3f}")

# Correlation analysis
correlation = successful[['dataset_size', 'records_per_second']].corr()
print(f"Scaling correlation: {correlation.iloc[0,1]:.3f}")
```

## 🎯 **Research Questions Addressed**

### **RQ1: Pipeline Architecture Effectiveness**

- **Question**: How do different pipeline architectures affect compliance violation detection performance?
- **Metrics**: `violation_rate`, `records_per_second`, `pure_processing_time_seconds`
- **Analysis**: Compare batch vs. stream vs. hybrid performance across datasets

### **RQ2: Anonymization Method Impact**

- **Question**: How do different anonymization methods affect processing performance and data utility?
- **Metrics**: `information_loss_score`, `utility_preservation_score`, `records_per_second`
- **Analysis**: Compare k-anonymity vs. differential privacy vs. tokenization

### **RQ3: Scaling Characteristics**

- **Question**: How do pipeline architectures scale with increasing dataset sizes?
- **Metrics**: `records_per_second` vs. `dataset_size`
- **Analysis**: Scaling efficiency across pipeline types

## 🔧 **Advanced Usage**

### **Custom Configurations**

```python
# Modify anonymization configurations
from research_utils import AnonymizationConfigManager

config_manager = AnonymizationConfigManager()

# Add custom k-anonymity values
custom_configs = []
for k in [2, 7, 20]:  # Custom k values
    config = AnonymizationConfig(
        method=AnonymizationMethod.K_ANONYMITY,
        k_value=k
    )
    custom_configs.append(config)

config_manager.all_configs.extend(custom_configs)
```

### **Custom Dataset Sizes**

```python
# Modify dataset sizes in research_utils.py
class ResearchDataGenerator:
    def generate_test_datasets(self, base_dir: str = "test_data"):
        # Custom dataset sizes
        dataset_sizes = [100, 250, 750, 1500, 3000]  # Custom sizes
        # ... rest of method
```

## 🚨 **Troubleshooting**

### **Common Issues**

**1. Kafka Connection Failed**

```bash
# Start Kafka services
docker-compose up -d kafka

# Or run without Kafka
python run_all_research_analysis.py --skip-kafka-check
```

**2. Memory Issues with Large Datasets**

```python
# Reduce dataset sizes in research_utils.py
dataset_sizes = [100, 500, 1000]  # Smaller sizes
```

**3. Spark Initialization Failed**

```bash
# Check Java installation
java -version

# Or run stream/hybrid only
python run_all_research_analysis.py --stream-only
```

### **Performance Optimization**

```python
# For faster testing, reduce configurations
class AnonymizationConfigManager:
    def _generate_all_configs(self):
        configs = []
        # Test fewer configurations
        for k in [3, 10]:  # Reduced from [3, 5, 10, 15]
            configs.append(AnonymizationConfig(
                method=AnonymizationMethod.K_ANONYMITY,
                k_value=k
            ))
        return configs
```

## 📚 **Research Citation**

When using these results in research publications, include:

```bibtex
@misc{pipeline_research_framework,
  title={Comprehensive Pipeline Performance Analysis Framework},
  author={Your Name},
  year={2024},
  note={Research analysis framework for batch, stream, and hybrid processing pipelines with anonymization}
}
```

## 🎉 **Expected Results**

A complete run generates:

- **330 total experiments** across all configurations
- **Research-grade metrics** with clean timing separation
- **Statistical significance** data for pipeline comparison
- **Comprehensive analysis** ready for research publication
- **Performance visualizations** for academic presentations

The framework provides the foundation for rigorous empirical evaluation of data processing pipeline architectures in compliance-sensitive environments.

---

**🔬 Ready for research publication and academic evaluation!**
