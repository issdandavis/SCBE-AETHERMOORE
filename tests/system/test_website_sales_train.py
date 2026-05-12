from __future__ import annotations

from scripts.system.website_sales_train import page_flags, score_page


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
