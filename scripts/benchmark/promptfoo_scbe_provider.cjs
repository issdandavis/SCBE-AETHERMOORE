const { spawnSync } = require('node:child_process');
const path = require('node:path');

class ScbePromptfooProvider {
  id() {
    return 'scbe-local-detector';
  }

  async callApi(prompt) {
    const repoRoot = path.resolve(__dirname, '..', '..');
    const detectorPath = path.join(repoRoot, 'scripts', 'benchmark', 'promptfoo_scbe_detector.py');
    const result = spawnSync('python', [detectorPath], {
      cwd: repoRoot,
      input: JSON.stringify({ prompt }),
      encoding: 'utf8',
      maxBuffer: 1024 * 1024,
    });

    if (result.status !== 0) {
      return {
        error: result.stderr || result.stdout || `Detector exited with status ${result.status}`,
      };
    }

    const parsed = JSON.parse(result.stdout);
    return {
      output: parsed.decision,
      metadata: parsed,
    };
  }
}

module.exports = ScbePromptfooProvider;
