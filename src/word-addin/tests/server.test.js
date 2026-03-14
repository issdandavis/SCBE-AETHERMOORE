const test = require("node:test");
const assert = require("node:assert/strict");
const http = require("http");

const { app, extractCommands } = require("../server.js");

let server;
let baseUrl;

test.before(async () => {
  server = http.createServer(app);
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  baseUrl = `http://127.0.0.1:${address.port}`;
});

test.after(async () => {
  await new Promise((resolve, reject) => {
    server.close((err) => (err ? reject(err) : resolve()));
  });
});

test("health endpoint returns service status", async () => {
  const response = await fetch(`${baseUrl}/health`);
  assert.equal(response.status, 200);

  const payload = await response.json();
  assert.equal(payload.status, "ok");
  assert.equal(payload.service, "scbe-word-addin");
});

test("root redirects to the writer taskpane", async () => {
  const response = await fetch(`${baseUrl}/`, { redirect: "manual" });
  assert.equal(response.status, 302);
  assert.equal(response.headers.get("location"), "/taskpane/writer.html");
});

test("manifest endpoint serves office manifest xml", async () => {
  const response = await fetch(`${baseUrl}/manifest.xml`);
  assert.equal(response.status, 200);

  const xml = await response.text();
  assert.match(xml, /<OfficeApp[\s>]/);
  assert.match(xml, /SCBE Writer/);
  assert.match(xml, /https:\/\/localhost:3000\/taskpane\/taskpane\.html/);
});

test("reader edition endpoint returns manuscript payload", async () => {
  const response = await fetch(`${baseUrl}/api/manuscript/reader-edition`);
  assert.equal(response.status, 200);

  const payload = await response.json();
  assert.equal(payload.title, "The Six Tongues Protocol");
  assert.ok(typeof payload.content === "string" && payload.content.length > 1000);
});

test("extractCommands pulls structured command payloads", () => {
  const text = [
    'Intro text',
    '@@WORD_CMD@@{"action":"replace_selection_text","text":"hello"}@@END@@',
    '@@WORD_CMD@@{"action":"append_document_html","html":"<p>hi</p>"}@@END@@',
  ].join("\n");

  const commands = extractCommands(text, "@@WORD_CMD@@");
  assert.equal(commands.length, 2);
  assert.deepEqual(commands[0], { action: "replace_selection_text", text: "hello" });
  assert.deepEqual(commands[1], { action: "append_document_html", html: "<p>hi</p>" });
});
