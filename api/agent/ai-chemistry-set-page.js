'use strict';

const { serveDocsHtml } = require('./_static_file');

module.exports = async function handler(req, res) {
  return serveDocsHtml(req, res, 'ai-chemistry-set.html', 'ai_chemistry_set_page_unavailable');
};
