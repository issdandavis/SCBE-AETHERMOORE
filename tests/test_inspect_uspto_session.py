import pytest

try:
    from scripts.system.inspect_uspto_session import classify_session, cookie_domain_summary, trim_text
except ImportError:
    classify_session = cookie_domain_summary = trim_text = None

pytestmark = pytest.mark.skipif(classify_session is None, reason="scripts.system.inspect_uspto_session not importable")


def test_classify_session_detects_auth_wall_from_password_field() -> None:
    dom = {
        "title": "Sign in - USPTO",
        "headings": ["Sign in"],
        "forms": [{"fields": [{"type": "email"}, {"type": "password"}]}],
    }
    result = classify_session("https://auth.uspto.gov/login", dom)
    assert result["state"] == "auth_wall"
    assert result["has_password_field"] is True


def test_classify_session_detects_patent_center_surface() -> None:
    dom = {
        "title": "Patent Center",
        "headings": ["Existing submissions"],
        "forms": [{"fields": [{"type": "text"}]}],
    }
    result = classify_session("https://patentcenter.uspto.gov/applications", dom)
    assert result["state"] == "patent_center_surface"
    assert result["patent_center_markers"] is True


def test_cookie_domain_summary_counts_domains_and_flags() -> None:
    summary = cookie_domain_summary(
        [
            {"domain": ".uspto.gov", "secure": True, "httpOnly": True},
            {"domain": ".uspto.gov", "secure": True, "httpOnly": False},
            {"domain": ".auth.uspto.gov", "secure": False, "httpOnly": True},
        ]
    )
    assert summary["total"] == 3
    assert summary["secure_count"] == 2
    assert summary["http_only_count"] == 2
    assert summary["domains"][0] == {"domain": "uspto.gov", "count": 2}


def test_trim_text_collapses_whitespace_and_clips() -> None:
    assert trim_text(" a   b \n c ", 20) == "a b c"
    assert trim_text("x" * 20, 10).endswith("...")
