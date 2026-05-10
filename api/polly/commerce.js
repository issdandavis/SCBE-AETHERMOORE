'use strict';

function checkoutUrlFromEnv(envName, fallback) {
  const value = String(process.env[envName] || '').trim();
  if (!value) return fallback;

  // Stripe Payment Link IDs (`plink_...`) are not browser checkout URLs.
  // Vercel historically stored those internal IDs in SCBE_PAYMENT_LINK_*.
  // Only accept public URLs that a customer can actually click.
  if (value.startsWith('https://buy.stripe.com/test_')) {
    return fallback;
  }
  if (
    value.startsWith('https://buy.stripe.com/') ||
    value.startsWith('https://ko-fi.com/') ||
    value.startsWith('mailto:')
  ) {
    return value;
  }
  return fallback;
}

const PRODUCT_CATALOG = [
  {
    sku: 'scbe-service-credits',
    name: 'SCBE Service Credits',
    priceLabel: '$5+ pay-as-you-go',
    short:
      'Small credit top-ups for hosted SCBE routing, governed runs, reports, and provider/model usage. We pass through compute/model cost and add only a 2-5% coordination fee where usage is billable.',
    checkoutUrl: 'https://ko-fi.com/izdandavis',
    deliveryUrl: 'https://aethermoore.com/SCBE-AETHERMOORE/service-credits.html',
    keywords: [
      'credits',
      'service credits',
      'pay as you go',
      'pay-as-you-go',
      'token routing',
      'tokens',
      'usage',
      'hosted run',
      'hosted routing',
      'ollama cloud',
      'cloud models',
    ],
  },
  {
    sku: 'aethermoore-supporter',
    name: 'AetherMoore Supporter',
    priceLabel: '$20/month',
    short:
      'Monthly supporter subscription for people who want the open-source work to keep moving without scoping a formal service engagement.',
    checkoutUrl: checkoutUrlFromEnv(
      'SCBE_PAYMENT_LINK_SUPPORTER',
      'https://buy.stripe.com/00w8wQd4CbqfgJidOKdby0i'
    ),
    deliveryUrl: 'https://aethermoore.com/SCBE-AETHERMOORE/supporter.html',
    keywords: [
      'supporter',
      'aethermoore supporter',
      'monthly supporter',
      'support monthly',
      '20/month',
      '$20',
      'sponsor monthly',
      'small subscription',
    ],
  },
  {
    sku: 'ai-governance-snapshot',
    name: 'AI Governance Snapshot',
    priceLabel: '$500 one-time',
    short:
      'Fixed-scope governance assessment for one AI workflow. Includes a 2-page findings memo, three prioritized fixes, and an evidence checklist.',
    checkoutUrl: checkoutUrlFromEnv(
      'SCBE_PAYMENT_LINK_SNAPSHOT',
      'https://buy.stripe.com/eVqeVeaWu79ZgJi11Ydby0j'
    ),
    deliveryUrl: 'https://aethermoore.com/SCBE-AETHERMOORE/governance-snapshot.html',
    keywords: [
      'governance snapshot',
      'snapshot',
      'risk read',
      'fixed scope',
      'evidence checklist',
      'governance assessment',
    ],
  },
  {
    sku: 'governance-heartbeat',
    name: 'Governance Heartbeat',
    priceLabel: '$99/month',
    short:
      'Monthly governance scan for one AI workflow. Includes a short delta report, risk/change summary, recommended action list, and optional training/dataset capture notes.',
    checkoutUrl: checkoutUrlFromEnv(
      'SCBE_PAYMENT_LINK_HEARTBEAT',
      'mailto:issdandavis7795@gmail.com?subject=Governance%20Heartbeat%20signup'
    ),
    deliveryUrl: 'https://aethermoore.com/SCBE-AETHERMOORE/governance-snapshot.html#heartbeat',
    keywords: [
      'governance heartbeat',
      'heartbeat',
      'monthly governance',
      'monthly scan',
      'monthly ai governance',
      'monthly report',
      'recurring governance',
      'subscription governance',
      '$99',
      '99/month',
      '99 per month',
    ],
  },
  {
    sku: 'ai-governance-toolkit',
    name: 'SCBE AI Governance Toolkit',
    priceLabel: '$29 one-time',
    short:
      'Templates, decision records, setup guidance, buyer manual, and a support route for governed AI workflows. Shipped as a downloadable ZIP after Stripe checkout.',
    checkoutUrl: checkoutUrlFromEnv(
      'SCBE_PAYMENT_LINK_TOOLKIT',
      'https://buy.stripe.com/cNibJ25Ca2TJ9gQ3a6dby06'
    ),
    deliveryUrl: 'https://aethermoore.com/product-manual/ai-governance-toolkit.html',
    keywords: ['toolkit', 'governance toolkit', 'ai governance', 'templates', 'decision records'],
  },
  {
    sku: 'ai-security-training-vault',
    name: 'SCBE AI Security Training Vault',
    priceLabel: '$29 one-time',
    short:
      'Training data, projector weights, benchmark suite, and notebook materials for governed AI model work. Shipped as a downloadable ZIP after Stripe checkout.',
    checkoutUrl: checkoutUrlFromEnv(
      'SCBE_PAYMENT_LINK_VAULT',
      'https://buy.stripe.com/28E8wQ5Cacuj64EaCydby0g'
    ),
    deliveryUrl: 'https://aethermoore.com/product-manual/training-vault.html',
    keywords: [
      'training vault',
      'training data',
      'vault',
      'ai security',
      'benchmark suite',
      'notebooks',
    ],
  },
  {
    sku: 'five-dollar-tip-jar',
    name: '$5 SCBE Tip Jar',
    priceLabel: '$5 one-time',
    short:
      "If the open-source work has helped you and there's no formal engagement, a tip keeps the next release shipping.",
    checkoutUrl: 'https://ko-fi.com/izdandavis',
    deliveryUrl: '',
    keywords: ['tip', 'tip jar', 'donate', 'donation', 'support', 'buy a coffee', 'coffee'],
  },
];

const CONSULTING_TIERS = [
  {
    name: 'Short advisory call',
    price: '$300 / 60 min',
    fit: "one concrete AI safety / governance problem you're facing",
  },
  {
    name: 'Adversarial audit',
    price: '$5,000 – $15,000 / 1–3 weeks',
    fit: 'audit your production LLM endpoint or agent against the SCBE governance harness',
  },
  {
    name: 'Custom governance overlay',
    price: '$25,000 – $80,000 / 4–10 weeks',
    fit: 'build a deployable governance layer in front of your model API',
  },
  {
    name: 'Federal subcontract role',
    price: '$150 – $250 / hour, contract',
    fit: "AI safety / LLM evaluation work on a SAM-registered prime's contract",
  },
];

const SERVICE_CREDITS_POLICY = {
  name: 'SCBE Service Credits',
  serviceFeePercentRange: [2, 5],
  minimumTopUpUsd: 5,
  usageModel:
    'mostly-free local tools; service credits only pay for hosted routing, reports, delivery, storage, and provider/model usage',
  feeFormula:
    'customer_charge = actual_provider_cost + max(actual_provider_cost * service_fee_percent, small_run_floor)',
  preferredRouting:
    'local/Ollama and deterministic harness first; paid providers only when the run needs hosted capacity or a customer explicitly requests it',
};

// Apex aethermoore.com only resolves Pages content under the project-prefixed
// path; bare /hire returns 404 via the current Cloudflare routing. Use the
// canonical Pages URL until a custom rewrite is configured.
const CONSULTING_LANDING_URL = 'https://aethermoore.com/SCBE-AETHERMOORE/hire.html';
const HIRE_EMAIL = 'issdandavis7795@gmail.com';
const MEMBERSHIP_KOFI_URL = 'https://ko-fi.com/izdandavis';
const SERVICE_FAST_START_URL =
  'https://aethermoore.com/SCBE-AETHERMOORE/product-manual/service-fast-start.html';

const BUY_PATTERN =
  /\b(buy|purchase|order|checkout|pay\s+for|get\s+the|want\s+the|how\s+much|sign\s+me\s+up|add\s+to\s+cart)\b/i;

const CUSTOM_PATTERN =
  /\b(custom|bespoke|tailor|specifically\s+for|my\s+team|my\s+company|my\s+org|my\s+(use\s*case|workflow)|something\s+else|not\s+listed|build\s+me|hire\s+(you|issac|isaac|davis|me)|consulting|advisory|audit|engagement|contract|chatbot\s+safer|llm\s+safer|ai\s+safety|governance\s+help)\b/i;

const RESEARCH_PATTERN =
  /\b(research|find|look\s+up|search|investigate|what\s+do\s+you\s+know|recent|latest|news|paper|study|literature|sources?|cite|references?)\b/i;

const MEMBERSHIP_PATTERN =
  /\b(member|membership|subscribe|signup|sign\s*up|join|newsletter|follow|stay\s+updated|notify|sponsor|tip|donate)\b/i;

// HELP: bare "/help", "?", "what can you do" — meta-help asking what Polly
// understands. Sidebar starters advertise /help so this can't be a dead-end.
// Returns a structured capability list with one-click action chips.
const HELP_PATTERN =
  /^(\/help|\/\?|help)\s*$|^\?+\s*$|\b(what\s+can\s+you\s+(do|help\s+with)|what\s+do\s+you\s+know(\s+about)?\s*$|what\s+(commands?|options?|features?|topics?)\s+do\s+you\s+(have|support)|how\s+do\s+(you|i\s+use\s+you)\s+work|help\s+menu|show\s+me\s+(the\s+)?(commands?|options?|menu))\b/i;

// DISCOUNT: user is asking for cheaper / coupon / student / nonprofit /
// first-time pricing. Direct purchase lever — every reply ends with an
// active code + checkout link.
const DISCOUNT_PATTERN =
  /\b(discount|coupon|promo(\s*code)?|sale|deal|cheap(er)?|afford(able)?|student|non[-\s]?profit|nonprofit|charity|educational|first[-\s]?time|trial|free\s+trial|broke|tight\s+budget|on\s+a\s+budget|can'?t\s+afford)\b/i;

// CHAPTER: user wants a specific chapter — "chapter 1", "ch 2", "show me
// chapter 1 of the book". Numeric extraction handles "one"/"two" too.
const CHAPTER_PATTERN =
  /\b(chapter|ch\.?)\s*(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b/i;

// BOOK: catalog-level — "book", "ebook", "textbook", "table of contents",
// "what's in the book". CHAPTER is more specific so it runs first.
const BOOK_PATTERN =
  /\b(books?|ebooks?|textbooks?|manuals?|table\s+of\s+contents|what'?s\s+in\s+(the\s+)?(book|ebook)|read(ing)?\s+(material|list))\b/i;

// DEMO: "demo", "show me", "try it", "see it work", "play with it" —
// returns runnable chapter / notebook links. Distinct from BOOK because the
// user wants to *do* something, not browse.
const DEMO_PATTERN =
  /\b(demo|demos|show\s+me\s+(a|the|how|it)|try\s+(it|the|a)|see\s+it\s+(work|in\s+action)|play\s+with(\s+it)?|live\s+(example|demo)|interactive)\b/i;

// AGENT TASK: user wants to dispatch a one-shot agent run (research, monitor,
// scrape, web_search) through the SCBE agent-router workflow. Distinct from
// the `research` intent above which renders topic explainers — this intent
// hands off to /agents.html with the dispatch form pre-filled. Worded to
// catch action verbs that imply tool use ("the web", "these sites", "this
// URL", "/dispatch") without colliding with topic explainer phrases.
const AGENT_TASK_PATTERN =
  /\b(use\s+the\s+agent|run\s+(an?\s+)?agent|dispatch\s+(an?\s+)?agent|agent\s+router|search\s+the\s+web|monitor\s+(these|this|the)\s+(sites?|urls?|pages?)|scrape\s+(this|the)\s+(url|page|site)|crawl\s+(this|the)|fetch\s+(this|the)\s+url)\b|^\/(?:agent|dispatch|bus)\b/i;

const AGENT_TASK_PAGE_URL = 'https://aethermoore.com/SCBE-AETHERMOORE/agents.html';
const URL_EXTRACT_PATTERN = /\bhttps?:\/\/[^\s,]+/gi;

// Heuristic: pick the most-specific agent-router task the user implied.
// Defaults to research because that's the safest "tell me about X" run.
function classifyAgentTaskType(message) {
  const lower = String(message || '').toLowerCase();
  if (/\bmonitor\b/.test(lower)) return 'monitor';
  if (/\bscrape\b|\bcrawl\b|\bfetch\s+this\s+url\b/.test(lower)) return 'scrape';
  if (/\b(search\s+the\s+web|web\s+search)\b/.test(lower)) return 'web_search';
  if (/\bdispatch\b|\bbus\b|^\/(?:agent|dispatch|bus)\b/i.test(message || '')) return 'agent_bus';
  return 'research';
}

// Strip the trigger phrasing so the dispatch form's query field gets just
// the substantive part. Falls back to the whole message when nothing comes
// after the trigger (e.g. bare "run an agent").
function extractAgentQuery(message, taskType) {
  const text = String(message || '').trim();
  if (!text) return '';
  const urls = text.match(URL_EXTRACT_PATTERN);
  if (urls && (taskType === 'monitor' || taskType === 'scrape')) {
    return urls.join(',');
  }
  // Try splitting on common connector words so "search the web for AI safety"
  // → "AI safety".
  const split = text.split(/\b(?:for|on|about|regarding|of)\b/i);
  if (split.length >= 2) {
    const tail = split.slice(1).join(' ').trim();
    if (tail) return tail.replace(/^[,:\s-]+/, '').slice(0, 400);
  }
  return text.slice(0, 400);
}

// "I don't know what I need" signals. These are the chat-side mirror of the
// /products.html "find your fit" picker. When the user is uncertain, we walk
// them through 2-3 plain-language questions instead of dumping the catalog.
const GUIDE_PATTERN =
  /\b(help\s+me\s+(choose|pick|decide|figure|find|select)|what\s+should\s+i\s+(get|buy|use|pick|choose|order)|which\s+one\s+(is|fits|do|should|works)|i\s+(don'?t|do\s+not)\s+know\s+(what|which|where)|i'?m\s+new|i\s+am\s+new|where\s+(do|should)\s+i\s+(start|begin)|not\s+sure\s+(what|which|where)|guide\s+me|walk\s+me\s+through|recommend\s+(me|something|a\s+product)|find\s+my\s+fit|find\s+the\s+(right|best)\s+(one|tool|product|fit)|help\s+choosing)\b/i;

function resolveProduct(message) {
  const lower = String(message || '').toLowerCase();
  for (const product of PRODUCT_CATALOG) {
    for (const keyword of product.keywords) {
      if (lower.includes(keyword)) return product;
    }
  }
  return null;
}

function classifyIntent(message) {
  if (typeof message !== 'string' || !message.trim()) {
    return { name: 'general', confidence: 0, matchedTerm: null, product: null };
  }

  // HELP runs first so "/help" and "what can you do" never fall through to
  // a topic-explainer or LLM fallback. Sidebar starters advertise /help.
  const helpMatch = HELP_PATTERN.exec(message);
  if (helpMatch) {
    return { name: 'help', confidence: 0.95, matchedTerm: helpMatch[0], product: null };
  }

  // DISCOUNT runs before buy/guide so "I want a discount on the toolkit"
  // surfaces the coupon code instead of the full-price checkout, AND so
  // "I'm a student" doesn't get classified as custom-engagement intake.
  const discountMatch = DISCOUNT_PATTERN.exec(message);
  if (discountMatch) {
    return { name: 'discount', confidence: 0.88, matchedTerm: discountMatch[0], product: null };
  }

  // CHAPTER before BOOK because "chapter 1 of the book" matches both —
  // chapter is more specific.
  const chapterMatch = CHAPTER_PATTERN.exec(message);
  if (chapterMatch) {
    return { name: 'chapter', confidence: 0.9, matchedTerm: chapterMatch[0], product: null };
  }

  const bookMatch = BOOK_PATTERN.exec(message);
  if (bookMatch) {
    return { name: 'book', confidence: 0.85, matchedTerm: bookMatch[0], product: null };
  }

  const demoMatch = DEMO_PATTERN.exec(message);
  if (demoMatch) {
    return { name: 'demo', confidence: 0.82, matchedTerm: demoMatch[0], product: null };
  }

  // Guide goes before buy: "what should I get" / "i don't know what to buy"
  // signal uncertainty, not purchase intent. Walk them through the picker.
  const guideMatch = GUIDE_PATTERN.exec(message);
  if (guideMatch) {
    return { name: 'guide', confidence: 0.85, matchedTerm: guideMatch[0], product: null };
  }

  const buyMatch = BUY_PATTERN.exec(message);
  if (buyMatch) {
    const product = resolveProduct(message);
    return {
      name: 'buy',
      confidence: product ? 0.95 : 0.7,
      matchedTerm: buyMatch[0],
      product,
    };
  }

  const product = resolveProduct(message);
  if (product) {
    return { name: 'buy', confidence: 0.6, matchedTerm: product.sku, product };
  }

  // AGENT_TASK comes BEFORE custom AND research because its trigger phrases
  // ("search the web", "monitor these sites", "/dispatch") are more specific
  // than custom's broad keywords like "ai safety" and research's "search".
  const agentTaskMatch = AGENT_TASK_PATTERN.exec(message);
  if (agentTaskMatch) {
    return {
      name: 'agent_task',
      confidence: 0.82,
      matchedTerm: agentTaskMatch[0],
      product: null,
    };
  }

  const customMatch = CUSTOM_PATTERN.exec(message);
  if (customMatch) {
    return { name: 'custom', confidence: 0.85, matchedTerm: customMatch[0], product: null };
  }

  const researchMatch = RESEARCH_PATTERN.exec(message);
  if (researchMatch) {
    return { name: 'research', confidence: 0.8, matchedTerm: researchMatch[0], product: null };
  }

  // Topic-key fallback: "What is the harmonic wall?" doesn't match the
  // RESEARCH_PATTERN regex but contains a known topic key. If the message
  // hits a registered topic AND looks like a question/explanation prompt,
  // route it to research.
  const looksLikeQuestion =
    /\b(what|how|why|when|where|who|which|explain|describe|tell\s+me)\b/i.test(message);
  if (looksLikeQuestion) {
    const topic = resolveResearchTopic(message);
    if (topic) {
      return {
        name: 'research',
        confidence: 0.78,
        matchedTerm: topic.title,
        product: null,
      };
    }
  }

  const membershipMatch = MEMBERSHIP_PATTERN.exec(message);
  if (membershipMatch) {
    return { name: 'membership', confidence: 0.75, matchedTerm: membershipMatch[0], product: null };
  }

  return { name: 'general', confidence: 0, matchedTerm: null, product: null };
}

function renderBuyReply(product) {
  if (!product) {
    const lines = ['Current products. Click to check out:', ''];
    const actions = [];
    for (const item of PRODUCT_CATALOG) {
      lines.push(`- **${item.name}** — ${item.priceLabel}. ${item.short}`);
      actions.push({ label: `Buy ${item.name}`, url: item.checkoutUrl });
    }
    return { text: lines.join('\n'), actions };
  }

  let text = `**${product.name}** — ${product.priceLabel}.\n\n${product.short}\n\nCheckout: ${product.checkoutUrl}`;
  if (product.deliveryUrl) {
    text += `\nWhat you get + delivery: ${product.deliveryUrl}`;
  }
  if (product.sku === 'governance-heartbeat') {
    text +=
      '\n\nImmediate value after signup: reply with one workflow URL or repo path and the first scan starts as an intake checklist + baseline review.';
  }
  if (product.sku === 'ai-governance-snapshot') {
    text +=
      '\n\nImmediate value after purchase: buyer intake checklist, order recap, starter governance resources, and a 1-business-day human inspection window.';
  }
  const actions = [{ label: `Buy ${product.name}`, url: product.checkoutUrl }];
  if (product.deliveryUrl) {
    actions.push({ label: "What's inside", url: product.deliveryUrl });
  }
  return { text, actions };
}

function renderCustomReply(message) {
  const subject = 'Custom engagement inquiry — from Polly chat';
  const trimmed = String(message || '').slice(0, 300);
  const body =
    `Hi Issac,\n\n` +
    `I described to Polly: "${trimmed}"\n\n` +
    `I'd like to discuss:\n` +
    `[ ] Short advisory call ($300, 60 min)\n` +
    `[ ] Adversarial audit\n` +
    `[ ] Custom governance overlay\n` +
    `[ ] Federal subcontract conversation\n\n` +
    `Context:\n\n` +
    `Thanks,\n`;
  const mailto = `mailto:${HIRE_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;

  const tierLines = CONSULTING_TIERS.map((t) => `- **${t.name}** (${t.price}) — ${t.fit}`);
  const text =
    "What you're describing is custom — not in the stock catalog. " +
    'Four ways we can scope it:\n\n' +
    tierLines.join('\n') +
    '\n\nEvery serious inquiry now gets an instant fast-start packet: order recap, intake checklist, ' +
    'starter governance resources, human inspection window, and follow-up steps. Fastest path: email ' +
    'with a one-paragraph description of the outcome you want. I reply same day where I can.';
  const actions = [
    { label: 'Email Issac with this context', url: mailto },
    { label: 'Full hire details', url: CONSULTING_LANDING_URL },
    { label: 'Service fast-start packet', url: SERVICE_FAST_START_URL },
  ];
  return { text, actions };
}

const RESEARCH_TOPICS = [
  {
    keys: ['harmonic wall', 'h(d', 'safety score', 'governance score'],
    title: 'Harmonic wall (L12)',
    body:
      'The harmonic wall is the canonical SCBE safety score: H(d, pd) = 1/(1 + phi*d_H + 2*pd). ' +
      'd_H is hyperbolic distance from the safe-operating manifold (Layer 5), pd is the prior ' +
      'governance penalty. The score sits in (0, 1] — closer to 0 means heavier governance ' +
      'pressure, closer to 1 means safer operation. Layer 13 maps the score to ' +
      'ALLOW / QUARANTINE / ESCALATE / DENY decisions.',
    links: [
      {
        label: 'LAYER_INDEX.md',
        url: 'https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/LAYER_INDEX.md',
      },
      {
        label: 'src/harmonic/harmonicScaling.ts',
        url: 'https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/src/harmonic/harmonicScaling.ts',
      },
    ],
  },
  {
    keys: ['14-layer', 'pipeline', 'fourteen layer', 'layers'],
    title: '14-layer pipeline',
    body:
      'SCBE runs every interaction through 14 layers: L1-2 complex context + realification, ' +
      'L3-4 weighted Sacred Tongues + Poincare embedding, L5 hyperbolic distance, L6-7 breathing ' +
      'transform + Mobius phase, L8 multi-well Hamiltonian realms, L9-10 spectral + spin ' +
      'coherence, L11 triadic temporal distance, L12 harmonic wall, L13 risk decision, L14 audio ' +
      'telemetry. Adversarial intent costs grow exponentially with hyperbolic distance.',
    links: [
      {
        label: 'LAYER_INDEX.md',
        url: 'https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/LAYER_INDEX.md',
      },
      {
        label: 'SYSTEM_ARCHITECTURE.md',
        url: 'https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/SYSTEM_ARCHITECTURE.md',
      },
    ],
  },
  {
    keys: ['axiom', 'unitarity', 'locality', 'causality', 'symmetry', 'composition'],
    title: 'Quantum Axiom Mesh',
    body:
      'Five axioms enforce mathematical invariants across the 14 layers: Unitarity (norm ' +
      'preservation, L2/4/7), Locality (spatial bounds, L3/8), Causality (time-ordering, ' +
      'L6/11/13), Symmetry (gauge invariance, L5/9/10/12), Composition (pipeline integrity, ' +
      'L1/14). Each has a Python reference implementation and TypeScript canonical version.',
    links: [
      {
        label: 'CORE_AXIOMS_CANONICAL_INDEX.md',
        url: 'https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/docs/CORE_AXIOMS_CANONICAL_INDEX.md',
      },
    ],
  },
  {
    keys: [
      'sacred tongue',
      'tongues',
      'kor',
      'avali',
      'runethic',
      'cassisivadan',
      'umbroth',
      'draumric',
      'langues',
    ],
    title: 'Sacred Tongues / Langues Weighting System',
    body:
      'Six tongues (Kor’aelin, Avali, Runethic, Cassisivadan, Umbroth, Draumric) weight ' +
      'token vectors by phi-scaled energy. KO=1.00, AV=1.62, RU=2.62, CA=4.24, UM=6.85, ' +
      'DR=11.09. Each tongue has a 16x16 token grid (256 tokens each, 1536 total). The ' +
      'weighting drives Layer 3 transform and bridges into the Poincare embedding.',
    links: [
      {
        label: 'LANGUES_WEIGHTING_SYSTEM.md',
        url: 'https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/docs/LANGUES_WEIGHTING_SYSTEM.md',
      },
    ],
  },
  {
    keys: ['petri', 'anthropic petri'],
    title: 'Composing with Anthropic Petri',
    body:
      'Petri is detection-only auditing (36 dims, 181 seeds). SCBE composes with it as the ' +
      'enforcement layer: 173/173 Petri seeds blocked when SCBE wired in front. Petri tells ' +
      'you what the model would do; SCBE prevents the high-cost trajectories from running.',
    links: [
      {
        label: 'Anthropic Petri (2026 Q1)',
        url: 'https://www.anthropic.com/research',
      },
    ],
  },
  {
    keys: ['post-quantum', 'pqc', 'ml-kem', 'ml-dsa', 'kyber', 'dilithium'],
    title: 'Post-quantum primitives',
    body:
      'SCBE uses ML-KEM-768 (key encapsulation, formerly Kyber768), ML-DSA-65 (signatures, ' +
      'formerly Dilithium3), and AES-256-GCM throughout. Key auditor agent verifies key ' +
      'rotation and algorithm migration. liboqs is the underlying C library; Python and ' +
      'TypeScript bindings both target the new ML- naming with fall-through to the legacy names.',
    links: [
      {
        label: 'src/crypto/',
        url: 'https://github.com/issdandavis/SCBE-AETHERMOORE/tree/main/src/crypto',
      },
    ],
  },
  {
    keys: ['darpa', 'mathbac', 'clara', 'federal'],
    title: 'Federal proposals',
    body:
      'Two active DARPA proposals: CLARA FP-033 (submitted, award decision 2026-06-16) and ' +
      'MATHBAC abstract (submitted 2026-04-27, full proposal due 2026-06-16). SCBE positions ' +
      'as post-quantum hyperbolic successor to DARPA I2O Mission-oriented Resilient Clouds ' +
      '(MRC, ~2011-2017). SAM.gov UEI J4NXHM6N5F59, CAGE 1EXD5.',
    links: [{ label: 'Hire / federal subcontract', url: CONSULTING_LANDING_URL }],
  },
];

function resolveResearchTopic(message) {
  const lower = String(message || '').toLowerCase();
  for (const topic of RESEARCH_TOPICS) {
    for (const key of topic.keys) {
      if (lower.includes(key)) return topic;
    }
  }
  return null;
}

function renderResearchReply(message) {
  const topic = resolveResearchTopic(message);
  if (topic) {
    const linkLines = topic.links.map((link) => `- [${link.label}](${link.url})`);
    const text =
      `**${topic.title}**\n\n${topic.body}\n\n` +
      (linkLines.length ? `Read more:\n${linkLines.join('\n')}` : '');
    const actions = topic.links.map((link) => ({ label: link.label, url: link.url }));
    actions.push({
      label: 'Full repo',
      url: 'https://github.com/issdandavis/SCBE-AETHERMOORE',
    });
    return { text, actions };
  }

  const titles = RESEARCH_TOPICS.map((t) => `- ${t.title}`);
  const text =
    'I can answer research questions about any of these directly without an LLM call:\n\n' +
    titles.join('\n') +
    '\n\nAsk again with one of those terms in your question, or ' +
    'browse the full repo for the longer-form documentation.';
  const actions = [
    {
      label: 'LAYER_INDEX.md',
      url: 'https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/LAYER_INDEX.md',
    },
    {
      label: 'Full repo',
      url: 'https://github.com/issdandavis/SCBE-AETHERMOORE',
    },
  ];
  return { text, actions };
}

// Mirror of the /products.html "find your fit" picker, in chat form. We keep
// the four top-level routes terse so a cold visitor can pick one in one read.
const GUIDE_ROUTES = [
  {
    key: 'support',
    label: 'Support the open work',
    hint: 'Tip, monthly subscription, or pay-as-you-go credits',
    products: ['five-dollar-tip-jar', 'aethermoore-supporter', 'scbe-service-credits'],
  },
  {
    key: 'read',
    label: 'Get a written read on an AI workflow',
    hint: 'Snapshot for a one-time read, Heartbeat for monthly',
    products: ['ai-governance-snapshot', 'governance-heartbeat'],
  },
  {
    key: 'build',
    label: 'Build with the code yourself',
    hint: 'Toolkit templates, training vault, or the open repo',
    products: ['ai-governance-toolkit', 'ai-security-training-vault'],
  },
  {
    key: 'custom',
    label: 'My situation is custom',
    hint: 'Talk to a human about scoping it',
    products: [],
  },
];

const START_HERE_URL = 'https://aethermoore.com/SCBE-AETHERMOORE/start-here.html';
const PRODUCTS_PAGE_URL = 'https://aethermoore.com/SCBE-AETHERMOORE/products.html';

function renderGuideReply() {
  const lines = [
    'Happy to help you pick. Three or four routes cover almost everyone — which one fits?',
    '',
  ];
  for (const route of GUIDE_ROUTES) {
    lines.push(`- **${route.label}** — ${route.hint}`);
  }
  lines.push('');
  lines.push(
    "Tell me which one and I'll point you at the right product. " +
      "If you'd rather see all options at once, the full picker is on the products page."
  );

  const actions = [
    { label: 'Open the find-your-fit picker', url: PRODUCTS_PAGE_URL },
    { label: 'Three-route start page', url: START_HERE_URL },
    { label: 'Email Issac', url: `mailto:${HIRE_EMAIL}?subject=Help%20me%20pick%20a%20product` },
  ];
  return { text: lines.join('\n'), actions };
}

function renderMembershipReply() {
  const text =
    'Three ways to stay close to the work:\n\n' +
    '- **Use service credits** for pay-as-you-go hosted routing without a big subscription\n' +
    '- **AetherMoore Supporter** for a $20/month open-source support subscription\n' +
    '- **Governance Heartbeat** for a $99/month scan/report loop on one AI workflow\n' +
    '- **Sponsor / tip** the open-source work via Ko-fi\n' +
    '- **Watch the GitHub repo** for releases (`Watch -> Custom -> Releases`)\n' +
    '- **Email** me at the address below for a private update list\n\n' +
    'The target model is mostly free local tools, with credits only used when a hosted run, report, ' +
    'or provider/model call is needed. Billable usage is passed through with a small 2-5% SCBE coordination fee.';
  const actions = [
    {
      label: 'Service credits',
      url: 'https://aethermoore.com/SCBE-AETHERMOORE/service-credits.html',
    },
    {
      label: 'AetherMoore Supporter',
      url: checkoutUrlFromEnv(
        'SCBE_PAYMENT_LINK_SUPPORTER',
        'https://buy.stripe.com/00w8wQd4CbqfgJidOKdby0i'
      ),
    },
    {
      label: 'Governance Heartbeat',
      url: 'mailto:issdandavis7795@gmail.com?subject=Governance%20Heartbeat%20signup',
    },
    { label: 'Top up on Ko-fi', url: MEMBERSHIP_KOFI_URL },
    { label: 'Watch the repo', url: 'https://github.com/issdandavis/SCBE-AETHERMOORE' },
    { label: 'Email Issac', url: `mailto:${HIRE_EMAIL}` },
  ];
  return { text, actions };
}

// Discount codes. Real Stripe coupons should match these names so checkout
// auto-applies. If env vars are unset, the codes still surface (the user
// can copy them and we can wire Stripe coupons later — every reply ends
// with a working full-price checkout link as a safety hatch).
const DISCOUNT_CODES = {
  WELCOME20: {
    code: process.env.SCBE_DISCOUNT_CODE_WELCOME || 'WELCOME20',
    description: '20% off your first SCBE purchase',
    audience: 'First-time buyers — no verification needed',
  },
  STUDENT50: {
    code: process.env.SCBE_DISCOUNT_CODE_STUDENT || 'STUDENT50',
    description: '50% off any one-time SCBE product',
    audience: 'Verified students — email a .edu address for confirmation',
  },
  NONPROFIT50: {
    code: process.env.SCBE_DISCOUNT_CODE_NONPROFIT || 'NONPROFIT50',
    description: '50% off any one-time SCBE product or month of subscription',
    audience: '501(c)(3) non-profits — email your EIN for confirmation',
  },
};

// Book catalog. Mirrors book/<slug>/book.yaml; commerce.js runs in Vercel
// Node so the YAML is hand-mirrored here for v1 (one book, one chapter).
// When the catalog grows beyond 3 books, switch to a JSON sidecar built
// at deploy time.
const BOOK_CATALOG = [
  {
    slug: 'ai-governance-fundamentals',
    title: 'AI Governance Fundamentals',
    subtitle: 'A runnable book for engineers shipping their first governed LLM feature',
    sample_price: 'Free',
    bundle_price: '$19 one-time (planned)',
    catalog_url: 'https://aethermoore.com/SCBE-AETHERMOORE/book/ai-governance-fundamentals/',
    chapters: [
      {
        number: 1,
        slug: 'harmonic-wall',
        title: 'The Harmonic Wall — bounded safety scoring',
        who: 'AI engineers shipping LLM-backed features for the first time',
        what: 'How H(d, pd) = 1/(1+d+2*pd) bounds adversarial cost in (0, 1]',
        when: 'Before deploying any model that takes free-form user input',
        where: 'At the output gate, between the model response and the downstream caller',
        why: 'Unbounded safety scores let attackers walk the threshold without paying cost',
        estimated_minutes: 12,
        url: 'https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/book/ai-governance-fundamentals/chapter-01-harmonic-wall.md',
        notebook: null,
      },
    ],
  },
];

const NUMBER_WORDS = {
  one: 1,
  two: 2,
  three: 3,
  four: 4,
  five: 5,
  six: 6,
  seven: 7,
  eight: 8,
  nine: 9,
  ten: 10,
};

function extractChapterNumber(message) {
  const match = CHAPTER_PATTERN.exec(message);
  if (!match) return null;
  const raw = (match[2] || '').toLowerCase();
  if (/^\d+$/.test(raw)) return parseInt(raw, 10);
  return NUMBER_WORDS[raw] || null;
}

function findChapter(chapterNumber, bookSlug) {
  const book = bookSlug ? BOOK_CATALOG.find((b) => b.slug === bookSlug) : BOOK_CATALOG[0]; // default to first book when not specified
  if (!book) return null;
  const chapter = book.chapters.find((c) => c.number === chapterNumber);
  if (!chapter) return null;
  return { book, chapter };
}

function renderDiscountReply() {
  const lines = [
    "Yes — here's the current discount ladder. All codes go in the Stripe checkout's promo field:",
    '',
  ];
  for (const slot of Object.values(DISCOUNT_CODES)) {
    lines.push(`- **\`${slot.code}\`** — ${slot.description}. _${slot.audience}._`);
  }
  lines.push('');
  lines.push(
    "Pick a product and I'll send you to checkout — the code applies at the Stripe page. " +
      "If it doesn't auto-apply, paste the code into the promo field. If you need a custom rate " +
      '(volume / federal / open-source maintainer), email the address below.'
  );

  const actions = [
    {
      label: 'See all products',
      url: PRODUCTS_PAGE_URL,
    },
    {
      label: 'Help me pick',
      prompt: 'Help me choose a product',
    },
    {
      label: `Email about a custom rate`,
      url: `mailto:${HIRE_EMAIL}?subject=Custom%20discount%20rate&body=Hi%20Issac%2C%0A%0AMy%20situation%3A%20`,
    },
  ];
  return { text: lines.join('\n'), actions };
}

function renderBookReply() {
  const lines = [
    "Here's the runnable book catalog (every chapter ships with a tested code example):",
    '',
  ];
  for (const book of BOOK_CATALOG) {
    lines.push(`### ${book.title}`);
    lines.push(`_${book.subtitle}_`);
    lines.push('');
    lines.push(`Sample chapter: ${book.sample_price} · Full bundle: ${book.bundle_price}`);
    lines.push('');
    for (const ch of book.chapters) {
      lines.push(`- **Chapter ${ch.number}** — ${ch.title} _(≈${ch.estimated_minutes} min read)_`);
    }
    lines.push('');
  }
  lines.push(
    'Ask me about a specific chapter ("show me chapter 1") for the 5W summary + the full chapter link.'
  );

  const actions = [];
  const firstBook = BOOK_CATALOG[0];
  if (firstBook && firstBook.chapters.length) {
    const first = firstBook.chapters[0];
    actions.push({ label: `Read chapter ${first.number} free`, url: first.url });
    actions.push({
      label: `Show me chapter ${first.number}`,
      prompt: `Show me chapter ${first.number}`,
    });
  }
  actions.push({
    label: 'Buy the toolkit ($29)',
    url: PRODUCT_CATALOG.find((p) => p.sku === 'ai-governance-toolkit').checkoutUrl,
  });
  return { text: lines.join('\n'), actions };
}

function renderChapterReply(message) {
  const chapterNumber = extractChapterNumber(message);
  if (!chapterNumber) {
    return renderBookReply();
  }
  const found = findChapter(chapterNumber);
  if (!found) {
    const lines = [`I don't have a chapter ${chapterNumber} yet. The current catalog:`, ''];
    for (const book of BOOK_CATALOG) {
      lines.push(`**${book.title}** — ${book.chapters.length} chapter(s) shipped`);
    }
    return {
      text: lines.join('\n'),
      actions: [{ label: 'Browse the book', prompt: 'Show me the book' }],
    };
  }

  const { book, chapter } = found;
  const lines = [
    `**${book.title}** · Chapter ${chapter.number}: ${chapter.title}`,
    '',
    `**Who** — ${chapter.who}`,
    `**What** — ${chapter.what}`,
    `**When** — ${chapter.when}`,
    `**Where** — ${chapter.where}`,
    `**Why** — ${chapter.why}`,
    '',
    `≈${chapter.estimated_minutes} min read. Every code example is verified against the live SCBE codebase on every CI run.`,
  ];
  const actions = [{ label: 'Read the full chapter', url: chapter.url }];
  if (chapter.notebook) {
    actions.push({ label: 'Try the notebook', url: chapter.notebook });
  }
  actions.push({
    label: 'Buy the toolkit ($29)',
    url: PRODUCT_CATALOG.find((p) => p.sku === 'ai-governance-toolkit').checkoutUrl,
  });
  actions.push({ label: 'Discount codes', prompt: 'discount' });
  return { text: lines.join('\n'), actions };
}

function renderDemoReply() {
  const lines = [
    'Live demos are linked from the chapters — every chapter ships with a runnable example.',
    '',
  ];
  let count = 0;
  for (const book of BOOK_CATALOG) {
    for (const ch of book.chapters) {
      lines.push(
        `- **${ch.title}** _(book: ${book.title})_ — read the chapter, paste the example.`
      );
      count += 1;
    }
  }
  if (!count) {
    lines.push('_No chapters published yet — check back soon._');
  }
  lines.push('');
  lines.push(
    "If you'd rather have me run a real-time agent against the web instead, ask me to 'search the web for X' or 'monitor these sites'."
  );

  const actions = [];
  const firstBook = BOOK_CATALOG[0];
  if (firstBook && firstBook.chapters.length) {
    const first = firstBook.chapters[0];
    actions.push({ label: `Read ${first.title}`, url: first.url });
  }
  actions.push({
    label: 'Run a research agent instead',
    prompt: 'search the web for SCBE governance latest',
  });
  actions.push({ label: 'Browse all chapters', prompt: 'Show me the book' });
  return { text: lines.join('\n'), actions };
}

function renderHelpReply() {
  const text =
    "Here's what I can do — pick a chip below or just ask in plain English.\n\n" +
    '**Pick a tool**\n' +
    '- "Help me choose a product" → 3-question picker\n' +
    '- "Buy the toolkit" / "I want the snapshot" → direct checkout\n' +
    '- "I need a custom audit" → scoping path\n' +
    '- "discount" / "student" / "nonprofit" → active coupon codes\n\n' +
    '**Ask a question**\n' +
    '- "What is the harmonic wall?" → topic explainer\n' +
    '- "Tell me about the 14-layer pipeline" / Sacred Tongues / axiom mesh\n\n' +
    '**Read the runnable book**\n' +
    '- "Show me the book" / "table of contents" → catalog\n' +
    '- "Show me chapter 1" → 5W summary + full chapter link\n' +
    '- "demo" / "show me a demo" → runnable chapter examples\n\n' +
    '**Run an agent**\n' +
    '- "Search the web for X" → web_search agent\n' +
    '- "Monitor these sites: a.com, b.com" → monitor agent\n' +
    '- "Scrape this URL: https://..." → scrape agent\n' +
    '- "/agent" or "/dispatch" → agent_bus event\n\n' +
    '**Stay close**\n' +
    '- "Subscribe / tip / sponsor" → membership routes\n' +
    '- "Watch the repo" → GitHub releases\n\n' +
    "If your question doesn't match any of the above, I'll fall back to a free " +
    'LLM with the SCBE governance pipeline checking the response.';

  const actions = [
    { label: 'Help me choose a product', prompt: 'Help me choose a product' },
    { label: 'Show me chapter 1 of the book', prompt: 'Show me chapter 1' },
    { label: 'Discount codes', prompt: 'discount' },
    { label: 'What is the harmonic wall?', prompt: 'What is the harmonic wall?' },
    { label: 'Browse all products', url: PRODUCTS_PAGE_URL },
  ];
  return { text, actions };
}

function renderAgentTaskReply(message) {
  const taskType = classifyAgentTaskType(message);
  const query = extractAgentQuery(message, taskType);
  const params = new URLSearchParams();
  params.set('task', taskType);
  if (query) params.set('query', query);
  const dispatchUrl = `${AGENT_TASK_PAGE_URL}?${params.toString()}`;

  const taskDescriptions = {
    research: 'deep web research with AI summary and source citations',
    monitor: 'quick-read of multiple URLs (titles, word counts, key text)',
    scrape: 'structured extraction from one URL (text, links, metadata, JSON-LD)',
    web_search: 'web search + AI summary',
    agent_bus: 'one SCBE agent-bus event through the typed envelope pipeline',
  };
  const description = taskDescriptions[taskType] || taskDescriptions.research;

  const lines = [
    `I can route that to the **${taskType}** agent — ${description}.`,
    '',
    query
      ? `I pulled this query from your message: \`${query.slice(0, 200)}\``
      : "Click through and I'll leave the query field blank for you to fill in.",
    '',
    'The agent runs on a free GitHub server (the Vercel bridge will queue it ' +
      'when configured, otherwise the page falls back to opening the GitHub ' +
      'workflow form). Results land on the Latest Results panel and are ' +
      'published to the public agent-data feed when the run finishes.',
  ];

  const actions = [
    { label: `Open ${taskType} dispatch`, url: dispatchUrl },
    { label: 'See all agent tasks', url: AGENT_TASK_PAGE_URL },
    {
      label: 'Pick a different tool',
      prompt: 'Help me choose a product',
    },
  ];
  return { text: lines.join('\n'), actions, taskType, query };
}

module.exports = {
  PRODUCT_CATALOG,
  CONSULTING_TIERS,
  SERVICE_CREDITS_POLICY,
  CONSULTING_LANDING_URL,
  HIRE_EMAIL,
  MEMBERSHIP_KOFI_URL,
  SERVICE_FAST_START_URL,
  RESEARCH_TOPICS,
  GUIDE_ROUTES,
  START_HERE_URL,
  PRODUCTS_PAGE_URL,
  AGENT_TASK_PAGE_URL,
  BOOK_CATALOG,
  DISCOUNT_CODES,
  classifyIntent,
  classifyAgentTaskType,
  extractAgentQuery,
  extractChapterNumber,
  findChapter,
  renderBuyReply,
  renderCustomReply,
  renderGuideReply,
  renderHelpReply,
  renderMembershipReply,
  renderResearchReply,
  renderAgentTaskReply,
  renderBookReply,
  renderChapterReply,
  renderDemoReply,
  renderDiscountReply,
  resolveProduct,
  resolveResearchTopic,
};
