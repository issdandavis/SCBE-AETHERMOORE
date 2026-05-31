'use strict';

const { serveDocsAsset } = require('./_static_file');

module.exports = async function handler(req, res) {
  return serveDocsAsset(req, res);
};
