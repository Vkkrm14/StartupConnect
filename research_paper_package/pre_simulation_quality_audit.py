#!/usr/bin/env python3
"""
Pre-simulation data quality audit for TrustGraph synthetic generator.

Purpose:
- Validate structural realism before trial simulation claims.
- Check edge distributions, reciprocity, blocked-node prevalence,
  and path availability under distrust constraints.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

# Import from local simulation module
import sys
from pathlib import Path as _Path

_THIS_DIR = _Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.append(str(_THIS_DIR))

from simulate_trustgraph_pipeline import (  # noqa: E402
    CONDITIONS,
    generate_graph,
    enumerate_paths,
    path_features,
)


def _seed_rng(condition_id: str, seed: int) -> np.random.Generator:
    return np.random.default_rng(seed + (1000 * (int(condition_id[1]) - 1)))


def _collect_graph_stats(condition_id: str, seed: int, sampled_pairs: int = 160) -> Dict[str, float]:
    rng = _seed_rng(condition_id, seed)

    founders, investors, connectors, all_nodes, edges, adjacency, blocked_nodes, reputation = generate_graph(
        rng, condition_id
    )

    edge_props = list(edges.values())
    trust_vals = np.array([p["trust"] for p in edge_props], dtype=float)
    strength_vals = np.array([p["strength"] for p in edge_props], dtype=float)
    recency_vals = np.array([p["recency"] for p in edge_props], dtype=float)

    edge_count = len(edges)
    node_count = len(all_nodes)
    possible_directed = max(node_count * (node_count - 1), 1)
    density = edge_count / possible_directed

    reciprocal = 0
    for (u, v) in edges.keys():
        if (v, u) in edges:
            reciprocal += 1
    reciprocity_ratio = reciprocal / max(edge_count, 1)

    out_degrees = np.array([len(adjacency[n]) for n in all_nodes], dtype=float)

    # Path availability checks (raw and distrust-safe)
    raw_found = 0
    safe_found = 0
    blocked_selected_ratio_num = 0

    for _ in range(sampled_pairs):
        f = str(rng.choice(founders))
        i = str(rng.choice(investors))

        paths = enumerate_paths(adjacency, f, i, max_hops=4, max_paths=220)
        if paths:
            raw_found += 1

            feats = [path_features(p, edges, blocked_nodes, reputation) for p in paths]
            has_safe = any(not ft.has_blocked for ft in feats)
            if has_safe:
                safe_found += 1

            # Approximate blocked exposure if selecting pure weighted path (V2-style)
            chosen_v2 = max(feats, key=lambda z: z.score_v2)
            blocked_selected_ratio_num += int(chosen_v2.has_blocked)

    return {
        "condition_id": condition_id,
        "seed": seed,
        "users_founders": len(founders),
        "users_investors": len(investors),
        "users_connectors": len(connectors),
        "users_total": node_count,
        "trust_edges": edge_count,
        "trust_density_directed": density,
        "trust_reciprocity_ratio": reciprocity_ratio,
        "blocked_nodes": len(blocked_nodes),
        "blocked_node_ratio": len(blocked_nodes) / max(node_count, 1),
        "trust_mean": float(np.mean(trust_vals)) if len(trust_vals) else 0.0,
        "trust_std": float(np.std(trust_vals)) if len(trust_vals) else 0.0,
        "trust_min": float(np.min(trust_vals)) if len(trust_vals) else 0.0,
        "trust_max": float(np.max(trust_vals)) if len(trust_vals) else 0.0,
        "strength_mean": float(np.mean(strength_vals)) if len(strength_vals) else 0.0,
        "recency_mean": float(np.mean(recency_vals)) if len(recency_vals) else 0.0,
        "out_degree_mean": float(np.mean(out_degrees)) if len(out_degrees) else 0.0,
        "out_degree_p95": float(np.percentile(out_degrees, 95)) if len(out_degrees) else 0.0,
        "sampled_pairs": sampled_pairs,
        "raw_path_found_rate": raw_found / sampled_pairs,
        "safe_path_found_rate": safe_found / sampled_pairs,
        "blocked_top_path_rate_v2": blocked_selected_ratio_num / sampled_pairs,
    }


def _summarize(df: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = [
        c
        for c in df.columns
        if c not in {"condition_id", "seed"}
    ]

    grouped = df.groupby("condition_id")[numeric_cols]
    mean_df = grouped.mean().add_suffix("_mean")
    std_df = grouped.std(ddof=1).fillna(0.0).add_suffix("_std")

    summary = pd.concat([mean_df, std_df], axis=1).reset_index()
    return summary


def main() -> None:
    seeds = [11, 17, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61]

    rows: List[Dict[str, float]] = []
    for condition_id in ["C1", "C2", "C3"]:
        for seed in seeds:
            rows.append(_collect_graph_stats(condition_id, seed, sampled_pairs=160))

    detailed = pd.DataFrame(rows).sort_values(["condition_id", "seed"])
    summary = _summarize(detailed)

    out_dir = Path("research_paper_package/output_simulation")
    out_dir.mkdir(parents=True, exist_ok=True)

    detailed_path = out_dir / "pre_sim_quality_detailed.csv"
    summary_path = out_dir / "pre_sim_quality_summary.csv"
    report_path = out_dir / "pre_sim_quality_report.md"

    detailed.to_csv(detailed_path, index=False)
    summary.to_csv(summary_path, index=False)

    lines = []
    lines.append("# Pre-Simulation Data Quality Audit")
    lines.append("")
    lines.append("## Scope")
    lines.append("- Conditions audited: C1, C2, C3")
    lines.append("- Seeds per condition: 12")
    lines.append("- Founder-investor pairs sampled per seed: 160")
    lines.append("")
    lines.append("## Key checks")
    lines.append("- Network structure: node counts, edge counts, density, reciprocity")
    lines.append("- Feature distributions: trust, strength, recency")
    lines.append("- Governance realism: blocked-node ratio from active undisputed distrust")
    lines.append("- Reachability realism: raw vs distrust-safe path availability")
    lines.append("- Risk baseline: blocked top-path rate for weighted non-governed routing (V2-style)")
    lines.append("")
    lines.append("## Condition means (selected)")

    for _, row in summary.iterrows():
        c = row["condition_id"]
        lines.append(f"### {c}")
        lines.append(
            f"- trust_mean: {row['trust_mean_mean']:.4f}, trust_std: {row['trust_std_mean']:.4f}, reciprocity: {row['trust_reciprocity_ratio_mean']:.4f}"
        )
        lines.append(
            f"- blocked_node_ratio: {row['blocked_node_ratio_mean']:.4f}, raw_path_found_rate: {row['raw_path_found_rate_mean']:.4f}, safe_path_found_rate: {row['safe_path_found_rate_mean']:.4f}"
        )
        lines.append(
            f"- blocked_top_path_rate_v2: {row['blocked_top_path_rate_v2_mean']:.4f}"
        )
        lines.append("")

    lines.append("## Output files")
    lines.append(f"- {detailed_path.as_posix()}")
    lines.append(f"- {summary_path.as_posix()}")
    lines.append(f"- {report_path.as_posix()}")

    report_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {detailed_path}")
    print(f"Wrote {summary_path}")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
