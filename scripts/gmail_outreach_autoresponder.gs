/**
 * SCBE Outreach Auto-Responder (Google Apps Script)
 *
 * Watches Gmail for replies from outreach contacts, drafts AI-assisted
 * replies using your business context. Free, runs on Google's servers.
 *
 * Setup:
 * 1. Go to script.google.com → New Project
 * 2. Paste this entire file
 * 3. Set these in Script Properties (Settings → Script Properties):
 *    - HF_TOKEN: your HuggingFace token (for your own model)
 *    - GEMINI_API_KEY: (optional fallback) Google Gemini API key
 * 4. Run setupTrigger() once to start the 5-minute timer
 * 5. Authorize when prompted
 *
 * AI Priority: HuggingFace (your model) → Gemini Flash (fallback)
 */

// ── Configuration ──────────────────────────────────────────────────

const OUTREACH_DOMAINS = [
  'hiddenlayer.com', 'bah.com', 'credo.ai', 'guardrailsai.com',
  'holisticai.com', 'dynamo.ai', 'lmco.com', 'ngc.com',
  'palantir.com', 'iqt.org', 'saif.vc', 'jpmorgan.com',
  'wellsfargo.com', 'citi.com', 'salesforce.com', 'boozallen.com',
  'lockheedmartin.com', 'northropgrumman.com', 'microsoft.com',
  'generalcatalyst.com', 'a16z.com', 'luxcapital.com',
  'openphilanthropy.org', 'schmidtsciences.org'
];

const BUSINESS_CONTEXT = `
You are drafting email replies on behalf of Issac Davis, founder of SCBE-AETHERMOORE.

ABOUT SCBE-AETHERMOORE:
- AI governance framework using hyperbolic geometry + post-quantum cryptography
- Patent pending: USPTO #63/961,403
- The only framework combining PQC, hyperbolic cost scaling, multi-agent security, and inference-time guardrails

FOUR PILLARS (no competitor has all four):
1. Post-Quantum Crypto: ML-KEM-768 (FIPS 203) + ML-DSA-65 (FIPS 204) + AES-256-GCM
2. Hyperbolic Cost Scaling: H(d,R) = R^(d²) — adversarial intent costs exponentially more
3. Multi-Agent Coordination: 14-layer pipeline with 5 quantum axioms
4. Inference-Time Guardrails: ALLOW/QUARANTINE/ESCALATE/DENY in <10ms

VERIFIED METRICS:
- 6,742 tests passing (5,957 TypeScript + 785 Python)
- 100% crypto module pass rate, 0 CVEs
- 85.7% attack detection at 0% false positives
- 91/91 attacks blocked vs industry comparison 62/91
- F1 score: 0.813 (semantic projector orientation)
- 233K multi-view SFT training pairs
- <10ms governance overhead per query

PRICING:
- Pump API: $49/mo (1,000 calls/day, governance gate, audit log)
- Pump Pro: $199/mo (10,000 calls/day, cascade detection, custom profiles)
- Governance-as-a-Service: $499/mo (unlimited, trichromatic, PQC, compliance docs)

LINKS:
- Website: https://aethermoorgames.com
- Enterprise: https://aethermoorgames.com/enterprise.html
- Live demos: https://aethermoorgames.com/demos/
- GitHub: https://github.com/issdandavis/SCBE-AETHERMOORE
- HuggingFace: https://huggingface.co/issdandavis
- Book: "The Six Tongues Protocol" on Amazon
- ORCID: 0009-0002-3936-9369

POSITIONING:
- Complement, not competitor — PQC + multi-agent security fills gaps no one else covers
- Solo founder, Port Angeles, WA
- Background: 12,596-paragraph D&D campaign → security framework → patent → product

TONE: Professional, direct, confident but not arrogant. Always offer a demo or technical briefing as next step. Reference specific metrics when relevant. Keep replies concise (3-4 paragraphs max).

REPLY RULES:
- If they ask about pricing: share the three tiers and link to pricing page
- If they ask for a demo: offer live demos at aethermoorgames.com/demos/ and a 30-min technical briefing
- If they ask technical questions: reference GitHub, test suite, or specific metrics
- If they mention partnership/licensing: position as capability extension, not overlap
- If they ask about the team: solo founder, transparent about it, emphasize the math and test suite
- If they want to schedule: suggest aethermoregames@pm.me for calendar coordination
- Always end with a clear next step
`;

// ── Main Functions ─────────────────────────────────────────────────

function checkOutreachReplies() {
  const processedLabel = getOrCreateLabel_('SCBE-AutoDrafted');

  OUTREACH_DOMAINS.forEach(domain => {
    const query = `from:${domain} is:unread -label:SCBE-AutoDrafted newer_than:1d`;
    const threads = GmailApp.search(query, 0, 5);

    threads.forEach(thread => {
      const messages = thread.getMessages();
      const latest = messages[messages.length - 1];

      if (!latest.isUnread()) return;

      const sender = latest.getFrom();
      const subject = latest.getSubject();
      const body = latest.getPlainBody().substring(0, 2000); // Cap at 2K chars

      Logger.log(`Processing reply from ${sender}: ${subject}`);

      // Generate draft reply
      const draftText = generateReply_(sender, subject, body);

      if (draftText) {
        // Create draft reply in the same thread
        const replySubject = subject.startsWith('Re:') ? subject : `Re: ${subject}`;
        GmailApp.createDraft(
          extractEmail_(sender),
          replySubject,
          draftText,
          {
            htmlBody: formatReplyHtml_(draftText),
            inReplyTo: latest.getId()
          }
        );

        // Label as processed
        thread.addLabel(processedLabel);

        // Also email yourself a notification
        GmailApp.sendEmail(
          Session.getActiveUser().getEmail(),
          `[SCBE Draft Ready] Reply to ${sender} — ${subject}`,
          `A draft reply has been created for:\n\nFrom: ${sender}\nSubject: ${subject}\n\nCheck your Gmail drafts to review and send.\n\n--- Their message ---\n${body.substring(0, 500)}...`
        );

        Logger.log(`Draft created for ${sender}`);
      }
    });
  });
}

function generateReply_(sender, subject, body) {
  const props = PropertiesService.getScriptProperties();
  const hfToken = props.getProperty('HF_TOKEN');
  const geminiKey = props.getProperty('GEMINI_API_KEY');

  const userPrompt = `Draft a reply to this email.\n\nFrom: ${sender}\nSubject: ${subject}\n\nTheir message:\n${body}\n\nWrite the reply only (no subject line, no "Dear..." unless appropriate). Sign off as "Issac Davis" with title "Founder, SCBE-AETHERMOORE".`;

  // Try HuggingFace first (your own model)
  if (hfToken) {
    const hfResult = callHuggingFace_(hfToken, userPrompt);
    if (hfResult) return hfResult;
    Logger.log('HF model failed, trying Gemini fallback...');
  }

  // Fallback to Gemini
  if (geminiKey) {
    const geminiResult = callGemini_(geminiKey, userPrompt);
    if (geminiResult) return geminiResult;
  }

  Logger.log('No AI API available. Set HF_TOKEN or GEMINI_API_KEY in Script Properties.');
  return null;
}

function callHuggingFace_(token, userPrompt) {
  const url = 'https://router.huggingface.co/v1/chat/completions';

  try {
    const response = UrlFetchApp.fetch(url, {
      method: 'POST',
      contentType: 'application/json',
      headers: { 'Authorization': `Bearer ${token}` },
      payload: JSON.stringify({
        model: 'issdandavis/scbe-pivot-qwen-0.5b',
        messages: [
          { role: 'system', content: BUSINESS_CONTEXT },
          { role: 'user', content: userPrompt }
        ],
        max_tokens: 600,
        temperature: 0.4
      }),
      muteHttpExceptions: true
    });

    const data = JSON.parse(response.getContentText());

    if (data.choices && data.choices[0] && data.choices[0].message) {
      const content = data.choices[0].message.content;
      if (typeof content === 'string' && content.trim().length > 20) {
        Logger.log('Reply generated via HuggingFace (your model)');
        return content.trim();
      }
    }

    Logger.log('HF response insufficient: ' + JSON.stringify(data).substring(0, 200));
    return null;
  } catch (e) {
    Logger.log('HF API error: ' + e.toString());
    return null;
  }
}

function callGemini_(apiKey, userPrompt) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`;
  const prompt = `${BUSINESS_CONTEXT}\n\n${userPrompt}`;

  try {
    const response = UrlFetchApp.fetch(url, {
      method: 'POST',
      contentType: 'application/json',
      payload: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: {
          temperature: 0.4,
          maxOutputTokens: 800,
          topP: 0.9
        }
      }),
      muteHttpExceptions: true
    });

    const data = JSON.parse(response.getContentText());

    if (data.candidates && data.candidates[0] && data.candidates[0].content) {
      Logger.log('Reply generated via Gemini (fallback)');
      return data.candidates[0].content.parts[0].text;
    }

    Logger.log('No response from Gemini: ' + JSON.stringify(data).substring(0, 200));
    return null;
  } catch (e) {
    Logger.log('Gemini API error: ' + e.toString());
    return null;
  }
}

// ── Helpers ─────────────────────────────────────────────────────────

function extractEmail_(fromField) {
  const match = fromField.match(/<([^>]+)>/);
  return match ? match[1] : fromField;
}

function formatReplyHtml_(text) {
  return '<div style="font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif; font-size: 14px; line-height: 1.6; color: #333;">'
    + text.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>')
    + '</div>';
}

function getOrCreateLabel_(name) {
  let label = GmailApp.getUserLabelByName(name);
  if (!label) {
    label = GmailApp.createLabel(name);
  }
  return label;
}

// ── Setup ───────────────────────────────────────────────────────────

function setupTrigger() {
  // Remove existing triggers
  ScriptApp.getProjectTriggers().forEach(trigger => {
    if (trigger.getHandlerFunction() === 'checkOutreachReplies') {
      ScriptApp.deleteTrigger(trigger);
    }
  });

  // Create 5-minute trigger
  ScriptApp.newTrigger('checkOutreachReplies')
    .timeBased()
    .everyMinutes(5)
    .create();

  Logger.log('Trigger set: checkOutreachReplies every 5 minutes');
}

function removeTrigger() {
  ScriptApp.getProjectTriggers().forEach(trigger => {
    if (trigger.getHandlerFunction() === 'checkOutreachReplies') {
      ScriptApp.deleteTrigger(trigger);
      Logger.log('Trigger removed');
    }
  });
}

// Run this to test with a specific email
function testWithLatestEmail() {
  const threads = GmailApp.getInboxThreads(0, 1);
  if (threads.length === 0) {
    Logger.log('No threads found');
    return;
  }
  const msg = threads[0].getMessages().pop();
  const reply = generateReply_(msg.getFrom(), msg.getSubject(), msg.getPlainBody().substring(0, 2000));
  Logger.log('Draft reply:\n' + reply);
}
