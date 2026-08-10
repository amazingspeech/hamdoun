"""Shared structural checks for the Tessar content-brief workflow JSON."""
import json


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def assert_node(wf, name, node_type):
    matches = [n for n in wf["nodes"] if n["name"] == name]
    assert matches, f"node '{name}' not found (have: {[n['name'] for n in wf['nodes']]})"
    assert matches[0]["type"] == node_type, (
        f"node '{name}' has type {matches[0]['type']!r}, expected {node_type!r}"
    )
    return matches[0]


def assert_connection(wf, source, target, conn_type="main", target_index=0):
    conns = wf["connections"].get(source, {}).get(conn_type, [])
    flat = [c for bucket in conns for c in bucket]
    matches = [c for c in flat if c["node"] == target and c["type"] == conn_type]
    assert matches, (
        f"no {conn_type!r} connection from '{source}' to '{target}' "
        f"(have: {[(c['node'], c['type']) for c in flat]})"
    )
    assert matches[0]["index"] == target_index, (
        f"connection '{source}' -> '{target}' has index {matches[0]['index']}, "
        f"expected {target_index}"
    )


def assert_full_chain(wf, node_names_in_order):
    """Every node in the list must be reachable from the trigger via `main` edges,
    and every node in the workflow must appear in node_names_in_order (no orphans)."""
    actual_names = {n["name"] for n in wf["nodes"]}
    expected_names = set(node_names_in_order)
    missing = expected_names - actual_names
    extra = actual_names - expected_names
    assert not missing, f"expected nodes missing from workflow: {missing}"
    assert not extra, f"workflow has nodes not accounted for: {extra}"
