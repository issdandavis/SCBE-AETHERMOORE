'use strict';

const { serveDocsHtml } = require('./_static_file');

module.exports = async function handler(req, res) {
  return serveDocsHtml(req, res, 'geoseal-hermes.html', 'geoseal_hermes_page_unavailable');
};
