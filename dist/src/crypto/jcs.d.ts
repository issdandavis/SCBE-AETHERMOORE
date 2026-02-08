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
export declare function canonicalize(value: unknown): string;
//# sourceMappingURL=jcs.d.ts.map