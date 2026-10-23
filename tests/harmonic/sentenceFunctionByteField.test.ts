import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  decodeSentenceByteField,
  encodeSentenceByteField,
  guideSentenceCount,
  identityBytes,
  matchesGuide,
  permuteByteField,
} from "../../research/sentence-function-byte-field/sentenceFunctionByteField";

const PLAIN = Buffer.from(
  "53464231010101010101020102000a000000627974652d6669656c64" + "01".repeat(40) + "00".repeat(10),
  "hex",
);
const SPANNED = Buffer.from(
  "53464231010101010101020102020000000004000000040000000a0000000a000000" +
    "30313233343536373839" +
    "01".repeat(44) +
    "02".repeat(6),
  "hex",
);
const PERMUTED_SORT = Buffer.from(
  "53464231010101010401020102000a000000627974652d6669656c64" +
    "01".repeat(10) +
    "04".repeat(10) +
    "01".repeat(20) +
    "00".repeat(10),
  "hex",
);

const catalog = JSON.parse(
  readFileSync(
    join(
      dirname(fileURLToPath(import.meta.url)),
      "../../research/sentence-function-byte-field/sentenceFunctionCatalog.json",
    ),
    "utf8",
  ),
) as {
  prose: string;
  slots: unknown[];
  jobs: unknown[];
  phrases: unknown[];
  sentences: Array<{ id: number; sort: number; slot: number }>;
};

describe("sentence function byte field", () => {
  it("matches the shared plain vector", () => {
    const encoded = encodeSentenceByteField(
      new TextEncoder().encode("byte-field"),
      1,
    );
    expect(Buffer.from(encoded).equals(PLAIN)).toBe(true);
  });

  it("paints phrase spans without changing the identity", () => {
    const identity = new TextEncoder().encode("0123456789");
    const encoded = encodeSentenceByteField(identity, 1, [
      [0, 4],
      [4, 10],
    ]);
    expect(Buffer.from(encoded).equals(SPANNED)).toBe(true);
    const decoded = decodeSentenceByteField(encoded);
    expect(Array.from(decoded.channels.phrase)).toEqual([
      1, 1, 1, 1, 2, 2, 2, 2, 2, 2,
    ]);
    expect(Buffer.from(decoded.identity).equals(Buffer.from(identity))).toBe(
      true,
    );
  });

  it("keeps the identity when the sort channel is permuted", () => {
    const encoded = encodeSentenceByteField(
      new TextEncoder().encode("byte-field"),
      1,
    );
    const permuted = permuteByteField(encoded, "sort", 7);
    expect(Buffer.from(permuted).equals(PERMUTED_SORT)).toBe(true);
    expect(Buffer.from(identityBytes(permuted)).toString()).toBe("byte-field");
    expect(matchesGuide(decodeSentenceByteField(permuted))).toBe(false);
    expect(matchesGuide(decodeSentenceByteField(encoded))).toBe(true);
  });

  it("round-trips every guide row", () => {
    expect(guideSentenceCount()).toBe(84);
    expect(catalog.slots).toHaveLength(32);
    expect(catalog.jobs).toHaveLength(32);
    expect(catalog.phrases).toHaveLength(175);
    const marker = new TextEncoder().encode("id");
    catalog.sentences.forEach((row) => {
      const decoded = decodeSentenceByteField(
        encodeSentenceByteField(marker, row.id),
      );
      expect(Buffer.from(decoded.identity).toString()).toBe("id");
      expect(matchesGuide(decoded)).toBe(true);
    });
  });

  it("gives claim rows one sort and more than one slot", () => {
    const claims = catalog.sentences.filter((row) => row.sort === 2);
    expect(new Set(claims.map((row) => row.slot)).size).toBeGreaterThan(1);
  });

  it("refuses a short span list and an overlap", () => {
    const identity = new TextEncoder().encode("abcd");
    expect(() => encodeSentenceByteField(identity, 1, [[0, 1]])).toThrow(
      RangeError,
    );
    expect(() =>
      encodeSentenceByteField(identity, 1, [
        [0, 3],
        [2, 4],
      ]),
    ).toThrow(RangeError);
  });

  it("does not store the essay prose", () => {
    const text = readFileSync(
      join(
        dirname(fileURLToPath(import.meta.url)),
        "../../research/sentence-function-byte-field/sentenceFunctionCatalog.json",
      ),
      "utf8",
    );
    expect(text).not.toContain("Where I come from");
    expect(catalog.prose).toBe("absent");
  });
});
