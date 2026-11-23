import argparse
import random
import sys
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Set
from sqlalchemy.orm import Session
from database.database import SessionLocal, engine
from database.models import Base, Entity, GroundTruth
from app.services.normalization_service import normalization_service

# Words for realistic company generation
FIRST_NAMES = [
    "Apex", "Beacon", "Crest", "Delta", "Echo", "Falcon", "Genesis", "Horizon",
    "Ironwood", "Jupiter", "Keystone", "Lighthouse", "Monarch", "Nexus", "Omega",
    "Pinnacle", "Quantum", "Radiant", "Summit", "Titan", "Unity", "Vanguard",
    "Westbridge", "Zenith", "Sterling", "Paramount", "Silverline", "Trident",
    "Cascade", "Meridian", "Solstice", "Timberline", "Clearwater", "Northstar",
    "Frontier", "Cobalt", "Harbor", "Atlas", "Catalyst", "Evergreen", "Redwood",
    "Trimark", "Venture", "Bluestone", "Starlight", "Oasis", "Terra", "Matrix"
]

BUSINESS_DOMAINS = [
    "Property Group", "Properties", "Petroleum Group", "Holdings", "Technologies",
    "Solutions", "Capital", "Partners", "Management", "Logistics", "Enterprises",
    "Industries", "Consulting", "Systems", "Healthcare", "Financial", "Energy",
    "BioTech", "Media", "Aerospace", "Robotics", "Analytics", "Communications"
]

LEGAL_SUFFIXES_LIST = [
    "LLC", "Inc.", "Corporation", "Ltd.", "Co.", "Limited", "L.P.", "P.L.L.C.", "GmbH"
]

DETERMINISTIC_TIMESTAMP = "2026-11-23T00:00:00+00:00"

def utcnow_str():
    return DETERMINISTIC_TIMESTAMP

def generate_synthetic_dataset(
    seed: int = 42,
    total_rows: int = 10000,
    duplicate_groups_count: int = 200
) -> Tuple[List[Dict], List[Dict]]:
    """
    Generates EXACTLY total_rows synthetic company records with EXACTLY duplicate_groups_count
    intentional duplicate groups.
    Returns:
    - entities: list of entity dicts
    - ground_truth_pairs: list of ground truth pair dicts
    """
    rng = random.Random(seed)

    entities = []
    ground_truth_pairs = []

    # Calculate distribution of duplicate groups:
    # 180 groups with 2 members = 360 entities
    # 15 groups with 3 members  = 45 entities
    # 5 groups with 4 members   = 20 entities
    # Total duplicate entities = 425 entities across 200 groups.
    group_sizes = [2] * (duplicate_groups_count - 20) + [3] * 15 + [4] * 5
    rng.shuffle(group_sizes)

    total_dup_entities = sum(group_sizes)
    singleton_count = total_rows - total_dup_entities
    if singleton_count < 0:
        raise ValueError("Duplicate groups exceed total requested rows.")

    entity_id_counter = 1

    # 1. Create the 200 Intentional Duplicate Groups (DS-01 to DS-20 controlled scenarios)
    for group_idx, size in enumerate(group_sizes):
        scenario_type = group_idx % 20 # Distribute across 20 scenarios
        base_first = rng.choice(FIRST_NAMES)
        base_industry = rng.choice(BUSINESS_DOMAINS)
        slug_base = f"{base_first.lower()}-{base_industry.lower().replace(' ', '-')}"

        base_domain = f"{slug_base}.example"
        base_linkedin = f"https://www.linkedin.com/company/{slug_base}"

        group_entity_ids = []

        for member_idx in range(size):
            ent_id = entity_id_counter
            entity_id_counter += 1
            group_entity_ids.append(ent_id)

            # Apply scenario variations
            suffix = rng.choice(LEGAL_SUFFIXES_LIST)
            company_name = f"{base_first} {base_industry}"
            legal_name = f"{base_first} {base_industry} {suffix}"
            domain = base_domain
            linkedin = base_linkedin

            if scenario_type == 0:
                # DS-01: Exact names & identifiers
                pass
            elif scenario_type == 1:
                # DS-02: Legal suffix variants
                legal_name = f"{base_first} {base_industry} {LEGAL_SUFFIXES_LIST[member_idx % len(LEGAL_SUFFIXES_LIST)]}"
            elif scenario_type == 2:
                # DS-03: Casing & whitespace changes
                if member_idx > 0:
                    company_name = company_name.upper() if member_idx == 1 else company_name.lower()
                    legal_name = f"  {legal_name.upper()}  "
            elif scenario_type == 3:
                # DS-04: Minor typo in company name
                if member_idx > 0:
                    company_name = company_name[:-1] + "x"
            elif scenario_type == 4:
                # DS-05: Website URL formatting variants (http vs https vs www vs query params)
                if member_idx == 1:
                    domain = f"http://www.{base_domain}/"
                elif member_idx > 1:
                    domain = f"https://{base_domain}/about?ref=share"
            elif scenario_type == 5:
                # DS-06: LinkedIn URL variants
                if member_idx == 1:
                    linkedin = f"http://linkedin.com/company/{slug_base}/?trk=profile"
                elif member_idx > 1:
                    linkedin = f"https://www.linkedin.com/company/{slug_base}/"
            elif scenario_type == 6:
                # DS-07: Both identifiers missing / blank; legal name match >= 80% (Fuzzy fallback scenario)
                domain = None
                linkedin = None
                if member_idx > 0:
                    legal_name = f"{base_first} {base_industry} Solutions {suffix}" # High name similarity
            elif scenario_type == 7:
                # DS-08: Website-only match; LinkedIn missing on one side
                if member_idx == 1:
                    linkedin = None
            elif scenario_type == 8:
                # DS-09: LinkedIn-only match; Website missing on one side
                if member_idx == 1:
                    domain = None
            elif scenario_type == 9:
                # DS-10: Domain match, LinkedIn conflict (Needs Review scenario)
                if member_idx > 0:
                    linkedin = f"https://www.linkedin.com/company/{slug_base}-alt-{member_idx}"
            elif scenario_type == 10:
                # DS-11: LinkedIn match, Domain conflict (Needs Review scenario)
                if member_idx > 0:
                    domain = f"{slug_base}-alt-{member_idx}.example"
            elif scenario_type == 11:
                # DS-12: Both identifiers absent on one side, populated on other (DEC-01 provisional test)
                if member_idx == 0:
                    domain = None
                    linkedin = None
            elif scenario_type == 12:
                # DS-13: Multiple entities in group (group size 3 or 4)
                pass
            elif scenario_type == 13:
                # DS-14: Word reordering
                tokens = company_name.split()
                if len(tokens) >= 2 and member_idx > 0:
                    company_name = f"{tokens[1]} {tokens[0]}"
            elif scenario_type == 14:
                # DS-15: Malformed website URL retained raw
                if member_idx > 0:
                    domain = "invalid-url-no-domain"
            elif scenario_type == 15:
                # DS-16: Malformed LinkedIn URL (personal profile /in/)
                if member_idx > 0:
                    linkedin = f"https://www.linkedin.com/in/{slug_base}-founder"
            else:
                # Standard realistic duplicate variant
                if member_idx > 0:
                    legal_name = f"{base_first} {base_industry} {rng.choice(LEGAL_SUFFIXES_LIST)}"

            norm_comp = normalization_service.normalize_name(company_name)
            norm_leg = normalization_service.normalize_name(legal_name)
            norm_dom, _ = normalization_service.normalize_domain(domain)
            norm_li, _ = normalization_service.normalize_linkedin(linkedin)

            entities.append({
                "entity_id": ent_id,
                "company_name": company_name,
                "legal_name": legal_name,
                "web_domain": domain,
                "linkedin_url": linkedin,
                "normalized_company_name": norm_comp,
                "normalized_legal_name": norm_leg,
                "normalized_domain": norm_dom,
                "normalized_linkedin": norm_li,
                "normalization_version": "v1",
                "created_at": utcnow_str()
            })

        # Record all ground truth positive duplicate pairs for this group
        partition = "test" if group_idx < 140 else ("dev" if group_idx < 170 else "train")
        for i in range(len(group_entity_ids)):
            for j in range(i + 1, len(group_entity_ids)):
                id_a = min(group_entity_ids[i], group_entity_ids[j])
                id_b = max(group_entity_ids[i], group_entity_ids[j])
                ground_truth_pairs.append({
                    "entity_id_a": id_a,
                    "entity_id_b": id_b,
                    "is_duplicate": True,
                    "relationship_type": "same_entity",
                    "scenario_id": f"DS-{scenario_type+1:02d}",
                    "label_source": "synthetic_generator",
                    "dataset_partition": partition
                })

    # 2. Add Hard Negatives (Trimark look-alikes across industries, shared corporate domains)
    # These are intentional singletons that have deceptive similarities but are NOT duplicates
    hard_negative_scenarios = [
        # Trimark Property Group vs Trimark Petroleum Group
        ("Trimark", "Property Group", "trimark-property.example", "linkedin.com/company/trimark-property"),
        ("Trimark", "Petroleum Group", "trimark-petroleum.example", "linkedin.com/company/trimark-petroleum"),
        ("Westbridge", "Capital Management", "westbridge-capital.example", "linkedin.com/company/westbridge-capital"),
        ("Westbridge", "Logistics Solutions", "westbridge-logistics.example", "linkedin.com/company/westbridge-logistics"),
        ("Horizon", "Healthcare Systems", "horizon-health.example", "linkedin.com/company/horizon-health"),
        ("Horizon", "Aerospace Technologies", "horizon-aero.example", "linkedin.com/company/horizon-aero"),
    ]

    hard_negative_ids = []
    for fn, ind, dom, li in hard_negative_scenarios:
        ent_id = entity_id_counter
        entity_id_counter += 1
        hard_negative_ids.append(ent_id)
        comp_name = f"{fn} {ind}"
        leg_name = f"{fn} {ind} LLC"
        norm_comp = normalization_service.normalize_name(comp_name)
        norm_leg = normalization_service.normalize_name(leg_name)
        norm_dom, _ = normalization_service.normalize_domain(dom)
        norm_li, _ = normalization_service.normalize_linkedin(li)

        entities.append({
            "entity_id": ent_id,
            "company_name": comp_name,
            "legal_name": leg_name,
            "web_domain": dom,
            "linkedin_url": li,
            "normalized_company_name": norm_comp,
            "normalized_legal_name": norm_leg,
            "normalized_domain": norm_dom,
            "normalized_linkedin": norm_li,
            "normalization_version": "v1",
            "created_at": utcnow_str()
        })

    # Record hard negative ground truth pairs (is_duplicate = False)
    ground_truth_pairs.append({
        "entity_id_a": min(hard_negative_ids[0], hard_negative_ids[1]),
        "entity_id_b": max(hard_negative_ids[0], hard_negative_ids[1]),
        "is_duplicate": False,
        "relationship_type": "unrelated",
        "scenario_id": "DS-17_TRIMARK_HARD_NEGATIVE",
        "label_source": "synthetic_generator",
        "dataset_partition": "test"
    })
    ground_truth_pairs.append({
        "entity_id_a": min(hard_negative_ids[2], hard_negative_ids[3]),
        "entity_id_b": max(hard_negative_ids[2], hard_negative_ids[3]),
        "is_duplicate": False,
        "relationship_type": "unrelated",
        "scenario_id": "DS-17_WESTBRIDGE_HARD_NEGATIVE",
        "label_source": "synthetic_generator",
        "dataset_partition": "test"
    })

    # 3. Fill the rest of the 10,000 entities with distinct singletons
    remaining_count = total_rows - len(entities)
    for i in range(remaining_count):
        ent_id = entity_id_counter
        entity_id_counter += 1

        first = rng.choice(FIRST_NAMES)
        ind = rng.choice(BUSINESS_DOMAINS)
        num_suffix = f" {ent_id}" if i > 500 else ""
        comp_name = f"{first} {ind}{num_suffix}"
        suffix = rng.choice(LEGAL_SUFFIXES_LIST)
        leg_name = f"{comp_name} {suffix}"
        slug = f"{first.lower()}-{ind.lower().replace(' ', '-')}-{ent_id}"
        dom = f"{slug}.example"
        li = f"https://www.linkedin.com/company/{slug}"

        # 5% have missing domain, 5% have missing linkedin
        if rng.random() < 0.05:
            dom = None
        if rng.random() < 0.05:
            li = None

        norm_comp = normalization_service.normalize_name(comp_name)
        norm_leg = normalization_service.normalize_name(leg_name)
        norm_dom, _ = normalization_service.normalize_domain(dom)
        norm_li, _ = normalization_service.normalize_linkedin(li)

        entities.append({
            "entity_id": ent_id,
            "company_name": comp_name,
            "legal_name": leg_name,
            "web_domain": dom,
            "linkedin_url": li,
            "normalized_company_name": norm_comp,
            "normalized_legal_name": norm_leg,
            "normalized_domain": norm_dom,
            "normalized_linkedin": norm_li,
            "normalization_version": "v1",
            "created_at": utcnow_str()
        })

    assert len(entities) == total_rows, f"Expected {total_rows} entities, got {len(entities)}"
    return entities, ground_truth_pairs

def seed_db(
    reset: bool = False,
    seed: int = 42,
    rows: int = 10000,
    duplicate_groups: int = 200
):
    session: Session = SessionLocal()
    try:
        existing_count = session.query(Entity).count()
        if existing_count > 0:
            if not reset:
                print(f"[SEED] Database already contains {existing_count} entities. Pass --reset to re-seed. Aborting.")
                return
            print(f"[SEED] --reset flag passed. Clearing existing data...")
            session.query(GroundTruth).delete()
            session.query(Entity).delete()
            session.commit()

        print(f"[SEED] Generating synthetic dataset: {rows} rows, {duplicate_groups} duplicate groups, seed={seed}...")
        entities_data, gt_data = generate_synthetic_dataset(
            seed=seed,
            total_rows=rows,
            duplicate_groups_count=duplicate_groups
        )

        print(f"[SEED] Inserting {len(entities_data)} entities in batches...")
        batch_size = 1000
        for i in range(0, len(entities_data), batch_size):
            batch = [Entity(**data) for data in entities_data[i:i + batch_size]]
            session.bulk_save_objects(batch)
            session.commit()

        print(f"[SEED] Inserting {len(gt_data)} ground truth pairs...")
        for i in range(0, len(gt_data), batch_size):
            batch = [GroundTruth(**data) for data in gt_data[i:i + batch_size]]
            session.bulk_save_objects(batch)
            session.commit()

        final_count = session.query(Entity).count()
        gt_count = session.query(GroundTruth).count()
        print(f"[SEED SUCCESS] Verified {final_count} entities and {gt_count} ground truth pairs in database.")
    except Exception as e:
        session.rollback()
        print(f"[SEED ERROR] Failed to seed database: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deterministic Company Master Database Seeder")
    parser.add_argument("--reset", action="store_true", help="Reset existing database data before seeding")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--rows", type=int, default=10000, help="Total synthetic master rows (default 10,000)")
    parser.add_argument("--duplicate-groups", type=int, default=200, help="Exact number of intentional duplicate groups (default 200)")

    args = parser.parse_args()
    seed_db(reset=args.reset, seed=args.seed, rows=args.rows, duplicate_groups=args.duplicate_groups)
