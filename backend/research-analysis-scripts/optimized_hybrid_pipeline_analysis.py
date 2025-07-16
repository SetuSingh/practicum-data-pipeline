"""
Optimized Hybrid Pipeline Research Analysis Script (Apache Flink)
Combines batch-and-stream processing with intelligent routing **and** the same
optimizations we applied to the pure-stream pipeline:

1. 10 predefined Kafka topics (500-→10 000 × healthcare & financial)
2. Data streamed **once** at the beginning of the run
3. 110 unique consumer-groups (one per anonymization config × dataset)
4. TRUE COLD STARTS for the Flink processor – every experiment executes in a
   _separate subprocess_ so the JVM / Python interpreter is freshly started
   (mirrors the technique used in `batch_pipeline_analysis.py`).

Usage:
    python optimized_hybrid_pipeline_analysis.py

Note: Requires a running Kafka broker on localhost:9093.
"""

import os
import sys
import json
import time
import uuid
import queue
import threading
import subprocess
from datetime import datetime
from typing import Dict, Any, List

import pandas as pd
import numpy as np
from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError

# ─────────────────────────────────────────────────────────────────────────────
# Dynamic import path setup (backend + src)
# ─────────────────────────────────────────────────────────────────────────────
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
src_dir = os.path.join(backend_dir, 'src')
sys.path.insert(0, backend_dir)
sys.path.insert(0, src_dir)

# Research utilities
from research_utils import (
    ResearchDataGenerator,
    AnonymizationConfigManager,
    ResearchMetricsCollector,
    TimingUtilities,
    create_research_directory_structure,
)

try:
    from src.common.anonymization_engine import AnonymizationConfig, AnonymizationMethod
except ImportError:
    from common.anonymization_engine import AnonymizationConfig, AnonymizationMethod

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
DATASET_SIZES = [500, 1000, 2500, 5000, 10000]
DATASET_TYPES = ["healthcare", "financial"]


class OptimizedHybridPipelineAnalyzer:
    """Hybrid (batch+stream) analyzer with predefined topics + cold starts."""

    # ------------------------------------------------------------------
    # Init / setup helpers
    # ------------------------------------------------------------------
    def __init__(self, output_dir: str = "results"):
        self.output_dir = output_dir
        self.results_file = os.path.join(output_dir, "hybrid_pipeline_results.csv")
        os.makedirs(output_dir, exist_ok=True)

        self.kafka_servers = ["localhost:9093"]

        # helpers
        self.data_gen = ResearchDataGenerator()
        self.config_mgr = AnonymizationConfigManager()
        self.metrics = ResearchMetricsCollector(self.results_file)

        # topic / consumer-group registry
        self.topics: Dict[str, str] = self._build_topics()

        print("🧠 Optimized Hybrid Pipeline Analyzer initialised")
        print(f"📊 Results → {self.results_file}")
        print(f"🔌 Kafka brokers → {self.kafka_servers}")
        print(f"📝 Topics ✖ {len(self.topics)} – Consumers ✖ 110")

    # --------------------------------- helpers
    @staticmethod
    def _config_suffix(cfg: AnonymizationConfig) -> str:
        if cfg.method == AnonymizationMethod.K_ANONYMITY:
            return f"k_{cfg.k_value}"
        if cfg.method == AnonymizationMethod.DIFFERENTIAL_PRIVACY:
            return f"dp_{str(cfg.epsilon).replace('.', '_')}"
        if cfg.method == AnonymizationMethod.TOKENIZATION:
            return f"token_{cfg.key_length}"
        return "unknown"

    def _build_topics(self) -> Dict[str, str]:
        topics = {}
        for t in DATASET_TYPES:
            for s in DATASET_SIZES:
                topics[f"{t}_{s}"] = f"{t}_{s}"
        return topics

    # ------------------------------------------------------------------
    # Kafka utilities (create topics / stream data once)
    # ------------------------------------------------------------------
    def _ensure_topics(self) -> bool:
        admin = KafkaAdminClient(bootstrap_servers=self.kafka_servers)
        new_topics = [NewTopic(name=name, num_partitions=1, replication_factor=1) for name in self.topics.values()]
        try:
            admin.create_topics(new_topics)
            print("✅ Kafka topics created")
        except TopicAlreadyExistsError:
            print("ℹ️  Kafka topics already exist – skipping creation")
        finally:
            admin.close()
        return True

    def _stream_data_once(self) -> bool:
        producer = KafkaProducer(bootstrap_servers=self.kafka_servers, value_serializer=lambda x: json.dumps(x).encode())
        datasets = self.data_gen.generate_test_datasets()
        for d in datasets:
            topic = self.topics[f"{d['type']}_{d['size']}"]
            df = pd.read_csv(d['file_path'])
            for record in df.to_dict("records"):
                producer.send(topic, record)
            producer.flush()
            print(f"📤 Streamed {len(df)} → {topic}")
        producer.close()
        return True

    # ------------------------------------------------------------------
    # Main experiment loop
    # ------------------------------------------------------------------
    def run(self):
        print("\n🔬 OPTIMIZED HYBRID PIPELINE ANALYSIS – Flink")
        if not self._ensure_topics():
            return {"error": "Kafka topic creation failed"}
        self._stream_data_once()

        datasets = self.data_gen.generate_test_datasets()
        configs = self.config_mgr.get_all_configs()
        total = len(datasets) * len(configs)
        exp_num = 0

        for d in datasets:
            for cfg in configs:
                exp_num += 1
                self._run_single_experiment(d, cfg, exp_num, total)

        summary = self.metrics.get_experiment_summary()
        print("🎉 Hybrid analysis complete – results saved")
        return summary

    # ------------------------------------------------------------------
    # Single experiment (cold-start via subprocess)
    # ------------------------------------------------------------------
    def _run_single_experiment(self, d: Dict[str, Any], cfg: AnonymizationConfig, n: int, total: int):
        cfg_suffix = self._config_suffix(cfg)
        topic = self.topics[f"{d['type']}_{d['size']}"]
        group = f"{cfg_suffix}_{d['type']}_{d['size']}"
        print(f"\n⚙️  Exp {n}/{total} – {d['description']} – {cfg_suffix}")

        # ---------------------------------------------
        # Prepare lightweight JSON-serialisable config
        # ---------------------------------------------
        config_data = {
            'method': cfg.method.value,
            'k_value': cfg.k_value,
            'epsilon': cfg.epsilon,
            'key_length': cfg.key_length
        }

        # ---------------------------------------------
        # Build subprocess script (cold-start FlinkHybridProcessor)
        # ---------------------------------------------
        sub_script = f"""
import os, sys, json, time
from datetime import datetime
from kafka import KafkaConsumer
# dynamic path
current = os.getcwd()
backend = os.path.dirname(current)
sys.path.insert(0, backend)
sys.path.insert(0, os.path.join(backend, 'src'))
from src.hybrid.flink_processor import FlinkHybridProcessor
from src.common.anonymization_engine import AnonymizationConfig, AnonymizationMethod

# reconstruct config & vars
config_data = json.loads('{json.dumps(config_data)}')
ac = AnonymizationConfig(
    method=AnonymizationMethod(config_data['method']),
    k_value=config_data.get('k_value'),
    epsilon=config_data.get('epsilon'),
    key_length=config_data.get('key_length')
)

topic = '{topic}'
group = '{group}'
size  = {d['size']}
servers = ['localhost:9093']

proc = FlinkHybridProcessor(servers)
consumer = KafkaConsumer(topic,
                         bootstrap_servers=servers,
                         auto_offset_reset='earliest',
                         group_id=group,
                         enable_auto_commit=True,
                         value_deserializer=lambda x: json.loads(x.decode()))

start = time.time()
processed = 0
batch = stream = violations = 0
for msg in consumer:
    record = msg.value
    characteristics = proc.analyze_data_characteristics(record)
    decision = proc.make_routing_decision(record, characteristics)
    if decision['route'] == 'batch':
        out, _ = proc.process_via_batch(record, ac)
        batch += 1
    else:
        out, _ = proc.process_via_stream(record, ac)
        stream += 1
    if out.get('has_violations'):
        violations += 1
    processed += 1
    if processed >= size:
        break
end = time.time()

print('RESULT_JSON:' + json.dumps({{
    'pure_processing_time': end-start,
    'total_records': processed,
    'batch_routed': batch,
    'stream_routed': stream,
    'violations_detected': violations,
    'records_per_second': processed/(end-start) if end-start>0 else 0
}}))
"""
        # ---------------------------------------------
        # Run subprocess (cold start)
        # ---------------------------------------------
        proc = subprocess.Popen([sys.executable, "-c", sub_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = proc.communicate()
        result = None
        for line in out.split("\n"):
            if line.startswith("RESULT_JSON:"):
                result = json.loads(line[len("RESULT_JSON:"):])
                break
        if result is None:
            print("❌ Experiment failed", err)
            return

        # ---------------------------------------------
        # Record metrics
        # ---------------------------------------------
        timing = {
            'pure_processing_time': result['pure_processing_time'],
            'pre_processing_time': 0,
            'post_processing_time': 0,
            'total_time': result['pure_processing_time']
        }
        processing = {
            'total_records': result['total_records'],
            'violations_detected': result['violations_detected'],
            'violation_rate': result['violations_detected'] / result['total_records'] if result['total_records'] else 0,
            'records_per_second': result['records_per_second'],
            'information_loss_score': 0,
            'utility_preservation_score': 0,
            'privacy_level_score': 0,
        }
        self.metrics.record_experiment(
            pipeline_type="hybrid_optimized",
            dataset_info=d,
            anonymization_config=cfg,
            timing_results=timing,
            processing_results=processing,
            success=True,
            notes=f"Hybrid routing – batch:{result['batch_routed']} stream:{result['stream_routed']}"
        )
        print(f"✅ {result['records_per_second']:.0f} rec/s – {result['violations_detected']} viol.")


# ---------------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------------
def main():
    create_research_directory_structure()
    analyzer = OptimizedHybridPipelineAnalyzer()
    analyzer.run()


if __name__ == "__main__":
    main() 