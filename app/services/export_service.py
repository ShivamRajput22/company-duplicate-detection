import csv
import io
import json
from typing import Optional
from sqlalchemy.orm import Session
from database.models import ImportRun, ImportRow, MatchCandidate, Entity, DuplicateReview
from app.services.csv_service import csv_service
from app.services.grouping_service import grouping_service

class ExportService:
    @classmethod
    def generate_csv_export(
        cls,
        session: Session,
        run_id: str,
        export_type: str  # uploaded_summary | master_summary | candidate_details
    ) -> str:
        """
        One backend export service implementing the 3 views defined in Appendix E.3.
        Guarantees:
        - Real entities.entity_id and adjacent entities.legal_name (AC-03, AC-04)
        - Zero duplicate rows at the declared grain (AC-05)
        - Defends against CSV spreadsheet formula injection
        - Deterministic ordering
        """
        run = session.query(ImportRun).filter(ImportRun.run_id == run_id).first()
        if not run:
            raise ValueError(f"Run ID '{run_id}' not found.")

        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\r\n")

        if export_type == "uploaded_summary":
            headers = [
                "Run ID", "Upload Record ID", "CSV Row Number",
                "Uploaded Company Name", "Uploaded Legal Name",
                "Website Domain", "LinkedIn URL",
                "Validation Status", "Candidate Matches Count", "Strongest Match Status"
            ]
            writer.writerow(headers)

            data = grouping_service.get_uploaded_summary_view(session, run_id)
            for row in data:
                writer.writerow([
                    csv_service.sanitize_for_formula_injection(row["run_id"]),
                    csv_service.sanitize_for_formula_injection(row["upload_record_id"]),
                    row["csv_row_number"],
                    csv_service.sanitize_for_formula_injection(row["company_name"]),
                    csv_service.sanitize_for_formula_injection(row["legal_name"]),
                    csv_service.sanitize_for_formula_injection(row["web_domain"]),
                    csv_service.sanitize_for_formula_injection(row["linkedin_url"]),
                    row["validation_status"],
                    row["candidate_count"],
                    row["strongest_status"]
                ])

        elif export_type == "master_summary":
            # Master company summary: exactly one row per master entity_id
            headers = [
                "Run ID", "Matched Entity ID", "Matched Legal Name",
                "Matched Company Name", "Website Domain", "LinkedIn URL",
                "Matched Uploaded Rows Count", "Strongest Match Status"
            ]
            writer.writerow(headers)

            data = grouping_service.get_master_summary_view(session, run_id)
            for row in data:
                writer.writerow([
                    csv_service.sanitize_for_formula_injection(row["run_id"]),
                    row["matched_entity_id"], # AC-03: Actual entity_id, never IMPORT_BATCH
                    csv_service.sanitize_for_formula_injection(row["matched_legal_name"]), # AC-04: adjacent legal name
                    csv_service.sanitize_for_formula_injection(row["matched_company_name"]),
                    csv_service.sanitize_for_formula_injection(row["web_domain"]),
                    csv_service.sanitize_for_formula_injection(row["linkedin_url"]),
                    row["matched_uploaded_count"],
                    row["strongest_status"]
                ])

        elif export_type == "candidate_details":
            # Detailed candidate pairs: one row per (run_id, upload_record_id, entity_id)
            headers = [
                "Run ID", "Upload Record ID", "CSV Row Number",
                "Uploaded Company Name", "Uploaded Legal Name",
                "Matched Entity ID", "Matched Legal Name", "Matched Company Name",
                "Matched Domain", "Matched LinkedIn",
                "Match Method(s)", "Name Similarity (%)", "Match Status", "Discovery Type",
                "Matched Fields", "Conflicting Fields", "Rationale",
                "Latest Review Decision"
            ]
            writer.writerow(headers)

            candidates = session.query(MatchCandidate).filter(
                MatchCandidate.run_id == run_id
            ).all()

            # Pre-load entities and rows
            ent_ids = [c.candidate_entity_id for c in candidates]
            entities = {e.entity_id: e for e in session.query(Entity).filter(Entity.entity_id.in_(ent_ids)).all()}

            rows = {r.upload_record_id: r for r in session.query(ImportRow).filter(ImportRow.run_id == run_id).all()}

            # Load latest reviews
            reviews = {}
            for c in candidates:
                latest_rev = session.query(DuplicateReview).filter(
                    DuplicateReview.candidate_id == c.candidate_id
                ).order_by(DuplicateReview.reviewed_at.desc()).first()
                if latest_rev:
                    reviews[c.candidate_id] = latest_rev.new_decision

            # Sort deterministically
            candidates.sort(key=lambda x: (x.upload_record_id, x.candidate_entity_id))

            for c in candidates:
                ent = entities.get(c.candidate_entity_id)
                row_src = rows.get(c.upload_record_id)

                methods_list = json.loads(c.match_methods) if c.match_methods else []
                matched_f = json.loads(c.matched_fields) if c.matched_fields else []
                conflict_f = json.loads(c.conflicting_fields) if c.conflicting_fields else []

                sim_display = f"{c.name_similarity_percent:.1f}%" if c.name_similarity_percent is not None else "N/A"

                writer.writerow([
                    csv_service.sanitize_for_formula_injection(c.run_id),
                    csv_service.sanitize_for_formula_injection(c.upload_record_id),
                    row_src.csv_row_number if row_src else "",
                    csv_service.sanitize_for_formula_injection(row_src.company_name_original if row_src else ""),
                    csv_service.sanitize_for_formula_injection(row_src.legal_name_original if row_src else ""),
                    c.candidate_entity_id, # AC-03: Real entity_id
                    csv_service.sanitize_for_formula_injection(ent.legal_name if ent else ""), # AC-04: adjacent legal name
                    csv_service.sanitize_for_formula_injection(ent.company_name if ent else ""),
                    csv_service.sanitize_for_formula_injection(ent.web_domain if ent else ""),
                    csv_service.sanitize_for_formula_injection(ent.linkedin_url if ent else ""),
                    ", ".join(methods_list),
                    sim_display,
                    c.match_status,
                    c.discovery_type,
                    ", ".join(matched_f),
                    ", ".join(conflict_f),
                    csv_service.sanitize_for_formula_injection(c.rationale),
                    reviews.get(c.candidate_id, "pending")
                ])
        else:
            raise ValueError(f"Unknown export type '{export_type}'. Must be uploaded_summary, master_summary, or candidate_details.")

        return buffer.getvalue()

export_service = ExportService()
