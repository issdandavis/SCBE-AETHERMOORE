'use strict';

const { serveDocsHtml } = require('./_static_file');

module.exports = async function handler(req, res) {
  return serveDocsHtml(req, res, 'robot.md', 'robot_map_unavailable');
};
