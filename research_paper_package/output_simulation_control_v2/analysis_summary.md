# Statistical Analysis Summary

Input file: research_paper_package\data\trustgraph_simulation_trials.csv
Group column: variant_id
Control variant: V2
Alpha: 0.05

## Generated Tables
- table_descriptive_binary.csv/.tex
- table_descriptive_continuous.csv/.tex
- table_hypothesis_tests.csv/.tex
- table_ablation_gains.csv/.tex

## Notes
- q_value uses Benjamini-Hochberg FDR correction.
- Binary metrics are tested with Chi-square or Fisher exact based on expected counts.
- Continuous metrics use Welch t-test when both groups pass normality, else Mann-Whitney U.