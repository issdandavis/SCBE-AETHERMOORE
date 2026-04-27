import { chromium } from "playwright";
import { execFileSync } from "node:child_process";

const USER = process.env.BAAT_USER;
const PASS = process.env.BAAT_PASS;
const ZIP = process.env.MATHBAC_ZIP;

if (!USER || !PASS || !ZIP) {
  console.error("Missing BAAT_USER, BAAT_PASS, or MATHBAC_ZIP");
  process.exit(2);
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function fetchOtp() {
  try {
    return execFileSync("python", ["scripts/system/fetch_baat_otp.py"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
      timeout: 30000,
    }).trim();
  } catch {
    return "";
  }
}

async function pollOtp(timeoutMs = 240000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const code = fetchOtp();
    if (/^\d{6,8}$/.test(code)) return code;
    await sleep(10000);
  }
  return "";
}

async function clickText(page, text, opts = {}) {
  const loc = page.getByText(text, { exact: opts.exact ?? false }).first();
  await loc.waitFor({ timeout: opts.timeout ?? 15000 });
  await loc.click();
}

async function fillFirstVisible(page, selectors, value) {
  for (const selector of selectors) {
    const loc = page.locator(selector).first();
    try {
      await loc.waitFor({ timeout: 2500, state: "visible" });
      await loc.fill(value);
      return true;
    } catch {
      // Try the next selector.
    }
  }
  return false;
}

async function fillByRowLabel(page, label, value) {
  return await page.evaluate(
    ({ label, value }) => {
      const norm = (s) => (s || "").replace(/\s+/g, " ").trim().toLowerCase();
      const wanted = norm(label);
      const fields = [
        ...document.querySelectorAll("input:not([type=hidden]):not([type=file]), textarea, select"),
      ];

      for (const field of fields) {
        let text = "";
        if (field.id) {
          const lab = document.querySelector(`label[for="${CSS.escape(field.id)}"]`);
          if (lab) text += ` ${lab.innerText}`;
        }
        let node = field;
        for (let i = 0; i < 8 && node; i += 1, node = node.parentElement) {
          text += ` ${(node.innerText || "").slice(0, 800)}`;
        }
        if (!norm(text).includes(wanted)) continue;

        field.focus();
        if (field.tagName === "SELECT") {
          const opt = [...field.options].find(
            (o) => norm(o.text) === norm(value) || norm(o.value) === norm(value),
          );
          if (opt) field.value = opt.value;
        } else {
          field.value = value;
        }
        field.dispatchEvent(new Event("input", { bubbles: true }));
        field.dispatchEvent(new Event("change", { bubbles: true }));
        field.blur();
        return true;
      }
      return false;
    },
    { label, value },
  );
}

async function main() {
  const browser = await chromium.launch({ channel: "chrome", headless: false });
  const page = await browser.newPage();
  page.setDefaultTimeout(25000);

  await page.goto("https://baa.darpa.mil", { waitUntil: "domcontentloaded" });
  if (await page.getByRole("button", { name: /agree\/continue/i }).count()) {
    await page.getByRole("button", { name: /agree\/continue/i }).click();
  }

  await page.waitForLoadState("domcontentloaded").catch(() => {});
  await sleep(1500);

  if (/okta|signin|login|securityagreement/i.test(page.url()) || (await page.locator("input").count())) {
    await fillFirstVisible(
      page,
      [
        'input[name="identifier"]',
        'input[type="email"]',
        'input[name="username"]',
        'input[id*="user" i]',
        'input',
      ],
      USER,
    );
    const next = page.getByRole("button", { name: /next|sign in|continue/i }).first();
    if (await next.count()) await next.click();
    await sleep(1500);

    const passFilled = await fillFirstVisible(
      page,
      ['input[type="password"]', 'input[name="password"]', 'input[id*="pass" i]'],
      PASS,
    );
    if (passFilled) {
      const verify = page.getByRole("button", { name: /verify|sign in|continue|submit/i }).first();
      if (await verify.count()) await verify.click();
    }
  }

  await page.waitForLoadState("domcontentloaded").catch(() => {});
  await sleep(5000);

  if (await page.getByText(/Verify it's you with a security method/i).count()) {
    const emailText = page.getByText(/^Email$/).first();
    if (await emailText.count()) {
      const emailCard = emailText.locator("xpath=ancestor::*[.//a[contains(normalize-space(.),'Select')] or .//button[contains(normalize-space(.),'Select')]][1]");
      const emailSelect = emailCard.getByText(/^Select$/).first();
      await emailSelect.click();
      await sleep(3000);
      const code = await pollOtp();
      if (!code) {
        await page.screenshot({ path: "artifacts/mathbac/baat_email_code_missing.png", fullPage: true });
        console.log("EMAIL_CODE_MISSING");
        return;
      }
      await fillFirstVisible(
        page,
        ['input[name="credentials.passcode"]', 'input[type="text"]', 'input[inputmode="numeric"]', 'input'],
        code,
      );
      const verify = page.getByRole("button", { name: /verify|continue|submit|sign in/i }).first();
      if (await verify.count()) await verify.click();
      await sleep(5000);
    }
  }

  if (/okta|signin|login/i.test(page.url()) || (await page.getByText(/verify|password|authenticator|code/i).count())) {
    await page.screenshot({ path: "artifacts/mathbac/baat_login_blocked.png", fullPage: true });
    console.log(`LOGIN_BLOCKED url=${page.url()}`);
    return;
  }

  await page.goto("https://baa.darpa.mil/Submission/create/?type=WhitePaper&topicId=937", {
    waitUntil: "domcontentloaded",
  });
  await sleep(2500);

  const values = [
    ["Proposal Abstract Title", "A Geometric Protocol Substrate for Agentic Communication: Bounded Harmonic Governance and Falsifiable Living Metrics"],
    ["Proposed Cost", "2000000"],
    ["Duration In Months", "16"],
    ["Salutation", "Mr."],
    ["First Name", "Issac"],
    ["Last Name", "Davis"],
    ["Organization Name", "SCBE AetherMoore"],
    ["Country", "United States"],
    ["Address 1", "2361 E Ryan Drive"],
    ["Address 2", ""],
    ["City", "Port Angeles"],
    ["State/Province", "WA"],
    ["Zip/Postal Code", "98362-0000"],
    ["Phone", "360-808-0876"],
    ["Fax", ""],
    ["Email", "issac@aethermoorgames.com"],
  ];

  const results = [];
  for (const [label, value] of values) {
    results.push([label, await fillByRowLabel(page, label, value)]);
  }
  console.log(JSON.stringify({ fillResults: results }, null, 2));

  const noTeam = page.locator('input[type="checkbox"]').filter({ hasText: /team/i }).first();
  // Leave team membership untouched unless the portal exposes a clearly-labeled checkbox.
  if (await noTeam.count()) {
    console.log("Team checkbox present; not changing automatically.");
  }

  const fileInput = page.locator('input[type="file"]').first();
  await fileInput.waitFor({ timeout: 15000 });
  await fileInput.setInputFiles(ZIP);
  await sleep(1500);

  await page.screenshot({ path: "artifacts/mathbac/baat_after_zip_attached.png", fullPage: true });
  console.log(`ZIP_ATTACHED ${ZIP}`);

  const save = page.getByRole("button", { name: /save|continue|next/i }).first();
  if (await save.count()) {
    console.log(`NEXT_ACTION_AVAILABLE ${(await save.textContent())?.trim()}`);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
