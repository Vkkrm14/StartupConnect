#!/usr/bin/env python3
"""
Statistical analysis template for TrustGraph research experiments.

Input: trial-level CSV with one row per founder-investor trial or workflow episode.
Output: publication-ready CSV and LaTeX tables for descriptive and inferential analysis.

Usage:
  python research_paper_package/statistical_analysis_template.py \
    --input research_paper_package/trial_results_template.csv \
    --output-dir research_paper_package/output \
    --group-col variant_id \
    --control V0
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from scipy import stats
from statsmodels.stats.multitest import multipletests


BINARY_METRICS = [
    "path_found",
    "intro_created",
    "intro_accepted",
    "intro_completed",
    "intro_declined",
]

CONTINUOUS_METRICS = [
    "top_path_score",
    "hop_count",
    "discovery_latency_ms",
    "completion_time_hours",
]

HIGHER_BETTER = {
    "path_found",
    "intro_created",
    "intro_accepted",
    "intro_completed",
    "top_path_score",
}

LOWER_BETTER = {
    "intro_declined",
    "hop_count",
    "discovery_latency_ms",
    "completion_time_hours",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run statistical analysis for TrustGraph experiments.")
    parser.add_argument("--input", required=True, help="Path to trial-level CSV file")
    parser.add_argument("--output-dir", required=True, help="Directory for output tables")
    parser.add_argument("--group-col", default="variant_id", help="Column defining experiment variants")
    parser.add_argument("--control", default="V0", help="Control variant label")
    parser.add_argument("--alpha", type=float, default=0.05, help="Significance level")
    return parser.parse_args()


def _safe_float(val):
    try:
        return float(val)
    except Exception:
        return np.nan


def _wilson_ci(successes: int, n: int, alpha: float = 0.05) -> Tuple[float, float]:
    if n == 0:
        return (np.nan, np.nan)
    z = stats.norm.ppf(1 - alpha / 2)
    phat = successes / n
    denom = 1 + z ** 2 / n
    center = (phat + z ** 2 / (2 * n)) / denom
    margin = z * np.sqrt((phat * (1 - phat) + z ** 2 / (4 * n)) / n) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def _mean_ci_t(values: np.ndarray, alpha: float = 0.05) -> Tuple[float, float]:
    values = values[~np.isnan(values)]
    n = len(values)
    if n < 2:
        return (np.nan, np.nan)
    mean = np.mean(values)
    sem = stats.sem(values, nan_policy="omit")
    t_crit = stats.t.ppf(1 - alpha / 2, df=n - 1)
    margin = t_crit * sem
    return (mean - margin, mean + margin)


def _iqr(values: np.ndarray) -> float:
    values = values[~np.isnan(values)]
    if len(values) == 0:
        return np.nan
    q1 = np.percentile(values, 25)
    q3 = np.percentile(values, 75)
    return q3 - q1


def _is_normal(values: np.ndarray, alpha: float = 0.05) -> bool:
    values = values[~np.isnan(values)]
    n = len(values)
    if n < 8:
        return False
    if n > 5000:
        return False
    try:
        _, p = stats.shapiro(values)
        return p > alpha
    except Exception:
        return False


def _cohens_d(x: np.ndarray, y: np.ndarray) -> float:
    x = x[~np.isnan(x)]
    y = y[~np.isnan(y)]
    if len(x) < 2 or len(y) < 2:
        return np.nan
    vx = np.var(x, ddof=1)
    vy = np.var(y, ddof=1)
    pooled = np.sqrt(((len(x) - 1) * vx + (len(y) - 1) * vy) / (len(x) + len(y) - 2))
    if pooled == 0:
        return 0.0
    return (np.mean(y) - np.mean(x)) / pooled


def _cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    x = x[~np.isnan(x)]
    y = y[~np.isnan(y)]
    if len(x) == 0 or len(y) == 0:
        return np.nan
    gt = 0
    lt = 0
    for xi in x:
        gt += np.sum(xi > y)
        lt += np.sum(xi < y)
    total = len(x) * len(y)
    return (gt - lt) / total


def _binary_test(control: pd.Series, treatment: pd.Series) -> Dict[str, float]:
    control = pd.to_numeric(control, errors="coerce").fillna(0).astype(int)
    treatment = pd.to_numeric(treatment, errors="coerce").fillna(0).astype(int)

    a = int(treatment.sum())
    b = int(len(treatment) - a)
    c = int(control.sum())
    d = int(len(control) - c)

    table = np.array([[a, b], [c, d]], dtype=float)

    p_t = a / len(treatment) if len(treatment) else np.nan
    p_c = c / len(control) if len(control) else np.nan
    risk_diff = p_t - p_c

    # Approximate CI for risk difference
    if len(control) > 0 and len(treatment) > 0:
        se = np.sqrt((p_c * (1 - p_c) / len(control)) + (p_t * (1 - p_t) / len(treatment)))
        ci_low = risk_diff - 1.96 * se
        ci_high = risk_diff + 1.96 * se
    else:
        ci_low, ci_high = (np.nan, np.nan)

    # Odds ratio with Haldane-Anscombe correction for stability
    a2, b2, c2, d2 = table.flatten()
    if np.any(table == 0):
        a2 += 0.5
        b2 += 0.5
        c2 += 0.5
        d2 += 0.5
    odds_ratio = (a2 * d2) / (b2 * c2)

    expected = None
    test_name = ""
    statistic = np.nan
    p_value = np.nan

    try:
        chi2, p_chi, _, exp = stats.chi2_contingency(table, correction=False)
        expected = exp
        if (exp < 5).any():
            odds_stat, p_fisher = stats.fisher_exact(table)
            test_name = "Fisher exact"
            statistic = odds_stat
            p_value = p_fisher
        else:
            test_name = "Chi-square"
            statistic = chi2
            p_value = p_chi
    except Exception:
        odds_stat, p_fisher = stats.fisher_exact(table)
        test_name = "Fisher exact"
        statistic = odds_stat
        p_value = p_fisher

    return {
        "test": test_name,
        "statistic": float(statistic),
        "p_value": float(p_value),
        "effect_name": "risk_difference",
        "effect_value": float(risk_diff),
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "odds_ratio": float(odds_ratio),
        "n_control": int(len(control)),
        "n_treatment": int(len(treatment)),
        "success_control": int(c),
        "success_treatment": int(a),
    }


def _continuous_test(control: pd.Series, treatment: pd.Series, alpha: float) -> Dict[str, float]:
    x = pd.to_numeric(control, errors="coerce").to_numpy(dtype=float)
    y = pd.to_numeric(treatment, errors="coerce").to_numpy(dtype=float)

    x = x[~np.isnan(x)]
    y = y[~np.isnan(y)]

    if len(x) < 2 or len(y) < 2:
        return {
            "test": "Insufficient data",
            "statistic": np.nan,
            "p_value": np.nan,
            "effect_name": "none",
            "effect_value": np.nan,
            "ci_low": np.nan,
            "ci_high": np.nan,
            "n_control": int(len(x)),
            "n_treatment": int(len(y)),
            "mean_control": np.nan if len(x) == 0 else float(np.mean(x)),
            "mean_treatment": np.nan if len(y) == 0 else float(np.mean(y)),
        }

    normal_x = _is_normal(x, alpha=alpha)
    normal_y = _is_normal(y, alpha=alpha)

    mean_diff = float(np.mean(y) - np.mean(x))

    # Approximate CI of mean difference
    sx2 = np.var(x, ddof=1) / len(x)
    sy2 = np.var(y, ddof=1) / len(y)
    se = np.sqrt(sx2 + sy2)
    ci_low = mean_diff - 1.96 * se
    ci_high = mean_diff + 1.96 * se

    if normal_x and normal_y:
        stat, p = stats.ttest_ind(y, x, equal_var=False)
        return {
            "test": "Welch t-test",
            "statistic": float(stat),
            "p_value": float(p),
            "effect_name": "cohens_d",
            "effect_value": float(_cohens_d(x, y)),
            "ci_low": float(ci_low),
            "ci_high": float(ci_high),
            "n_control": int(len(x)),
            "n_treatment": int(len(y)),
            "mean_control": float(np.mean(x)),
            "mean_treatment": float(np.mean(y)),
        }

    stat, p = stats.mannwhitneyu(y, x, alternative="two-sided")
    return {
        "test": "Mann-Whitney U",
        "statistic": float(stat),
        "p_value": float(p),
        "effect_name": "cliffs_delta",
        # Use treatment-vs-control orientation so sign matches mean_treatment-mean_control.
        "effect_value": float(_cliffs_delta(y, x)),
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "n_control": int(len(x)),
        "n_treatment": int(len(y)),
        "mean_control": float(np.mean(x)),
        "mean_treatment": float(np.mean(y)),
    }


def _direction(metric: str, effect_value: float) -> str:
    if np.isnan(effect_value):
        return "undetermined"
    if metric in HIGHER_BETTER:
        return "improved" if effect_value > 0 else "degraded"
    if metric in LOWER_BETTER:
        return "improved" if effect_value < 0 else "degraded"
    return "undetermined"


def _prepare_descriptive_tables(df: pd.DataFrame, group_col: str, alpha: float) -> Tuple[pd.DataFrame, pd.DataFrame]:
    binary_rows: List[Dict] = []
    continuous_rows: List[Dict] = []

    for variant, gdf in df.groupby(group_col):
        for metric in BINARY_METRICS:
            if metric not in gdf.columns:
                continue
            vals = pd.to_numeric(gdf[metric], errors="coerce").dropna()
            if vals.empty:
                continue
            vals = vals.astype(int)
            n = len(vals)
            s = int(vals.sum())
            rate = s / n if n else np.nan
            ci_l, ci_h = _wilson_ci(s, n, alpha=alpha)
            binary_rows.append(
                {
                    "variant": variant,
                    "metric": metric,
                    "n": n,
                    "successes": s,
                    "rate": rate,
                    "ci95_low": ci_l,
                    "ci95_high": ci_h,
                }
            )

        for metric in CONTINUOUS_METRICS:
            if metric not in gdf.columns:
                continue
            vals = pd.to_numeric(gdf[metric], errors="coerce").to_numpy(dtype=float)
            vals = vals[~np.isnan(vals)]
            if len(vals) == 0:
                continue
            ci_l, ci_h = _mean_ci_t(vals, alpha=alpha)
            continuous_rows.append(
                {
                    "variant": variant,
                    "metric": metric,
                    "n": len(vals),
                    "mean": float(np.mean(vals)),
                    "std": float(np.std(vals, ddof=1)) if len(vals) > 1 else np.nan,
                    "median": float(np.median(vals)),
                    "iqr": float(_iqr(vals)),
                    "ci95_low": float(ci_l),
                    "ci95_high": float(ci_h),
                }
            )

    return pd.DataFrame(binary_rows), pd.DataFrame(continuous_rows)


def _pairwise_tests(df: pd.DataFrame, group_col: str, control: str, alpha: float) -> pd.DataFrame:
    variants = [v for v in sorted(df[group_col].astype(str).unique()) if v != control]
    rows: List[Dict] = []

    control_df = df[df[group_col].astype(str) == str(control)]
    if control_df.empty:
        raise ValueError(f"Control variant '{control}' not found in column '{group_col}'.")

    for variant in variants:
        treat_df = df[df[group_col].astype(str) == str(variant)]

        for metric in BINARY_METRICS:
            if metric not in df.columns:
                continue
            out = _binary_test(control_df[metric], treat_df[metric])
            rows.append(
                {
                    "metric": metric,
                    "control": control,
                    "treatment": variant,
                    **out,
                    "direction": _direction(metric, out["effect_value"]),
                }
            )

        for metric in CONTINUOUS_METRICS:
            if metric not in df.columns:
                continue
            out = _continuous_test(control_df[metric], treat_df[metric], alpha=alpha)
            rows.append(
                {
                    "metric": metric,
                    "control": control,
                    "treatment": variant,
                    **out,
                    "direction": _direction(metric, out["effect_value"]),
                }
            )

    result = pd.DataFrame(rows)
    if not result.empty:
        pvals = result["p_value"].fillna(1.0).to_numpy(dtype=float)
        _, qvals, _, _ = multipletests(pvals, alpha=alpha, method="fdr_bh")
        result["q_value"] = qvals
        result["significant"] = result["q_value"] < alpha
    return result


def _ablation_gain_table(df: pd.DataFrame, group_col: str, control: str) -> pd.DataFrame:
    key_metrics = ["intro_accepted", "intro_completed", "top_path_score", "discovery_latency_ms"]
    rows: List[Dict] = []

    base = df[df[group_col].astype(str) == str(control)]
    if base.empty:
        return pd.DataFrame(rows)

    for variant in sorted(df[group_col].astype(str).unique()):
        var_df = df[df[group_col].astype(str) == str(variant)]
        if var_df.empty:
            continue
        for metric in key_metrics:
            if metric not in df.columns:
                continue
            b = pd.to_numeric(base[metric], errors="coerce").dropna()
            v = pd.to_numeric(var_df[metric], errors="coerce").dropna()
            if b.empty or v.empty:
                continue
            base_mean = float(b.mean())
            var_mean = float(v.mean())
            delta_abs = var_mean - base_mean
            delta_pct = np.nan
            if base_mean != 0:
                delta_pct = (delta_abs / base_mean) * 100.0
            rows.append(
                {
                    "metric": metric,
                    "control": control,
                    "variant": variant,
                    "control_mean": base_mean,
                    "variant_mean": var_mean,
                    "delta_abs": delta_abs,
                    "delta_pct": delta_pct,
                    "interpretation": _direction(metric, delta_abs),
                }
            )

    return pd.DataFrame(rows)


def _save_table(df: pd.DataFrame, path_csv: Path, path_tex: Path) -> None:
    df.to_csv(path_csv, index=False)
    tex_df = df.copy()
    for col in tex_df.columns:
        if is_numeric_dtype(tex_df[col]):
            tex_df[col] = tex_df[col].map(lambda x: f"{x:.4f}" if pd.notna(x) else "")
    tex_df.to_latex(path_tex, index=False, escape=False)


def main() -> None:
    args = parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    df = pd.read_csv(input_path)

    if args.group_col not in df.columns:
        raise ValueError(f"Group column '{args.group_col}' not found in CSV columns: {list(df.columns)}")

    df[args.group_col] = df[args.group_col].astype(str)

    binary_desc, cont_desc = _prepare_descriptive_tables(df, args.group_col, args.alpha)
    tests_df = _pairwise_tests(df, args.group_col, args.control, args.alpha)
    gains_df = _ablation_gain_table(df, args.group_col, args.control)

    _save_table(
        binary_desc,
        output_dir / "table_descriptive_binary.csv",
        output_dir / "table_descriptive_binary.tex",
    )
    _save_table(
        cont_desc,
        output_dir / "table_descriptive_continuous.csv",
        output_dir / "table_descriptive_continuous.tex",
    )
    _save_table(
        tests_df,
        output_dir / "table_hypothesis_tests.csv",
        output_dir / "table_hypothesis_tests.tex",
    )
    _save_table(
        gains_df,
        output_dir / "table_ablation_gains.csv",
        output_dir / "table_ablation_gains.tex",
    )

    summary_lines = [
        "# Statistical Analysis Summary",
        "",
        f"Input file: {input_path}",
        f"Group column: {args.group_col}",
        f"Control variant: {args.control}",
        f"Alpha: {args.alpha}",
        "",
        "## Generated Tables",
        "- table_descriptive_binary.csv/.tex",
        "- table_descriptive_continuous.csv/.tex",
        "- table_hypothesis_tests.csv/.tex",
        "- table_ablation_gains.csv/.tex",
        "",
        "## Notes",
        "- q_value uses Benjamini-Hochberg FDR correction.",
        "- Binary metrics are tested with Chi-square or Fisher exact based on expected counts.",
        "- Continuous metrics use Welch t-test when both groups pass normality, else Mann-Whitney U.",
    ]

    (output_dir / "analysis_summary.md").write_text("\n".join(summary_lines), encoding="utf-8")

    print("Analysis complete. Tables written to:", output_dir)


if __name__ == "__main__":
    main()
