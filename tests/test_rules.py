import pytest
from app.services.classification_service import classification_service

def test_br01_match_match():
    res = classification_service.classify_pair(
        upload_domain_norm="acme.example",
        upload_linkedin_norm="linkedin.com/company/acme",
        upload_legal_name_norm="acme group",
        upload_company_name_norm="acme",
        master_domain_norm="acme.example",
        master_linkedin_norm="linkedin.com/company/acme",
        master_legal_name_norm="acme group",
        master_company_name_norm="acme"
    )
    assert res.rule_id == "BR-01"
    assert res.match_status == "high_confidence_candidate"
    assert res.website_match_state == "MATCH"
    assert res.linkedin_match_state == "MATCH"
    assert "website" in res.match_methods
    assert "linkedin" in res.match_methods
    assert res.name_similarity_percent is None  # Exact match, no fuzzy score

def test_br02_match_unavailable():
    res = classification_service.classify_pair(
        upload_domain_norm="acme.example",
        upload_linkedin_norm=None,
        upload_legal_name_norm="acme corp",
        upload_company_name_norm="acme",
        master_domain_norm="acme.example",
        master_linkedin_norm=None,
        master_legal_name_norm="acme",
        master_company_name_norm="acme"
    )
    assert res.rule_id == "BR-02"
    assert res.match_status == "high_confidence_candidate"
    assert res.website_match_state == "MATCH"
    assert res.linkedin_match_state == "UNAVAILABLE"
    assert "website" in res.match_methods

def test_br03_unavailable_match():
    res = classification_service.classify_pair(
        upload_domain_norm=None,
        upload_linkedin_norm="linkedin.com/company/acme",
        upload_legal_name_norm="acme corp",
        upload_company_name_norm="acme",
        master_domain_norm=None,
        master_linkedin_norm="linkedin.com/company/acme",
        master_legal_name_norm="acme",
        master_company_name_norm="acme"
    )
    assert res.rule_id == "BR-03"
    assert res.match_status == "high_confidence_candidate"
    assert res.website_match_state == "UNAVAILABLE"
    assert res.linkedin_match_state == "MATCH"
    assert "linkedin" in res.match_methods

def test_br04_match_conflict():
    res = classification_service.classify_pair(
        upload_domain_norm="acme.example",
        upload_linkedin_norm="linkedin.com/company/acme-one",
        upload_legal_name_norm="acme",
        upload_company_name_norm="acme",
        master_domain_norm="acme.example",
        master_linkedin_norm="linkedin.com/company/acme-two",
        master_legal_name_norm="acme",
        master_company_name_norm="acme"
    )
    assert res.rule_id == "BR-04"
    assert res.match_status == "needs_review"
    assert res.website_match_state == "MATCH"
    assert res.linkedin_match_state == "CONFLICT"
    assert "web_domain" in res.matched_fields
    assert "linkedin_url" in res.conflicting_fields

def test_br05_conflict_match():
    res = classification_service.classify_pair(
        upload_domain_norm="acme1.example",
        upload_linkedin_norm="linkedin.com/company/acme",
        upload_legal_name_norm="acme",
        upload_company_name_norm="acme",
        master_domain_norm="acme2.example",
        master_linkedin_norm="linkedin.com/company/acme",
        master_legal_name_norm="acme",
        master_company_name_norm="acme"
    )
    assert res.rule_id == "BR-05"
    assert res.match_status == "needs_review"
    assert res.website_match_state == "CONFLICT"
    assert res.linkedin_match_state == "MATCH"
    assert "linkedin_url" in res.matched_fields
    assert "web_domain" in res.conflicting_fields

def test_br06_conflict_conflict():
    res = classification_service.classify_pair(
        upload_domain_norm="acme1.example",
        upload_linkedin_norm="linkedin.com/company/acme-one",
        upload_legal_name_norm="acme",
        upload_company_name_norm="acme",
        master_domain_norm="acme2.example",
        master_linkedin_norm="linkedin.com/company/acme-two",
        master_legal_name_norm="acme",
        master_company_name_norm="acme"
    )
    assert res.rule_id == "BR-06"
    assert res.match_status == "not_a_match"

def test_br07_fuzzy_fallback_qualifies():
    # Master has both identifiers unavailable
    # Legal names match >= 80%
    res = classification_service.classify_pair(
        upload_domain_norm=None,
        upload_linkedin_norm=None,
        upload_legal_name_norm="westbridge property group",
        upload_company_name_norm="westbridge",
        master_domain_norm=None,
        master_linkedin_norm=None,
        master_legal_name_norm="westbridge property groups",
        master_company_name_norm="westbridge",
        fuzzy_threshold=80.0
    )
    assert res.rule_id == "BR-07"
    assert res.match_status == "potential_duplicate"
    assert res.name_similarity_percent is not None
    assert res.name_similarity_percent >= 80.0
    assert "fuzzy_legal_name" in res.match_methods

def test_br07_exact_80_threshold_boundary():
    # Test boundary where ratio is >= 80.0
    # "12345678" vs "12345679" -> length 8, 7 matches -> 14/16 = 87.5%
    # "12345" vs "1234" -> 8/9 = 88.8%
    # Let's test exact threshold check: threshold 80.0, score 80.0
    res = classification_service.classify_pair(
        upload_domain_norm=None,
        upload_linkedin_norm=None,
        upload_legal_name_norm="abcdefghij", # 10 chars
        upload_company_name_norm="abc",
        master_domain_norm=None,
        master_linkedin_norm=None,
        master_legal_name_norm="abcdefghkl", # 8 matches out of 10 -> 16/20 = 80.0%
        master_company_name_norm="abc",
        fuzzy_threshold=80.0
    )
    assert res.rule_id == "BR-07"
    assert res.match_status == "potential_duplicate"
    assert res.name_similarity_percent == 80.0

def test_br08_fuzzy_fallback_below_threshold():
    res = classification_service.classify_pair(
        upload_domain_norm=None,
        upload_linkedin_norm=None,
        upload_legal_name_norm="global property holdings",
        upload_company_name_norm="global property",
        master_domain_norm=None,
        master_linkedin_norm=None,
        master_legal_name_norm="global petroleum services",
        master_company_name_norm="global petroleum",
        fuzzy_threshold=80.0
    )
    # Ratio is ~61% < 80.0
    assert res.rule_id == "BR-08"
    assert res.match_status == "not_a_match"
    assert res.name_similarity_percent is not None
    assert res.name_similarity_percent < 80.0

def test_trimark_hard_negative_with_domains():
    # Trimark look-alike hard negative:
    # "Trimark Property Group" (trimarkproperties.example) vs
    # "Trimark Petroleum Group" (trimarkpetroleum.example)
    # Distinct domains conflict -> Not a duplicate, but flagged as related-name lead!
    res = classification_service.classify_pair(
        upload_domain_norm="trimarkproperties.example",
        upload_linkedin_norm=None,
        upload_legal_name_norm="trimark property group",
        upload_company_name_norm="trimark",
        master_domain_norm="trimarkpetroleum.example",
        master_linkedin_norm=None,
        master_legal_name_norm="trimark petroleum group",
        master_company_name_norm="trimark",
        is_related_lead_discovery=True
    )
    # Should NOT be high_confidence_candidate or potential_duplicate!
    assert res.match_status == "needs_review"
    assert res.discovery_type == "related_name"
    assert res.website_match_state == "CONFLICT"

def test_br09_fuzzy_unusable_legal_name():
    res = classification_service.classify_pair(
        upload_domain_norm=None,
        upload_linkedin_norm=None,
        upload_legal_name_norm=None, # unusable
        upload_company_name_norm="trimark",
        master_domain_norm=None,
        master_linkedin_norm=None,
        master_legal_name_norm="trimark property group",
        master_company_name_norm="trimark"
    )
    assert res.rule_id == "BR-09"
    assert res.match_status == "insufficient_data"
    assert res.name_similarity_percent is None

def test_br10_conflict_unavailable_with_master_identifier():
    # Master has domain populated, upload domain conflicts, linkedin unavailable
    res = classification_service.classify_pair(
        upload_domain_norm="upload.example",
        upload_linkedin_norm=None,
        upload_legal_name_norm="acme",
        upload_company_name_norm="acme",
        master_domain_norm="master.example",
        master_linkedin_norm=None,
        master_legal_name_norm="acme",
        master_company_name_norm="acme"
    )
    assert res.rule_id == "BR-10"
    assert res.match_status == "not_a_match"

def test_br11_unavailable_conflict_with_master_identifier():
    # Master has linkedin populated, upload linkedin conflicts, domain unavailable
    res = classification_service.classify_pair(
        upload_domain_norm=None,
        upload_linkedin_norm="linkedin.com/company/upload",
        upload_legal_name_norm="acme",
        upload_company_name_norm="acme",
        master_domain_norm=None,
        master_linkedin_norm="linkedin.com/company/master",
        master_legal_name_norm="acme",
        master_company_name_norm="acme"
    )
    assert res.rule_id == "BR-11"
    assert res.match_status == "not_a_match"

def test_br12_insufficient_comparable_identifiers():
    # Master has domain populated, but upload has neither domain nor linkedin
    res = classification_service.classify_pair(
        upload_domain_norm=None,
        upload_linkedin_norm=None,
        upload_legal_name_norm="acme corporation",
        upload_company_name_norm="acme",
        master_domain_norm="acme.example",
        master_linkedin_norm="linkedin.com/company/acme",
        master_legal_name_norm="acme corporation",
        master_company_name_norm="acme"
    )
    assert res.rule_id == "BR-12"
    assert res.match_status == "insufficient_data"
    assert res.name_similarity_percent is None

def test_provisional_dec01_upload_has_identifier_master_has_none():
    # DEC-01: master website AND LinkedIn are missing; upload may have domain
    # Fuzzy fallback still applies to master_both_unavailable
    res = classification_service.classify_pair(
        upload_domain_norm="somecompany.example",
        upload_linkedin_norm=None,
        upload_legal_name_norm="alpha beta consulting",
        upload_company_name_norm="alpha beta",
        master_domain_norm=None,
        master_linkedin_norm=None,
        master_legal_name_norm="alpha beta consulting",
        master_company_name_norm="alpha beta",
        fuzzy_threshold=80.0
    )
    assert res.rule_id == "BR-07"
    assert res.match_status == "potential_duplicate"
    assert res.name_similarity_percent == 100.0
