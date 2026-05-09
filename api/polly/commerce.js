'use strict';

const PRODUCT_CATALOG = [
  {
    sku: 'ai-governance-toolkit',
    name: 'SCBE AI Governance Toolkit',
    priceLabel: '$29 one-time',
    short:
      'Templates, decision records, setup guidance, buyer manual, and a support route for governed AI workflows. Shipped as a downloadable ZIP after Stripe checkout.',
    checkoutUrl: 'https://buy.stripe.com/cNibJ25Ca2TJ9gQ3a6dby06',
    deliveryUrl: 'https://aethermoore.com/product-manual/ai-governance-toolkit.html',
    keywords: ['toolkit', 'governance toolkit', 'ai governance', 'templates', 'decision records'],
  },
  {
    sku: 'ai-security-training-vault',
    name: 'SCBE AI Security Training Vault',
    priceLabel: '$29 one-time',
    short:
      'Training data, projector weights, benchmark suite, and notebook materials for governed AI model work. Shipped as a downloadable ZIP after Stripe checkout.',
    checkoutUrl: 'https://buy.stripe.com/28E8wQ5Cacuj64EaCydby0g',
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
    checkoutUrl: 'https://ko-fi.com/Y8Y51UQYWZ',
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

const CONSULTING_LANDING_URL = 'https://aethermoore.com/hire';
const HIRE_EMAIL = 'issdandavis7795@gmail.com';
const MEMBERSHIP_KOFI_URL = 'https://ko-fi.com/Y8Y51UQYWZ';

const BUY_PATTERN =
  /\b(buy|purchase|order|checkout|pay\s+for|get\s+the|want\s+the|how\s+much|sign\s+me\s+up|add\s+to\s+cart)\b/i;

const CUSTOM_PATTERN =
  /\b(custom|bespoke|tailor|specifically\s+for|my\s+team|my\s+company|my\s+org|my\s+(use\s*case|workflow)|something\s+else|not\s+listed|build\s+me|hire\s+you|consulting|advisory|audit|engagement|contract)\b/i;

const RESEARCH_PATTERN =
  /\b(research|find|look\s+up|search|investigate|what\s+do\s+you\s+know|recent|latest|news|paper|study|literature|sources?|cite|references?)\b/i;

const MEMBERSHIP_PATTERN =
  /\b(member|membership|subscribe|signup|sign\s*up|join|newsletter|follow|stay\s+updated|notify|sponsor|tip|donate)\b/i;

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

  const customMatch = CUSTOM_PATTERN.exec(message);
  if (customMatch) {
    return { name: 'custom', confidence: 0.85, matchedTerm: customMatch[0], product: null };
  }

  const researchMatch = RESEARCH_PATTERN.exec(message);
  if (researchMatch) {
    return { name: 'research', confidence: 0.8, matchedTerm: researchMatch[0], product: null };
  }

  const membershipMatch = MEMBERSHIP_PATTERN.exec(message);
  if (membershipMatch) {
    return { name: 'membership', confidence: 0.75, matchedTerm: membershipMatch[0], product: null };
  }

  return { name: 'general', confidence: 0, matchedTerm: null, product: null };
}

function renderBuyReply(product) {
  if (!product) {
    const lines = ['Three current products. Click to check out:', ''];
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
    '\n\nFastest path: email with a one-paragraph description of the ' +
    'outcome you want. I reply same day where I can.';
  const actions = [
    { label: 'Email Issac with this context', url: mailto },
    { label: 'Full hire details', url: CONSULTING_LANDING_URL },
  ];
  return { text, actions };
}

function renderMembershipReply() {
  const text =
    'Three ways to stay close to the work:\n\n' +
    '- **Sponsor / tip** the open-source work via Ko-fi\n' +
    '- **Watch the GitHub repo** for releases (`Watch -> Custom -> Releases`)\n' +
    '- **Email** me at the address below for a private update list\n\n' +
    'There is no paid membership tier yet — open-source first; ' +
    'sponsorships keep the next release shipping.';
  const actions = [
    { label: 'Tip on Ko-fi', url: MEMBERSHIP_KOFI_URL },
    { label: 'Watch the repo', url: 'https://github.com/issdandavis/SCBE-AETHERMOORE' },
    { label: 'Email Issac', url: `mailto:${HIRE_EMAIL}` },
  ];
  return { text, actions };
}

module.exports = {
  PRODUCT_CATALOG,
  CONSULTING_TIERS,
  CONSULTING_LANDING_URL,
  HIRE_EMAIL,
  MEMBERSHIP_KOFI_URL,
  classifyIntent,
  renderBuyReply,
  renderCustomReply,
  renderMembershipReply,
  resolveProduct,
};
