'use strict';

const { serveDocsHtml } = require('./_static_file');

// SCBE Customer Launch bridge markers.
// Payment Center: href="/payments"
// Products: href="/products"
// Workflow Snapshot: href="/workflow-snapshot"
// Hosted Run Intake: href="/hosted-run"
// Service Credits: href="/service-credits"
// Supporter: href="/supporter"
// Agents: href="/agents"
// Chat: href="/chat"
// Health: /api/agent/health
// Status: /api/agent/status?limit=5
module.exports = async function handler(req, res) {
  return serveDocsHtml(req, res, 'index.html', 'home_page_unavailable');
};
