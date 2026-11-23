import csv
import io
import re
from typing import List, Dict, Any, Tuple, Optional
from app.services.normalization_service import normalization_service
from app.config import settings

HEADER_MAPPINGS = {
    "company_name": ["company_name", "companyname", "company", "company name"],
    "legal_name": ["legal_name", "legalname", "legal", "legal name"],
    "web_domain": ["web_domain", "webdomain", "website_domain", "website domain", "domain", "website", "url"],
    "linkedin_url": ["linkedin_url", "linkedinurl", "linkedin", "linkedin url", "linkedin_company_url"]
}

class CSVValidationError(Exception):
    def __init__(self, message: str, errors: Optional[List[str]] = None):
        super().__init__(message)
        self.message = message
        self.errors = errors or []

class CSVService:
    @staticmethod
    def sanitize_for_formula_injection(val: Optional[str]) -> Optional[str]:
        """
        Guards against CSV / Spreadsheet formula injection:
        If string begins with =, +, -, @, \t, \r, prepend a single quote '.
        """
        if val is None:
            return None
        text = str(val)
        stripped = text.lstrip()
        if stripped and stripped[0] in ("=", "+", "-", "@", "\t", "\r"):
            return f"'{text}"
        return text

    @classmethod
    def parse_and_validate_csv(
        cls,
        file_bytes: bytes,
        filename: str
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Parses and validates CSV input according to Group 2 / Appendix A.4 (CSV-01 to CSV-18).
        Returns:
        - parsed_rows: list of row dicts ready for persistence in import_rows
        - stats: {total_rows, accepted_rows, rejected_rows, empty_rows_skipped, invalid_identifiers}
        """
        # CSV-02: Size check
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(file_bytes) > max_bytes:
            raise CSVValidationError(f"File size exceeds maximum allowed {settings.MAX_UPLOAD_SIZE_MB} MB limit.")

        if len(file_bytes) == 0:
            raise CSVValidationError("The uploaded CSV file is empty.")

        # CSV-03: Support UTF-8 and UTF-8 BOM
        try:
            content = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                content = file_bytes.decode("latin-1")
            except Exception as e:
                raise CSVValidationError(f"Could not decode file as UTF-8 or standard text: {e}")

        # CSV-01: Validate CSV structure
        f = io.StringIO(content)
        try:
            reader = csv.reader(f)
            header_row = next(reader, None)
        except Exception as e:
            raise CSVValidationError(f"Malformed CSV content: {e}")

        if not header_row:
            raise CSVValidationError("CSV file does not contain a header row.")

        # CSV-04: Header mapping
        header_map = {}
        for idx, col in enumerate(header_row):
            col_clean = col.strip().lower()
            for std_field, aliases in HEADER_MAPPINGS.items():
                if col_clean in aliases:
                    header_map[std_field] = idx
                    break

        if "company_name" not in header_map and "legal_name" not in header_map:
            raise CSVValidationError(
                "CSV must contain at least a 'company_name' or 'legal_name' header column.",
                errors=[f"Found headers: {header_row}"]
            )

        parsed_rows = []
        total_rows_counted = 0
        accepted_count = 0
        rejected_count = 0
        empty_count = 0
        invalid_identifier_count = 0

        physical_row_number = 1 # Header was row 1

        for row_values in reader:
            physical_row_number += 1

            # Check if row is completely empty
            if not row_values or all(c.strip() == "" for c in row_values):
                empty_count += 1
                continue

            total_rows_counted += 1
            row_id_str = f"ROW-{physical_row_number:04d}"

            def get_col(field_name: str) -> Optional[str]:
                idx = header_map.get(field_name)
                if idx is not None and idx < len(row_values):
                    v = row_values[idx].strip()
                    return v if v else None
                return None

            raw_company = get_col("company_name")
            raw_legal = get_col("legal_name")
            raw_domain = get_col("web_domain")
            raw_linkedin = get_col("linkedin_url")

            # Normalization
            norm_company = normalization_service.normalize_name(raw_company)
            norm_legal = normalization_service.normalize_name(raw_legal)
            norm_domain, domain_status = normalization_service.normalize_domain(raw_domain)
            norm_linkedin, linkedin_status = normalization_service.normalize_linkedin(raw_linkedin)

            row_errors = []

            # CSV-05: Reject if both name fields are unusable
            if norm_company is None and norm_legal is None:
                row_errors.append("Both company_name and legal_name are unusable or missing.")
                record_status = "rejected"
                rejected_count += 1
            else:
                record_status = "accepted"
                accepted_count += 1

            if domain_status == "invalid":
                invalid_identifier_count += 1
                row_errors.append(f"Invalid website domain: '{raw_domain}'")

            if linkedin_status == "invalid":
                invalid_identifier_count += 1
                row_errors.append(f"Invalid LinkedIn URL: '{raw_linkedin}'")

            parsed_rows.append({
                "upload_record_id": row_id_str,
                "csv_row_number": physical_row_number,
                "company_name_original": raw_company,
                "legal_name_original": raw_legal,
                "web_domain_original": raw_domain,
                "linkedin_url_original": raw_linkedin,
                "company_name_normalized": norm_company,
                "legal_name_normalized": norm_legal,
                "web_domain_normalized": norm_domain,
                "linkedin_url_normalized": norm_linkedin,
                "website_validation_status": domain_status,
                "linkedin_validation_status": linkedin_status,
                "record_validation_status": record_status,
                "validation_errors": row_errors
            })

        stats = {
            "total_rows": total_rows_counted,
            "accepted_rows": accepted_count,
            "rejected_rows": rejected_count,
            "empty_rows_skipped": empty_count,
            "invalid_identifiers": invalid_identifier_count
        }

        return parsed_rows, stats

csv_service = CSVService()
