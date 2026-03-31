(() => {
  const body = document.body;
  if (!body || body.dataset.pollyMounted === 'true') return;
  body.dataset.pollyMounted = 'true';

  const root = body.dataset.pollyRoot || '.';
  const context = body.dataset.pollyContext || 'site';
  const contexts = {
    home: {
      kicker: 'Site guide',
      title: "Polly's got the map.",
      copy: 'The homepage is the front door: offers first, demos second, proof stack behind them.',
      prompt: 'I am on the SCBE-AETHERMOORE homepage. Summarize the site, separate the buy lane, the demo lane, and the research proof lane, and tell me which one I should open next.'
    },
    demos: {
      kicker: 'Demo guide',
      title: 'Polly can orient this page.',
      copy: 'This page is the try-it-now lane for working public surfaces, not the full manual or the full research archive.',
      prompt: 'I am on the SCBE demo page. Explain the working surfaces in plain language, then tell me whether I should open the product path, the manual hub, or the research proof stack next.'
    },
    games: {
      kicker: 'Games guide',
      title: 'This is the public play shelf.',
      copy: 'Use this page for AI-playable arenas, browser-task lanes, public Hugging Face models and datasets, host-side training bridges, and future long-horizon game routes without mixing them into the sales page or the proof stack.',
      prompt: 'I am on the SCBE games and training hub. Separate what is live now, what is hosted on Hugging Face, what is part of the host-side training bridge, what is benchmark proof, and what is still planned, then tell me whether I should open the arena, the browser demo, the model dock, the training bridge, the eval lab, or the product path next.'
    },
    research: {
      kicker: 'Research guide',
      title: 'Keep proof and theory separated.',
      copy: 'This page is the back-page proof stack behind the demos and sales surfaces. Use it when you need evidence and claim boundaries first.',
      prompt: 'I am on the SCBE research page. Separate what is benchmarked, what is implemented, and what is still exploratory, then tell me whether I should go next to demos, manuals, support, or the product page.'
    },
    articles: {
      kicker: 'Article guide',
      title: 'Read the field notes in order.',
      copy: 'This hub is for public writing and launch-facing notes, not the whole repo or every private research artifact.',
      prompt: 'I am on the SCBE article hub. Summarize the featured articles, keep product claims separate from research claims, and tell me which one I should read next.'
    },
    support: {
      kicker: 'Support guide',
      title: 'Start with the exact break.',
      copy: 'Support works faster when you keep the failure concrete: what you clicked, what you expected, and what happened instead.',
      prompt: 'I am on the SCBE support page. Help me troubleshoot one issue at a time. First ask for the exact error text, the page or command I used, my OS, and what I expected to happen.'
    },
    manual: {
      kicker: 'Manual guide',
      title: 'Use the bought thing first.',
      copy: 'Manual pages explain how to use the purchased package, not the entire research stack.',
      prompt: 'I am on the SCBE product manual hub. Help me identify which package page I need, what should have been delivered, and the shortest safe setup path.'
    },
    delivery: {
      kicker: 'Delivery guide',
      title: 'Receipt, manual, bundle, then keys if needed.',
      copy: 'Do not assume a package needs a key unless the delivery page or manual says it does.',
      prompt: 'I am on the SCBE delivery and access page. Help me verify what should have arrived after purchase and what support details I should gather before emailing.'
    },
    network: {
      kicker: 'Ops map',
      title: 'Follow the flows.',
      copy: 'Use this when you want the external writing lane (Medium/GitHub) and the internal public lanes (demos, research, manuals) without losing the thread.',
      prompt: 'I am on the SCBE network page. Summarize the external links (Medium, GitHub, YouTube), then give me the shortest route into demos, manuals, and benchmark proof based on my goal.'
    },
    site: {
      kicker: 'Page guide',
      title: 'Polly can route you.',
      copy: 'Use the quick links first, then hand the prompt to your AI if you want guided help.',
      prompt: 'I am browsing the SCBE-AETHERMOORE site. Summarize this page, tell me what it is for, and tell me which page I should open next.'
    }
  };

  const data = contexts[context] || contexts.site;
  const links = [
    { href: `${root}/index.html`, title: 'Home', text: 'Front door for offers, demos, and proof routing.' },
    { href: `${root}/network.html`, title: 'Network', text: 'External links, writing lanes, and AI-readable entry points.' },
    { href: `${root}/demos/index.html`, title: 'Demos', text: 'Working browser demos and operator-facing public surfaces.' },
    { href: `${root}/games/index.html`, title: 'Games', text: 'AI-playable arenas, model docks, training bridges, and long-horizon game lanes.' },
    { href: 'https://huggingface.co/issdandavis', title: 'Hugging Face', text: 'Public models, datasets, and Spaces for SCBE.' },
    { href: `${root}/redteam.html`, title: 'Red Team', text: 'Current public benchmark surface, dataset link, and eval entry path.' },
    { href: `${root}/articles/index.html`, title: 'Articles', text: 'Field notes, public explanations, and launch-facing writing.' },
    { href: `${root}/research/index.html`, title: 'Research', text: 'Back-page proof stack, benchmarks, and active experiment tracks.' },
    { href: `${root}/product-manual/index.html`, title: 'Manuals', text: 'Buyer-facing package manuals and setup guides.' },
    { href: `${root}/support.html`, title: 'Support', text: 'Delivery, setup, AI troubleshooting, and broken-link recovery.' },
    { href: 'https://github.com/issdandavis', title: 'GitHub', text: 'Repos, code, and source writing.' },
    { href: 'https://medium.com/@issdandavis7795', title: 'Medium', text: 'External essays and public drafts.' }
  ];

  const launcher = document.createElement('button');
  launcher.className = 'polly-launcher';
  launcher.type = 'button';
  launcher.setAttribute('aria-expanded', 'false');
  launcher.innerHTML = '<span class="polly-dot"></span><span>Polly</span>';

  const panel = document.createElement('aside');
  panel.className = 'polly-panel';
  panel.setAttribute('aria-hidden', 'true');
  panel.innerHTML = `
    <div class="polly-panel-inner">
      <div class="polly-kicker">${data.kicker}</div>
      <div class="polly-title">${data.title}</div>
      <p class="polly-copy">${data.copy}</p>

      <section class="polly-section">
        <h3>Quick links</h3>
        <div class="polly-link-grid">
          ${links.map(link => `
            <a class="polly-link" href="${link.href}">
              <strong>${link.title}</strong>
              <span>${link.text}</span>
            </a>
          `).join('')}
        </div>
      </section>

      <section class="polly-section">
        <h3>Ask your AI</h3>
        <div class="polly-prompt">
          <p class="polly-prompt-copy" id="pollyPromptText">${data.prompt}</p>
          <div class="polly-actions">
            <button class="polly-btn" type="button" id="pollyCopyPrompt">Copy prompt</button>
            <a class="polly-btn" href="mailto:aethermoregames@pm.me?subject=SCBE%20Support%20Help">Email support</a>
          </div>
          <div class="polly-status" id="pollyStatus" aria-live="polite"></div>
        </div>
      </section>
    </div>
  `;

  launcher.addEventListener('click', () => {
    const open = panel.classList.toggle('open');
    launcher.setAttribute('aria-expanded', String(open));
    panel.setAttribute('aria-hidden', String(!open));
  });

  panel.addEventListener('click', async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    if (target.id !== 'pollyCopyPrompt') return;
    const promptEl = panel.querySelector('#pollyPromptText');
    const statusEl = panel.querySelector('#pollyStatus');
    if (!promptEl || !statusEl) return;

    try {
      await navigator.clipboard.writeText(promptEl.textContent || '');
      statusEl.textContent = 'Prompt copied.';
    } catch {
      statusEl.textContent = 'Copy failed. Select the text manually.';
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      panel.classList.remove('open');
      launcher.setAttribute('aria-expanded', 'false');
      panel.setAttribute('aria-hidden', 'true');
    }
  });

  document.body.appendChild(launcher);
  document.body.appendChild(panel);
})();
