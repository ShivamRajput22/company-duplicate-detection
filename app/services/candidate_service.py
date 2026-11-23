from typing import List, Dict, Any, Set, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from database.models import Entity
from app.services.matching_service import matching_service
from app.services.classification_service import classification_service, ClassificationResult

class CandidateService:
    @classmethod
    def get_candidates_for_row(
        cls,
        session: Session,
        row: Dict[str, Any],
        fuzzy_threshold: float = 80.0
    ) -> List[Tuple[Entity, ClassificationResult]]:
        """
        Retrieves and evaluates master candidates for a single uploaded row.
        Follows Group 3 / Appendix B.2 & B.6:
        1. Retrieves exact domain matches
        2. Retrieves exact LinkedIn matches
        3. Scans eligible master rows (both identifiers unavailable) for Legal Name fuzzy fallback >= threshold
        4. Discovers related-name look-alikes (e.g. Trimark cases) as separate leads
        5. Unions by entity_id: exactly one candidate per (upload_row, entity_id)
        """
        upload_domain = row.get("web_domain_normalized")
        upload_linkedin = row.get("linkedin_url_normalized")
        upload_legal = row.get("legal_name_normalized")
        upload_company = row.get("company_name_normalized")

        candidate_entities: Dict[int, Entity] = {}
        retrieval_reasons: Dict[int, Set[str]] = {}
        is_lead_discovery: Dict[int, bool] = {}

        # 1. Exact Domain hits
        if upload_domain:
            domain_matches = session.query(Entity).filter(
                Entity.normalized_domain == upload_domain
            ).all()
            for ent in domain_matches:
                candidate_entities[ent.entity_id] = ent
                retrieval_reasons.setdefault(ent.entity_id, set()).add("domain_index")

        # 2. Exact LinkedIn hits
        if upload_linkedin:
            li_matches = session.query(Entity).filter(
                Entity.normalized_linkedin == upload_linkedin
            ).all()
            for ent in li_matches:
                candidate_entities[ent.entity_id] = ent
                retrieval_reasons.setdefault(ent.entity_id, set()).add("linkedin_index")

        # 3. Exact Legal Name hits
        if upload_legal:
            exact_name_matches = session.query(Entity).filter(
                Entity.normalized_legal_name == upload_legal
            ).all()
            for ent in exact_name_matches:
                candidate_entities[ent.entity_id] = ent
                retrieval_reasons.setdefault(ent.entity_id, set()).add("exact_name")

        # 4. Mandatory Fuzzy Fallback for Master-side both identifiers unavailable (DEC-01)
        if upload_legal:
            blank_identifier_masters = session.query(Entity).filter(
                Entity.normalized_domain.is_(None),
                Entity.normalized_linkedin.is_(None),
                Entity.normalized_legal_name.isnot(None)
            ).all()

            for ent in blank_identifier_masters:
                # Compute RapidFuzz ratio on normalized legal name
                sim = matching_service.compute_legal_name_similarity(upload_legal, ent.normalized_legal_name)
                if sim is not None and sim >= fuzzy_threshold:
                    candidate_entities[ent.entity_id] = ent
                    retrieval_reasons.setdefault(ent.entity_id, set()).add("fuzzy_legal_name")

        # 5. Related-Name Discovery (Trimark Look-Alike policy)
        # Search for distinctive token leads even if domains/linkedin differ
        search_tokens = []
        name_for_tokens = upload_legal or upload_company
        if name_for_tokens:
            tokens = [t for t in name_for_tokens.split() if len(t) >= 4 and t not in (
                "group", "company", "holdings", "management", "services", "solutions"
            )]
            search_tokens = tokens[:2] # Top 2 distinctive tokens

        for token in search_tokens:
            token_matches = session.query(Entity).filter(
                Entity.normalized_company_name.like(f"%{token}%")
            ).limit(20).all()

            for ent in token_matches:
                if ent.entity_id not in candidate_entities:
                    # Check if token overlap justifies a related-name investigation lead
                    # E.g. Trimark Property vs Trimark Petroleum
                    candidate_entities[ent.entity_id] = ent
                    retrieval_reasons.setdefault(ent.entity_id, set()).add("related_name_lead")
                    is_lead_discovery[ent.entity_id] = True

        # Now classify each unique candidate pair using the authoritative ClassificationService
        results: List[Tuple[Entity, ClassificationResult]] = []

        for ent_id, ent in candidate_entities.items():
            reasons = retrieval_reasons.get(ent_id, set())
            is_lead = is_lead_discovery.get(ent_id, False)

            classification = classification_service.classify_pair(
                upload_domain_norm=upload_domain,
                upload_linkedin_norm=upload_linkedin,
                upload_legal_name_norm=upload_legal,
                upload_company_name_norm=upload_company,
                master_domain_norm=ent.normalized_domain,
                master_linkedin_norm=ent.normalized_linkedin,
                master_legal_name_norm=ent.normalized_legal_name,
                master_company_name_norm=ent.normalized_company_name,
                fuzzy_threshold=fuzzy_threshold,
                is_related_lead_discovery=is_lead
            )

            # Filter out true non-matches that were not even requested as leads
            if classification.match_status == "not_a_match" and not is_lead:
                # If it's not a match under business rules, skip emitting as candidate pair
                continue

            results.append((ent, classification))

        return results

candidate_service = CandidateService()
