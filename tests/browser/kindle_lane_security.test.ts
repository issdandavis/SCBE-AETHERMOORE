import * as fs from 'fs';
import * as path from 'path';
import { describe, expect, it } from 'vitest';

function readLane(fileName: string): string {
  return fs.readFileSync(path.join(process.cwd(), 'kindle-app', 'www', fileName), 'utf-8');
}

describe('Kindle phone lane API key handling', () => {
  it('ops lane clears legacy API key session state without persisting new values', () => {
    const html = readLane('ops.html');
    expect(html).toContain('sessionStorage.removeItem(LEGACY_STATE_SESSION_KEY)');
    expect(html).not.toMatch(/PhoneShell\.readSessionJson\(/);
    expect(html).not.toMatch(/PhoneShell\.writeSessionJson\(/);
  });

  it('test lane clears legacy API key session state without persisting new values', () => {
    const html = readLane('test.html');
    expect(html).toContain('sessionStorage.removeItem(LEGACY_TEST_STATE_SESSION_KEY)');
    expect(html).not.toMatch(/PhoneShell\.readSessionJson\(/);
    expect(html).not.toMatch(/PhoneShell\.writeSessionJson\(/);
  });
});
