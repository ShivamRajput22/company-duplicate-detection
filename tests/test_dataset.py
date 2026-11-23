import pytest
from database.database import SessionLocal
from database.models import Entity, GroundTruth
from database.seed_database import generate_synthetic_dataset

def test_generate_synthetic_dataset_exact_counts():
    entities, ground_truth = generate_synthetic_dataset(seed=42, total_rows=10000, duplicate_groups_count=200)

    # Invariant: exactly 10,000 entities
    assert len(entities) == 10000

    # Invariant: all entity_ids are unique from 1 to 10000
    ids = [e["entity_id"] for e in entities]
    assert len(ids) == len(set(ids))
    assert min(ids) == 1
    assert max(ids) == 10000

    # Invariant: exactly 200 duplicate groups
    # Group truth positive pairs
    dup_pairs = [gt for gt in ground_truth if gt["is_duplicate"]]
    # Build connected components to count groups
    adj = {}
    for p in dup_pairs:
        a, b = p["entity_id_a"], p["entity_id_b"]
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)

    visited = set()
    group_count = 0
    for node in adj:
        if node not in visited:
            group_count += 1
            queue = [node]
            visited.add(node)
            while queue:
                curr = queue.pop(0)
                for neighbor in adj.get(curr, set()):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

    assert group_count == 200, f"Expected 200 duplicate groups, found {group_count}"

    # Verify each group has >= 2 records
    assert len(visited) >= 400

def test_database_seeded_counts():
    session = SessionLocal()
    try:
        count = session.query(Entity).count()
        assert count == 10000, f"Expected 10,000 entities in database, found {count}"

        gt_count = session.query(GroundTruth).count()
        assert gt_count > 0, "Expected ground truth records in database"
    finally:
        session.close()

def test_dataset_determinism():
    e1, gt1 = generate_synthetic_dataset(seed=42, total_rows=100, duplicate_groups_count=5)
    e2, gt2 = generate_synthetic_dataset(seed=42, total_rows=100, duplicate_groups_count=5)
    assert e1 == e2
    assert gt1 == gt2
