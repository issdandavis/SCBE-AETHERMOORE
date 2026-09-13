from __future__ import annotations

import pytest

from scripts.system.website_sales_train import ROOT, audit_page, extract_ctas, page_flags, score_page


@pytest.mark.parametrize(
    "classes", ["btn btn-primary", "button button-primary", "button-primary extra button", "btn-primary\tbtn"]
)
def test_primary_actions_accept_both_site_vocabularies(classes: str) -> None:
    html = f"<section class='hero'><div><a href='#work' class='{classes}'>Explore</a></div></section>"
    ctas = extract_ctas(html)
    assert (ctas.primary, ctas.hero_primary) == (1, 1)
    assert page_flags(html)["has_primary_cta_in_hero"]
    assert "No primary CTA found." not in score_page(html)[1]


def test_non_actions_and_hidden_markup_do_not_inflate_counts() -> None:
    html = """
      <!-- <a class="btn btn-primary" href="/">comment</a> -->
      <style>.btn btn-primary {color:red}</style>
      <script>const example = '<a class="btn btn-primary" href="/">script</a>';</script>
      <template><a class="button-primary" href="/">template</a></template>
      <div hidden><a class="button-primary" href="/">hidden</a></div>
      <div aria-hidden="true"><button class="button-primary">hidden</button></div>
      <div style="display: none"><button class="button-primary">hidden</button></div>
      <button disabled class="button-primary">disabled</button>
      <a aria-disabled="true" class="button-primary" href="/">disabled</a>
      <div class="btn btn-primary">decoration</div>
      <a class="button-primary">no destination</a>
      <a href="#" class="button-primary">placeholder</a>
      <a href="javascript:void(0)" class="button-primary">placeholder</a>
      <a href="/docs" class="button-primary-extra">different class</a>
    """
    ctas = extract_ctas(html)
    assert (ctas.primary, ctas.secondary, ctas.hero_primary) == (0, 0, 0)
    assert "No primary CTA found." in score_page(html)[1]


def test_hero_scope_ends_and_void_elements_do_not_hide_later_actions() -> None:
    ctas = extract_ctas("""
      <header id="offer"><img hidden src="x"><a href="/start" class="btn-primary">Start</a></header>
      <footer><button class="button-primary">Submit</button><a class="button-secondary" href="/">Back</a></footer>
    """)
    assert (ctas.primary, ctas.secondary, ctas.hero_primary) == (2, 1, 1)


def test_actual_homepage_primary_action_is_recognized() -> None:
    audit = audit_page(ROOT / "docs" / "index.html")
    assert audit.primary_cta_count >= 1
    assert audit.secondary_cta_count >= 1
    assert audit.flags["has_primary_cta_in_hero"]
    assert "No primary CTA found." not in audit.risks


def test_price_detection_accepts_non_29_offers() -> None:
    html = """
    <main>
      <header id="offer">
        <h1>Workflow Snapshot</h1>
        <a class="btn btn-primary" href="https://example.com">Start for $99</a>
      </header>
      <section id="includes">
        decision record threshold pilot checklist review notes manual delivery
      </section>
      <section id="faq">FAQ</section>
      <p>one-time no subscription manual delivery support success check</p>
      <p>good fit and not for every buyer</p>
      <a href="use-cases/governed-ai-workflows.html">Use cases</a>
      <a href="comparison/toolkit-vs-full-repo.html">Comparison</a>
      <a href="proof/why-the-manual-exists.html">Manual proof</a>
      <a href="redteam.html">Red team</a>
      <a href="proof/red-team-summary.html">Red-team summary</a>
      <div>final cta</div>
    </main>
    """

    flags = page_flags(html)
    metrics, risks, _strengths = score_page(html)

    assert flags["has_price"] is True
    assert metrics["offer_strength"] >= 8.0
    assert "No primary CTA found." not in risks
