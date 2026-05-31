import { execFileSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

describe('scbe-patent workbench CLI', () => {
  it('initializes a complete patent workbench packet', () => {
    const workdir = mkdtempSync(join(tmpdir(), 'scbe-patent-'));

    const raw = execFileSync(
      'node',
      ['bin/scbe-patent.cjs', 'init', '--workdir', workdir, '--json'],
      {
        encoding: 'utf8',
      }
    );
    const payload = JSON.parse(raw);

    expect(payload.schema).toBe('scbe_patent_workbench_manifest_v1');
    expect(payload.counts.official_sources).toBeGreaterThanOrEqual(6);
    expect(payload.counts.prior_art_queries).toBeGreaterThanOrEqual(8);
    expect(payload.counts.support_families).toBeGreaterThanOrEqual(5);
    expect(payload.counts.readiness_items).toBeGreaterThanOrEqual(8);
    expect(existsSync(join(workdir, 'official_sources.json'))).toBe(true);
    expect(existsSync(join(workdir, 'claim_support_scan.json'))).toBe(true);
    expect(existsSync(join(workdir, 'filing_readiness_checklist.md'))).toBe(true);
  });

  it('runs the patent benchmark through the workbench CLI', () => {
    const workdir = mkdtempSync(join(tmpdir(), 'scbe-patent-'));

    execFileSync('node', ['bin/scbe-patent.cjs', 'init', '--workdir', workdir], {
      encoding: 'utf8',
    });
    const raw = execFileSync(
      'node',
      ['bin/scbe-patent.cjs', 'benchmark', '--workdir', workdir, '--json'],
      {
        encoding: 'utf8',
      }
    );
    const payload = JSON.parse(raw);

    expect(payload.schema).toBe('scbe_patent_benchmark_command_v1');
    expect(payload.application_number).toBe('19/691,526');
    expect(payload.docket).toBe('SCBE-2026-0001');
    expect(payload.title).toContain('Hyperbolic Geometry-Based Authorization');
    expect(payload.counts.cases).toBe(8);
    expect(payload.metrics.lattice_mean).toBeGreaterThan(payload.metrics.baseline_mean);
    expect(existsSync(join(workdir, 'benchmarks', 'resonant_thought_lattice_benchmark.json'))).toBe(
      true
    );
    expect(existsSync(join(workdir, 'benchmarks', 'resonant_thought_lattice_benchmark.md'))).toBe(
      true
    );
  });

  it('writes official USPTO source URLs and support evidence', () => {
    const workdir = mkdtempSync(join(tmpdir(), 'scbe-patent-'));

    execFileSync('node', ['bin/scbe-patent.cjs', 'init', '--workdir', workdir], {
      encoding: 'utf8',
    });

    const sources = readFileSync(join(workdir, 'official_sources.md'), 'utf8');
    const support = JSON.parse(readFileSync(join(workdir, 'claim_support_scan.json'), 'utf8'));

    expect(sources).toContain('https://www.uspto.gov/patents/basics/apply/utility-patent');
    expect(sources).toContain('https://patentcenter.uspto.gov');
    expect(
      support.families.some(
        (family: { family: string }) => family.family === 'bijective_tamper_canonicality'
      )
    ).toBe(true);
  });
});
