/**
 * Minimal JCS (RFC 8785-like) canonicalization: UTF-8, lexicographic sorting of keys,
 * no insignificant whitespace, stable numbers.
 */

/** JSON-compatible primitive types */
export type JsonPrimitive = string | number | boolean | null;

/** JSON-compatible value types (recursive) */
export type JsonValue = JsonPrimitive | JsonObject | JsonArray;

/** JSON-compatible object type */
export interface JsonObject {
  [key: string]: JsonValue;
}

/** JSON-compatible array type */
export type JsonArray = JsonValue[];

/**
 * Canonicalize a JSON-compatible value according to RFC 8785
 * @param value - The value to canonicalize (must be JSON-serializable)
 * @returns Canonicalized JSON string
 */
export function canonicalize(value: unknown): string {
  return JSON.stringify(sort(value as JsonValue));
}

function sort(x: JsonValue): JsonValue {
  if (x === null || typeof x !== 'object') return normalizeNumber(x);
  if (Array.isArray(x)) return x.map(sort);
  const out: JsonObject = {};
  for (const k of Object.keys(x).sort()) out[k] = sort((x as JsonObject)[k]);
  return out;
}

function normalizeNumber(x: JsonPrimitive): JsonPrimitive {
  if (typeof x !== 'number') return x;
  // Ensure JSON number normalization: finite -> as-is, otherwise stringify
  if (!Number.isFinite(x)) return String(x);
  return x;
}
