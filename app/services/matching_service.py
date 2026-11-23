from typing import Optional, Tuple
from rapidfuzz import fuzz
from app.services.normalization_service import normalization_service

class MatchingService:
    @staticmethod
    def compare_identifier(val1: Optional[str], val2: Optional[str]) -> str:
        """
        Compares two normalized identifiers (registered domains or LinkedIn URLs).
        Returns one of:
        - MATCH: both valid, present and equal
        - CONFLICT: both valid, present and differ
        - UNAVAILABLE: one or both missing or invalid
        Blank-to-blank is NEVER a match.
        """
        if not val1 or not val2:
            return "UNAVAILABLE"
        if val1 == val2:
            return "MATCH"
        return "CONFLICT"

    @staticmethod
    def compute_legal_name_similarity(
        legal_name_1_norm: Optional[str],
        legal_name_2_norm: Optional[str]
    ) -> Optional[float]:
        """
        Computes RapidFuzz ratio string similarity (0.0 to 100.0).
        Returns None if either normalized legal name is unusable.
        """
        if not legal_name_1_norm or not legal_name_2_norm:
            return None
        return float(fuzz.ratio(legal_name_1_norm, legal_name_2_norm))

    @staticmethod
    def compute_supplementary_name_similarity(
        name_1_norm: Optional[str],
        name_2_norm: Optional[str]
    ) -> Optional[float]:
        """
        Supplementary similarity score (e.g. company name vs company name, or token set ratio)
        used for related-name discovery, never to override legal-name rule.
        """
        if not name_1_norm or not name_2_norm:
            return None
        return float(fuzz.token_set_ratio(name_1_norm, name_2_norm))

matching_service = MatchingService()
