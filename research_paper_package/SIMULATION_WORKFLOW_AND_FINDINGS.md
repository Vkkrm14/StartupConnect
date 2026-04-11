# Simulation Workflow and Findings (Reproducibility Note)

## 1. Generated Dataset
- File: `research_paper_package/data/trustgraph_simulation_trials.csv`
- Rows: 25,200
- Variants: V0, V1, V2, V3, V4
- Conditions: C1 (low conflict), C2 (moderate conflict), C3 (high conflict)
- Seeds: 12 per condition
- Queries: 140 founder-investor pairs per seed

Computation:
- 3 conditions x 12 seeds x 140 queries x 5 variants = 25,200 trials

## 2. Simulation of Project Data Processing
The simulator models the same pipeline stages as the implemented architecture:
1. Graph traversal over directed trust edges.
2. Distrust governance check (active, undisputed distrust).
3. Path scoring and ranking (variant-dependent).
4. Workflow validation for intermediary approvals.
5. Trust update propagation after successful completion.

Per-trial stage latencies are recorded in:
- `graph_traversal_ms`
- `distrust_check_ms`
- `scoring_ms`
- `workflow_validation_ms`
- `trust_update_ms`
- `total_pipeline_ms`

## 3. Why This Processing Differs from Typical Related Baselines
Compared to shortest-path and trust-only approaches:
- TrustGraph simulation uses distrust as an explicit governance filter, not only weak penalty terms.
- Completion is modeled through sequential intermediary workflow constraints.
- Path selection quality is evaluated jointly with end-to-end completion outcomes, not only retrieval score.

## 4. Output Artifacts Used in the Paper
Primary analysis outputs:
- `research_paper_package/output_simulation/table_descriptive_binary.csv`
- `research_paper_package/output_simulation/table_descriptive_continuous.csv`
- `research_paper_package/output_simulation/table_hypothesis_tests.csv`
- `research_paper_package/output_simulation/table_ablation_gains.csv`
- `research_paper_package/output_simulation/processing_summary.csv`

Additional control comparisons:
- `research_paper_package/output_simulation_control_v1/*`
- `research_paper_package/output_simulation_control_v2/*`

## 5. Key Findings Inserted into the IEEE Draft
- Acceptance: V4 > V0, V1, V2 (statistically significant).
- Completion: V4 > V0, V1, V2 (statistically significant).
- Safety: blocked-path exposure reduced to 0% for created intros in V3/V4.
- Trade-off: discovery latency increases due to distrust checks and richer scoring.

## 6. Re-run Commands
Generate dataset:

```powershell
e:/Sem-6/NoSQL/startupConnect_draft/.venv/Scripts/python.exe research_paper_package/simulate_trustgraph_pipeline.py --output research_paper_package/data/trustgraph_simulation_trials.csv
```

Run baseline analysis:

```powershell
e:/Sem-6/NoSQL/startupConnect_draft/.venv/Scripts/python.exe research_paper_package/statistical_analysis_template.py --input research_paper_package/data/trustgraph_simulation_trials.csv --output-dir research_paper_package/output_simulation --group-col variant_id --control V0
```

Run trust-only and weighted controls:

```powershell
e:/Sem-6/NoSQL/startupConnect_draft/.venv/Scripts/python.exe research_paper_package/statistical_analysis_template.py --input research_paper_package/data/trustgraph_simulation_trials.csv --output-dir research_paper_package/output_simulation_control_v1 --group-col variant_id --control V1

e:/Sem-6/NoSQL/startupConnect_draft/.venv/Scripts/python.exe research_paper_package/statistical_analysis_template.py --input research_paper_package/data/trustgraph_simulation_trials.csv --output-dir research_paper_package/output_simulation_control_v2 --group-col variant_id --control V2
```
