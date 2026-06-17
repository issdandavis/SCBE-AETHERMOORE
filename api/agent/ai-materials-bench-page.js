'use strict';

const { serveDocsHtml } = require('./_static_file');

module.exports = async function handler(req, res) {
  return serveDocsHtml(req, res, 'ai-materials-bench.html', 'ai_materials_bench_page_unavailable');
};
