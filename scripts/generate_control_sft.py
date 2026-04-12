#!/usr/bin/env python3
"""
Control Group SFT Generator
=============================
Generates ~22,000 standard math/code/science training records
with NO SCBE tongues, NO geometry, NO lore. Pure educational content
for the A/B/C comparison control group (Group C).

Topics: arithmetic, algebra, geometry (standard), physics, chemistry,
programming (Python/JS/SQL), logic puzzles, data structures, algorithms.

Output: training-data/sft/control_math_code_sft.jsonl
"""

from __future__ import annotations

import json
import math
import random
import sys
from fractions import Fraction
from pathlib import Path

SEED = 42
random.seed(SEED)

OUT_DIR = Path(__file__).resolve().parent.parent / "training-data" / "sft"
OUT_FILE = OUT_DIR / "control_math_code_sft.jsonl"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def rec(system: str, user: str, assistant: str, tags: dict) -> dict:
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "tags": tags,
    }

MATH_SYSTEM = "You are a helpful math tutor. Show your work step by step."
CODE_SYSTEM = "You are a coding assistant. Write clear, correct code with brief explanations."
SCIENCE_SYSTEM = "You are a science tutor. Explain concepts clearly and give the correct answer."
LOGIC_SYSTEM = "You are a logic puzzle expert. Reason step by step to find the answer."

# ---------------------------------------------------------------------------
# 1. Arithmetic (2000 records)
# ---------------------------------------------------------------------------

def gen_arithmetic() -> list[dict]:
    records = []
    ops = [("+", lambda a, b: a + b), ("-", lambda a, b: a - b),
           ("×", lambda a, b: a * b)]

    # Basic operations (600)
    for _ in range(600):
        a, b = random.randint(1, 999), random.randint(1, 999)
        op_sym, op_fn = random.choice(ops)
        result = op_fn(a, b)
        records.append(rec(MATH_SYSTEM,
            f"What is {a} {op_sym} {b}?",
            f"{a} {op_sym} {b} = {result}",
            {"topic": "arithmetic", "subtopic": "basic_ops"}))

    # Division with remainders (400)
    for _ in range(400):
        b = random.randint(2, 50)
        a = random.randint(b, 1000)
        q, r = divmod(a, b)
        ans = f"{a} ÷ {b} = {q} remainder {r}" if r else f"{a} ÷ {b} = {q}"
        records.append(rec(MATH_SYSTEM,
            f"Divide {a} by {b}. Give quotient and remainder.",
            ans, {"topic": "arithmetic", "subtopic": "division"}))

    # Fractions (500)
    for _ in range(500):
        n1, d1 = random.randint(1, 12), random.randint(2, 12)
        n2, d2 = random.randint(1, 12), random.randint(2, 12)
        f1, f2 = Fraction(n1, d1), Fraction(n2, d2)
        op = random.choice(["+", "-", "×"])
        if op == "+": result = f1 + f2
        elif op == "-": result = f1 - f2
        else: result = f1 * f2
        records.append(rec(MATH_SYSTEM,
            f"Compute {f1} {op} {f2}. Simplify your answer.",
            f"{f1} {op} {f2} = {result}",
            {"topic": "arithmetic", "subtopic": "fractions"}))

    # Percentages (500)
    for _ in range(500):
        base = random.randint(10, 1000)
        pct = random.choice([5, 10, 15, 20, 25, 30, 40, 50, 60, 75, 80, 90])
        val = base * pct / 100
        records.append(rec(MATH_SYSTEM,
            f"What is {pct}% of {base}?",
            f"{pct}% of {base} = {base} × {pct}/100 = {val:.2f}".rstrip('0').rstrip('.'),
            {"topic": "arithmetic", "subtopic": "percentages"}))

    return records

# ---------------------------------------------------------------------------
# 2. Algebra (2500 records)
# ---------------------------------------------------------------------------

def gen_algebra() -> list[dict]:
    records = []

    # Linear equations (800)
    for _ in range(800):
        a = random.choice([i for i in range(-10, 11) if i != 0])
        x_val = random.randint(-20, 20)
        b = random.randint(-50, 50)
        c = a * x_val + b
        records.append(rec(MATH_SYSTEM,
            f"Solve for x: {a}x + {b} = {c}",
            f"{a}x + {b} = {c}\n{a}x = {c} - {b} = {c - b}\nx = {c - b}/{a} = {x_val}",
            {"topic": "algebra", "subtopic": "linear"}))

    # Quadratic equations (700)
    for _ in range(700):
        r1, r2 = random.randint(-10, 10), random.randint(-10, 10)
        a, b, c = 1, -(r1 + r2), r1 * r2
        disc = b * b - 4 * a * c
        records.append(rec(MATH_SYSTEM,
            f"Find the roots of x² + {b}x + {c} = 0",
            f"Using the quadratic formula or factoring:\n"
            f"x² + {b}x + {c} = (x - {r1})(x - {r2}) = 0\n"
            f"x = {r1} or x = {r2}",
            {"topic": "algebra", "subtopic": "quadratic"}))

    # Systems of equations (500)
    for _ in range(500):
        x, y = random.randint(-10, 10), random.randint(-10, 10)
        a1, b1 = random.choice([i for i in range(-5, 6) if i != 0]), random.choice([i for i in range(-5, 6) if i != 0])
        a2, b2 = random.choice([i for i in range(-5, 6) if i != 0]), random.choice([i for i in range(-5, 6) if i != 0])
        c1, c2 = a1 * x + b1 * y, a2 * x + b2 * y
        det = a1 * b2 - a2 * b1
        if det == 0:
            continue
        records.append(rec(MATH_SYSTEM,
            f"Solve the system:\n{a1}x + {b1}y = {c1}\n{a2}x + {b2}y = {c2}",
            f"Using elimination or substitution:\nx = {x}, y = {y}\n"
            f"Check: {a1}({x}) + {b1}({y}) = {c1} ✓\n"
            f"       {a2}({x}) + {b2}({y}) = {c2} ✓",
            {"topic": "algebra", "subtopic": "systems"}))

    # Exponents and logs (500)
    for _ in range(500):
        base = random.choice([2, 3, 5, 10])
        exp = random.randint(1, 8)
        val = base ** exp
        records.append(rec(MATH_SYSTEM,
            f"What is log base {base} of {val}?",
            f"log_{base}({val}) = {exp}\nBecause {base}^{exp} = {val}",
            {"topic": "algebra", "subtopic": "logarithms"}))

    return records[:2500]

# ---------------------------------------------------------------------------
# 3. Geometry (standard, no hyperbolic) (2000 records)
# ---------------------------------------------------------------------------

def gen_geometry() -> list[dict]:
    records = []

    # Triangle area (500)
    for _ in range(500):
        b = random.randint(1, 50)
        h = random.randint(1, 50)
        area = b * h / 2
        records.append(rec(MATH_SYSTEM,
            f"Find the area of a triangle with base {b} and height {h}.",
            f"Area = (1/2) × base × height = (1/2) × {b} × {h} = {area}",
            {"topic": "geometry", "subtopic": "triangle_area"}))

    # Circle calculations (500)
    for _ in range(500):
        r = random.randint(1, 30)
        area = math.pi * r * r
        circ = 2 * math.pi * r
        q = random.choice(["area", "circumference"])
        if q == "area":
            records.append(rec(MATH_SYSTEM,
                f"Find the area of a circle with radius {r}.",
                f"Area = πr² = π × {r}² = {area:.4f}",
                {"topic": "geometry", "subtopic": "circle_area"}))
        else:
            records.append(rec(MATH_SYSTEM,
                f"Find the circumference of a circle with radius {r}.",
                f"C = 2πr = 2 × π × {r} = {circ:.4f}",
                {"topic": "geometry", "subtopic": "circumference"}))

    # Pythagorean theorem (500)
    triples = [(3,4,5),(5,12,13),(8,15,17),(7,24,25),(6,8,10),(9,12,15),(12,16,20),(15,20,25)]
    for _ in range(500):
        a, b, c = random.choice(triples)
        k = random.randint(1, 5)
        a, b, c = a * k, b * k, c * k
        records.append(rec(MATH_SYSTEM,
            f"A right triangle has legs {a} and {b}. Find the hypotenuse.",
            f"c² = a² + b² = {a}² + {b}² = {a*a} + {b*b} = {a*a + b*b}\n"
            f"c = √{c*c} = {c}",
            {"topic": "geometry", "subtopic": "pythagorean"}))

    # Volume (500)
    for _ in range(500):
        shape = random.choice(["cube", "sphere", "cylinder"])
        if shape == "cube":
            s = random.randint(1, 20)
            v = s ** 3
            records.append(rec(MATH_SYSTEM,
                f"Find the volume of a cube with side length {s}.",
                f"V = s³ = {s}³ = {v}",
                {"topic": "geometry", "subtopic": "volume_cube"}))
        elif shape == "sphere":
            r = random.randint(1, 15)
            v = (4/3) * math.pi * r ** 3
            records.append(rec(MATH_SYSTEM,
                f"Find the volume of a sphere with radius {r}.",
                f"V = (4/3)πr³ = (4/3) × π × {r}³ = {v:.4f}",
                {"topic": "geometry", "subtopic": "volume_sphere"}))
        else:
            r = random.randint(1, 15)
            h = random.randint(1, 30)
            v = math.pi * r * r * h
            records.append(rec(MATH_SYSTEM,
                f"Find the volume of a cylinder with radius {r} and height {h}.",
                f"V = πr²h = π × {r}² × {h} = {v:.4f}",
                {"topic": "geometry", "subtopic": "volume_cylinder"}))

    return records

# ---------------------------------------------------------------------------
# 4. Physics (2500 records)
# ---------------------------------------------------------------------------

def gen_physics() -> list[dict]:
    records = []

    # Kinematics (600)
    for _ in range(600):
        v0 = random.randint(0, 30)
        a = random.uniform(-5, 10)
        t = random.randint(1, 20)
        v = v0 + a * t
        d = v0 * t + 0.5 * a * t * t
        records.append(rec(SCIENCE_SYSTEM,
            f"An object starts at {v0} m/s with acceleration {a:.1f} m/s². "
            f"Find its velocity and distance after {t} seconds.",
            f"v = v₀ + at = {v0} + {a:.1f}×{t} = {v:.2f} m/s\n"
            f"d = v₀t + ½at² = {v0}×{t} + ½×{a:.1f}×{t}² = {d:.2f} m",
            {"topic": "physics", "subtopic": "kinematics"}))

    # Newton's laws (500)
    for _ in range(500):
        m = random.randint(1, 100)
        a = random.uniform(0.5, 15)
        f = m * a
        records.append(rec(SCIENCE_SYSTEM,
            f"A {m} kg object accelerates at {a:.1f} m/s². What force is applied?",
            f"F = ma = {m} × {a:.1f} = {f:.1f} N",
            {"topic": "physics", "subtopic": "newtons_laws"}))

    # Energy (500)
    for _ in range(500):
        m = random.randint(1, 50)
        v = random.randint(1, 30)
        ke = 0.5 * m * v * v
        records.append(rec(SCIENCE_SYSTEM,
            f"Find the kinetic energy of a {m} kg object moving at {v} m/s.",
            f"KE = ½mv² = ½ × {m} × {v}² = {ke:.1f} J",
            {"topic": "physics", "subtopic": "energy"}))

    # Gravity (500)
    g = 9.8
    for _ in range(500):
        m = random.randint(1, 200)
        h = random.randint(1, 100)
        pe = m * g * h
        records.append(rec(SCIENCE_SYSTEM,
            f"Find the gravitational PE of a {m} kg object at height {h} m.",
            f"PE = mgh = {m} × 9.8 × {h} = {pe:.1f} J",
            {"topic": "physics", "subtopic": "gravity"}))

    # Ohm's law / circuits (400)
    for _ in range(400):
        v = random.randint(1, 240)
        r = random.randint(1, 100)
        i = v / r
        p = v * i
        q = random.choice(["current", "power"])
        if q == "current":
            records.append(rec(SCIENCE_SYSTEM,
                f"A circuit has {v}V across a {r}Ω resistor. Find the current.",
                f"I = V/R = {v}/{r} = {i:.4f} A",
                {"topic": "physics", "subtopic": "circuits"}))
        else:
            records.append(rec(SCIENCE_SYSTEM,
                f"A circuit has {v}V across a {r}Ω resistor. Find the power dissipated.",
                f"I = V/R = {v}/{r} = {i:.4f} A\nP = VI = {v} × {i:.4f} = {p:.2f} W",
                {"topic": "physics", "subtopic": "circuits"}))

    return records

# ---------------------------------------------------------------------------
# 5. Programming (Python/JS/SQL) (3000 records)
# ---------------------------------------------------------------------------

def gen_programming() -> list[dict]:
    records = []

    # Python basics (1000)
    py_tasks = [
        ("Write a function to check if a number is prime.",
         "def is_prime(n):\n    if n < 2:\n        return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0:\n            return False\n    return True"),
        ("Write a function to reverse a string.",
         "def reverse_string(s):\n    return s[::-1]"),
        ("Write a function to find the factorial of n.",
         "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)"),
        ("Write a function to check if a string is a palindrome.",
         "def is_palindrome(s):\n    s = s.lower().replace(' ', '')\n    return s == s[::-1]"),
        ("Write a function to find the GCD of two numbers.",
         "def gcd(a, b):\n    while b:\n        a, b = b, a % b\n    return a"),
        ("Write a function to flatten a nested list.",
         "def flatten(lst):\n    result = []\n    for item in lst:\n        if isinstance(item, list):\n            result.extend(flatten(item))\n        else:\n            result.append(item)\n    return result"),
        ("Write a function to count word frequencies in a string.",
         "def word_freq(s):\n    words = s.lower().split()\n    freq = {}\n    for w in words:\n        freq[w] = freq.get(w, 0) + 1\n    return freq"),
        ("Write a function to find the nth Fibonacci number.",
         "def fibonacci(n):\n    if n <= 1:\n        return n\n    a, b = 0, 1\n    for _ in range(2, n + 1):\n        a, b = b, a + b\n    return b"),
        ("Write a function to merge two sorted lists.",
         "def merge_sorted(a, b):\n    result = []\n    i = j = 0\n    while i < len(a) and j < len(b):\n        if a[i] <= b[j]:\n            result.append(a[i]); i += 1\n        else:\n            result.append(b[j]); j += 1\n    result.extend(a[i:])\n    result.extend(b[j:])\n    return result"),
        ("Write a function to compute the power set of a list.",
         "def power_set(s):\n    if not s:\n        return [[]]\n    rest = power_set(s[1:])\n    return rest + [[s[0]] + r for r in rest]"),
    ]
    for i in range(1000):
        task, code = py_tasks[i % len(py_tasks)]
        # Add variation
        if i >= len(py_tasks):
            n = random.randint(1, 100)
            task = f"{task} Test it with input {n}."
        records.append(rec(CODE_SYSTEM, task, code,
            {"topic": "programming", "subtopic": "python"}))

    # JavaScript (500)
    js_tasks = [
        ("Write a JS function to find the maximum in an array.",
         "function findMax(arr) {\n  return Math.max(...arr);\n}"),
        ("Write a JS function to remove duplicates from an array.",
         "function removeDuplicates(arr) {\n  return [...new Set(arr)];\n}"),
        ("Write a JS function to deep clone an object.",
         "function deepClone(obj) {\n  return JSON.parse(JSON.stringify(obj));\n}"),
        ("Write a JS function to debounce another function.",
         "function debounce(fn, delay) {\n  let timer;\n  return (...args) => {\n    clearTimeout(timer);\n    timer = setTimeout(() => fn(...args), delay);\n  };\n}"),
        ("Write a JS function to check if two arrays are equal.",
         "function arraysEqual(a, b) {\n  if (a.length !== b.length) return false;\n  return a.every((val, i) => val === b[i]);\n}"),
    ]
    for i in range(500):
        task, code = js_tasks[i % len(js_tasks)]
        records.append(rec(CODE_SYSTEM, task, code,
            {"topic": "programming", "subtopic": "javascript"}))

    # SQL (500)
    sql_tasks = [
        ("Write a SQL query to find the top 5 highest-paid employees.",
         "SELECT name, salary\nFROM employees\nORDER BY salary DESC\nLIMIT 5;"),
        ("Write SQL to count orders per customer.",
         "SELECT customer_id, COUNT(*) as order_count\nFROM orders\nGROUP BY customer_id\nORDER BY order_count DESC;"),
        ("Write SQL to find customers who have never placed an order.",
         "SELECT c.name\nFROM customers c\nLEFT JOIN orders o ON c.id = o.customer_id\nWHERE o.id IS NULL;"),
        ("Write SQL to calculate running total of sales by date.",
         "SELECT date, amount,\n  SUM(amount) OVER (ORDER BY date) as running_total\nFROM sales\nORDER BY date;"),
        ("Write SQL to find duplicate email addresses.",
         "SELECT email, COUNT(*) as cnt\nFROM users\nGROUP BY email\nHAVING COUNT(*) > 1;"),
    ]
    for i in range(500):
        task, code = sql_tasks[i % len(sql_tasks)]
        records.append(rec(CODE_SYSTEM, task, code,
            {"topic": "programming", "subtopic": "sql"}))

    # Data structures & algorithms (1000)
    ds_tasks = [
        ("Explain binary search and write it in Python.",
         "Binary search finds a target in a sorted array by repeatedly halving the search range.\n\n"
         "def binary_search(arr, target):\n    lo, hi = 0, len(arr) - 1\n    while lo <= hi:\n"
         "        mid = (lo + hi) // 2\n        if arr[mid] == target:\n            return mid\n"
         "        elif arr[mid] < target:\n            lo = mid + 1\n        else:\n            hi = mid - 1\n"
         "    return -1\n\nTime: O(log n), Space: O(1)"),
        ("Implement a stack using a list in Python.",
         "class Stack:\n    def __init__(self):\n        self.items = []\n    def push(self, x):\n"
         "        self.items.append(x)\n    def pop(self):\n        return self.items.pop()\n"
         "    def peek(self):\n        return self.items[-1]\n    def is_empty(self):\n"
         "        return len(self.items) == 0"),
        ("Implement BFS on a graph.",
         "from collections import deque\n\ndef bfs(graph, start):\n    visited = set([start])\n"
         "    queue = deque([start])\n    order = []\n    while queue:\n        node = queue.popleft()\n"
         "        order.append(node)\n        for neighbor in graph[node]:\n"
         "            if neighbor not in visited:\n                visited.add(neighbor)\n"
         "                queue.append(neighbor)\n    return order"),
        ("Implement quicksort in Python.",
         "def quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr)//2]\n"
         "    left = [x for x in arr if x < pivot]\n    mid = [x for x in arr if x == pivot]\n"
         "    right = [x for x in arr if x > pivot]\n    return quicksort(left) + mid + quicksort(right)"),
        ("Implement a hash map with chaining.",
         "class HashMap:\n    def __init__(self, size=16):\n        self.size = size\n"
         "        self.buckets = [[] for _ in range(size)]\n    def _hash(self, key):\n"
         "        return hash(key) % self.size\n    def put(self, key, val):\n"
         "        bucket = self.buckets[self._hash(key)]\n        for i, (k, v) in enumerate(bucket):\n"
         "            if k == key:\n                bucket[i] = (key, val); return\n"
         "        bucket.append((key, val))\n    def get(self, key):\n"
         "        for k, v in self.buckets[self._hash(key)]:\n"
         "            if k == key: return v\n        return None"),
    ]
    for i in range(1000):
        task, code = ds_tasks[i % len(ds_tasks)]
        records.append(rec(CODE_SYSTEM, task, code,
            {"topic": "programming", "subtopic": "data_structures"}))

    return records

# ---------------------------------------------------------------------------
# 6. Logic puzzles (2000 records)
# ---------------------------------------------------------------------------

def gen_logic() -> list[dict]:
    records = []

    # Number sequences (500)
    for _ in range(500):
        start = random.randint(1, 20)
        step = random.randint(1, 10)
        seq = [start + i * step for i in range(5)]
        next_val = start + 5 * step
        records.append(rec(LOGIC_SYSTEM,
            f"What comes next: {', '.join(map(str, seq))}, ?",
            f"The pattern is: add {step} each time.\n"
            f"Next: {seq[-1]} + {step} = {next_val}",
            {"topic": "logic", "subtopic": "sequences"}))

    # Age problems (500)
    for _ in range(500):
        age_now = random.randint(5, 50)
        years = random.randint(1, 20)
        ratio = random.randint(2, 5)
        parent_age = ratio * age_now - (ratio - 1) * years if random.random() < 0.5 else age_now + random.randint(15, 35)
        records.append(rec(LOGIC_SYSTEM,
            f"Alice is {age_now} years old. In {years} years, she will be {age_now + years}. "
            f"How old was she {years} years ago?",
            f"Alice's age {years} years ago = {age_now} - {years} = {age_now - years}",
            {"topic": "logic", "subtopic": "age_problems"}))

    # Set operations (500)
    for _ in range(500):
        a = set(random.sample(range(1, 20), random.randint(3, 7)))
        b = set(random.sample(range(1, 20), random.randint(3, 7)))
        op = random.choice(["union", "intersection", "difference"])
        if op == "union":
            result = sorted(a | b)
            records.append(rec(LOGIC_SYSTEM,
                f"Find A ∪ B where A = {{{', '.join(map(str, sorted(a)))}}} and B = {{{', '.join(map(str, sorted(b)))}}}",
                f"A ∪ B = {{{', '.join(map(str, result))}}}",
                {"topic": "logic", "subtopic": "sets"}))
        elif op == "intersection":
            result = sorted(a & b)
            records.append(rec(LOGIC_SYSTEM,
                f"Find A ∩ B where A = {{{', '.join(map(str, sorted(a)))}}} and B = {{{', '.join(map(str, sorted(b)))}}}",
                f"A ∩ B = {{{', '.join(map(str, result))}}}",
                {"topic": "logic", "subtopic": "sets"}))
        else:
            result = sorted(a - b)
            records.append(rec(LOGIC_SYSTEM,
                f"Find A \\ B where A = {{{', '.join(map(str, sorted(a)))}}} and B = {{{', '.join(map(str, sorted(b)))}}}",
                f"A \\ B = {{{', '.join(map(str, result))}}}",
                {"topic": "logic", "subtopic": "sets"}))

    # Boolean logic (500)
    for _ in range(500):
        p = random.choice([True, False])
        q = random.choice([True, False])
        op = random.choice(["AND", "OR", "XOR", "IMPLIES"])
        if op == "AND": result = p and q
        elif op == "OR": result = p or q
        elif op == "XOR": result = p ^ q
        else: result = (not p) or q
        records.append(rec(LOGIC_SYSTEM,
            f"Evaluate: {p} {op} {q}",
            f"{p} {op} {q} = {result}",
            {"topic": "logic", "subtopic": "boolean"}))

    return records

# ---------------------------------------------------------------------------
# 7. Statistics & Probability (2000 records)
# ---------------------------------------------------------------------------

def gen_stats() -> list[dict]:
    records = []

    # Mean, median, mode (700)
    for _ in range(700):
        n = random.randint(5, 12)
        data = [random.randint(1, 100) for _ in range(n)]
        mean = sum(data) / len(data)
        sorted_d = sorted(data)
        if n % 2 == 0:
            median = (sorted_d[n//2 - 1] + sorted_d[n//2]) / 2
        else:
            median = sorted_d[n//2]
        records.append(rec(MATH_SYSTEM,
            f"Find the mean and median of: {data}",
            f"Mean = {sum(data)}/{len(data)} = {mean:.2f}\n"
            f"Sorted: {sorted_d}\nMedian = {median}",
            {"topic": "statistics", "subtopic": "central_tendency"}))

    # Probability (700)
    for _ in range(700):
        scenario = random.choice(["dice", "cards", "coins"])
        if scenario == "dice":
            target = random.randint(1, 6)
            records.append(rec(MATH_SYSTEM,
                f"What is the probability of rolling a {target} on a fair 6-sided die?",
                f"P({target}) = 1/6 ≈ {1/6:.4f}",
                {"topic": "statistics", "subtopic": "probability"}))
        elif scenario == "cards":
            suit = random.choice(["hearts", "spades", "diamonds", "clubs"])
            records.append(rec(MATH_SYSTEM,
                f"What is the probability of drawing a {suit} card from a standard deck?",
                f"There are 13 {suit} in 52 cards.\nP({suit}) = 13/52 = 1/4 = 0.25",
                {"topic": "statistics", "subtopic": "probability"}))
        else:
            n = random.randint(2, 5)
            k = random.randint(0, n)
            from math import comb
            prob = comb(n, k) / (2 ** n)
            records.append(rec(MATH_SYSTEM,
                f"Flip {n} fair coins. What is the probability of exactly {k} heads?",
                f"P(X={k}) = C({n},{k}) / 2^{n} = {comb(n,k)}/{2**n} = {prob:.4f}",
                {"topic": "statistics", "subtopic": "probability"}))

    # Standard deviation (600)
    for _ in range(600):
        n = random.randint(4, 8)
        data = [random.randint(1, 50) for _ in range(n)]
        mean = sum(data) / n
        var = sum((x - mean) ** 2 for x in data) / n
        std = math.sqrt(var)
        records.append(rec(MATH_SYSTEM,
            f"Find the population standard deviation of: {data}",
            f"Mean = {mean:.2f}\n"
            f"Variance = Σ(x-μ)²/N = {var:.4f}\n"
            f"σ = √{var:.4f} = {std:.4f}",
            {"topic": "statistics", "subtopic": "standard_deviation"}))

    return records

# ---------------------------------------------------------------------------
# 8. Chemistry basics (2000 records)
# ---------------------------------------------------------------------------

def gen_chemistry() -> list[dict]:
    records = []
    elements = [
        ("H", "Hydrogen", 1, 1.008), ("He", "Helium", 2, 4.003),
        ("Li", "Lithium", 3, 6.941), ("C", "Carbon", 6, 12.011),
        ("N", "Nitrogen", 7, 14.007), ("O", "Oxygen", 8, 15.999),
        ("Na", "Sodium", 11, 22.990), ("Cl", "Chlorine", 17, 35.453),
        ("Fe", "Iron", 26, 55.845), ("Au", "Gold", 79, 196.967),
        ("Cu", "Copper", 29, 63.546), ("Ag", "Silver", 47, 107.868),
        ("K", "Potassium", 19, 39.098), ("Ca", "Calcium", 20, 40.078),
        ("S", "Sulfur", 16, 32.065), ("P", "Phosphorus", 15, 30.974),
        ("Al", "Aluminum", 13, 26.982), ("Si", "Silicon", 14, 28.086),
        ("Mg", "Magnesium", 12, 24.305), ("Zn", "Zinc", 30, 65.38),
    ]

    # Element identification (500)
    for i in range(500):
        sym, name, num, mass = elements[i % len(elements)]
        q = random.choice(["number", "mass", "name"])
        if q == "number":
            records.append(rec(SCIENCE_SYSTEM,
                f"What is the atomic number of {name}?",
                f"The atomic number of {name} ({sym}) is {num}.",
                {"topic": "chemistry", "subtopic": "elements"}))
        elif q == "mass":
            records.append(rec(SCIENCE_SYSTEM,
                f"What is the atomic mass of {name}?",
                f"The atomic mass of {name} ({sym}) is approximately {mass} amu.",
                {"topic": "chemistry", "subtopic": "elements"}))
        else:
            records.append(rec(SCIENCE_SYSTEM,
                f"What element has the symbol {sym}?",
                f"{sym} is the symbol for {name} (atomic number {num}).",
                {"topic": "chemistry", "subtopic": "elements"}))

    # Molar mass calculations (500)
    compounds = [
        ("H2O", "water", 2 * 1.008 + 15.999),
        ("CO2", "carbon dioxide", 12.011 + 2 * 15.999),
        ("NaCl", "sodium chloride", 22.990 + 35.453),
        ("C6H12O6", "glucose", 6 * 12.011 + 12 * 1.008 + 6 * 15.999),
        ("CaCO3", "calcium carbonate", 40.078 + 12.011 + 3 * 15.999),
        ("H2SO4", "sulfuric acid", 2 * 1.008 + 32.065 + 4 * 15.999),
        ("NH3", "ammonia", 14.007 + 3 * 1.008),
        ("CH4", "methane", 12.011 + 4 * 1.008),
    ]
    for i in range(500):
        formula, name, mm = compounds[i % len(compounds)]
        records.append(rec(SCIENCE_SYSTEM,
            f"Calculate the molar mass of {formula} ({name}).",
            f"Molar mass of {formula} = {mm:.3f} g/mol",
            {"topic": "chemistry", "subtopic": "molar_mass"}))

    # Balancing equations (500)
    equations = [
        ("_ H2 + _ O2 -> _ H2O", "2 H2 + 1 O2 -> 2 H2O"),
        ("_ Fe + _ O2 -> _ Fe2O3", "4 Fe + 3 O2 -> 2 Fe2O3"),
        ("_ CH4 + _ O2 -> _ CO2 + _ H2O", "1 CH4 + 2 O2 -> 1 CO2 + 2 H2O"),
        ("_ Na + _ Cl2 -> _ NaCl", "2 Na + 1 Cl2 -> 2 NaCl"),
        ("_ N2 + _ H2 -> _ NH3", "1 N2 + 3 H2 -> 2 NH3"),
    ]
    for i in range(500):
        unbal, bal = equations[i % len(equations)]
        records.append(rec(SCIENCE_SYSTEM,
            f"Balance this chemical equation: {unbal}",
            f"Balanced: {bal}",
            {"topic": "chemistry", "subtopic": "balancing"}))

    # pH and solutions (500)
    for _i in range(500):
        conc = 10 ** (-random.randint(1, 13))
        ph = -math.log10(conc)
        records.append(rec(SCIENCE_SYSTEM,
            f"What is the pH of a solution with [H+] = {conc:.0e} M?",
            f"pH = -log₁₀([H+]) = -log₁₀({conc:.0e}) = {ph:.1f}",
            {"topic": "chemistry", "subtopic": "pH"}))

    return records

# ---------------------------------------------------------------------------
# 9. Unit conversions & word problems (2000 records)
# ---------------------------------------------------------------------------

def gen_word_problems() -> list[dict]:
    records = []

    # Unit conversions (500)
    conversions = [
        ("km", "miles", 0.621371), ("kg", "pounds", 2.20462),
        ("celsius", "fahrenheit", None), ("liters", "gallons", 0.264172),
        ("meters", "feet", 3.28084), ("cm", "inches", 0.393701),
    ]
    for _ in range(500):
        from_u, to_u, factor = random.choice(conversions)
        val = random.randint(1, 100)
        if from_u == "celsius":
            result = val * 9/5 + 32
            records.append(rec(MATH_SYSTEM,
                f"Convert {val}°C to Fahrenheit.",
                f"°F = °C × 9/5 + 32 = {val} × 9/5 + 32 = {result:.1f}°F",
                {"topic": "word_problems", "subtopic": "conversions"}))
        else:
            result = val * factor
            records.append(rec(MATH_SYSTEM,
                f"Convert {val} {from_u} to {to_u}.",
                f"{val} {from_u} × {factor} = {result:.2f} {to_u}",
                {"topic": "word_problems", "subtopic": "conversions"}))

    # Rate problems (500)
    for _ in range(500):
        speed = random.randint(20, 120)
        time = random.randint(1, 10)
        dist = speed * time
        records.append(rec(MATH_SYSTEM,
            f"A car travels at {speed} km/h for {time} hours. How far does it go?",
            f"Distance = speed × time = {speed} × {time} = {dist} km",
            {"topic": "word_problems", "subtopic": "rate"}))

    # Mixture problems (500)
    for _ in range(500):
        c1 = random.randint(5, 40)
        c2 = random.randint(c1 + 5, 90)
        v1 = random.randint(1, 20)
        v2 = random.randint(1, 20)
        result_conc = (c1 * v1 + c2 * v2) / (v1 + v2)
        records.append(rec(MATH_SYSTEM,
            f"Mix {v1}L of {c1}% solution with {v2}L of {c2}% solution. "
            f"What is the resulting concentration?",
            f"Total solute = {c1}%×{v1} + {c2}%×{v2} = {c1*v1/100:.2f} + {c2*v2/100:.2f} = {(c1*v1+c2*v2)/100:.2f}\n"
            f"Total volume = {v1+v2}L\n"
            f"Concentration = {result_conc:.2f}%",
            {"topic": "word_problems", "subtopic": "mixtures"}))

    # Profit/loss (500)
    for _ in range(500):
        cost = random.randint(10, 500)
        markup_pct = random.randint(5, 100)
        sell = cost * (1 + markup_pct / 100)
        profit = sell - cost
        records.append(rec(MATH_SYSTEM,
            f"An item costs ${cost}. It is sold at a {markup_pct}% markup. "
            f"Find the selling price and profit.",
            f"Selling price = ${cost} × (1 + {markup_pct}/100) = ${sell:.2f}\n"
            f"Profit = ${sell:.2f} - ${cost} = ${profit:.2f}",
            {"topic": "word_problems", "subtopic": "profit_loss"}))

    return records

# ---------------------------------------------------------------------------
# 10. Trigonometry (2000 records)
# ---------------------------------------------------------------------------

def gen_trig() -> list[dict]:
    records = []

    angles_deg = [0, 30, 45, 60, 90, 120, 135, 150, 180, 210, 225, 240, 270, 300, 315, 330, 360]

    # sin/cos/tan values (700)
    for _ in range(700):
        deg = random.choice(angles_deg[:9])  # 0-180
        rad = math.radians(deg)
        fn = random.choice(["sin", "cos", "tan"])
        if fn == "sin":
            val = math.sin(rad)
        elif fn == "cos":
            val = math.cos(rad)
        else:
            if deg == 90:
                continue
            val = math.tan(rad)
        records.append(rec(MATH_SYSTEM,
            f"What is {fn}({deg}°)?",
            f"{fn}({deg}°) = {val:.4f}",
            {"topic": "trigonometry", "subtopic": "values"}))

    # Inverse trig (500)
    for _ in range(500):
        val = round(random.uniform(-1, 1), 2)
        angle = math.degrees(math.asin(val))
        records.append(rec(MATH_SYSTEM,
            f"Find arcsin({val}) in degrees.",
            f"arcsin({val}) = {angle:.2f}°",
            {"topic": "trigonometry", "subtopic": "inverse"}))

    # Radian conversion (400)
    for _ in range(400):
        deg = random.choice(angles_deg)
        rad = deg * math.pi / 180
        records.append(rec(MATH_SYSTEM,
            f"Convert {deg}° to radians.",
            f"{deg}° = {deg} × π/180 = {rad:.4f} radians",
            {"topic": "trigonometry", "subtopic": "conversion"}))

    # Law of cosines (400)
    for _ in range(400):
        a = random.randint(3, 20)
        b = random.randint(3, 20)
        C_deg = random.choice([30, 45, 60, 90, 120])
        C_rad = math.radians(C_deg)
        c_sq = a*a + b*b - 2*a*b*math.cos(C_rad)
        c = math.sqrt(c_sq)
        records.append(rec(MATH_SYSTEM,
            f"Triangle with sides a={a}, b={b} and included angle C={C_deg}°. Find side c.",
            f"c² = a² + b² - 2ab·cos(C)\n"
            f"c² = {a}² + {b}² - 2({a})({b})cos({C_deg}°)\n"
            f"c² = {a*a} + {b*b} - {2*a*b}×{math.cos(C_rad):.4f} = {c_sq:.4f}\n"
            f"c = {c:.4f}",
            {"topic": "trigonometry", "subtopic": "law_of_cosines"}))

    return records[:2000]

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("Control Group SFT Generator (NO SCBE, pure math/code/science)")
    print("=" * 70)

    generators = [
        ("arithmetic", gen_arithmetic),
        ("algebra", gen_algebra),
        ("geometry", gen_geometry),
        ("physics", gen_physics),
        ("programming", gen_programming),
        ("logic", gen_logic),
        ("statistics", gen_stats),
        ("chemistry", gen_chemistry),
        ("word_problems", gen_word_problems),
        ("trigonometry", gen_trig),
    ]

    all_records = []
    for name, gen_fn in generators:
        print(f"\n  Generating {name}...", end="", flush=True)
        recs = gen_fn()
        print(f"  {len(recs)} records")
        all_records.extend(recs)

    random.shuffle(all_records)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nWriting {len(all_records)} records to {OUT_FILE.name}...", end="", flush=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        for r in all_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(" done")

    fsize = OUT_FILE.stat().st_size
    print(f"\n{'=' * 70}")
    print(f"GENERATION COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Total records:     {len(all_records):,}")
    print(f"  File size:      {fsize:,} bytes ({fsize / 1_048_576:.1f} MB)")

    # Topic distribution
    from collections import Counter
    topics = Counter(r["tags"]["topic"] for r in all_records)
    print(f"\n  Topic distribution:")
    for t, c in sorted(topics.items()):
        print(f"    {t:<25} {c:>5} ({100*c/len(all_records):.1f}%)")

if __name__ == "__main__":
    main()
