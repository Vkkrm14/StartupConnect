# Pre-Simulation Data Quality Audit

## Scope
- Conditions audited: C1, C2, C3
- Seeds per condition: 12
- Founder-investor pairs sampled per seed: 160

## Key checks
- Network structure: node counts, edge counts, density, reciprocity
- Feature distributions: trust, strength, recency
- Governance realism: blocked-node ratio from active undisputed distrust
- Reachability realism: raw vs distrust-safe path availability
- Risk baseline: blocked top-path rate for weighted non-governed routing (V2-style)

## Condition means (selected)
### C1
- trust_mean: 0.7186, trust_std: 0.1106, reciprocity: 0.5748
- blocked_node_ratio: 0.0727, raw_path_found_rate: 1.0000, safe_path_found_rate: 0.9167
- blocked_top_path_rate_v2: 0.2620

### C2
- trust_mean: 0.6422, trust_std: 0.1126, reciprocity: 0.5175
- blocked_node_ratio: 0.2106, raw_path_found_rate: 1.0000, safe_path_found_rate: 0.7474
- blocked_top_path_rate_v2: 0.5839

### C3
- trust_mean: 0.5727, trust_std: 0.1141, reciprocity: 0.4622
- blocked_node_ratio: 0.3447, raw_path_found_rate: 1.0000, safe_path_found_rate: 0.5219
- blocked_top_path_rate_v2: 0.8359

## Output files
- research_paper_package/output_simulation/pre_sim_quality_detailed.csv
- research_paper_package/output_simulation/pre_sim_quality_summary.csv
- research_paper_package/output_simulation/pre_sim_quality_report.md