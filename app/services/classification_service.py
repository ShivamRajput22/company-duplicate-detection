from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from app.services.matching_service import matching_service

@dataclass
class ClassificationResult:
    rule_id: str
    match_status: str  # high_confidence_candidate, potential_duplicate, needs_review, insufficient_data, not_a_match
    website_match_state: str  # MATCH, CONFLICT, UNAVAILABLE
    linkedin_match_state: str # MATCH, CONFLICT, UNAVAILABLE
    name_similarity_percent: Optional[float]
    match_methods: List[str]
    matched_fields: List[str]
    conflicting_fields: List[str]
    rationale: str
    discovery_type: str = "standard"  # standard, related_name

class ClassificationService:
    @classmethod
    def classify_pair(
        cls,
        upload_domain_norm: Optional[str],
        upload_linkedin_norm: Optional[str],
        upload_legal_name_norm: Optional[str],
        upload_company_name_norm: Optional[str],
        master_domain_norm: Optional[str],
        master_linkedin_norm: Optional[str],
        master_legal_name_norm: Optional[str],
        master_company_name_norm: Optional[str],
        fuzzy_threshold: float = 80.0,
        is_related_lead_discovery: bool = False
    ) -> ClassificationResult:
        """
        Authoritative evaluation matrix following Group 1 / BR-01 to BR-15.
        Priority:
        1. Any MATCH + CONFLICT -> Needs Review (BR-04, BR-05)
        2. Unconflicted MATCH -> High-confidence Duplicate Candidate (BR-01, BR-02, BR-03)
        3. CONFLICT + CONFLICT -> Not a Match (BR-06)
        4. CONFLICT + UNAVAILABLE or UNAVAILABLE + CONFLICT when master has >=1 usable identifiers -> Not a Match (BR-10, BR-11)
        5. UNAVAILABLE + UNAVAILABLE:
           - Master both unavailable (DEC-01):
             - Both legal names usable:
               - Sim >= threshold (default 80.0): Potential Duplicate (BR-07)
               - Sim < threshold: Not a Match (BR-08)
             - Either legal name unusable: Insufficient Data (BR-09)
           - Master has usable identifier(s) but upload lacks comparable:
             - Insufficient Data / insufficient comparable identifiers (BR-12)
        """
        web_state = matching_service.compare_identifier(upload_domain_norm, master_domain_norm)
        linkedin_state = matching_service.compare_identifier(upload_linkedin_norm, master_linkedin_norm)

        matched_fields = []
        conflicting_fields = []
        match_methods = []

        if web_state == "MATCH":
            matched_fields.append("web_domain")
            match_methods.append("website")
        elif web_state == "CONFLICT":
            conflicting_fields.append("web_domain")

        if linkedin_state == "MATCH":
            matched_fields.append("linkedin_url")
            match_methods.append("linkedin")
        elif linkedin_state == "CONFLICT":
            conflicting_fields.append("linkedin_url")

        master_both_unavailable = (master_domain_norm is None and master_linkedin_norm is None)

        # BR-01: MATCH + MATCH
        if web_state == "MATCH" and linkedin_state == "MATCH":
            return ClassificationResult(
                rule_id="BR-01",
                match_status="high_confidence_candidate",
                website_match_state=web_state,
                linkedin_match_state=linkedin_state,
                name_similarity_percent=None,
                match_methods=match_methods,
                matched_fields=matched_fields,
                conflicting_fields=conflicting_fields,
                rationale="Exact registered domain match and exact LinkedIn company URL match."
            )

        # BR-04: MATCH + CONFLICT
        if web_state == "MATCH" and linkedin_state == "CONFLICT":
            return ClassificationResult(
                rule_id="BR-04",
                match_status="needs_review",
                website_match_state=web_state,
                linkedin_match_state=linkedin_state,
                name_similarity_percent=None,
                match_methods=match_methods,
                matched_fields=matched_fields,
                conflicting_fields=conflicting_fields,
                rationale="Registered domain matches, but LinkedIn company URL conflicts. Requires human review."
            )

        # BR-05: CONFLICT + MATCH
        if web_state == "CONFLICT" and linkedin_state == "MATCH":
            return ClassificationResult(
                rule_id="BR-05",
                match_status="needs_review",
                website_match_state=web_state,
                linkedin_match_state=linkedin_state,
                name_similarity_percent=None,
                match_methods=match_methods,
                matched_fields=matched_fields,
                conflicting_fields=conflicting_fields,
                rationale="LinkedIn company URL matches, but registered domain conflicts. Requires human review."
            )

        # BR-02: MATCH + UNAVAILABLE
        if web_state == "MATCH" and linkedin_state == "UNAVAILABLE":
            return ClassificationResult(
                rule_id="BR-02",
                match_status="high_confidence_candidate",
                website_match_state=web_state,
                linkedin_match_state=linkedin_state,
                name_similarity_percent=None,
                match_methods=match_methods,
                matched_fields=matched_fields,
                conflicting_fields=conflicting_fields,
                rationale="Exact registered domain match; LinkedIn identifier unavailable on one or both records."
            )

        # BR-03: UNAVAILABLE + MATCH
        if web_state == "UNAVAILABLE" and linkedin_state == "MATCH":
            return ClassificationResult(
                rule_id="BR-03",
                match_status="high_confidence_candidate",
                website_match_state=web_state,
                linkedin_match_state=linkedin_state,
                name_similarity_percent=None,
                match_methods=match_methods,
                matched_fields=matched_fields,
                conflicting_fields=conflicting_fields,
                rationale="Exact LinkedIn company URL match; website domain unavailable on one or both records."
            )

        # BR-06: CONFLICT + CONFLICT
        if web_state == "CONFLICT" and linkedin_state == "CONFLICT":
            # Can be flagged as related-name lead if name is similar
            if is_related_lead_discovery:
                sim = matching_service.compute_legal_name_similarity(upload_legal_name_norm, master_legal_name_norm)
                return ClassificationResult(
                    rule_id="BR-06",
                    match_status="needs_review",
                    website_match_state=web_state,
                    linkedin_match_state=linkedin_state,
                    name_similarity_percent=sim,
                    match_methods=["related_name_lead"],
                    matched_fields=[],
                    conflicting_fields=conflicting_fields,
                    rationale="Both identifiers conflict. Discovered as potential look-alike lead for investigation.",
                    discovery_type="related_name"
                )
            return ClassificationResult(
                rule_id="BR-06",
                match_status="not_a_match",
                website_match_state=web_state,
                linkedin_match_state=linkedin_state,
                name_similarity_percent=None,
                match_methods=[],
                matched_fields=[],
                conflicting_fields=conflicting_fields,
                rationale="Both registered domain and LinkedIn company URL conflict. Not a match under identifier rules."
            )

        # BR-10: CONFLICT + UNAVAILABLE (master has >= 1 usable identifier)
        if web_state == "CONFLICT" and linkedin_state == "UNAVAILABLE":
            if is_related_lead_discovery:
                sim = matching_service.compute_legal_name_similarity(upload_legal_name_norm, master_legal_name_norm)
                return ClassificationResult(
                    rule_id="BR-10",
                    match_status="needs_review",
                    website_match_state=web_state,
                    linkedin_match_state=linkedin_state,
                    name_similarity_percent=sim,
                    match_methods=["related_name_lead"],
                    matched_fields=[],
                    conflicting_fields=conflicting_fields,
                    rationale="Website conflicts and LinkedIn unavailable. Discovered as look-alike lead.",
                    discovery_type="related_name"
                )
            return ClassificationResult(
                rule_id="BR-10",
                match_status="not_a_match",
                website_match_state=web_state,
                linkedin_match_state=linkedin_state,
                name_similarity_percent=None,
                match_methods=[],
                matched_fields=[],
                conflicting_fields=conflicting_fields,
                rationale="Website domain conflicts and master has populated identifiers. No fuzzy fallback."
            )

        # BR-11: UNAVAILABLE + CONFLICT (master has >= 1 usable identifier)
        if web_state == "UNAVAILABLE" and linkedin_state == "CONFLICT":
            if is_related_lead_discovery:
                sim = matching_service.compute_legal_name_similarity(upload_legal_name_norm, master_legal_name_norm)
                return ClassificationResult(
                    rule_id="BR-11",
                    match_status="needs_review",
                    website_match_state=web_state,
                    linkedin_match_state=linkedin_state,
                    name_similarity_percent=sim,
                    match_methods=["related_name_lead"],
                    matched_fields=[],
                    conflicting_fields=conflicting_fields,
                    rationale="LinkedIn conflicts and website unavailable. Discovered as look-alike lead.",
                    discovery_type="related_name"
                )
            return ClassificationResult(
                rule_id="BR-11",
                match_status="not_a_match",
                website_match_state=web_state,
                linkedin_match_state=linkedin_state,
                name_similarity_percent=None,
                match_methods=[],
                matched_fields=[],
                conflicting_fields=conflicting_fields,
                rationale="LinkedIn company URL conflicts and master has populated identifiers. No fuzzy fallback."
            )

        # BR-07, BR-08, BR-09, BR-12: UNAVAILABLE + UNAVAILABLE
        if web_state == "UNAVAILABLE" and linkedin_state == "UNAVAILABLE":
            if master_both_unavailable:
                # Master has both identifiers blank -> Eligible for mandatory Legal Name fuzzy fallback (provisional DEC-01)
                if upload_legal_name_norm and master_legal_name_norm:
                    sim = matching_service.compute_legal_name_similarity(upload_legal_name_norm, master_legal_name_norm)
                    if sim is not None and sim >= fuzzy_threshold:
                        # BR-07: >= threshold
                        return ClassificationResult(
                            rule_id="BR-07",
                            match_status="potential_duplicate",
                            website_match_state=web_state,
                            linkedin_match_state=linkedin_state,
                            name_similarity_percent=round(sim, 1),
                            match_methods=["fuzzy_legal_name"],
                            matched_fields=["legal_name"],
                            conflicting_fields=[],
                            rationale=f"Both master identifiers unavailable. Legal Name fuzzy similarity {sim:.1f}% >= threshold {fuzzy_threshold}%."
                        )
                    else:
                        # BR-08: < threshold
                        score_text = f"{sim:.1f}%" if sim is not None else "N/A"
                        return ClassificationResult(
                            rule_id="BR-08",
                            match_status="not_a_match",
                            website_match_state=web_state,
                            linkedin_match_state=linkedin_state,
                            name_similarity_percent=round(sim, 1) if sim is not None else None,
                            match_methods=["fuzzy_legal_name"],
                            matched_fields=[],
                            conflicting_fields=[],
                            rationale=f"Both master identifiers unavailable. Legal Name fuzzy similarity {score_text} < threshold {fuzzy_threshold}%."
                        )
                else:
                    # BR-09: Either legal name unusable
                    return ClassificationResult(
                        rule_id="BR-09",
                        match_status="insufficient_data",
                        website_match_state=web_state,
                        linkedin_match_state=linkedin_state,
                        name_similarity_percent=None,
                        match_methods=[],
                        matched_fields=[],
                        conflicting_fields=[],
                        rationale="Both master identifiers unavailable, and one or both legal names are missing or unusable."
                    )
            else:
                # Master has usable identifier(s), but upload lacks comparable identifiers
                # BR-12
                if is_related_lead_discovery:
                    sim = matching_service.compute_legal_name_similarity(upload_legal_name_norm, master_legal_name_norm)
                    if sim and sim >= 70.0:
                        return ClassificationResult(
                            rule_id="BR-12-lead",
                            match_status="needs_review",
                            website_match_state=web_state,
                            linkedin_match_state=linkedin_state,
                            name_similarity_percent=round(sim, 1),
                            match_methods=["related_name_lead"],
                            matched_fields=[],
                            conflicting_fields=[],
                            rationale="Master has identifiers not present in upload. Similar name surfaced as lead.",
                            discovery_type="related_name"
                        )
                return ClassificationResult(
                    rule_id="BR-12",
                    match_status="insufficient_data",
                    website_match_state=web_state,
                    linkedin_match_state=linkedin_state,
                    name_similarity_percent=None,
                    match_methods=[],
                    matched_fields=[],
                    conflicting_fields=[],
                    rationale="Master has registered identifiers, but uploaded record lacks comparable identifiers. Fuzzy fallback ineligible."
                )

        # Fallback default
        return ClassificationResult(
            rule_id="BR-DEFAULT",
            match_status="not_a_match",
            website_match_state=web_state,
            linkedin_match_state=linkedin_state,
            name_similarity_percent=None,
            match_methods=[],
            matched_fields=[],
            conflicting_fields=[],
            rationale="No matching criteria satisfied."
        )

classification_service = ClassificationService()
