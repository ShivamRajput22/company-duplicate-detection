import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from database.models import ImportRow, MatchCandidate, Entity, DuplicateReview

class GroupingService:
    @classmethod
    def get_uploaded_summary_view(
        cls,
        session: Session,
        run_id: str
    ) -> List[Dict[str, Any]]:
        """
        One row per (run_id, upload_record_id).
        Includes accepted incoming records even if they have 0 candidates.
        """
        rows = session.query(ImportRow).filter(
            ImportRow.run_id == run_id
        ).order_by(ImportRow.csv_row_number).all()

        candidates = session.query(MatchCandidate).filter(
            MatchCandidate.run_id == run_id
        ).all()

        # Group candidates by upload_record_id
        cand_map: Dict[str, List[MatchCandidate]] = {}
        for c in candidates:
            cand_map.setdefault(c.upload_record_id, []).append(c)

        summary = []
        for r in rows:
            cands = cand_map.get(r.upload_record_id, [])

            # Determine strongest system outcome
            strongest_status = "no_match"
            if cands:
                statuses = [c.match_status for c in cands]
                if "high_confidence_candidate" in statuses:
                    strongest_status = "high_confidence_candidate"
                elif "potential_duplicate" in statuses:
                    strongest_status = "potential_duplicate"
                elif "needs_review" in statuses:
                    strongest_status = "needs_review"
                elif "insufficient_data" in statuses:
                    strongest_status = "insufficient_data"
                else:
                    strongest_status = statuses[0]

            summary.append({
                "run_id": run_id,
                "upload_record_id": r.upload_record_id,
                "csv_row_number": r.csv_row_number,
                "company_name": r.company_name_original,
                "legal_name": r.legal_name_original,
                "web_domain": r.web_domain_original,
                "linkedin_url": r.linkedin_url_original,
                "validation_status": r.record_validation_status,
                "candidate_count": len(cands),
                "strongest_status": strongest_status,
                "candidate_entity_ids": [c.candidate_entity_id for c in cands]
            })

        return summary

    @classmethod
    def get_master_summary_view(
        cls,
        session: Session,
        run_id: str
    ) -> List[Dict[str, Any]]:
        """
        One row per (run_id, entity_id).
        Shows master Entity ID with ADJACENT Legal Name and number of matched uploaded rows.
        Guarantees zero repeat master companies.
        """
        candidates = session.query(MatchCandidate).filter(
            MatchCandidate.run_id == run_id
        ).all()

        # Group by candidate_entity_id
        ent_map: Dict[int, List[MatchCandidate]] = {}
        for c in candidates:
            ent_map.setdefault(c.candidate_entity_id, []).append(c)

        master_ids = list(ent_map.keys())
        if not master_ids:
            return []

        entities = session.query(Entity).filter(Entity.entity_id.in_(master_ids)).all()
        ent_dict = {e.entity_id: e for e in entities}

        summary = []
        for ent_id, cands in ent_map.items():
            ent = ent_dict.get(ent_id)
            if not ent:
                continue

            statuses = [c.match_status for c in cands]
            strongest = "needs_review"
            if "high_confidence_candidate" in statuses:
                strongest = "high_confidence_candidate"
            elif "potential_duplicate" in statuses:
                strongest = "potential_duplicate"
            elif "needs_review" in statuses:
                strongest = "needs_review"
            else:
                strongest = statuses[0]

            summary.append({
                "run_id": run_id,
                "matched_entity_id": ent.entity_id,
                "matched_legal_name": ent.legal_name,
                "matched_company_name": ent.company_name,
                "web_domain": ent.web_domain,
                "linkedin_url": ent.linkedin_url,
                "matched_uploaded_count": len(cands),
                "strongest_status": strongest,
                "uploaded_record_ids": [c.upload_record_id for c in cands]
            })

        # Sort deterministically by entity_id
        summary.sort(key=lambda x: x["matched_entity_id"])
        return summary

grouping_service = GroupingService()
