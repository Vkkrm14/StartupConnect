# TrustGraph Simulation and Ablation Plan

## 1. Objective
Establish whether TrustGraph's distrust-aware, trust-weighted routing and workflow constraints improve introduction quality over simpler baselines while maintaining acceptable latency.

This plan is aligned to the implemented architecture:
- Graph computations: `backend/graph-service`
- Workflow transitions: `backend/workflow-service`
- Optional reranking and indexing context: `backend/search-service`
- Seeded graph generation: `backend/scripts/seed_data.py`

## 2. Research Questions and Hypotheses

### RQ1
Does distrust-aware filtering improve downstream introduction outcomes compared to trust-only routing?

- H1a: Full model has higher intro completion rate than trust-only model.
- H1b: Full model has lower failed/declined workflow ratio than trust-only model.

### RQ2
Do trust + strength + recency + mutual-boost features outperform shortest-path routing?

- H2a: Weighted model has higher acceptance rate than shortest-path baseline.
- H2b: Weighted model yields higher median path quality score.

### RQ3
What latency overhead is introduced by distrust filtering and workflow checks?

- H3a: p95 path discovery latency increase is bounded and operationally acceptable.
- H3b: End-to-end workflow completion latency remains within target range.

## 3. Variants (Ablation Matrix)

| Variant | Description | Enabled Components |
|---|---|---|
| V0 | Shortest-path baseline | Hop count only; no trust weighting; no distrust filter |
| V1 | Trust-only | `trust_score` weighting; no recency/mutual/distrust |
| V2 | Trust+strength+recency+mutual | Full path score except distrust filtering |
| V3 | V2 + distrust filter | Exclude paths with active undisputed distrust nodes |
| V4 | Full model | V3 + workflow-constrained completion effects |

Note:
- V2-V4 map directly to `path_discovery.py` scoring design.
- V4 includes state-machine behavior from `workflow-service` approval chain.

## 4. Experimental Environment

## 4.1 Infrastructure
- Use Docker Compose stack from project root.
- Services required: graph-service, workflow-service, api-gateway, JanusGraph, Cassandra, MongoDB, Redis, Redpanda.

## 4.2 Reproducibility Controls
- Fixed random seed list, e.g., `S = [11, 19, 23, 31, 47, ...]`.
- Fixed founder-investor query set per run.
- Fixed max hops and trust threshold per condition.
- Record git commit hash and date for every run.

## 4.3 Dataset Conditions
Generate three network regimes to test robustness:
- C1 Low conflict: sparse `DISTRUSTS` edges.
- C2 Moderate conflict: balanced trust/distrust edges.
- C3 High conflict: dense distrust around connector subgraphs.

Use the seed script as baseline and add condition-specific modifiers.

## 5. Simulation Procedure

## 5.1 Initialization
1. Start containers.
2. Clear old state.
3. Seed graph/users/startups/edges with selected seed.
4. Verify service health endpoints.

## 5.2 Path Discovery Trials
For each `(condition, variant, seed)`:
1. Select founder-investor query batch (recommended >= 100 pairs).
2. Run path discovery API call per pair.
3. Record path existence, top path score, hop count, and endpoint latency.

## 5.3 Workflow Trials
For each accepted candidate path:
1. Create intro request in workflow service.
2. Simulate intermediary actions (accept/decline model).
3. Record status transitions and completion timestamp.

## 5.4 Trial Counts
Recommended minimum:
- At least 30 independent runs per variant per condition.
- Keep equal trial counts to simplify balanced comparisons.

## 6. Metrics and Logging Schema

## 6.1 Primary Metrics
- Acceptance rate = accepted intro requests / total intro requests.
- Completion rate = completed requests / approved requests.
- Median time-to-intro (hours).
- Path quality score of accepted paths.
- API latency (p50, p95, p99) for path discovery.

## 6.2 Secondary Metrics
- Decline ratio.
- No-path ratio.
- Distrust-filter trigger ratio.
- Reputation delta per completed intro (optional exploratory metric).

## 6.3 Required Per-Trial Fields
- run_id
- timestamp_utc
- condition_id
- variant_id
- random_seed
- founder_id
- investor_id
- path_found
- top_path_score
- hop_count
- discovery_latency_ms
- intro_created
- intro_accepted
- intro_completed
- intro_declined
- completion_time_hours

## 7. Statistical Design Requirements

## 7.1 Outcome Type Mapping
- Binary outcomes: acceptance/completion/decline/no-path.
- Continuous outcomes: latency, path score, time-to-intro.

## 7.2 Planned Tests
- Binary pairwise: chi-square or Fisher exact.
- Continuous pairwise: Welch t-test if normal; Mann-Whitney U otherwise.
- Multi-variant omnibus: ANOVA/Kruskal-Wallis + post-hoc tests.
- Multiple comparison control: Benjamini-Hochberg FDR.

## 7.3 Reporting Requirements
For each metric and comparison, report:
- Sample size.
- Central tendency and spread.
- Test name and statistic.
- p-value and FDR-adjusted q-value.
- Effect size with interpretation.
- 95% confidence interval where applicable.

## 8. Publication Deliverables Mapping

## 8.1 Paper Tables
- Table A: Descriptive statistics by variant.
- Table B: Hypothesis test outcomes.
- Table C: Effect sizes and practical significance.

## 8.2 Paper Figures
- Fig. 1: Acceptance/completion with confidence intervals.
- Fig. 2: Latency distributions by variant.
- Fig. 3: Ablation gain chart (delta vs V0).

## 9. Acceptance Readiness Checklist (Pre-Submission)
- Hypotheses explicitly stated and tested.
- No claim without a corresponding test.
- Effect sizes included for all key comparisons.
- Multiple-comparison correction applied.
- Reproducibility metadata logged (seed, commit, config).
- All result tables auto-generated from raw trial data.

## 10. Suggested Execution Order
1. Run V0 and V1 first to validate baseline signal.
2. Add V2 to quantify weighted-path gain.
3. Add V3 to isolate distrust filtering effect.
4. Add V4 to evaluate workflow-constrained full model.
5. Freeze dataset and rerun all variants for final statistical analysis.
