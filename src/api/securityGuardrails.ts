/**
 * @file securityGuardrails.ts
 * @module api/securityGuardrails
 * @layer Layer 13 (governance)
 * @component Security guardrails — prevent malicious code generation
 *
 * Scans browser actions, agent outputs, and API payloads for patterns
 * associated with credit card scams, phishing, and payment fraud.
 *
 * This module exists because open-source repos can be forked and weaponised.
 * Every action that flows through the SCBE pipeline is scanned before execution.
 *
 * A5: Composition — this guardrail integrates with L13 governance decisions.
 */

// ============================================================================
// Threat Patterns
// ============================================================================

/** Credit card / payment fraud patterns */
const PAYMENT_FRAUD_PATTERNS: ReadonlyArray<{ pattern: RegExp; severity: 'critical' | 'high' | 'medium'; description: string }> = [
  // Direct card number collection
  { pattern: /card[_\-\s]?number|cc[_\-\s]?num|pan[_\-\s]?number/i, severity: 'critical', description: 'Credit card number field detected' },
  { pattern: /cvv|cvc|csv|security[_\-\s]?code|card[_\-\s]?verification/i, severity: 'critical', description: 'CVV/security code field detected' },
  { pattern: /expir(y|ation)[_\-\s]?(date|month|year)|exp[_\-\s]?date/i, severity: 'high', description: 'Card expiration field detected' },

  // Fake checkout / phishing
  { pattern: /fake[_\-\s]?checkout|phish(ing)?[_\-\s]?(page|form|site)/i, severity: 'critical', description: 'Phishing page construction detected' },
  { pattern: /credential[_\-\s]?harvest|password[_\-\s]?steal/i, severity: 'critical', description: 'Credential harvesting detected' },
  { pattern: /clone[_\-\s]?(stripe|paypal|checkout|payment)/i, severity: 'critical', description: 'Payment page cloning detected' },

  // Card skimmer patterns
  { pattern: /skim(mer|ming)|magecart|form[_\-\s]?jack(ing)?/i, severity: 'critical', description: 'Card skimmer/formjacker pattern' },
  { pattern: /inject.*payment|overlay.*checkout/i, severity: 'critical', description: 'Payment injection/overlay attack' },
  { pattern: /exfiltrat(e|ion).*card|send.*card.*data/i, severity: 'critical', description: 'Card data exfiltration' },

  // Suspicious data transmission
  { pattern: /btoa\s*\(.*card|base64.*encode.*card/i, severity: 'high', description: 'Base64 encoding card data' },
  { pattern: /fetch\s*\(.*card|XMLHttpRequest.*card/i, severity: 'high', description: 'Transmitting card data via HTTP' },
  { pattern: /navigator\.sendBeacon.*card/i, severity: 'high', description: 'Beacon exfiltration of card data' },

  // PAN regex patterns (card number matchers)
  { pattern: /\b4\d{3}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/, severity: 'high', description: 'Visa card number pattern' },
  { pattern: /\b5[1-5]\d{2}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/, severity: 'high', description: 'Mastercard number pattern' },
  { pattern: /\b3[47]\d{2}[\s-]?\d{6}[\s-]?\d{5}\b/, severity: 'high', description: 'Amex card number pattern' },
];

/** Prompt injection / code execution patterns */
const CODE_INJECTION_PATTERNS: ReadonlyArray<{ pattern: RegExp; severity: 'critical' | 'high' | 'medium'; description: string }> = [
  { pattern: /eval\s*\(|new\s+Function\s*\(/i, severity: 'high', description: 'Dynamic code execution (eval/Function)' },
  { pattern: /document\.write\s*\(/i, severity: 'medium', description: 'document.write (potential XSS)' },
  { pattern: /innerHTML\s*=|outerHTML\s*=/i, severity: 'medium', description: 'Direct HTML injection' },
  { pattern: /exec\s*\(|spawn\s*\(|child_process/i, severity: 'high', description: 'Shell command execution' },
  { pattern: /require\s*\(\s*['"`]\s*child_process/i, severity: 'critical', description: 'child_process import' },
  { pattern: /__proto__|constructor\s*\[|Object\.assign.*prototype/i, severity: 'high', description: 'Prototype pollution' },
];

/** Social engineering patterns */
const SOCIAL_ENGINEERING_PATTERNS: ReadonlyArray<{ pattern: RegExp; severity: 'critical' | 'high' | 'medium'; description: string }> = [
  { pattern: /your\s+account\s+(has\s+been|was)\s+(suspended|locked|compromised)/i, severity: 'high', description: 'Account suspension scam' },
  { pattern: /verify\s+your\s+(identity|account|payment)/i, severity: 'medium', description: 'Verification scam' },
  { pattern: /urgent[:\s].*action\s+required/i, severity: 'medium', description: 'Urgency pressure tactic' },
  { pattern: /act\s+now\s+or\s+(lose|forfeit)/i, severity: 'medium', description: 'Fear-based pressure' },
  { pattern: /wire\s+transfer|western\s+union|moneygram/i, severity: 'high', description: 'Wire transfer scam' },
  { pattern: /gift\s+card\s+(code|number|payment)/i, severity: 'high', description: 'Gift card scam' },
];

// ============================================================================
// Scan Result
// ============================================================================

export interface GuardrailHit {
  category: 'payment_fraud' | 'code_injection' | 'social_engineering';
  severity: 'critical' | 'high' | 'medium';
  description: string;
  matchedText: string;
}

export interface GuardrailResult {
  safe: boolean;
  riskScore: number;
  hits: GuardrailHit[];
  recommendation: 'ALLOW' | 'QUARANTINE' | 'DENY';
}

// ============================================================================
// Scanner
// ============================================================================

/**
 * Scan text content for malicious patterns.
 *
 * Returns a GuardrailResult with severity-weighted risk score.
 * Any critical hit → automatic DENY.
 * High hits → QUARANTINE.
 * Medium hits → ALLOW with monitoring.
 */
export function scanForMaliciousContent(text: string): GuardrailResult {
  const hits: GuardrailHit[] = [];

  const allPatterns = [
    ...PAYMENT_FRAUD_PATTERNS.map((p) => ({ ...p, category: 'payment_fraud' as const })),
    ...CODE_INJECTION_PATTERNS.map((p) => ({ ...p, category: 'code_injection' as const })),
    ...SOCIAL_ENGINEERING_PATTERNS.map((p) => ({ ...p, category: 'social_engineering' as const })),
  ];

  for (const { pattern, severity, description, category } of allPatterns) {
    const match = text.match(pattern);
    if (match) {
      hits.push({
        category,
        severity,
        description,
        matchedText: match[0].slice(0, 100), // Truncate for safety
      });
    }
  }

  // Calculate risk score
  const severityWeights = { critical: 1.0, high: 0.6, medium: 0.2 };
  const riskScore = Math.min(
    1.0,
    hits.reduce((sum, h) => sum + severityWeights[h.severity], 0)
  );

  // Determine recommendation
  let recommendation: 'ALLOW' | 'QUARANTINE' | 'DENY';
  if (hits.some((h) => h.severity === 'critical')) {
    recommendation = 'DENY';
  } else if (hits.some((h) => h.severity === 'high')) {
    recommendation = 'QUARANTINE';
  } else if (hits.length > 0) {
    recommendation = 'ALLOW'; // Medium hits: allow with logging
  } else {
    recommendation = 'ALLOW';
  }

  return {
    safe: hits.length === 0,
    riskScore,
    hits,
    recommendation,
  };
}

/**
 * Scan a URL for known malicious patterns (typosquatting, data URIs, etc.)
 */
export function scanUrl(url: string): GuardrailResult {
  const hits: GuardrailHit[] = [];

  // Data URI attacks
  if (/^data:/i.test(url)) {
    hits.push({
      category: 'code_injection',
      severity: 'critical',
      description: 'Data URI (can embed executable content)',
      matchedText: url.slice(0, 50),
    });
  }

  // JavaScript URIs
  if (/^javascript:/i.test(url)) {
    hits.push({
      category: 'code_injection',
      severity: 'critical',
      description: 'JavaScript URI (XSS vector)',
      matchedText: url.slice(0, 50),
    });
  }

  // Common phishing domain patterns
  const phishingPatterns = [
    /stripe[^.]*\.(xyz|tk|ml|ga|cf|pw)/i,
    /paypal[^.]*\.(xyz|tk|ml|ga|cf|pw)/i,
    /login[^.]*\.(xyz|tk|ml|ga|cf|pw)/i,
    /account[^.]*verify/i,
    /secure.*update.*\.(com|net|org)/i,
  ];

  for (const pattern of phishingPatterns) {
    if (pattern.test(url)) {
      hits.push({
        category: 'social_engineering',
        severity: 'high',
        description: 'Suspicious domain pattern (potential phishing)',
        matchedText: url.slice(0, 100),
      });
    }
  }

  const riskScore = Math.min(
    1.0,
    hits.reduce((sum, h) => sum + (h.severity === 'critical' ? 1.0 : h.severity === 'high' ? 0.6 : 0.2), 0)
  );

  return {
    safe: hits.length === 0,
    riskScore,
    hits,
    recommendation: hits.some((h) => h.severity === 'critical') ? 'DENY' : hits.length > 0 ? 'QUARANTINE' : 'ALLOW',
  };
}

/**
 * Scan an HTML form for credit card input fields.
 *
 * This is the specific defence against the credit card scam attack vector:
 * if anyone forks the repo and tries to build a fake checkout page,
 * the browser agent will refuse to interact with it.
 */
export function scanHtmlForCardFields(html: string): GuardrailResult {
  const hits: GuardrailHit[] = [];

  // Input fields with card-related names/types
  const cardInputPatterns = [
    /<input[^>]*(?:name|id)\s*=\s*["'](?:card|cc|pan|cvv|cvc|csv|expir)[^"']*["'][^>]*>/gi,
    /<input[^>]*type\s*=\s*["'](?:tel|number)["'][^>]*(?:card|cc|cvv|cvc)[^>]*>/gi,
    /<input[^>]*autocomplete\s*=\s*["']cc-(?:number|csc|exp)[^"']*["'][^>]*>/gi,
    /<input[^>]*data-stripe[^>]*>/gi,
    /<div[^>]*class\s*=\s*["'][^"']*(?:card-element|payment-form|checkout-form)[^"']*["'][^>]*>/gi,
  ];

  for (const pattern of cardInputPatterns) {
    const match = html.match(pattern);
    if (match) {
      hits.push({
        category: 'payment_fraud',
        severity: 'critical',
        description: 'HTML form contains credit card input fields — browser agent will not interact',
        matchedText: match[0].slice(0, 100),
      });
    }
  }

  // Forms that POST to unknown/suspicious endpoints
  const formAction = html.match(/<form[^>]*action\s*=\s*["']([^"']+)["']/gi);
  if (formAction) {
    for (const action of formAction) {
      const url = action.match(/action\s*=\s*["']([^"']+)["']/i)?.[1] ?? '';
      if (url && !url.startsWith('/') && !url.includes('stripe.com') && !url.includes('paypal.com')) {
        const urlScan = scanUrl(url);
        hits.push(...urlScan.hits);
      }
    }
  }

  const riskScore = Math.min(
    1.0,
    hits.reduce((sum, h) => sum + (h.severity === 'critical' ? 1.0 : h.severity === 'high' ? 0.6 : 0.2), 0)
  );

  return {
    safe: hits.length === 0,
    riskScore,
    hits,
    recommendation: hits.some((h) => h.severity === 'critical') ? 'DENY' : hits.length > 0 ? 'QUARANTINE' : 'ALLOW',
  };
}
