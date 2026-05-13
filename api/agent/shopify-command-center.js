'use strict';

const { serveDocsHtml } = require('./_static_file');

module.exports = async function handler(req, res) {
  return serveDocsHtml(
    req,
    res,
    'shopify-command-center.html',
    'shopify_command_center_page_unavailable'
  );
};
