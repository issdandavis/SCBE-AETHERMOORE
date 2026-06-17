'use strict';

const { serveDocsHtml } = require('./_static_file');

module.exports = async function handler(req, res) {
  return serveDocsHtml(req, res, 'atomic-lab.html', 'atomic_lab_page_unavailable');
};
