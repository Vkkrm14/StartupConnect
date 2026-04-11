#!/usr/bin/env python3
"""
Synthetic simulation generator for TrustGraph-style trials.

The generator models:
- Trust graph construction with weighted directed TRUSTS edges.
- Active/disputed DISTRUSTS edges and blocked-node filtering.
- Multi-variant path selection (V0..V4 ablation matrix).
- Workflow acceptance/completion outcomes.
- Processing-stage latency breakdown.

Output schema is compatible with statistical_analysis_template.py.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


VARIANTS = ["V0", "V1", "V2", "V3", "V4"]

CONDITIONS = {
    "C1": {
        "name": "low_conflict",
        "trust_mu": 0.72,
        "strength_mu": 0.70,
        "recency_scale_days": 22.0,
        "mutual_prob": 0.40,
        "distrust_factor": 0.16,
        "distrust_active_prob": 0.58,
        "distrust_disputed_prob": 0.34,
        "conflict_pressure": 0.25,
        "time_penalty_hours": 0.0,
    },
    "C2": {
        "name": "moderate_conflict",
        "trust_mu": 0.64,
        "strength_mu": 0.62,
        "recency_scale_days": 36.0,
        "mutual_prob": 0.34,
        "distrust_factor": 0.30,
        "distrust_active_prob": 0.68,
        "distrust_disputed_prob": 0.26,
        "conflict_pressure": 0.45,
        "time_penalty_hours": 1.2,
    },
    "C3": {
        "name": "high_conflict",
        "trust_mu": 0.57,
        "strength_mu": 0.56,
        "recency_scale_days": 48.0,
        "mutual_prob": 0.29,
        "distrust_factor": 0.48,
        "distrust_active_prob": 0.78,
        "distrust_disputed_prob": 0.18,
        "conflict_pressure": 0.70,
        "time_penalty_hours": 2.4,
    },
}


@dataclass
class PathFeatures:
    path: List[str]
    hops: int
    score_v1: float
    score_v2: float
    avg_trust: float
    has_blocked: bool
    intermediaries: int
    intermediary_reputation_mean: float


def clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def make_nodes() -> Tuple[List[str], List[str], List[str], List[str]]:
    founders = [f"F{i:03d}" for i in range(1, 31)]
    investors = [f"I{i:03d}" for i in range(1, 21)]
    connectors = [f"C{i:03d}" for i in range(1, 61)]
    all_nodes = founders + investors + connectors
    return founders, investors, connectors, all_nodes


def make_edge_props(rng: np.random.Generator, params: Dict) -> Dict[str, float]:
    trust = clip(float(rng.normal(params["trust_mu"], 0.12)), 0.15, 0.98)
    strength = clip(float(rng.normal(params["strength_mu"], 0.14)), 0.10, 0.98)
    days = float(rng.exponential(params["recency_scale_days"]))
    recency = clip(1.0 - (days / 90.0), 0.0, 1.0)
    return {"trust": trust, "strength": strength, "recency": recency}


def generate_graph(rng: np.random.Generator, condition_id: str):
    params = CONDITIONS[condition_id]

    founders, investors, connectors, all_nodes = make_nodes()
    edges: Dict[Tuple[str, str], Dict[str, float]] = {}
    adjacency: Dict[str, List[str]] = {node: [] for node in all_nodes}

    def add_edge(u: str, v: str):
        if u == v:
            return
        if (u, v) in edges:
            return
        props = make_edge_props(rng, params)
        edges[(u, v)] = props
        adjacency[u].append(v)

        # Mutual trust appears probabilistically as reciprocal accepted edge.
        if rng.random() < params["mutual_prob"] and (v, u) not in edges:
            rev_props = make_edge_props(rng, params)
            # Keep reciprocal edge moderately correlated.
            rev_props["trust"] = clip((rev_props["trust"] + props["trust"]) / 2 + rng.normal(0, 0.03), 0.12, 0.99)
            edges[(v, u)] = rev_props
            adjacency[v].append(u)

    # Directed trust topology.
    for f in founders:
        for c in connectors:
            if rng.random() < 0.19:
                add_edge(f, c)
        for i in investors:
            if rng.random() < 0.03:
                add_edge(f, i)

    for c in connectors:
        for i in investors:
            if rng.random() < 0.16:
                add_edge(c, i)
        for c2 in connectors:
            if c == c2:
                continue
            if rng.random() < 0.042:
                add_edge(c, c2)

    for i in investors:
        for c in connectors:
            if rng.random() < 0.028:
                add_edge(i, c)

    # Distrust edges and blocked nodes.
    distrust_candidates = connectors + investors
    distrust_count = int(len(distrust_candidates) * params["distrust_factor"])
    blocked_nodes = set()

    for _ in range(distrust_count):
        src, dst = rng.choice(distrust_candidates, size=2, replace=False)
        is_active = rng.random() < params["distrust_active_prob"]
        is_disputed = rng.random() < params["distrust_disputed_prob"]
        if is_active and not is_disputed:
            blocked_nodes.add(src)
            blocked_nodes.add(dst)

    # Reputation proxy from incoming/outgoing trust and distrust penalties.
    incoming: Dict[str, List[float]] = {n: [] for n in all_nodes}
    outgoing: Dict[str, List[float]] = {n: [] for n in all_nodes}
    for (u, v), p in edges.items():
        outgoing[u].append(p["trust"])
        incoming[v].append(p["trust"])

    reputation: Dict[str, float] = {}
    for node in all_nodes:
        in_mean = float(np.mean(incoming[node])) if incoming[node] else 0.40
        out_mean = float(np.mean(outgoing[node])) if outgoing[node] else 0.40
        vouch_proxy = float(rng.uniform(0.30, 0.90))
        distrust_penalty = 0.08 if node in blocked_nodes else 0.0
        rep = clip(0.45 * in_mean + 0.35 * out_mean + 0.20 * vouch_proxy - distrust_penalty, 0.0, 1.0)
        reputation[node] = rep

    return founders, investors, connectors, all_nodes, edges, adjacency, blocked_nodes, reputation


def enumerate_paths(
    adjacency: Dict[str, List[str]],
    src: str,
    dst: str,
    max_hops: int = 4,
    max_paths: int = 220,
) -> List[List[str]]:
    if src == dst:
        return [[src]]

    paths: List[List[str]] = []
    stack: List[Tuple[str, List[str]]] = [(src, [src])]

    while stack and len(paths) < max_paths:
        node, path = stack.pop()
        hops = len(path) - 1
        if hops >= max_hops:
            continue

        neighbors = adjacency.get(node, [])
        for nbr in neighbors:
            if nbr in path:
                continue
            new_path = path + [nbr]
            if nbr == dst:
                paths.append(new_path)
                if len(paths) >= max_paths:
                    break
            else:
                stack.append((nbr, new_path))

    return paths


def path_features(
    path: List[str],
    edges: Dict[Tuple[str, str], Dict[str, float]],
    blocked_nodes: set,
    reputation: Dict[str, float],
) -> PathFeatures:
    hops = len(path) - 1
    trust_vals = []
    core_vals = []

    for i in range(hops):
        u, v = path[i], path[i + 1]
        props = edges[(u, v)]
        t = props["trust"]
        s = props["strength"]
        r = props["recency"]
        mutual = 1.5 if (v, u) in edges else 1.0
        trust_vals.append(t)
        core_vals.append(t * s * r * mutual)

    hop_penalty = max(1.0 - 0.1 * (hops - 1), 0.6)
    score_v1 = float(np.mean(trust_vals) * hop_penalty)
    score_v2 = float(np.mean(core_vals) * hop_penalty)

    intermediaries = max(hops - 1, 0)
    inter_nodes = path[1:-1]
    inter_rep = float(np.mean([reputation[n] for n in inter_nodes])) if inter_nodes else float(np.mean([reputation[path[0]], reputation[path[-1]]]))

    # Match governance intuition: blocked checks apply to intermediaries and destination side.
    has_blocked = any(node in blocked_nodes for node in path[1:])

    return PathFeatures(
        path=path,
        hops=hops,
        score_v1=score_v1,
        score_v2=score_v2,
        avg_trust=float(np.mean(trust_vals)),
        has_blocked=has_blocked,
        intermediaries=intermediaries,
        intermediary_reputation_mean=inter_rep,
    )


def choose_path(features: List[PathFeatures], variant: str) -> PathFeatures | None:
    if not features:
        return None

    candidates = features
    if variant in ("V3", "V4"):
        candidates = [p for p in candidates if not p.has_blocked]
        if not candidates:
            return None

    if variant == "V0":
        # Shortest path first baseline.
        candidates = sorted(candidates, key=lambda p: (p.hops, -p.score_v2))
        return candidates[0]
    if variant == "V1":
        return max(candidates, key=lambda p: p.score_v1)

    # V2/V3/V4
    return max(candidates, key=lambda p: p.score_v2)


def simulate_trial(
    rng: np.random.Generator,
    variant: str,
    condition_id: str,
    chosen: PathFeatures | None,
    candidate_paths_count: int,
) -> Dict[str, float]:
    params = CONDITIONS[condition_id]

    graph_traversal_ms = max(4.0, 15.0 + 0.09 * candidate_paths_count + rng.normal(0, 1.1))
    distrust_check_ms = 0.0
    if variant in ("V3", "V4"):
        distrust_check_ms = max(0.2, 2.8 + 0.03 * candidate_paths_count + rng.normal(0, 0.45))

    score_base = {
        "V0": 1.5,
        "V1": 2.8,
        "V2": 4.6,
        "V3": 4.9,
        "V4": 5.2,
    }[variant]
    scoring_ms = max(0.3, score_base + 0.01 * candidate_paths_count + rng.normal(0, 0.4))

    discovery_latency_ms = graph_traversal_ms + distrust_check_ms + scoring_ms

    if chosen is None:
        return {
            "path_found": 0,
            "intro_created": 0,
            "intro_accepted": 0,
            "intro_completed": 0,
            "intro_declined": 0,
            "top_path_score": 0.0,
            "hop_count": 0,
            "completion_time_hours": 0.0,
            "contains_blocked_path_nodes": 0,
            "candidate_paths_count": candidate_paths_count,
            "graph_traversal_ms": graph_traversal_ms,
            "distrust_check_ms": distrust_check_ms,
            "scoring_ms": scoring_ms,
            "workflow_validation_ms": 0.0,
            "trust_update_ms": 0.0,
            "total_pipeline_ms": discovery_latency_ms,
            "discovery_latency_ms": discovery_latency_ms,
        }

    q_norm = clip(chosen.score_v2 / 1.1, 0.0, 1.0)
    hops = chosen.hops

    # Acceptance model.
    p_accept = 0.18 + 0.58 * q_norm - 0.06 * (hops - 1)
    if variant == "V0":
        p_accept -= 0.08
    elif variant == "V1":
        p_accept -= 0.03
    elif variant in ("V3", "V4"):
        p_accept += 0.05

    if chosen.has_blocked and variant in ("V0", "V1", "V2"):
        p_accept -= 0.14

    p_accept -= params["conflict_pressure"] * 0.08
    p_accept += (chosen.intermediary_reputation_mean - 0.5) * 0.10
    p_accept = clip(p_accept, 0.02, 0.95)

    intro_accepted = int(rng.random() < p_accept)

    workflow_validation_ms = max(0.2, 0.9 + 0.35 * chosen.intermediaries + rng.normal(0, 0.2))
    if variant == "V4":
        workflow_validation_ms += 0.75

    trust_update_ms = 0.0
    intro_completed = 0
    intro_declined = 0
    completion_time_hours = 0.0

    if intro_accepted:
        if chosen.intermediaries == 0:
            p_complete = clip(0.82 + 0.12 * q_norm, 0.05, 0.98)
        else:
            base_step = 0.72 + 0.18 * q_norm - 0.06 * params["conflict_pressure"]
            if variant == "V4":
                base_step += 0.07
            if chosen.has_blocked and variant in ("V0", "V1", "V2"):
                base_step -= 0.12
            base_step += (chosen.intermediary_reputation_mean - 0.5) * 0.08
            base_step = clip(base_step, 0.35, 0.97)
            p_complete = clip(base_step ** chosen.intermediaries, 0.02, 0.98)

        intro_completed = int(rng.random() < p_complete)

        if intro_completed:
            time_base = 5.2 + 3.3 * chosen.intermediaries + params["time_penalty_hours"]
            if variant == "V4":
                time_base *= 0.84
            elif variant in ("V2", "V3"):
                time_base *= 0.92

            completion_time_hours = max(1.0, float(rng.normal(time_base, 1.0 + 0.8 * chosen.intermediaries)))
            trust_update_ms = max(0.2, 1.35 + 0.25 * chosen.intermediaries + rng.normal(0, 0.2))
        else:
            intro_declined = 1
    else:
        intro_declined = 1

    total_pipeline_ms = discovery_latency_ms + workflow_validation_ms + trust_update_ms

    return {
        "path_found": 1,
        "intro_created": 1,
        "intro_accepted": intro_accepted,
        "intro_completed": intro_completed,
        "intro_declined": intro_declined,
        "top_path_score": chosen.score_v2,
        "hop_count": hops,
        "completion_time_hours": completion_time_hours,
        "contains_blocked_path_nodes": int(chosen.has_blocked),
        "candidate_paths_count": candidate_paths_count,
        "graph_traversal_ms": graph_traversal_ms,
        "distrust_check_ms": distrust_check_ms,
        "scoring_ms": scoring_ms,
        "workflow_validation_ms": workflow_validation_ms,
        "trust_update_ms": trust_update_ms,
        "total_pipeline_ms": total_pipeline_ms,
        "discovery_latency_ms": discovery_latency_ms,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic TrustGraph simulation dataset")
    parser.add_argument(
        "--output",
        default="research_paper_package/data/trustgraph_simulation_trials.csv",
        help="Output CSV path",
    )
    parser.add_argument("--queries-per-graph", type=int, default=140)
    parser.add_argument("--max-hops", type=int, default=4)
    parser.add_argument("--max-paths", type=int, default=220)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    seed_list = [11, 17, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61]
    rows = []

    run_id = 1
    base_ts = datetime(2026, 4, 4, 9, 0, 0, tzinfo=timezone.utc)

    for condition_id in ["C1", "C2", "C3"]:
        for seed in seed_list:
            rng = np.random.default_rng(seed + (1000 * (int(condition_id[1]) - 1)))

            founders, investors, _, _, edges, adjacency, blocked_nodes, reputation = generate_graph(rng, condition_id)

            for _ in range(args.queries_per_graph):
                founder_id = str(rng.choice(founders))
                investor_id = str(rng.choice(investors))

                paths = enumerate_paths(
                    adjacency,
                    founder_id,
                    investor_id,
                    max_hops=args.max_hops,
                    max_paths=args.max_paths,
                )

                features = [path_features(p, edges, blocked_nodes, reputation) for p in paths]
                candidate_count = len(features)

                for variant in VARIANTS:
                    chosen = choose_path(features, variant)
                    sim = simulate_trial(
                        rng=rng,
                        variant=variant,
                        condition_id=condition_id,
                        chosen=chosen,
                        candidate_paths_count=candidate_count,
                    )

                    ts = base_ts + timedelta(seconds=run_id)
                    rows.append(
                        {
                            "run_id": run_id,
                            "timestamp_utc": ts.isoformat().replace("+00:00", "Z"),
                            "condition_id": condition_id,
                            "variant_id": variant,
                            "random_seed": seed,
                            "founder_id": founder_id,
                            "investor_id": investor_id,
                            **sim,
                        }
                    )
                    run_id += 1

    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)

    # Quick console summary
    summary = (
        df.groupby("variant_id")[["intro_accepted", "intro_completed", "top_path_score", "discovery_latency_ms"]]
        .mean()
        .reset_index()
    )

    print(f"Generated {len(df):,} trial rows -> {output_path}")
    print("\nVariant means:")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
