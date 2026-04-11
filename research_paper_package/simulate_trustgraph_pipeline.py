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
    endpoint_affinity: float
    intermediary_responsiveness_mean: float
    intermediary_reliability_mean: float


@dataclass
class TrustCalibration:
    weight_interaction: float
    weight_success: float
    weight_recency: float
    tau_days: float
    n_ref_interactions: float
    n_ref_percentile: float
    calibration_logloss: float
    hop_alpha: float
    lambda_rho: float
    beta_risk: float
    path_param_calibration_mse: float
    alpha_sensitivity_delta_minus: float
    alpha_sensitivity_delta_plus: float
    lambda_sensitivity_delta_minus: float
    lambda_sensitivity_delta_plus: float
    beta_sensitivity_delta_minus: float
    beta_sensitivity_delta_plus: float


def clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def make_nodes() -> Tuple[List[str], List[str], List[str], List[str]]:
    founders = [f"F{i:03d}" for i in range(1, 31)]
    investors = [f"I{i:03d}" for i in range(1, 21)]
    connectors = [f"C{i:03d}" for i in range(1, 61)]
    all_nodes = founders + investors + connectors
    return founders, investors, connectors, all_nodes


def calibrate_trust_hyperparameters(
    rng: np.random.Generator,
    params: Dict,
    sample_size: int = 1800,
    n_ref_percentile: float = 90.0,
) -> TrustCalibration:
    # Build pseudo-historical edge outcomes and recover parameters by constrained search.
    interactions = rng.poisson(lam=max(2.0, params["trust_mu"] * 18.0), size=sample_size).astype(float)
    n_ref = max(5.0, float(np.percentile(interactions, n_ref_percentile)))
    f_int = np.clip(np.log1p(interactions) / np.log1p(n_ref), 0.0, 1.0)

    req_lambda = max(2.0, 5.5 + 2.0 * params["trust_mu"])
    intro_reqs = np.maximum(1, rng.poisson(lam=req_lambda, size=sample_size))
    succ_prob = clip(0.22 + 0.68 * params["trust_mu"] - 0.16 * params["conflict_pressure"], 0.05, 0.94)
    intro_succ = rng.binomial(intro_reqs.astype(int), succ_prob)
    f_succ = np.clip((intro_succ + 1.0) / (intro_reqs + 2.0), 0.0, 1.0)

    days = rng.exponential(scale=params["recency_scale_days"], size=sample_size)

    latent_w = np.array(
        [
            0.34 + 0.07 * (1.0 - params["conflict_pressure"]),
            0.41 + 0.10 * params["conflict_pressure"],
            0.25 - 0.05 * params["conflict_pressure"],
        ],
        dtype=float,
    )
    latent_w = np.clip(latent_w, 0.05, 0.9)
    latent_w = latent_w / latent_w.sum()
    latent_tau = clip(55.0 + 80.0 * params["conflict_pressure"], 35.0, 165.0)
    f_rec_latent = np.exp(-days / latent_tau)

    latent_score = latent_w[0] * f_int + latent_w[1] * f_succ + latent_w[2] * f_rec_latent
    latent_logit = -1.2 + 3.0 * latent_score + rng.normal(0.0, 0.35, size=sample_size)
    y = (rng.random(sample_size) < (1.0 / (1.0 + np.exp(-latent_logit)))).astype(float)

    tau_grid = np.arange(40.0, 181.0, 10.0)
    weight_step = 0.05
    best = None

    for tau in tau_grid:
        f_rec = np.exp(-days / tau)
        wi = 0.0
        while wi <= 1.0 + 1e-9:
            ws = 0.0
            while wi + ws <= 1.0 + 1e-9:
                wr = 1.0 - wi - ws
                if wr < -1e-9:
                    break
                wr = max(0.0, wr)
                score = wi * f_int + ws * f_succ + wr * f_rec
                pred = np.clip(score, 1e-5, 1.0 - 1e-5)
                logloss = float(-np.mean(y * np.log(pred) + (1.0 - y) * np.log(1.0 - pred)))
                if best is None or logloss < best[0]:
                    best = (logloss, wi, ws, wr, tau)
                ws += weight_step
            wi += weight_step

    assert best is not None

    # Calibrate path-level scoring hyperparameters (alpha, lambda_rho, beta) from pseudo historical utilities.
    path_hops = rng.integers(1, 5, size=sample_size).astype(float)
    distrust_density = rng.gamma(shape=1.4 + 1.8 * params["conflict_pressure"], scale=0.7, size=sample_size)
    quality = np.clip(latent_score + rng.normal(0.0, 0.04, size=sample_size), 0.0, 1.0)

    alpha_true = clip(0.14 + 0.34 * params["conflict_pressure"], 0.05, 0.85)
    lambda_true = clip(0.05 + 0.22 * params["conflict_pressure"], 0.01, 0.45)
    beta_true = clip(0.55 + 0.90 * params["conflict_pressure"], 0.2, 2.2)
    rho_true = np.minimum(1.0, beta_true * distrust_density)
    utility_true = quality * np.exp(-alpha_true * (path_hops - 1.0)) - lambda_true * rho_true + rng.normal(0.0, 0.02, size=sample_size)

    alpha_grid = np.arange(0.05, 0.86, 0.05)
    lambda_grid = np.arange(0.01, 0.46, 0.02)
    beta_grid = np.arange(0.2, 2.21, 0.1)

    best_path = None
    for alpha in alpha_grid:
        hop_term = np.exp(-alpha * (path_hops - 1.0))
        for lambda_rho in lambda_grid:
            for beta in beta_grid:
                rho = np.minimum(1.0, beta * distrust_density)
                utility_hat = quality * hop_term - lambda_rho * rho
                mse = float(np.mean((utility_hat - utility_true) ** 2))
                if best_path is None or mse < best_path[0]:
                    best_path = (mse, alpha, lambda_rho, beta)

    assert best_path is not None
    best_mse, best_alpha, best_lambda, best_beta = best_path

    def path_mse(alpha: float, lambda_rho: float, beta: float) -> float:
        hop_term = np.exp(-alpha * (path_hops - 1.0))
        rho = np.minimum(1.0, beta * distrust_density)
        utility_hat = quality * hop_term - lambda_rho * rho
        return float(np.mean((utility_hat - utility_true) ** 2))

    def rel_loss_delta(new_loss: float, baseline_loss: float) -> float:
        return float((new_loss - baseline_loss) / max(1e-8, baseline_loss))

    alpha_minus = clip(best_alpha * 0.8, 0.05, 0.9)
    alpha_plus = clip(best_alpha * 1.2, 0.05, 0.9)
    lambda_minus = clip(best_lambda * 0.8, 0.005, 0.6)
    lambda_plus = clip(best_lambda * 1.2, 0.005, 0.6)
    beta_minus = clip(best_beta * 0.8, 0.1, 3.0)
    beta_plus = clip(best_beta * 1.2, 0.1, 3.0)
    return TrustCalibration(
        weight_interaction=best[1],
        weight_success=best[2],
        weight_recency=best[3],
        tau_days=best[4],
        n_ref_interactions=n_ref,
        n_ref_percentile=n_ref_percentile,
        calibration_logloss=best[0],
        hop_alpha=best_alpha,
        lambda_rho=best_lambda,
        beta_risk=best_beta,
        path_param_calibration_mse=best_mse,
        alpha_sensitivity_delta_minus=rel_loss_delta(path_mse(alpha_minus, best_lambda, best_beta), best_mse),
        alpha_sensitivity_delta_plus=rel_loss_delta(path_mse(alpha_plus, best_lambda, best_beta), best_mse),
        lambda_sensitivity_delta_minus=rel_loss_delta(path_mse(best_alpha, lambda_minus, best_beta), best_mse),
        lambda_sensitivity_delta_plus=rel_loss_delta(path_mse(best_alpha, lambda_plus, best_beta), best_mse),
        beta_sensitivity_delta_minus=rel_loss_delta(path_mse(best_alpha, best_lambda, beta_minus), best_mse),
        beta_sensitivity_delta_plus=rel_loss_delta(path_mse(best_alpha, best_lambda, beta_plus), best_mse),
    )


def make_edge_props(rng: np.random.Generator, params: Dict, calibration: TrustCalibration) -> Dict[str, float]:
    interactions = float(rng.poisson(max(2.0, params["trust_mu"] * 18.0)))
    f_int = clip(float(np.log1p(interactions) / np.log1p(calibration.n_ref_interactions)), 0.0, 1.0)

    intro_reqs = int(max(1, rng.poisson(max(2.0, 5.5 + 2.0 * params["trust_mu"]))))
    succ_prob = clip(0.22 + 0.68 * params["trust_mu"] - 0.16 * params["conflict_pressure"], 0.05, 0.94)
    intro_succ = int(rng.binomial(intro_reqs, succ_prob))
    f_succ = clip(float((intro_succ + 1.0) / (intro_reqs + 2.0)), 0.0, 1.0)

    strength = clip(float(rng.normal(params["strength_mu"], 0.14)), 0.10, 0.98)
    days = float(rng.exponential(params["recency_scale_days"]))
    recency = clip(float(np.exp(-days / calibration.tau_days)), 0.0, 1.0)

    trust = clip(
        calibration.weight_interaction * f_int
        + calibration.weight_success * f_succ
        + calibration.weight_recency * recency
        + float(rng.normal(0.0, 0.02)),
        0.05,
        0.99,
    )
    return {"trust": trust, "strength": strength, "recency": recency}


def generate_graph(rng: np.random.Generator, condition_id: str, calibration: TrustCalibration):
    params = CONDITIONS[condition_id]

    founders, investors, connectors, all_nodes = make_nodes()
    edges: Dict[Tuple[str, str], Dict[str, float]] = {}
    adjacency: Dict[str, List[str]] = {node: [] for node in all_nodes}

    def add_edge(u: str, v: str):
        if u == v:
            return
        if (u, v) in edges:
            return
        props = make_edge_props(rng, params, calibration)
        edges[(u, v)] = props
        adjacency[u].append(v)

        # Mutual trust appears probabilistically as reciprocal accepted edge.
        if rng.random() < params["mutual_prob"] and (v, u) not in edges:
            rev_props = make_edge_props(rng, params, calibration)
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
    active_distrust_count: Dict[str, int] = {node: 0 for node in all_nodes}

    for _ in range(distrust_count):
        src, dst = rng.choice(distrust_candidates, size=2, replace=False)
        is_active = rng.random() < params["distrust_active_prob"]
        is_disputed = rng.random() < params["distrust_disputed_prob"]
        if is_active and not is_disputed:
            blocked_nodes.add(src)
            blocked_nodes.add(dst)
            active_distrust_count[str(src)] += 1
            active_distrust_count[str(dst)] += 1

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

    # Exogenous behavior factors drive workflow outcomes independently from ranking score.
    founder_open: Dict[str, float] = {f: clip(float(rng.normal(0.62, 0.13)), 0.05, 0.98) for f in founders}
    investor_receptive: Dict[str, float] = {
        i: clip(float(rng.normal(0.58 - 0.07 * params["conflict_pressure"], 0.14)), 0.03, 0.98) for i in investors
    }
    connector_responsive: Dict[str, float] = {
        c: clip(float(rng.normal(0.60 - 0.06 * params["conflict_pressure"], 0.16)), 0.02, 0.98) for c in connectors
    }
    connector_reliable: Dict[str, float] = {
        c: clip(float(rng.normal(0.63 - 0.08 * params["conflict_pressure"], 0.15)), 0.03, 0.98) for c in connectors
    }

    behavior = {
        "founder_open": founder_open,
        "investor_receptive": investor_receptive,
        "connector_responsive": connector_responsive,
        "connector_reliable": connector_reliable,
    }

    return founders, investors, connectors, all_nodes, edges, adjacency, blocked_nodes, reputation, behavior, active_distrust_count


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
    behavior: Dict[str, Dict[str, float]],
    active_distrust_count: Dict[str, int],
    calibration: TrustCalibration,
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

    hop_penalty = float(np.exp(-calibration.hop_alpha * max(0, hops - 1)))
    rho_vals = [min(1.0, calibration.beta_risk * float(active_distrust_count.get(node, 0))) for node in path]
    rho_bar = float(np.mean(rho_vals)) if rho_vals else 0.0
    score_v1 = float(np.mean(trust_vals) * hop_penalty)
    score_v2 = float(np.mean(core_vals) * hop_penalty - calibration.lambda_rho * rho_bar)

    intermediaries = max(hops - 1, 0)
    inter_nodes = path[1:-1]
    inter_rep = float(np.mean([reputation[n] for n in inter_nodes])) if inter_nodes else float(np.mean([reputation[path[0]], reputation[path[-1]]]))

    founder_open = behavior["founder_open"].get(path[0], 0.5)
    investor_receptive = behavior["investor_receptive"].get(path[-1], 0.5)
    endpoint_affinity = float(np.mean([founder_open, investor_receptive]))

    if inter_nodes:
        inter_resp = float(np.mean([behavior["connector_responsive"].get(n, 0.5) for n in inter_nodes]))
        inter_reliable = float(np.mean([behavior["connector_reliable"].get(n, 0.5) for n in inter_nodes]))
    else:
        inter_resp = 0.68
        inter_reliable = 0.72

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
        endpoint_affinity=endpoint_affinity,
        intermediary_responsiveness_mean=inter_resp,
        intermediary_reliability_mean=inter_reliable,
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

    hops = chosen.hops

    # Approval uses exogenous behavioral factors and governance friction, not ranking score.
    approval_logit = (
        -1.35
        + 1.40 * chosen.endpoint_affinity
        + 0.70 * chosen.intermediary_responsiveness_mean
        + 0.45 * chosen.intermediary_reliability_mean
        + 0.30 * (chosen.intermediary_reputation_mean - 0.5)
        - 0.28 * max(hops - 1, 0)
        - 0.95 * params["conflict_pressure"]
        - (0.90 if chosen.has_blocked and variant in ("V0", "V1", "V2") else 0.0)
        + (0.16 if variant == "V4" else 0.0)
    )
    p_accept = clip(float(1.0 / (1.0 + np.exp(-approval_logit))), 0.02, 0.95)

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
            completion_logit = (
                1.55
                + 0.45 * chosen.endpoint_affinity
                + 0.25 * chosen.intermediary_reliability_mean
                - 0.50 * params["conflict_pressure"]
                + (0.20 if variant == "V4" else 0.0)
            )
            p_complete = clip(float(1.0 / (1.0 + np.exp(-completion_logit))), 0.05, 0.98)
        else:
            step_logit = (
                0.58
                + 1.10 * chosen.intermediary_responsiveness_mean
                + 0.75 * chosen.intermediary_reliability_mean
                + 0.18 * (chosen.intermediary_reputation_mean - 0.5)
                - 0.65 * params["conflict_pressure"]
                - (0.75 if chosen.has_blocked and variant in ("V0", "V1", "V2") else 0.0)
                + (0.25 if variant == "V4" else 0.0)
            )
            p_step = clip(float(1.0 / (1.0 + np.exp(-step_logit))), 0.35, 0.97)
            p_complete = clip(p_step ** chosen.intermediaries, 0.02, 0.98)

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
    parser.add_argument(
        "--calibration-output",
        default="research_paper_package/output_simulation/trust_hyperparameter_calibration.csv",
        help="Output CSV path for learned trust weights and recency tau",
    )
    parser.add_argument(
        "--n-ref-percentile",
        type=float,
        default=90.0,
        help="Percentile used to define n_ref from interaction-count distribution on calibration split",
    )
    parser.add_argument("--queries-per-graph", type=int, default=140)
    parser.add_argument("--max-hops", type=int, default=4)
    parser.add_argument("--max-paths", type=int, default=220)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    calibration_output_path = Path(args.calibration_output)
    calibration_output_path.parent.mkdir(parents=True, exist_ok=True)

    seed_list = [11, 17, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61]
    rows = []
    calibration_rows = []

    run_id = 1
    base_ts = datetime(2026, 4, 4, 9, 0, 0, tzinfo=timezone.utc)

    for condition_id in ["C1", "C2", "C3"]:
        for seed in seed_list:
            rng = np.random.default_rng(seed + (1000 * (int(condition_id[1]) - 1)))
            calibration = calibrate_trust_hyperparameters(
                rng,
                CONDITIONS[condition_id],
                n_ref_percentile=args.n_ref_percentile,
            )
            calibration_rows.append(
                {
                    "condition_id": condition_id,
                    "random_seed": seed,
                    "weight_interaction": calibration.weight_interaction,
                    "weight_success": calibration.weight_success,
                    "weight_recency": calibration.weight_recency,
                    "tau_days": calibration.tau_days,
                    "n_ref_interactions": calibration.n_ref_interactions,
                    "n_ref_percentile": calibration.n_ref_percentile,
                    "calibration_logloss": calibration.calibration_logloss,
                    "hop_alpha": calibration.hop_alpha,
                    "lambda_rho": calibration.lambda_rho,
                    "beta_risk": calibration.beta_risk,
                    "path_param_calibration_mse": calibration.path_param_calibration_mse,
                    "alpha_sensitivity_delta_minus": calibration.alpha_sensitivity_delta_minus,
                    "alpha_sensitivity_delta_plus": calibration.alpha_sensitivity_delta_plus,
                    "lambda_sensitivity_delta_minus": calibration.lambda_sensitivity_delta_minus,
                    "lambda_sensitivity_delta_plus": calibration.lambda_sensitivity_delta_plus,
                    "beta_sensitivity_delta_minus": calibration.beta_sensitivity_delta_minus,
                    "beta_sensitivity_delta_plus": calibration.beta_sensitivity_delta_plus,
                }
            )

            founders, investors, _, _, edges, adjacency, blocked_nodes, reputation, behavior, active_distrust_count = generate_graph(
                rng,
                condition_id,
                calibration,
            )

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

                features = [
                    path_features(
                        p,
                        edges,
                        blocked_nodes,
                        reputation,
                        behavior,
                        active_distrust_count,
                        calibration,
                    )
                    for p in paths
                ]
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
                            "weight_interaction": calibration.weight_interaction,
                            "weight_success": calibration.weight_success,
                            "weight_recency": calibration.weight_recency,
                            "tau_days": calibration.tau_days,
                            "n_ref_interactions": calibration.n_ref_interactions,
                            "n_ref_percentile": calibration.n_ref_percentile,
                            "hop_alpha": calibration.hop_alpha,
                            "lambda_rho": calibration.lambda_rho,
                            "beta_risk": calibration.beta_risk,
                            **sim,
                        }
                    )
                    run_id += 1

    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)
    pd.DataFrame(calibration_rows).to_csv(calibration_output_path, index=False)

    # Quick console summary
    summary = (
        df.groupby("variant_id")[["intro_accepted", "intro_completed", "top_path_score", "discovery_latency_ms"]]
        .mean()
        .reset_index()
    )

    print(f"Generated {len(df):,} trial rows -> {output_path}")
    print(f"Saved trust hyperparameter calibration -> {calibration_output_path}")
    print("\nVariant means:")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
