# Measured results

Date: 2026-11-12 local / 2026-11-13 ledger UTC
Base revision: `abd1ba5962ea488d208b7b1b36a37fd47cc2d62b`
Benchmark command: `python benchmark_compression.py --repeats 3 --json-out compression_market_v1.json`

## Correctness

- Python unit tests: 20 passing after the model-view and sieve additions.
- Rust: 6 passing; `cargo fmt --check` and Clippy with warnings denied.
- Golden vector: 597 bytes, SHA-256
  `c549c006d3378380e37db58ddc44b3a167d3a63bad0f99e731d3d092ab838518`.
- Python, Rust, C, and Java all decoded and re-encoded the exact vector.
- All four rejected a one-byte corruption.

## Compression market report

Every result is lossless and decoder-verified. “Best standard” means the best
direct result among Brotli 11, Zstandard 22, LZMA 9, bzip2 9, zlib 9, and LZ4-HC
16 on this machine—not the best compressor in existence.

| Workload | Raw | HCTX Seam-Sieve + Brotli 11 | Best direct standard | Difference |
|---|---:|---:|---:|---:|
| 256 structured sector packets | 246,528 B | **13,974 B** | Brotli: 20,606 B | **6,632 B smaller (32.18%)** |
| 64 random-payload packet controls | 129,284 B | **36,864 B** | Brotli: 43,853 B | **6,989 B smaller (15.94%)** |
| mixed packets | 375,808 B | **48,412 B** | Brotli: 59,230 B | **10,818 B smaller (18.26%)** |
| packets made from seven tracked repo files | 495,075 B | **26,116 B** | bzip2: 55,413 B | **29,297 B smaller (52.87%)** |

The random-control payload bytes are pseudorandom, but the surrounding packet
and derived token view remain structured. This is intentional: Seam-Sieve is a
specialized packet codec. It does not claim to compress an opaque random byte
string below entropy.

### Speed tradeoff

On the mixed lane, Seam-Sieve + Brotli encoded in 360.070 ms and decoded in
47.637 ms (median of three). Direct Brotli encoded in 453.901 ms but decoded in
1.161 ms. The sieve wins size and encoding time here, but its current Python
structural decoder is much slower. Moving the reversible transform into Rust/C
is the next performance task.

## What has not been beaten

The heavyweight specialist compressors were researched but are not installed or
measured here:

- [cmix](https://github.com/byronknoll/cmix) optimizes ratio at high CPU/memory cost;
- [NNCP](https://bellard.org/nncp/) uses a Transformer-based lossless model;
- [ZPAQ](https://www.mattmahoney.net/dc/zpaqutil.html) supports configurable
  context-mixing models and preprocessing.

Mainstream references used to select the first control set:
[Zstandard](https://github.com/meta/zstd) and
[Brotli RFC 7932](https://www.rfc-editor.org/info/rfc7932/).

The next honest claim gate is an untouched corpus plus cmix/ZPAQ/NNCP when their
source-built runners and resource budgets are available. Program/model size,
peak RAM, encode/decode time, and corpus identity must be reported alongside
compressed bytes.
