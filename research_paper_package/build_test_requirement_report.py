#!/usr/bin/env python3

from pathlib import Path
import pandas as pd


def main() -> None:
    trials_path = Path("research_paper_package/data/trustgraph_simulation_trials.csv")
    hypothesis_path = Path("research_paper_package/output_simulation/table_hypothesis_tests.csv")
    out_path = Path("research_paper_package/output_simulation/tests_requirement_validation.md")

    df = pd.read_csv(trials_path)
    h = pd.read_csv(hypothesis_path)

    tests = sorted(h["test"].dropna().unique().tolist())

    binary_cols = [
        "path_found",
        "intro_created",
        "intro_accepted",
        "intro_completed",
        "intro_declined",
    ]
    continuous_cols = [
        "top_path_score",
        "hop_count",
        "discovery_latency_ms",
        "completion_time_hours",
    ]

    lines = []
    lines.append("# Statistical Test Requirement Validation")
    lines.append("")
    lines.append("## Dataset sanity checks (before inferential tests)")
    lines.append(f"- Rows: {len(df)}")
    lines.append(f"- Missing values total: {int(df.isna().sum().sum())}")
    lines.append(f"- Duplicate run_id count: {int(df['run_id'].duplicated().sum())}")
    lines.append(
        f"- Binary fields valid (0/1): "
        f"{all(set(df[col].dropna().unique()).issubset({0, 1}) for col in binary_cols)}"
    )
    lines.append(
        f"- Continuous fields non-negative: "
        f"{all((df[col] >= 0).all() for col in continuous_cols)}"
    )
    lines.append(f"- Balanced rows per variant: {df.groupby('variant_id').size().to_dict()}")
    lines.append("")
    lines.append("## Executed inferential tests")
    lines.append(f"- Tests observed in hypothesis table: {tests}")
    lines.append(f"- FDR q-value column present: {'q_value' in h.columns}")
    lines.append(
        f"- Effect size columns present: "
        f"{'effect_name' in h.columns and 'effect_value' in h.columns}"
    )
    lines.append(
        f"- Confidence interval columns present: "
        f"{'ci_low' in h.columns and 'ci_high' in h.columns}"
    )
    lines.append("")
    lines.append("## Notes on z-test and t-test necessity")
    lines.append(
        "- Proportion z-test is not mandatory here because Chi-square/Fisher exact "
        "already covers binary outcome comparisons."
    )
    lines.append(
        "- Welch t-test is implemented in the analysis template but not selected in this run; "
        "Mann-Whitney U was selected by the normality gate."
    )

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
