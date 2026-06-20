// SCBE governance-gate live demo. Pure client-side, no backend.
//
// What this is doing, briefly:
//   1. Estimate hyperbolic distance d_H from the prompt using a 12-feature
//      heuristic (jailbreak markers, instruction-override patterns, length
//      anomalies, etc.). The same canonical formulas run server-side in
//      scbe-agent-bus over the full 14-layer pipeline; this page is a
//      preview that runs the audited Layer-12 math on the heuristic d_H.
//
//   2. Compute the canonical Layer-12 harmonic score:
//        H(d, p_d) = 1 / (1 + d + 2 * p_d)        ∈ (0, 1]
//
//   3. Compute a cost multiplier that mirrors the moat claim:
//        cost = phi ^ (d ** 2)
//      φ = golden ratio. d=0 → 1×, d=1 → φ ≈ 1.618×, d=3 → φ⁹ ≈ 76×.
//
//   4. Map H to a Layer-13 verdict:
//        H >= 0.66 → ALLOW
//        H >= 0.40 → QUARANTINE
//        H >= 0.20 → ESCALATE
//        else      → DENY

(function () {
  'use strict';

  var PHI = (1 + Math.sqrt(5)) / 2;

  // --- 1. d_H heuristic -----------------------------------------------------

  // Fragments cribbed from public-domain jailbreak / prompt-injection corpora
  // (the kind every safety eval already uses). Each entry contributes a
  // weighted bump to d_H when it appears in the prompt.
  var JAILBREAK_FRAGMENTS = [
    { rx: /ignore (all )?(your |the )?(previous|prior|above) (instructions|prompts|rules)/i, w: 1.5 },
    { rx: /\b(you are|act as|pretend (you are|to be)) (an? )?(unrestricted|jailbroken|uncensored|evil|rogue)/i, w: 1.6 },
    { rx: /\bDAN\b.*(no rules|do anything|unrestricted)/i, w: 1.7 },
    { rx: /reveal (your |the )?(system )?(prompt|instructions|rules)/i, w: 1.4 },
    { rx: /(disregard|forget|override) (your )?(safety|policies|guidelines|rules)/i, w: 1.4 },
    { rx: /\bSTART( AGAIN)?\b.*ignore/i, w: 1.0 },
    { rx: /\bsudo\b|\broot\b.*shell/i, w: 0.7 },
    { rx: /(write|generate|give me) (working |functional )?(malware|ransomware|exploit|virus|trojan|keylogger)/i, w: 1.6 },
    { rx: /\b(api[_ ]?key|password|token|credential)s?\b.*(leak|reveal|list|dump|show)/i, w: 1.2 },
    { rx: /(hotwire|bypass|crack)\s+(a |the )?(car|lock|password|alarm)/i, w: 1.2 },
    { rx: /(without (the )?owner)/i, w: 0.5 },
    { rx: /\bbase64\b.*(decode|encoded payload)/i, w: 0.6 },
  ];

  // Soft signals — cumulative drift, not an automatic block.
  function lengthDrift(s) {
    var len = s.length;
    if (len < 8) return 0.4;       // suspiciously short / probing
    if (len > 1200) return 0.5;    // payload smuggling territory
    return 0;
  }

  function repetitionDrift(s) {
    if (s.length < 40) return 0;
    var trigrams = {};
    var lower = s.toLowerCase();
    for (var i = 0; i < lower.length - 2; i++) {
      var g = lower.substring(i, i + 3);
      trigrams[g] = (trigrams[g] || 0) + 1;
    }
    var total = lower.length - 2;
    var uniq = Object.keys(trigrams).length;
    var ratio = uniq / total;
    if (ratio < 0.35) return 0.4;  // looks like an exfil-by-repetition trick
    return 0;
  }

  function shoutiness(s) {
    var alpha = s.replace(/[^A-Za-z]/g, '');
    if (alpha.length < 12) return 0;
    var upper = alpha.replace(/[^A-Z]/g, '').length;
    return upper / alpha.length > 0.6 ? 0.3 : 0;
  }

  function fragmentScore(s) {
    var sum = 0;
    for (var i = 0; i < JAILBREAK_FRAGMENTS.length; i++) {
      if (JAILBREAK_FRAGMENTS[i].rx.test(s)) sum += JAILBREAK_FRAGMENTS[i].w;
    }
    return sum;
  }

  function estimateDH(text) {
    if (!text) return 0;
    var raw =
      fragmentScore(text) +
      lengthDrift(text) +
      repetitionDrift(text) +
      shoutiness(text);
    // Sigmoid-like compression so d_H stays in a UI-friendly band.
    return Math.min(6, raw);
  }

  // --- 2. canonical Layer-12 score ------------------------------------------

  function harmonicScale(d, pd) {
    if (d < 0) d = 0;
    if (pd < 0) pd = 0;
    return 1 / (1 + d + 2 * pd);
  }

  // --- 3. cost multiplier ---------------------------------------------------

  function costMultiplier(d) {
    return Math.pow(PHI, d * d);
  }

  // --- 4. L13 verdict -------------------------------------------------------

  function verdictFor(H) {
    if (H >= 0.66) return { label: 'ALLOW',      why: 'Within the safe well. Routes to the agent.' };
    if (H >= 0.40) return { label: 'QUARANTINE', why: 'Soft drift detected. Held for human review.' };
    if (H >= 0.20) return { label: 'ESCALATE',   why: 'Hard drift. Sent to governance for sign-off.' };
    return { label: 'DENY',                      why: 'Outside the harmonic wall. Blocked.' };
  }

  // --- UI binding -----------------------------------------------------------

  var els = {
    prompt:   document.getElementById('prompt'),
    dh:       document.getElementById('m-dh'),
    h:        document.getElementById('m-h'),
    cost:     document.getElementById('m-cost'),
    verdict:  document.getElementById('verdict'),
    why:      document.getElementById('why'),
  };

  function fmtCost(c) {
    if (c < 10)    return c.toFixed(2) + '×';
    if (c < 1000)  return c.toFixed(0) + '×';
    return c.toExponential(1).replace('e+', 'e') + '×';
  }

  function update() {
    var text = els.prompt.value || '';
    var d = estimateDH(text);
    var H = harmonicScale(d, 0);
    var cost = costMultiplier(d);
    var v = verdictFor(H);

    els.dh.textContent = d.toFixed(3);
    els.h.textContent = H.toFixed(3);
    els.cost.textContent = fmtCost(cost);

    els.verdict.textContent = v.label;
    els.verdict.className = 'verdict ' + v.label;
    els.why.textContent = text.trim() ? v.why : 'Type a prompt to begin.';
  }

  els.prompt.addEventListener('input', update);

  var presets = document.querySelectorAll('.preset');
  for (var i = 0; i < presets.length; i++) {
    presets[i].addEventListener('click', function (e) {
      els.prompt.value = e.currentTarget.getAttribute('data-text') || '';
      els.prompt.focus();
      update();
    });
  }

  update();
})();
