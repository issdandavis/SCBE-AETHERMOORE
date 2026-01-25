/**
 * Minimal JCS (RFC 8785-like) canonicalization: UTF-8, lexicographic sorting of keys,
 * no insignificant whitespace, stable numbers.
 */
export function canonicalize(value: any): string {
  return JSON.stringify(sort(value));
}

function sort(x: any): any {
  if (x === null || typeof x !== 'object') return normalizeNumber(x);
  if (Array.isArray(x)) return x.map(sort);
  const out: Record<string, any> = {};
  for (const k of Object.keys(x).sort()) out[k] = sort(x[k]);
  return out;
}

function normalizeNumber(x: any): any {
  if (typeof x !== 'number') return x;
  // Ensure JSON number normalization: finite -> as-is, otherwise stringify
  if (!Number.isFinite(x)) return String(x);
  return x;
}
