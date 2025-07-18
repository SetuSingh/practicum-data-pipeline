# Adaptive Hybrid Router – Implementation Plan

_Aim: demonstrate intelligent routing of records to either the existing Storm stream path or Spark batch path using lightweight Python logic and without introducing Flink._

## 1. Objectives

- Route each incoming record to **stream** or **batch** based on simple, declarative rules.
- Keep implementation to **one self-contained Python file** (`adaptive_router.py`).
- Re-use existing components:
  - `StormStreamProcessor` for real-time path.
  - `SparkBatchProcessor` for batch path.
- Record routing decisions & overhead in the existing CSV schema (two new columns).

## 2. Minimal Rule Set

| Rule ID         | Condition (Python expression)                                         | Route  |
| --------------- | --------------------------------------------------------------------- | ------ |
| urgent_deadline | `record.get('days_to_deadline', 999) < 1`                             | stream |
| high_risk_hc    | `record["type"] == "healthcare" and record.get('risk_score',0) > 0.8` | stream |
| default         | _(fallback)_                                                          | batch  |

Rules stored in `router_rules.yaml`; evaluated top-down.

## 3. High-Level Architecture

```
Kafka → adaptive_router.py ─┬─> StormStreamProcessor.process_record()
                            └─> BatchBuffer  ──(every N records/Δt)──> SparkBatchProcessor.run()
```

- **adaptive_router.py** acts as a Kafka consumer on topic `raw-data` and a producer for two internal queues:
  - _Stream path:_ direct in-process call to Storm.
  - _Batch path:_ append record to an in-memory list; flush to Spark when:
    - buffer length ≥ `BATCH_SIZE` **or**
    - time since last flush ≥ `BATCH_INTERVAL` (e.g. 60 s).

## 4. Key Implementation Steps (inside adaptive_router.py)

1. **Load rules** from YAML into a list of `(id, compiled_condition, route)`.
2. **Kafka consumer**: `KafkaConsumer('raw-data', group_id='adaptive-router', …)`.
3. **Main loop**
   ```python
   for msg in consumer:
       record = msg.value
       t0 = time.time()
       route = evaluate_rules(record)
       router_time_ms = (time.time()-t0)*1000
       if route == 'stream':
           stream_proc.process_record(record, ANONYM_CFG)
       else:
           batch_buffer.append(record)
       maybe_flush_batch()
       log_metrics(route, router_time_ms)
   ```
4. **Batch flush** triggers Spark job:
   ```python
   spark_proc.run_batch(batch_buffer, ANONYM_CFG)
   batch_buffer.clear()
   ```
5. **Metrics**
   - Extend `processing_results` with:
     - `routing_decision` (stream/batch)
     - `router_time_ms`
   - Accumulate counts of records routed per rule for end-of-run summary.

## 5. Parameters & Defaults

| Parameter              | Default           | Notes                       |
| ---------------------- | ----------------- | --------------------------- |
| `BATCH_SIZE`           | 500               | flush when buffer ≥ size    |
| `BATCH_INTERVAL` (sec) | 60                | flush when last flush older |
| `RULE_FILE`            | router_rules.yaml | hot-reload not required     |

## 6. Evaluation Plan

1. **Datasets**: reuse existing sizes (1 k → 10 k).
2. **Scenarios**
   - Baseline: all‐stream.
   - Baseline: all‐batch.
   - Adaptive router with rules above.
3. **Metrics compared**
   - `e2e_latency_ms` (urgent vs. non-urgent).
   - CPU / memory totals.
   - Fraction of records routed to each path.
   - SLA compliance (≤2 s for urgent records).

## 7. Deliverables

- `adaptive_router.py` (≈ 200 lines) – single file implementation.
- Updated CSVs with routing columns.
- Section in `research.tex` covering router design & results.

---

_This plan keeps complexity low while delivering demonstrable adaptive routing and measurable benefits._

## 8. Parity with Existing Scripts

The router will mirror the _user-experience_ of `batch_pipeline_analysis.py` and `optimized_stream_pipeline_analysis.py` so that automation, notebooks and LaTeX plots work unchanged.

| Aspect                    | Behaviour                                                                                                                                                              |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **CLI**                   | `python adaptive_hybrid_router.py` (all sizes) \| `--sizes 1000,5000` identical flag logic.                                                                            |
| **Dataset generation**    | Re-uses `ResearchDataGenerator`; size filter applied the same way as in the other two scripts.                                                                         |
| **Output file**           | `backend/research-analysis-scripts/results/hybrid_router_results.csv` – same directory, same header (plus `routing_decision`, `router_time_ms`).                       |
| **Metrics Collector**     | Calls `ResearchMetricsCollector`, guaranteeing schema compatibility.                                                                                                   |
| **Console banners**       | Prints the same start / end banners and success summaries for consistency.                                                                                             |
| **Cold-start philosophy** | Router is a long-lived process; Spark flushes happen in-process. If strict cold-start symmetry is desired, batch flushes can be off-loaded to a subprocess (optional). |

With this parity the adaptive router drops into the workflow without any extra dependencies or changes to plotting code.

## 9. Regulatory-Aware Routing (GDPR & HIPAA)

The router will include an **optional rule layer** that inspects lightweight compliance metadata attached to each record. Rules are phrased as pure functions → easy to unit-test and toggle at runtime (policy-as-code).

| ID  | Predicate (pseudo)                      | Source field(s)                       | Route  | Why                                                   |
| --- | --------------------------------------- | ------------------------------------- | ------ | ----------------------------------------------------- |
| G1  | `no legal_basis AND EU subject`         | `legal_basis`, `data_subject_country` | stream | GDPR Art 6 violation must alert instantly             |
| G2  | `category ∈ SPECIAL_CATEGORY_LIST`      | `category`                            | stream | Special-category data (Art 9) needs strict protection |
| G3  | `consent_expiry < now()`                | `consent_expiry`                      | batch  | Re-consent workflow (GDPR)                            |
| G4  | `retention_date < now() + 7 days`       | `retention_date`                      | batch  | Imminent deletion window                              |
| H1  | `contains_phi AND encryption == 'none'` | `contains_phi`, `encryption`          | stream | Un-encrypted ePHI (HIPAA Security Rule)               |
| H2  | `audit_required is True`                | `audit_required`                      | stream | Timely audit logging (HIPAA)                          |
| H3  | `breach_suspected is True`              | `breach_suspected`                    | stream | 72-h breach notification clock                        |

_Implementation notes_

- Place these checks **before** existing operational rules.
- Keep the rule list in `regulatory_rules.yml` → loaded at start; enables CI tests and policy-as-code discussions.
- Synthetic data generator will add the minimal metadata fields (boolean or ISO-timestamp strings) so rules can trigger during experiments.

---

**Policy-as-Code Angle**  
Because each rule is a pure function and the set is stored in version-controlled YAML, the router embodies _policy as code_. You can:

1. Review changes via pull-request diff.
2. Unit-test each predicate with fixtures.
3. Generate compliance reports (hit-rate per rule, mean time-to-decision).
