#!/usr/bin/env python3
"""Verify seeded data in JanusGraph - shows trust scores and data counts"""

import sys
import argparse
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __
from gremlin_python.driver.serializer import GraphBinarySerializersV1

# Force UTF-8 output on Windows so print() works with special chars
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DEFAULT_URL = 'ws://100.70.53.90:8182/gremlin'


def _v(val, default):
    """
    Safe property extractor for Gremlin valueMap results.
    GraphBinarySerializersV1 returns plain scalars  : val = 0.75
    GraphSON / older drivers return list-wrapped    : val = [0.75]
    This handles both so the script works regardless of serializer.
    """
    if val is None:
        return default
    if isinstance(val, list):
        return val[0] if val else default
    return val


def verify_data(janusgraph_url: str = DEFAULT_URL):
    """Connect to JanusGraph and verify data + trust scores"""
    print(f"[*] Connecting to JanusGraph at {janusgraph_url}...")

    connection = DriverRemoteConnection(
        janusgraph_url,
        'g',
        message_serializer=GraphBinarySerializersV1()
    )
    g = traversal().withRemote(connection)

    try:
        # ── VERTEX COUNTS ─────────────────────────────────────────────────────
        print("\n===== VERTEX COUNTS =====")
        total_vertices = g.V().count().next()
        user_count     = g.V().hasLabel('User').count().next()
        startup_count  = g.V().hasLabel('Startup').count().next()
        print(f"Total vertices : {total_vertices}")
        print(f"  Users        : {user_count}")
        print(f"  Startups     : {startup_count}")

        # ── EDGE COUNTS ───────────────────────────────────────────────────────
        print("\n===== EDGE COUNTS =====")
        total_edges    = g.E().count().next()
        trusts_count   = g.E().hasLabel('TRUSTS').count().next()
        founded_count  = g.E().hasLabel('FOUNDED').count().next()
        invested_count = g.E().hasLabel('INVESTED_IN').count().next()
        print(f"Total edges    : {total_edges}")
        print(f"  TRUSTS       : {trusts_count}")
        print(f"  FOUNDED      : {founded_count}")
        print(f"  INVESTED_IN  : {invested_count}")

        # ── TRUST SCORES ──────────────────────────────────────────────────────
        print("\n===== TRUST SCORES (all TRUSTS edges) =====")

        if trusts_count == 0:
            print("  (no TRUSTS edges found)")
        else:
            # Also build user_id -> name map
            all_users = g.V().hasLabel('User').valueMap('user_id', 'name').toList()
            id_to_name = {}
            for u in all_users:
                uid  = _v(u.get('user_id'), None)
                name = _v(u.get('name'), '?')
                if uid:
                    id_to_name[str(uid)] = name

            # Get from/to vertex user_ids for each edge
            trust_edges = []
            raw_edges_full = (
                g.E().hasLabel('TRUSTS')
                 .project('from_uid', 'to_uid', 'props')
                 .by(__.outV().values('user_id'))
                 .by(__.inV().values('user_id'))
                 .by(__.valueMap())
                 .toList()
            )
            for e in raw_edges_full:
                props       = e.get('props', {})
                trust_score = float(_v(props.get('trust_score'), 0.0))
                int_count   = int(_v(props.get('interaction_count'), 0))
                intros      = int(_v(props.get('successful_intros'), 0))
                from_uid    = str(e['from_uid'])
                to_uid      = str(e['to_uid'])
                trust_edges.append({
                    'from': id_to_name.get(from_uid, from_uid),
                    'to':   id_to_name.get(to_uid, to_uid),
                    'score': trust_score,
                    'interactions': int_count,
                    'intros': intros,
                })

            trust_edges.sort(key=lambda x: x['score'], reverse=True)

            bar_width = 20
            print(f"  {'FROM':<20} {'TO':<20}  {'SCORE':>6}  {'BAR':<22}  DETAILS")
            print("  " + "-" * 78)
            for e in trust_edges:
                filled = int(e['score'] * bar_width)
                bar    = '#' * filled + '-' * (bar_width - filled)
                print(f"  {e['from']:<20} {e['to']:<20}  {e['score']:>6.4f}  |{bar}|"
                      f"  (i={e['interactions']}, intros={e['intros']})")

            scores  = [e['score'] for e in trust_edges]
            nonzero = sum(1 for s in scores if s > 0)
            print(f"\n  Total edges  : {len(scores)}")
            print(f"  Non-zero     : {nonzero}/{len(scores)}")
            print(f"  Average score: {sum(scores)/len(scores):.4f}")
            print(f"  Min / Max    : {min(scores):.4f} / {max(scores):.4f}")

        # ── USER REPUTATION SCORES ────────────────────────────────────────────
        print("\n===== USER REPUTATION SCORES =====")
        rep_data = g.V().hasLabel('User').valueMap('name', 'reputation_score').toList()
        rep_data.sort(key=lambda u: float(_v(u.get('reputation_score'), 0.0)), reverse=True)
        for u in rep_data:
            name = _v(u.get('name'), '?')
            rep  = float(_v(u.get('reputation_score'), 0.0))
            filled = int(rep * 20)
            bar = '#' * filled + '-' * (20 - filled)
            print(f"  {name:<22} {rep:.4f}  |{bar}|")

        # ── VALIDATION ────────────────────────────────────────────────────────
        print("\n===== VALIDATION =====")
        expected = {'vertices': 14, 'users': 10, 'startups': 4,
                    'edges': 19, 'trusts': 12, 'founded': 4, 'invested': 3}
        actual   = {'vertices': total_vertices, 'users': user_count, 'startups': startup_count,
                    'edges': total_edges, 'trusts': trusts_count, 'founded': founded_count,
                    'invested': invested_count}

        if all(actual[k] == expected[k] for k in expected):
            print("[OK] All counts match expected values!")
        else:
            print("[WARN] Count mismatches:")
            for k in expected:
                status = "OK  " if actual[k] == expected[k] else "FAIL"
                print(f"  [{status}] {k}: expected {expected[k]}, got {actual[k]}")

    finally:
        connection.close()
        print("\n[*] Connection closed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify seeded JanusGraph data and trust scores")
    parser.add_argument("--url", default=DEFAULT_URL,
                        help=f"JanusGraph Gremlin URL (default: {DEFAULT_URL})")
    args = parser.parse_args()
    verify_data(args.url)
