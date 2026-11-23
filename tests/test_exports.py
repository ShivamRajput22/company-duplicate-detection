import io
import csv
import pytest
from app.services.csv_service import csv_service
from app.services.export_service import export_service
from database.database import SessionLocal
from database.models import ImportRun, ImportRow, MatchCandidate, Entity

def test_formula_injection_sanitization():
    assert csv_service.sanitize_for_formula_injection("=cmd|' /C calc'!A0") == "'=cmd|' /C calc'!A0"
    assert csv_service.sanitize_for_formula_injection("+12345") == "'+12345"
    assert csv_service.sanitize_for_formula_injection("-500") == "'-500"
    assert csv_service.sanitize_for_formula_injection("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert csv_service.sanitize_for_formula_injection("Normal Text LLC") == "Normal Text LLC"
    assert csv_service.sanitize_for_formula_injection(None) is None

def test_export_invalid_type_raises():
    session = SessionLocal()
    try:
        # Create a mock run if none
        run = session.query(ImportRun).first()
        if run:
            with pytest.raises(ValueError, match="Unknown export type"):
                export_service.generate_csv_export(session, run.run_id, "invalid_type")
    finally:
        session.close()

def test_export_id_name_integrity_on_seeded_data():
    session = SessionLocal()
    try:
        run = session.query(ImportRun).filter(ImportRun.run_status == "completed").first()
        if not run:
            pytest.skip("No completed run found in DB to test export integrity")

        csv_text = export_service.generate_csv_export(session, run.run_id, "master_summary")
        reader = csv.reader(io.StringIO(csv_text))
        header = next(reader)
        id_idx = header.index("Matched Entity ID")
        legal_name_idx = header.index("Matched Legal Name")

        # Invariant: Adjacent columns
        assert abs(id_idx - legal_name_idx) == 1

        for row in reader:
            ent_id = int(row[id_idx])
            exported_legal_name = row[legal_name_idx]

            # Cross-check directly against master entity in DB
            ent = session.query(Entity).filter(Entity.entity_id == ent_id).first()
            assert ent is not None
            expected_legal_name = csv_service.sanitize_for_formula_injection(ent.legal_name)
            assert exported_legal_name == expected_legal_name
    finally:
        session.close()
