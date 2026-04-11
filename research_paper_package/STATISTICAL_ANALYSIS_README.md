# Statistical Analysis Template Guide

## 1. Purpose
This template takes trial-level experiment CSV data and produces publication-ready tables in both CSV and LaTeX formats.

Generated outputs:
- Descriptive statistics table for binary outcomes.
- Descriptive statistics table for continuous outcomes.
- Hypothesis test summary table with FDR-corrected q-values.
- Ablation gain table (delta vs control variant).

## 2. Expected Input
Use a trial-level CSV with one row per experiment observation.

Minimum columns:
- `variant_id`
- `path_found`
- `intro_created`
- `intro_accepted`
- `intro_completed`
- `intro_declined`
- `top_path_score`
- `hop_count`
- `discovery_latency_ms`
- `completion_time_hours`

The file `trial_results_template.csv` shows the required schema.

## 3. Install Dependencies
Use your project virtual environment and install:

```powershell
pip install pandas numpy scipy statsmodels jinja2
```

## 4. Run Analysis

```powershell
python research_paper_package/statistical_analysis_template.py \
  --input research_paper_package/trial_results_template.csv \
  --output-dir research_paper_package/output \
  --group-col variant_id \
  --control V0
```

## 5. Statistical Logic Used
- Binary metrics: Chi-square test, or Fisher exact when expected counts are low.
- Continuous metrics:
  - Welch t-test when both groups pass normality checks.
  - Mann-Whitney U otherwise.
- Multiple comparisons: Benjamini-Hochberg FDR correction.
- Effect sizes:
  - Binary: risk difference (plus odds ratio)
  - Continuous: Cohen's d or Cliff's delta

## 6. How to Use in IEEE Paper
Map outputs directly:
- `table_descriptive_binary.tex` and `table_descriptive_continuous.tex` -> descriptive metrics section.
- `table_hypothesis_tests.tex` -> statistical significance section.
- `table_ablation_gains.tex` -> ablation results subsection.

## 7. Pre-Submission Checks
- Ensure final CSV contains all real experiment runs (not template rows).
- Confirm control variant label matches your baseline.
- Verify q-values, effect sizes, and confidence intervals are reported in manuscript text.
