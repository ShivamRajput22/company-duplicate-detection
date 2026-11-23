import re
import unicodedata
from urllib.parse import urlparse
from typing import Optional, Tuple
import tldextract

# Set up offline/cached tldextract to avoid network calls during runtime
# Add reserved RFC 2606 test TLDs (.example, .test) used in synthetic datasets
_tld_extractor = tldextract.TLDExtract(
    suffix_list_urls=(),
    extra_suffixes=["example", "test", "invalid", "localhost"],
    fallback_to_snapshot=True
)

# Null-like string patterns
NULL_LIKE_VALUES = {
    "", "none", "null", "n/a", "na", "nan", "-", "--", "undefined", "nil", "unknown"
}

# Legal suffixes to remove in suffix position (whole tokens only)
LEGAL_SUFFIXES = {
    "llc", "l.l.c.", "l.l.c", "llc.",
    "inc", "inc.", "incorporated",
    "corp", "corp.", "corporation",
    "ltd", "ltd.", "limited",
    "co", "co.", "company",
    "gmbh",
    "sa", "s.a.", "s.a",
    "plc", "p.l.c.", "p.l.c",
    "lp", "l.p.", "l.p",
    "llp", "l.l.p.", "l.l.p",
    "pllc", "p.l.l.c."
}

# Words that MUST be preserved and NEVER stripped as suffixes
PROTECTED_WORDS = {
    "group", "property", "properties", "petroleum", "holdings",
    "management", "services", "solutions", "technologies", "technology",
    "capital", "partners", "associates", "enterprises", "industries",
    "international", "consulting", "logistics", "systems", "global"
}

GENERIC_DOMAINS = {
    "linkedin.com", "facebook.com", "twitter.com", "x.com",
    "instagram.com", "youtube.com", "github.com", "google.com",
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com"
}

class NormalizationService:
    @staticmethod
    def is_null_like(val: Optional[str]) -> bool:
        if val is None:
            return True
        val_clean = val.strip().lower()
        return val_clean in NULL_LIKE_VALUES

    @classmethod
    def normalize_name(cls, name: Optional[str]) -> Optional[str]:
        """
        Normalizes company or legal name according to Group 2 / Appendix A.5:
        - Unicode NFKC normalization
        - Casefold (lowercase)
        - Normalizes whitespace and punctuation
        - Strips whole-token legal suffixes from the end
        - Retains meaningful business words (Property, Petroleum, Group, Holdings, etc.)
        - Never conflates 'Property' and 'Properties'
        """
        if cls.is_null_like(name):
            return None

        # 1. Unicode NFKC and strip diacritical marks
        text = unicodedata.normalize("NFKC", str(name))
        text = "".join(c for c in unicodedata.normalize("NFKD", text) if unicodedata.category(c) != "Mn")

        # 2. Casefold
        text = text.casefold()

        # 3. Replace punctuation (except ampersand which can be replaced with ' and ' or space)
        text = text.replace("&", " and ")
        # Replace non-alphanumeric characters with spaces
        text = re.sub(r"[^\w\s]", " ", text)

        # 4. Collapse spaces
        tokens = [t for t in text.split() if t]
        if not tokens:
            return None

        # 5. Remove legal suffixes from end of token list (while preserving protected business words)
        while tokens:
            last_token = tokens[-1]
            if last_token in LEGAL_SUFFIXES and last_token not in PROTECTED_WORDS:
                tokens.pop()
            else:
                break

        if not tokens:
            return None

        return " ".join(tokens)

    @classmethod
    def light_normalize_name(cls, name: Optional[str]) -> Optional[str]:
        """Preserves suffixes, just trims and casefolds with space collapse."""
        if cls.is_null_like(name):
            return None
        text = unicodedata.normalize("NFKC", str(name)).casefold()
        text = re.sub(r"\s+", " ", text).strip()
        return text if text else None

    @classmethod
    def normalize_domain(cls, val: Optional[str]) -> Tuple[Optional[str], str]:
        """
        Normalizes website domain according to Group 2 / Appendix A.5:
        - Safe parsing of bare domains or full URLs
        - Public Suffix List aware registered-domain extraction
        - Rejects social/generic platforms as unique business domain
        - Returns (registered_domain, validation_status) where status is:
          'valid', 'missing', or 'invalid'
        """
        if cls.is_null_like(val):
            return None, "missing"

        raw = str(val).strip()
        # Prepend scheme if missing so urlparse handles hostname properly
        parsed_url = raw
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", parsed_url):
            parsed_url = "http://" + parsed_url

        try:
            parsed = urlparse(parsed_url)
            netloc = parsed.netloc or parsed.path.split("/")[0]
            # Strip port if present
            netloc = netloc.split(":")[0].strip().lower()

            # Remove trailing dots and www.
            netloc = re.sub(r"^\.*www\.", "", netloc).strip(".")

            # Validate basic hostname characters
            if not netloc or not re.match(r"^[a-z0-9.-]+$", netloc):
                return None, "invalid"

            # Check for bare IP address (not a registered business domain)
            if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", netloc):
                return None, "invalid"

            # PSL extraction
            ext = _tld_extractor(netloc)
            if not ext.domain or not ext.suffix:
                return None, "invalid"

            registered_domain = f"{ext.domain}.{ext.suffix}".lower()

            # Reject social platforms / generic email hosts
            if registered_domain in GENERIC_DOMAINS:
                return None, "invalid"

            return registered_domain, "valid"
        except Exception:
            return None, "invalid"

    @classmethod
    def normalize_linkedin(cls, val: Optional[str]) -> Tuple[Optional[str], str]:
        """
        Normalizes LinkedIn URL according to Group 2 / Appendix A.5:
        - Must have exact recognized LinkedIn host (linkedin.com or www.linkedin.com)
        - Reject lookalike hosts (e.g. linkedin.com.evil.test)
        - Must be /company/<slug-or-id>
        - Reject personal profiles (/in/), school, etc.
        - Normalize to canonical 'linkedin.com/company/<slug>'
        - Returns (normalized_url, validation_status) where status is:
          'valid', 'missing', or 'invalid'
        """
        if cls.is_null_like(val):
            return None, "missing"

        raw = str(val).strip()
        parsed_url = raw
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", parsed_url):
            parsed_url = "https://" + parsed_url

        try:
            parsed = urlparse(parsed_url)
            host = (parsed.netloc or "").split(":")[0].strip().lower()

            # Host must be exactly linkedin.com or end with .linkedin.com (e.g. www.linkedin.com)
            if host != "linkedin.com" and not host.endswith(".linkedin.com"):
                return None, "invalid"

            # Check for evil subdomain/suffix tricks (e.g., linkedin.com.attacker.com)
            if host != "linkedin.com" and host != "www.linkedin.com":
                # Only allow standard subdomains like www.
                parts = host.split(".")
                if len(parts) > 3 or (len(parts) == 3 and parts[0] not in ["www", "ae", "uk", "in", "de"]):
                    return None, "invalid"

            path = parsed.path.strip("/")
            path_parts = [p for p in path.split("/") if p]

            # Path must start with 'company'
            if not path_parts or path_parts[0].lower() != "company" or len(path_parts) < 2:
                # Personal profiles (/in/...) or others are rejected
                return None, "invalid"

            slug = path_parts[1].lower().strip()
            # Clean trailing punctuation from slug if any
            slug = re.sub(r"[^\w-]", "", slug)
            if not slug:
                return None, "invalid"

            canonical = f"linkedin.com/company/{slug}"
            return canonical, "valid"
        except Exception:
            return None, "invalid"

# Central reusable instance
normalization_service = NormalizationService()
