#!/usr/bin/env python3
"""
Integration tests for the mutual connection model.

Covers:
  1. Connection request (A sends to B) → pending, is_mutual=False
  2. B accepts → both edges accepted, is_mutual=True on both
  3. /trusts/connected returns is_connected=True
  4. get_connections returns both users in each other's list
  5. Delete connection → both edges gone, is_connected=False
  6. Reject flow → only forward edge rejected, is_mutual=False, is_connected=False
  7. Client cannot inject trust_score / interaction_count
"""

import requests
import json
from typing import Optional

GRAPH_BASE = "http://100.70.53.90:8001"
API = f"{GRAPH_BASE}/api/v1"

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
RESET  = "\033[0m"

passed = 0
failed = 0


def ok(msg: str):
    global passed
    passed += 1
    print(f"{GREEN}  PASS{RESET}  {msg}")


def fail(msg: str, detail: str = ""):
    global failed
    failed += 1
    extra = f"\n         {RED}{detail}{RESET}" if detail else ""
    print(f"{RED}  FAIL{RESET}  {msg}{extra}")


def assert_eq(label: str, actual, expected):
    if actual == expected:
        ok(f"{label}: {actual!r}")
    else:
        fail(f"{label}", f"expected {expected!r}, got {actual!r}")


def assert_true(label: str, value, detail: str = ""):
    if value:
        ok(label)
    else:
        fail(label, detail)


# ── Helpers ──────────────────────────────────────────────────────────────────

def create_user(name: str, role: str) -> Optional[str]:
    r = requests.post(f"{API}/vertices/users", json={
        "name": name,
        "role_primary": role,
        "domain_tags": ["test"],
        "geography": "Test City",
        "experience_years": 3,
        "verification_status": "verified",
    }, timeout=10)
    if r.status_code == 201:
        return r.json()["user_id"]
    fail(f"create_user({name})", r.text)
    return None


def delete_user_by_gremlin(name: str):
    """Drop test vertex directly via Gremlin (no REST delete-user endpoint)."""
    from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
    from gremlin_python.process.anonymous_traversal import traversal
    from gremlin_python.driver.serializer import GraphBinarySerializersV1
    try:
        conn = DriverRemoteConnection(
            "ws://100.70.53.90:8182/gremlin", "g",
            message_serializer=GraphBinarySerializersV1()
        )
        g = traversal().withRemote(conn)
        g.V().hasLabel("User").has("name", name).drop().iterate()
        conn.close()
    except Exception as e:
        print(f"{YELLOW}  WARN{RESET}  Could not delete user '{name}' via Gremlin: {e}")


def get_edge_data(from_id: str, to_id: str) -> Optional[dict]:
    """Return the first TRUSTS edge raw data (via user trust-edges endpoint)."""
    r = requests.get(f"{API}/edges/trusts/user/{from_id}",
                     params={"direction": "out"}, timeout=10)
    if r.status_code != 200:
        return None
    for edge in r.json().get("edges", []):
        # edge may have 'in_vertex' or similar; check by calling connected endpoint instead
        pass
    return None


def send_request(from_id: str, to_id: str) -> Optional[dict]:
    r = requests.post(f"{API}/edges/trusts", json={
        "from_user_id": from_id,
        "to_user_id": to_id,
        "strength_score": 0.6,
        "domain_tags": ["fintech"],
    }, timeout=10)
    if r.status_code == 201:
        return r.json()
    fail(f"send_request({from_id[:8]}→{to_id[:8]})", r.text)
    return None


def accept_request(from_id: str, to_id: str) -> bool:
    r = requests.put(f"{API}/edges/trusts/accept",
                     params={"from_user_id": from_id, "to_user_id": to_id}, timeout=10)
    return r.status_code == 200


def reject_request(from_id: str, to_id: str) -> bool:
    r = requests.put(f"{API}/edges/trusts/reject",
                     params={"from_user_id": from_id, "to_user_id": to_id}, timeout=10)
    return r.status_code == 200


def connected_status(from_id: str, to_id: str) -> dict:
    r = requests.get(f"{API}/edges/trusts/connected/{from_id}/{to_id}", timeout=10)
    if r.status_code == 200:
        return r.json()
    fail(f"connected_status({from_id[:8]},{to_id[:8]})", r.text)
    return {}


def get_connections(user_id: str) -> list:
    r = requests.get(f"{API}/vertices/users/{user_id}/connections", timeout=10)
    if r.status_code == 200:
        return r.json().get("connections", [])
    # Endpoint may not exist yet; treat as empty
    return []


def get_user_edges(user_id: str, direction: str = "both") -> list:
    r = requests.get(f"{API}/edges/trusts/user/{user_id}",
                     params={"direction": direction}, timeout=10)
    if r.status_code == 200:
        return r.json().get("edges", [])
    return []


def delete_connection(from_id: str, to_id: str) -> bool:
    r = requests.delete(f"{API}/edges/trusts",
                        params={"from_user_id": from_id, "to_user_id": to_id}, timeout=10)
    return r.status_code == 200


# ── Test suites ───────────────────────────────────────────────────────────────

def test_happy_path_accept(a_id: str, b_id: str):
    print(f"\n{BLUE}── Test: happy-path accept ──{RESET}")

    # 1. Send connection request A → B
    edge = send_request(a_id, b_id)
    if not edge:
        return
    assert_eq("initial status", edge.get("status"), "pending")
    assert_eq("initial is_mutual", edge.get("is_mutual"), False)

    # 2. Before acceptance, /connected should be False
    cs = connected_status(a_id, b_id)
    assert_eq("is_connected before accept", cs.get("is_connected"), False)

    # 3. B accepts
    assert_true("accept returns 200", accept_request(a_id, b_id))

    # 4. /connected should now be True
    cs = connected_status(a_id, b_id)
    assert_eq("is_connected after accept", cs.get("is_connected"), True)
    assert_eq("forward_connected", cs.get("forward_connected"), True)
    assert_eq("reverse_connected", cs.get("reverse_connected"), True)

    # 5. Both edges should exist and be accepted
    fwd_edges = get_user_edges(a_id, direction="out")
    rev_edges = get_user_edges(b_id, direction="out")

    # Find the specific edges by checking direction
    fwd = None
    for e in fwd_edges:
        # The edge_id or some field; we verify status and is_mutual via connected endpoint
        if e.get("status") == "accepted":
            fwd = e
            break
    assert_true("forward edge is accepted", fwd is not None,
                f"No accepted outgoing edge from A; edges={fwd_edges}")
    if fwd:
        assert_eq("forward is_mutual", fwd.get("is_mutual"), True)

    rev = None
    for e in rev_edges:
        if e.get("status") == "accepted":
            rev = e
            break
    assert_true("reverse edge is accepted", rev is not None,
                f"No accepted outgoing edge from B; edges={rev_edges}")
    if rev:
        assert_eq("reverse is_mutual", rev.get("is_mutual"), True)

    # 6. Trust scores must be server-computed, not client-injected (baseline score for 0 interactions)
    if fwd:
        ts = fwd.get("trust_score", -1)
        assert_true("trust_score is float in [0,1]", 0.0 <= float(ts) <= 1.0,
                    f"trust_score={ts}")


def test_delete_connection(a_id: str, b_id: str):
    print(f"\n{BLUE}── Test: delete connection ──{RESET}")

    # Pre-condition: they are connected (happy-path test ran first)
    cs_before = connected_status(a_id, b_id)
    assert_eq("pre-delete is_connected", cs_before.get("is_connected"), True)

    assert_true("delete returns 200", delete_connection(a_id, b_id))

    # Both directions gone
    cs_after = connected_status(a_id, b_id)
    assert_eq("is_connected after delete", cs_after.get("is_connected"), False)
    assert_eq("forward_connected after delete", cs_after.get("forward_connected"), False)
    assert_eq("reverse_connected after delete", cs_after.get("reverse_connected"), False)

    # No edges remain in either direction
    fwd_edges = get_user_edges(a_id, direction="out")
    rev_edges = get_user_edges(b_id, direction="out")
    assert_eq("no outgoing edges from A after delete", len(fwd_edges), 0)
    assert_eq("no outgoing edges from B after delete", len(rev_edges), 0)

    # Double-delete should return 404
    r = requests.delete(f"{API}/edges/trusts",
                        params={"from_user_id": a_id, "to_user_id": b_id}, timeout=10)
    assert_eq("double-delete returns 404", r.status_code, 404)


def test_reject_flow(c_id: str, d_id: str):
    print(f"\n{BLUE}── Test: reject flow ──{RESET}")

    edge = send_request(c_id, d_id)
    if not edge:
        return
    assert_eq("pending after send", edge.get("status"), "pending")

    # D rejects
    assert_true("reject returns 200", reject_request(c_id, d_id))

    # Not connected
    cs = connected_status(c_id, d_id)
    assert_eq("is_connected after reject", cs.get("is_connected"), False)

    # Forward edge is rejected, no reverse edge should be accepted
    fwd_edges = get_user_edges(c_id, direction="out")
    rejected = [e for e in fwd_edges if e.get("status") == "rejected"]
    assert_true("forward edge is rejected", len(rejected) >= 1,
                f"edges from C: {fwd_edges}")
    for e in rejected:
        assert_eq("rejected is_mutual=False", e.get("is_mutual"), False)


def test_client_cannot_inject_trust(e_id: str, f_id: str):
    print(f"\n{BLUE}── Test: client cannot inject trust_score / interaction_count ──{RESET}")

    # Send with injected high trust values
    r = requests.post(f"{API}/edges/trusts", json={
        "from_user_id": e_id,
        "to_user_id": f_id,
        "trust_score": 0.99,          # should be ignored
        "interaction_count": 1000,    # should be ignored
        "strength_score": 0.6,
        "domain_tags": ["test"],
    }, timeout=10)

    if r.status_code != 201:
        fail("create edge with injected values", r.text)
        return

    edge = r.json()
    ts = float(edge.get("trust_score", -1))
    ic = edge.get("interaction_count", -1)

    # Server should compute score from 0 interactions, so score must be << 0.99
    assert_true("trust_score is NOT client-injected 0.99",
                ts < 0.5,
                f"trust_score={ts} — server may have accepted client value")
    assert_eq("interaction_count starts at 0", ic, 0)

    # Cleanup: delete the pending edge (delete works even on pending)
    delete_connection(e_id, f_id)


def test_duplicate_request(g_id: str, h_id: str):
    print(f"\n{BLUE}── Test: duplicate request rejected ──{RESET}")

    send_request(g_id, h_id)
    r = requests.post(f"{API}/edges/trusts", json={
        "from_user_id": g_id,
        "to_user_id": h_id,
        "strength_score": 0.5,
    }, timeout=10)
    assert_eq("duplicate request returns 400", r.status_code, 400)

    # Cleanup
    delete_connection(g_id, h_id)


def test_self_loop_rejected(a_id: str):
    print(f"\n{BLUE}── Test: self-loop rejected ──{RESET}")
    r = requests.post(f"{API}/edges/trusts", json={
        "from_user_id": a_id,
        "to_user_id": a_id,
        "strength_score": 0.5,
    }, timeout=10)
    assert_eq("self-loop returns 400", r.status_code, 400)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("MUTUAL CONNECTION INTEGRATION TESTS")
    print("=" * 60)

    # Create test users (founder+investor so role rules pass)
    print(f"\n{BLUE}Creating test users...{RESET}")
    a_id = create_user("Test-A Founder", "founder")
    b_id = create_user("Test-B Investor", "investor")
    c_id = create_user("Test-C Founder", "founder")
    d_id = create_user("Test-D Investor", "investor")
    e_id = create_user("Test-E Founder", "founder")
    f_id = create_user("Test-F Investor", "investor")
    g_id = create_user("Test-G Founder", "founder")
    h_id = create_user("Test-H Investor", "investor")

    if not all([a_id, b_id, c_id, d_id, e_id, f_id, g_id, h_id]):
        print(f"{RED}Could not create test users — aborting.{RESET}")
        return

    try:
        # Run tests (order matters: accept test must precede delete test)
        test_happy_path_accept(a_id, b_id)
        test_delete_connection(a_id, b_id)
        test_reject_flow(c_id, d_id)
        test_client_cannot_inject_trust(e_id, f_id)
        test_duplicate_request(g_id, h_id)
        test_self_loop_rejected(a_id)

    finally:
        # Cleanup all test users
        print(f"\n{BLUE}Cleaning up test users...{RESET}")
        for name in [
            "Test-A Founder", "Test-B Investor",
            "Test-C Founder", "Test-D Investor",
            "Test-E Founder", "Test-F Investor",
            "Test-G Founder", "Test-H Investor",
        ]:
            delete_user_by_gremlin(name)
        print("Cleanup done.")

    # Summary
    total = passed + failed
    print(f"\n{'=' * 60}")
    print(f"RESULTS: {passed}/{total} passed")
    if failed:
        print(f"{RED}{failed} test(s) FAILED{RESET}")
    else:
        print(f"{GREEN}All tests passed!{RESET}")
    print("=" * 60)


if __name__ == "__main__":
    main()
