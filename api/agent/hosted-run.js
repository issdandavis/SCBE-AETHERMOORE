'use strict';

const { serveDocsHtml } = require('./_static_file');

module.exports = async function handler(req, res) {
  return serveDocsHtml(req, res, 'hosted-run.html', 'hosted_run_page_unavailable');
};
