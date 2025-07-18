# 🔬 Optimized Stream Processing: Topics and Consumer Groups

## 📋 Overview

This document provides a comprehensive list of all Kafka topics and consumer groups used in the optimized stream processing analysis. The optimization eliminates redundant data streaming by:

- **Streaming data once** to predefined topics at the beginning
- **Using different consumer groups** for each anonymization configuration
- **Reusing the same topics** across different configurations
- **Avoiding 110+ redundant streaming operations**

## 🏗️ Architecture

### Original Approach (Inefficient)

```
For each of 110 experiments:
1. Create unique topic
2. Stream all data to topic
3. Process data from topic
4. Delete topic
```

### Optimized Approach (Efficient)

```
Setup Phase:
1. Create 10 predefined topics (once)
2. Stream all data to topics (once)

Processing Phase:
For each of 110 experiments:
1. Create unique consumer group
2. Subscribe to existing topic
3. Process data from topic
4. Consumer group automatically tracks offset
```

## 📝 Predefined Topics

### Healthcare Topics (5 topics)

- `healthcare_500` - 500 healthcare records
- `healthcare_1000` - 1,000 healthcare records
- `healthcare_2500` - 2,500 healthcare records
- `healthcare_5000` - 5,000 healthcare records
- `healthcare_10000` - 10,000 healthcare records

### Financial Topics (5 topics)

- `financial_500` - 500 financial records
- `financial_1000` - 1,000 financial records
- `financial_2500` - 2,500 financial records
- `financial_5000` - 5,000 financial records
- `financial_10000` - 10,000 financial records

**Total Topics: 10**

## 👥 Consumer Groups

### K-Anonymity Consumer Groups (20 groups)

#### K-Anonymity (k=3)

- `k_3_healthcare_500`
- `k_3_healthcare_1000`
- `k_3_healthcare_2500`
- `k_3_healthcare_5000`
- `k_3_healthcare_10000`
- `k_3_financial_500`
- `k_3_financial_1000`
- `k_3_financial_2500`
- `k_3_financial_5000`
- `k_3_financial_10000`

#### K-Anonymity (k=5)

- `k_5_healthcare_500`
- `k_5_healthcare_1000`
- `k_5_healthcare_2500`
- `k_5_healthcare_5000`
- `k_5_healthcare_10000`
- `k_5_financial_500`
- `k_5_financial_1000`
- `k_5_financial_2500`
- `k_5_financial_5000`
- `k_5_financial_10000`

#### K-Anonymity (k=10)

- `k_10_healthcare_500`
- `k_10_healthcare_1000`
- `k_10_healthcare_2500`
- `k_10_healthcare_5000`
- `k_10_healthcare_10000`
- `k_10_financial_500`
- `k_10_financial_1000`
- `k_10_financial_2500`
- `k_10_financial_5000`
- `k_10_financial_10000`

#### K-Anonymity (k=15)

- `k_15_healthcare_500`
- `k_15_healthcare_1000`
- `k_15_healthcare_2500`
- `k_15_healthcare_5000`
- `k_15_healthcare_10000`
- `k_15_financial_500`
- `k_15_financial_1000`
- `k_15_financial_2500`
- `k_15_financial_5000`
- `k_15_financial_10000`

### Differential Privacy Consumer Groups (40 groups)

#### Differential Privacy (ε=0.1)

- `dp_0_1_healthcare_500`
- `dp_0_1_healthcare_1000`
- `dp_0_1_healthcare_2500`
- `dp_0_1_healthcare_5000`
- `dp_0_1_healthcare_10000`
- `dp_0_1_financial_500`
- `dp_0_1_financial_1000`
- `dp_0_1_financial_2500`
- `dp_0_1_financial_5000`
- `dp_0_1_financial_10000`

#### Differential Privacy (ε=0.5)

- `dp_0_5_healthcare_500`
- `dp_0_5_healthcare_1000`
- `dp_0_5_healthcare_2500`
- `dp_0_5_healthcare_5000`
- `dp_0_5_healthcare_10000`
- `dp_0_5_financial_500`
- `dp_0_5_financial_1000`
- `dp_0_5_financial_2500`
- `dp_0_5_financial_5000`
- `dp_0_5_financial_10000`

#### Differential Privacy (ε=1.0)

- `dp_1_0_healthcare_500`
- `dp_1_0_healthcare_1000`
- `dp_1_0_healthcare_2500`
- `dp_1_0_healthcare_5000`
- `dp_1_0_healthcare_10000`
- `dp_1_0_financial_500`
- `dp_1_0_financial_1000`
- `dp_1_0_financial_2500`
- `dp_1_0_financial_5000`
- `dp_1_0_financial_10000`

#### Differential Privacy (ε=2.0)

- `dp_2_0_healthcare_500`
- `dp_2_0_healthcare_1000`
- `dp_2_0_healthcare_2500`
- `dp_2_0_healthcare_5000`
- `dp_2_0_healthcare_10000`
- `dp_2_0_financial_500`
- `dp_2_0_financial_1000`
- `dp_2_0_financial_2500`
- `dp_2_0_financial_5000`
- `dp_2_0_financial_10000`

### Tokenization Consumer Groups (30 groups)

#### Tokenization (128-bit)

- `token_128_healthcare_500`
- `token_128_healthcare_1000`
- `token_128_healthcare_2500`
- `token_128_healthcare_5000`
- `token_128_healthcare_10000`
- `token_128_financial_500`
- `token_128_financial_1000`
- `token_128_financial_2500`
- `token_128_financial_5000`
- `token_128_financial_10000`

#### Tokenization (256-bit)

- `token_256_healthcare_500`
- `token_256_healthcare_1000`
- `token_256_healthcare_2500`
- `token_256_healthcare_5000`
- `token_256_healthcare_10000`
- `token_256_financial_500`
- `token_256_financial_1000`
- `token_256_financial_2500`
- `token_256_financial_5000`
- `token_256_financial_10000`

#### Tokenization (512-bit)

- `token_512_healthcare_500`
- `token_512_healthcare_1000`
- `token_512_healthcare_2500`
- `token_512_healthcare_5000`
- `token_512_healthcare_10000`
- `token_512_financial_500`
- `token_512_financial_1000`
- `token_512_financial_2500`
- `token_512_financial_5000`
- `token_512_financial_10000`

**Total Consumer Groups: 110**

## 🔄 Processing Flow

### 1. Setup Phase (Once)

```bash
# Create all predefined topics
python optimized_stream_pipeline_analysis.py
```

### 2. Data Streaming Phase (Once)

```
Topics populated with data:
├── healthcare_500 → 500 healthcare records
├── healthcare_1000 → 1,000 healthcare records
├── healthcare_2500 → 2,500 healthcare records
├── healthcare_5000 → 5,000 healthcare records
├── healthcare_10000 → 10,000 healthcare records
├── financial_500 → 500 financial records
├── financial_1000 → 1,000 financial records
├── financial_2500 → 2,500 financial records
├── financial_5000 → 5,000 financial records
└── financial_10000 → 10,000 financial records
```

### 3. Processing Phase (110 experiments)

```
For each anonymization configuration:
1. Create unique consumer group
2. Subscribe to appropriate topic
3. Process messages from topic
4. Consumer group tracks offset automatically
```

## 🧹 Cleanup Operations

### Full Cleanup (Recreate Topics)

```bash
python kafka_topic_cleanup.py --full-cleanup
```

### Light Cleanup (Clear Messages)

```bash
python kafka_topic_cleanup.py --light-cleanup
```

### Status Check

```bash
python kafka_topic_cleanup.py --status
```

## 📊 Performance Benefits

### Original Approach

- **110 topic creations** (one per experiment)
- **110 data streaming operations** (redundant)
- **110 topic deletions** (cleanup)
- **High I/O overhead** and **network usage**

### Optimized Approach

- **10 topic creations** (once at start)
- **1 data streaming operation** (once at start)
- **110 consumer group subscriptions** (lightweight)
- **Minimal I/O overhead** and **reduced network usage**

## 🔧 Key Optimizations

1. **Predefined Topics**: Fixed set of 10 topics for all experiments
2. **Single Data Stream**: Stream all data once to populate topics
3. **Consumer Groups**: Each configuration uses unique consumer group
4. **Offset Tracking**: Kafka automatically tracks consumer progress
5. **Reusability**: Same topics used across multiple configurations

## 📈 Expected Performance Improvements

- **~90% reduction** in Kafka topic operations
- **~90% reduction** in data streaming overhead
- **~80% reduction** in total experiment runtime
- **Consistent performance** across all experiments
- **Better resource utilization** (CPU, memory, network)

## 🛠️ Usage Examples

### Run Optimized Analysis

```bash
cd backend/research-analysis-scripts
python optimized_stream_pipeline_analysis.py
```

### Clean Up Between Runs

```bash
# Full cleanup (recreate topics)
python kafka_topic_cleanup.py --full-cleanup

# Light cleanup (clear messages only)
python kafka_topic_cleanup.py --light-cleanup
```

### Monitor Status

```bash
# Check topic status
python kafka_topic_cleanup.py --status

# List existing topics
python kafka_topic_cleanup.py --list-topics
```

## 🚀 Integration with Existing Scripts

The optimized approach is designed to be a drop-in replacement for the original stream processing analysis. It maintains the same interface and output format while providing significant performance improvements.

### File Structure

```
backend/research-analysis-scripts/
├── optimized_stream_pipeline_analysis.py    # Main optimized analyzer
├── kafka_topic_cleanup.py                   # Cleanup utility
├── research_utils.py                        # Updated utilities (CSV generation commented)
└── OPTIMIZED_STREAM_TOPICS_AND_CONSUMERS.md # This documentation
```

## 📋 Summary

- **Topics**: 10 predefined topics for different dataset types and sizes
- **Consumer Groups**: 110 unique consumer groups for each configuration
- **Optimization**: Single data streaming operation vs. 110 redundant operations
- **Performance**: ~90% reduction in Kafka operations overhead
- **Compatibility**: Drop-in replacement for existing analysis scripts
