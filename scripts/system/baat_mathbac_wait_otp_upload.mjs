import { chromium } from "playwright";
import fs from "node:fs";

const USER = process.env.BAAT_USER;
const PASS = process.env.BAAT_PASS;
const ZIP = process.env.MATHBAC_ZIP;
const OTP_FILE = process.env.BAAT_OTP_FILE || "artifacts/mathbac/baat_otp.txt";

if (!USER || !PASS || !ZIP) {
  console.error("Missing BAAT_USER, BAAT_PASS, or MATHBAC_ZIP");
  process.exit(2);
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const shot = async (page, name) => page.screenshot({ path: `artifacts/mathbac/${name}.png`, fullPage: true }).catch(() => {});

async function fillFirst(page, selectors, value, timeout = 3000) {
  for (const selector of selectors) {
    const loc = page.locator(selector).first();
    try {
      await loc.waitFor({ state: "visible", timeout });
      await loc.fill(value);
      return true;
    } catch {}
  }
  return false;
}

async function clickFirst(page, locators, timeout = 3000) {
  for (const loc of locators) {
    try {
      await loc.first().waitFor({ state: "visible", timeout });
      await loc.first().click();
      return true;
    } catch {}
  }
  return false;
}

async function clickByTextLoose(page, patterns, timeout = 10000) {
  for (const pattern of patterns) {
    const loc = page.getByText(pattern).first();
    try {
      await loc.waitFor({ state: "visible", timeout });
      await loc.click();
      return true;
    } catch {}
  }
  return false;
}

async function waitForOtp(timeoutMs = 600000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (fs.existsSync(OTP_FILE)) {
      const code = fs.readFileSync(OTP_FILE, "utf8").trim();
      if (/^\d{6,8}$/.test(code) && code !== "000000") return code;
    }
    await sleep(1000);
  }
  return "";
}

async function fillByVisibleLabel(page, label, value) {
  return page.evaluate(
    ({ label, value }) => {
      const norm = (s) => (s || "").replace(/\s+/g, " ").trim().toLowerCase();
      const wanted = norm(label);
      const fields = [...document.querySelectorAll("input:not([type=hidden]):not([type=file]), textarea, select")];
      for (const field of fields) {
        let text = "";
        let node = field;
        for (let i = 0; i < 7 && node; i++, node = node.parentElement) text += ` ${(node.innerText || "").slice(0, 700)}`;
        if (!norm(text).includes(wanted)) continue;
        field.focus();
        if (field.tagName === "SELECT") {
          const opt = [...field.options].find((o) => norm(o.text) === norm(value) || norm(o.value) === norm(value));
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

async function waitPastOkta(page, label, timeoutMs = 120000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const text = await page.locator("body").innerText({ timeout: 5000 }).catch(() => "");
    const url = page.url();
    if (
      /baa\.darpa\.mil/i.test(url) &&
      !/Verifying your identity|Connecting to|Powered by Okta|Send me an email|One-time verification code/i.test(text)
    ) {
      console.log(`${label} BAAT_READY ${url}`);
      return true;
    }
    await sleep(2000);
  }
  console.log(`${label} BAAT_READY_TIMEOUT ${page.url()}`);
  await shot(page, `baat_${label.toLowerCase()}_ready_timeout`);
  return false;
}

async function waitForSubmissionForm(page, timeoutMs = 120000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const text = await page.locator("body").innerText({ timeout: 5000 }).catch(() => "");
    const fileCount = await page.locator('input[type="file"]').count().catch(() => 0);
    if (/Proposal Abstract Title|Upload|Abstract|Proposal/i.test(text) || fileCount > 0) {
      console.log(`FORM_READY ${page.url()} fileInputs=${fileCount}`);
      return true;
    }
    await sleep(2000);
  }
  console.log(`FORM_READY_TIMEOUT ${page.url()}`);
  await shot(page, "baat_form_ready_timeout");
  return false;
}

async function main() {
  fs.mkdirSync("artifacts/mathbac", { recursive: true });
  try { fs.unlinkSync(OTP_FILE); } catch {}

  const browser = await chromium.launch({ channel: "chrome", headless: false });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.setDefaultTimeout(20000);

  console.log("OPEN BAAT");
  await page.goto("https://baa.darpa.mil", { waitUntil: "domcontentloaded" });
  await shot(page, "baat_step_01_open");
  await clickFirst(page, [page.getByRole("button", { name: /agree\/continue/i }), page.getByText(/Agree\/Continue/i)]);
  await sleep(2500);

  console.log("LOGIN USER");
  await fillFirst(page, ['input[name="identifier"]', 'input[type="email"]', 'input[name="username"]', "input"], USER, 8000);
  await clickFirst(page, [page.getByRole("button", { name: /next|continue|sign in/i }), page.locator('input[type="submit"]')], 8000);
  await sleep(3000);
  await shot(page, "baat_step_02_after_user");

  if (await page.getByText(/Verify it's you with a security method/i).count()) {
    console.log("SELECT EMAIL MFA");
    await clickFirst(page, [
      page.getByText(/^Email$/).locator("xpath=ancestor::*[.//*[normalize-space()='Select']][1]").getByText(/^Select$/),
      page.getByRole("button", { name: /^Select$/ }).first(),
      page.getByText(/^Select$/).first(),
    ], 10000);
    await sleep(2500);
  } else {
    const passOk = await fillFirst(page, ['input[type="password"]', 'input[name="password"]'], PASS, 4000);
    if (passOk) {
      await clickFirst(page, [page.getByRole("button", { name: /verify|sign in|continue|submit/i }), page.locator('input[type="submit"]')], 8000);
      await sleep(3000);
    }
    if (await page.getByText(/Verify it's you with a security method/i).count()) {
      console.log("SELECT EMAIL MFA AFTER PASSWORD");
      await clickFirst(page, [
        page.getByText(/^Email$/).locator("xpath=ancestor::*[.//*[normalize-space()='Select']][1]").getByText(/^Select$/),
        page.getByRole("button", { name: /^Select$/ }).first(),
      ], 10000);
      await sleep(2500);
    }
  }

  if (await page.getByText(/Send me an email/i).count()) {
    console.log("CLICK SEND ME EMAIL");
    await clickFirst(page, [
      page.getByRole("button", { name: /send me an email/i }),
      page.getByText(/send me an email/i),
      page.locator("input[type='submit'][value*='email' i]"),
    ], 10000);
    await sleep(3000);
  } else if (await page.getByText(/Get a verification email/i).count()) {
    console.log("CLICK SEND EMAIL LOOSE");
    await clickByTextLoose(page, [/Send me an email/i, /Send/i], 10000);
    await sleep(3000);
  }

  await shot(page, "baat_step_03_waiting_otp");
  console.log(`WAITING_OTP_FILE ${OTP_FILE}`);
  const otp = await waitForOtp();
  if (!otp) {
    console.log("OTP_TIMEOUT");
    await shot(page, "baat_otp_timeout");
    process.exit(3);
  }
  console.log("OTP_RECEIVED");
  await fillFirst(page, ['input[name="credentials.passcode"]', 'input[inputmode="numeric"]', 'input[type="text"]', "input"], otp, 10000);
  await clickFirst(page, [page.getByRole("button", { name: /verify|continue|submit|sign in/i }), page.locator('input[type="submit"]')], 10000);
  await waitPastOkta(page, "AFTER_OTP");
  await shot(page, "baat_step_04_after_otp");

  console.log("OPEN MATHBAC FORM");
  await page.goto("https://baa.darpa.mil/Submission/create/?type=WhitePaper&topicId=937", { waitUntil: "domcontentloaded" });
  await waitPastOkta(page, "AFTER_FORM_GOTO", 60000);
  await waitForSubmissionForm(page);
  await shot(page, "baat_step_05_mathbac_form");

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
  for (const [label, value] of values) {
    const ok = await fillByVisibleLabel(page, label, value);
    console.log(`FIELD ${label} ${ok ? "OK" : "MISS"}`);
  }

  await shot(page, "baat_step_06_fields_filled");
  const fileInput = page.locator('input[type="file"]').first();
  await fileInput.waitFor({ state: "attached", timeout: 20000 });
  await fileInput.setInputFiles(ZIP);
  await sleep(2500);
  await shot(page, "baat_step_07_zip_attached");
  console.log(`ZIP_ATTACHED ${ZIP}`);

  await sleep(600000);
}

main().catch(async (err) => {
  console.error(err);
  process.exit(1);
});
