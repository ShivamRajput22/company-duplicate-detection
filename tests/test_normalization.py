import pytest
from app.services.normalization_service import normalization_service

def test_company_name_normalization_suffixes():
    # Legal suffixes stripped
    assert normalization_service.normalize_name("Acme Corp") == "acme"
    assert normalization_service.normalize_name("Acme Corporation") == "acme"
    assert normalization_service.normalize_name("Acme LLC") == "acme"
    assert normalization_service.normalize_name("Acme Inc.") == "acme"
    assert normalization_service.normalize_name("Acme Ltd.") == "acme"
    assert normalization_service.normalize_name("Acme Limited") == "acme"
    assert normalization_service.normalize_name("Acme Technologies Ltd.") == "acme technologies"

def test_protected_business_words_preserved():
    # Meaningful business words MUST BE PRESERVED
    assert normalization_service.normalize_name("Trimark Property Group LLC") == "trimark property group"
    assert normalization_service.normalize_name("Trimark Petroleum Group Inc") == "trimark petroleum group"
    assert normalization_service.normalize_name("Westbridge Properties LLC") == "westbridge properties"
    assert normalization_service.normalize_name("Westbridge Property LLC") == "westbridge property"
    # Never conflate Property and Properties
    assert normalization_service.normalize_name("Westbridge Properties") != normalization_service.normalize_name("Westbridge Property")

def test_unicode_and_punctuation():
    # Unicode NFKC and punctuation
    assert normalization_service.normalize_name("Café & Co. LLC") == "cafe and"
    assert normalization_service.normalize_name("A.B.C. Technologies") == "a b c technologies"

def test_null_like_names():
    assert normalization_service.normalize_name(None) is None
    assert normalization_service.normalize_name("") is None
    assert normalization_service.normalize_name("   ") is None
    assert normalization_service.normalize_name("N/A") is None
    assert normalization_service.normalize_name("null") is None
    assert normalization_service.normalize_name("-") is None

def test_domain_normalization():
    # URL variants of same domain
    domain1, status1 = normalization_service.normalize_domain("https://www.example.com/about?ref=1")
    domain2, status2 = normalization_service.normalize_domain("EXAMPLE.COM")
    domain3, status3 = normalization_service.normalize_domain("http://subdomain.example.com")
    assert status1 == "valid"
    assert status2 == "valid"
    assert status3 == "valid"
    assert domain1 == "example.com"
    assert domain2 == "example.com"
    assert domain3 == "example.com"

    # Different registered domains do not match
    domain4, _ = normalization_service.normalize_domain("example.net")
    assert domain4 != domain1

    # Invalid / generic
    _, status_generic = normalization_service.normalize_domain("https://www.linkedin.com")
    assert status_generic == "invalid"

    _, status_ip = normalization_service.normalize_domain("192.168.1.1")
    assert status_ip == "invalid"

    _, status_missing = normalization_service.normalize_domain("")
    assert status_missing == "missing"

def test_linkedin_normalization():
    # Valid company URL variants
    url1, status1 = normalization_service.normalize_linkedin("https://www.linkedin.com/company/acme-corp/")
    url2, status2 = normalization_service.normalize_linkedin("http://linkedin.com/company/acme-corp?trk=public_profile")
    assert status1 == "valid"
    assert status2 == "valid"
    assert url1 == "linkedin.com/company/acme-corp"
    assert url2 == "linkedin.com/company/acme-corp"

    # Personal profile /in/ rejected
    _, status_in = normalization_service.normalize_linkedin("https://www.linkedin.com/in/john-doe")
    assert status_in == "invalid"

    # Lookalike host rejected
    _, status_evil = normalization_service.normalize_linkedin("https://www.linkedin.com.evil.test/company/acme")
    assert status_evil == "invalid"

    # Missing
    _, status_missing = normalization_service.normalize_linkedin(None)
    assert status_missing == "missing"
