# Thread: I tested my own 109x claim

1.

I had a "109x faster than Python" claim attached to one of my Rust encoder builds.

It sounded great.

So I tested it properly.

The real number was not 109x.

It was about 4.5x.

2.

The project is an AST encoder: Python source in, structured cube/matrix representation out.

I had a Python path and a Rust path.

The kind of thing where "Rust is much faster" is believable enough that a bad number can survive if nobody checks it.

3.

I wrote a real benchmark instead of trusting the old claim:

- warmups
- 20+ measured runs
- median/mean/stddev
- coefficient of variation
- local laptop run
- clean Kaggle run

Then I compared the actual receipts.

4.

What reproduced:

- local full encode: about 3.4x
- Kaggle full encode: 4.53x
- startup-excluded engine: about 4.6x
- parse-only best case: about 6x

What did not reproduce:

- 109x

5.

The important correction:

Python's parser is not "slow Python code."

`ast.parse` is backed by CPython internals. So my Rust parser was not racing naive Python. It was racing a serious C-backed baseline.

That matters.

6.

The 109x number probably came from a very favorable slice:

- parse-heavy
- different parser path
- startup excluded
- maybe different corpus

That is not the same as the thing I actually ship.

7.

I could have left the big number alone.

But a 109x claim that collapses when someone checks it is not marketing.

It is debt.

A reproduced 4.5x is smaller, but it is real.

8.

That is the lesson I am taking forward:

I would rather publish a humble number with receipts than a giant number that evaporates under a stopwatch.

Especially in AI/dev tools, where the internet is already drowning in 100x claims.

9.

The full writeup has the benchmark table and the reasoning.

The repo has the harness, cards, and Kaggle run.

Title:

"I said my code was 109x faster than Python. I tested it. Here's the real number."

