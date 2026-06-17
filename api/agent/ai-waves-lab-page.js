'use strict';

const { serveDocsHtml } = require('./_static_file');

module.exports = async function handler(req, res) {
  return serveDocsHtml(req, res, 'ai-waves-lab.html', 'ai_waves_lab_page_unavailable');
};
