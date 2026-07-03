# Machine Crystal - Bhargava Factorial Layer

Date: 2026-06-27

## Why this exists

Bhargava did not stop at cubes. One adjacent tool is the Bhargava factorial:
a generalized factorial `k!_S` associated with a set `S`, developed through
`p`-orderings.

For the Machine Crystal, this gives a second arithmetic layer:

```text
generalized factorial values -> 8-address cube entries -> Bhargava-cube overlay
```

## Implemented

```text
python/scbe/machine_crystal_bhargava_factorial.py
scripts/benchmarks/bench_machine_crystal_bhargava_factorial.py
```

Implemented exact surfaces:

- `S = Z`: `k!_S = k!`
- `S = aZ + b`: `k!_S = |a|^k k!`

Validated:

- ordinary factorial reconstructed from prime-power valuations for `0..12`.
- divisibility law `(m+n)!_S` divisible by `m!_S n!_S` where checked.
- even integers formula `2^k k!`.
- arithmetic progression formula `|a|^k k!`.
- first eight factorial values feed into the Bhargava cube overlay and preserve equal discriminants.

## Command

```powershell
python scripts\benchmarks\bench_machine_crystal_bhargava_factorial.py
```

Receipt:

```text
artifacts/machine_crystal/bhargava_factorial.json
```

## Honest boundary

This is not the full arbitrary-set `p`-ordering algorithm.

Supported now:

- exact integer factorial surface,
- exact arithmetic-progression surface,
- Machine Crystal cube overlay.

Backlog:

- finite p-ordering search,
- arbitrary subsets of `Z`,
- prime sets,
- squares,
- polynomial interpolation applications.

## Sources

- Bhargava factorial summary: https://en.wikipedia.org/wiki/Bhargava_factorial
- Bhargava, The Factorial Function and Generalizations: https://gaurish4math.wordpress.com/wp-content/uploads/2015/11/2695734.pdf
- p-ordering algorithms: https://arxiv.org/abs/2011.10978
- IMU Fields Medal note: https://www.mathunion.org/fileadmin/IMU/Prizes/Fields/2014/news_release_bhargava.pdf
