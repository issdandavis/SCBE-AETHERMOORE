#!/usr/bin/env python3
"""Generate Rosetta Stone SFT dataset: identical operations across 10 languages.

Each record shows the SAME operation in multiple languages so the model learns
cross-language equivalence. Covers fundamentals through advanced patterns.

Languages: Python, TypeScript, Rust, Go, Java, C++, C#, Ruby, Swift, Kotlin
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "training-data" / "sft"
OUT.mkdir(parents=True, exist_ok=True)

SYSTEM_MSG = (
    "You are Polly, the SCBE-AETHERMOORE coding assistant. "
    "You help developers understand how to implement identical operations "
    "across different programming languages."
)

LANGS = ["Python", "TypeScript", "Rust", "Go", "Java", "C++", "C#", "Ruby", "Swift", "Kotlin"]

# ─────────────────────────────────────────────
# Operation definitions: (category, name, description, {lang: code})
# ─────────────────────────────────────────────

OPERATIONS: list[dict] = [
    # ── Basics ──
    {
        "category": "basics",
        "name": "Hello World",
        "desc": "Print 'Hello, World!' to stdout",
        "code": {
            "Python": 'print("Hello, World!")',
            "TypeScript": 'console.log("Hello, World!");',
            "Rust": 'fn main() {\n    println!("Hello, World!");\n}',
            "Go": 'package main\n\nimport "fmt"\n\nfunc main() {\n    fmt.Println("Hello, World!")\n}',
            "Java": 'public class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello, World!");\n    }\n}',
            "C++": '#include <iostream>\n\nint main() {\n    std::cout << "Hello, World!" << std::endl;\n    return 0;\n}',
            "C#": 'Console.WriteLine("Hello, World!");',
            "Ruby": 'puts "Hello, World!"',
            "Swift": 'print("Hello, World!")',
            "Kotlin": 'fun main() {\n    println("Hello, World!")\n}',
        },
    },
    {
        "category": "basics",
        "name": "Variable Declaration",
        "desc": "Declare typed and inferred variables",
        "code": {
            "Python": 'name: str = "Polly"\nage: int = 1\npi = 3.14159  # inferred',
            "TypeScript": 'const name: string = "Polly";\nlet age: number = 1;\nconst pi = 3.14159;  // inferred',
            "Rust": 'let name: &str = "Polly";\nlet age: i32 = 1;\nlet pi = 3.14159_f64;  // inferred',
            "Go": 'var name string = "Polly"\nvar age int = 1\npi := 3.14159  // inferred',
            "Java": 'String name = "Polly";\nint age = 1;\nvar pi = 3.14159;  // inferred (Java 10+)',
            "C++": 'std::string name = "Polly";\nint age = 1;\nauto pi = 3.14159;  // inferred',
            "C#": 'string name = "Polly";\nint age = 1;\nvar pi = 3.14159;  // inferred',
            "Ruby": 'name = "Polly"  # dynamic\nage = 1\npi = 3.14159',
            "Swift": 'let name: String = "Polly"\nvar age: Int = 1\nlet pi = 3.14159  // inferred',
            "Kotlin": 'val name: String = "Polly"\nvar age: Int = 1\nval pi = 3.14159  // inferred',
        },
    },
    {
        "category": "basics",
        "name": "String Interpolation",
        "desc": "Embed variables inside strings",
        "code": {
            "Python": 'name = "Polly"\nprint(f"Hello, {name}! You are {2+1} years old.")',
            "TypeScript": 'const name = "Polly";\nconsole.log(`Hello, ${name}! You are ${2+1} years old.`);',
            "Rust": 'let name = "Polly";\nprintln!("Hello, {}! You are {} years old.", name, 2+1);',
            "Go": 'name := "Polly"\nfmt.Sprintf("Hello, %s! You are %d years old.", name, 2+1)',
            "Java": 'String name = "Polly";\nString msg = String.format("Hello, %s! You are %d years old.", name, 2+1);',
            "C++": 'std::string name = "Polly";\nstd::format("Hello, {}! You are {} years old.", name, 2+1);  // C++20',
            "C#": 'string name = "Polly";\nConsole.WriteLine($"Hello, {name}! You are {2+1} years old.");',
            "Ruby": 'name = "Polly"\nputs "Hello, #{name}! You are #{2+1} years old."',
            "Swift": 'let name = "Polly"\nprint("Hello, \\(name)! You are \\(2+1) years old.")',
            "Kotlin": 'val name = "Polly"\nprintln("Hello, $name! You are ${2+1} years old.")',
        },
    },
    # ── Control Flow ──
    {
        "category": "control-flow",
        "name": "If/Else",
        "desc": "Conditional branching",
        "code": {
            "Python": 'if score > 90:\n    grade = "A"\nelif score > 70:\n    grade = "B"\nelse:\n    grade = "C"',
            "TypeScript": 'if (score > 90) {\n    grade = "A";\n} else if (score > 70) {\n    grade = "B";\n} else {\n    grade = "C";\n}',
            "Rust": 'let grade = if score > 90 {\n    "A"\n} else if score > 70 {\n    "B"\n} else {\n    "C"\n};',
            "Go": 'if score > 90 {\n    grade = "A"\n} else if score > 70 {\n    grade = "B"\n} else {\n    grade = "C"\n}',
            "Java": 'if (score > 90) {\n    grade = "A";\n} else if (score > 70) {\n    grade = "B";\n} else {\n    grade = "C";\n}',
            "C++": 'if (score > 90) {\n    grade = "A";\n} else if (score > 70) {\n    grade = "B";\n} else {\n    grade = "C";\n}',
            "C#": 'if (score > 90) {\n    grade = "A";\n} else if (score > 70) {\n    grade = "B";\n} else {\n    grade = "C";\n}',
            "Ruby": 'grade = if score > 90\n    "A"\n  elsif score > 70\n    "B"\n  else\n    "C"\n  end',
            "Swift": 'if score > 90 {\n    grade = "A"\n} else if score > 70 {\n    grade = "B"\n} else {\n    grade = "C"\n}',
            "Kotlin": 'val grade = when {\n    score > 90 -> "A"\n    score > 70 -> "B"\n    else -> "C"\n}',
        },
    },
    {
        "category": "control-flow",
        "name": "For Loop",
        "desc": "Iterate over a range of numbers",
        "code": {
            "Python": "for i in range(10):\n    print(i)",
            "TypeScript": "for (let i = 0; i < 10; i++) {\n    console.log(i);\n}",
            "Rust": "for i in 0..10 {\n    println!(\"{}\", i);\n}",
            "Go": "for i := 0; i < 10; i++ {\n    fmt.Println(i)\n}",
            "Java": "for (int i = 0; i < 10; i++) {\n    System.out.println(i);\n}",
            "C++": "for (int i = 0; i < 10; i++) {\n    std::cout << i << std::endl;\n}",
            "C#": "for (int i = 0; i < 10; i++) {\n    Console.WriteLine(i);\n}",
            "Ruby": "(0...10).each { |i| puts i }",
            "Swift": "for i in 0..<10 {\n    print(i)\n}",
            "Kotlin": "for (i in 0 until 10) {\n    println(i)\n}",
        },
    },
    {
        "category": "control-flow",
        "name": "While Loop",
        "desc": "Loop until a condition is false",
        "code": {
            "Python": "count = 0\nwhile count < 5:\n    print(count)\n    count += 1",
            "TypeScript": "let count = 0;\nwhile (count < 5) {\n    console.log(count);\n    count++;\n}",
            "Rust": "let mut count = 0;\nwhile count < 5 {\n    println!(\"{}\", count);\n    count += 1;\n}",
            "Go": "count := 0\nfor count < 5 {\n    fmt.Println(count)\n    count++\n}",
            "Java": "int count = 0;\nwhile (count < 5) {\n    System.out.println(count);\n    count++;\n}",
            "C++": "int count = 0;\nwhile (count < 5) {\n    std::cout << count << std::endl;\n    count++;\n}",
            "C#": "int count = 0;\nwhile (count < 5) {\n    Console.WriteLine(count);\n    count++;\n}",
            "Ruby": "count = 0\nwhile count < 5\n  puts count\n  count += 1\nend",
            "Swift": "var count = 0\nwhile count < 5 {\n    print(count)\n    count += 1\n}",
            "Kotlin": "var count = 0\nwhile (count < 5) {\n    println(count)\n    count++\n}",
        },
    },
    {
        "category": "control-flow",
        "name": "Pattern Matching / Switch",
        "desc": "Match a value against multiple patterns",
        "code": {
            "Python": 'match command:\n    case "start":\n        run()\n    case "stop":\n        halt()\n    case _:\n        print("unknown")',
            "TypeScript": 'switch (command) {\n    case "start": run(); break;\n    case "stop": halt(); break;\n    default: console.log("unknown");\n}',
            "Rust": 'match command {\n    "start" => run(),\n    "stop" => halt(),\n    _ => println!("unknown"),\n}',
            "Go": 'switch command {\ncase "start":\n    run()\ncase "stop":\n    halt()\ndefault:\n    fmt.Println("unknown")\n}',
            "Java": 'switch (command) {\n    case "start" -> run();\n    case "stop" -> halt();\n    default -> System.out.println("unknown");\n}',
            "C++": 'switch (command) {  // only works with int/enum\n    case START: run(); break;\n    case STOP: halt(); break;\n    default: std::cout << "unknown";\n}',
            "C#": 'switch (command) {\n    case "start": Run(); break;\n    case "stop": Halt(); break;\n    default: Console.WriteLine("unknown"); break;\n}',
            "Ruby": 'case command\nwhen "start" then run\nwhen "stop" then halt\nelse puts "unknown"\nend',
            "Swift": 'switch command {\ncase "start": run()\ncase "stop": halt()\ndefault: print("unknown")\n}',
            "Kotlin": 'when (command) {\n    "start" -> run()\n    "stop" -> halt()\n    else -> println("unknown")\n}',
        },
    },
    # ── Data Structures ──
    {
        "category": "data-structures",
        "name": "Array / List Creation",
        "desc": "Create and manipulate ordered collections",
        "code": {
            "Python": "nums = [1, 2, 3, 4, 5]\nnums.append(6)\nfirst = nums[0]\nlength = len(nums)",
            "TypeScript": "const nums: number[] = [1, 2, 3, 4, 5];\nnums.push(6);\nconst first = nums[0];\nconst length = nums.length;",
            "Rust": "let mut nums = vec![1, 2, 3, 4, 5];\nnums.push(6);\nlet first = nums[0];\nlet length = nums.len();",
            "Go": "nums := []int{1, 2, 3, 4, 5}\nnums = append(nums, 6)\nfirst := nums[0]\nlength := len(nums)",
            "Java": "List<Integer> nums = new ArrayList<>(List.of(1, 2, 3, 4, 5));\nnums.add(6);\nint first = nums.get(0);\nint length = nums.size();",
            "C++": "std::vector<int> nums = {1, 2, 3, 4, 5};\nnums.push_back(6);\nint first = nums[0];\nsize_t length = nums.size();",
            "C#": "var nums = new List<int> {1, 2, 3, 4, 5};\nnums.Add(6);\nint first = nums[0];\nint length = nums.Count;",
            "Ruby": "nums = [1, 2, 3, 4, 5]\nnums << 6\nfirst = nums[0]\nlength = nums.length",
            "Swift": "var nums = [1, 2, 3, 4, 5]\nnums.append(6)\nlet first = nums[0]\nlet length = nums.count",
            "Kotlin": "val nums = mutableListOf(1, 2, 3, 4, 5)\nnums.add(6)\nval first = nums[0]\nval length = nums.size",
        },
    },
    {
        "category": "data-structures",
        "name": "Hash Map / Dictionary",
        "desc": "Key-value storage with string keys",
        "code": {
            "Python": 'scores = {"alice": 95, "bob": 87}\nscores["carol"] = 92\nval = scores.get("alice", 0)',
            "TypeScript": 'const scores: Record<string, number> = { alice: 95, bob: 87 };\nscores["carol"] = 92;\nconst val = scores["alice"] ?? 0;',
            "Rust": 'use std::collections::HashMap;\nlet mut scores = HashMap::new();\nscores.insert("alice", 95);\nscores.insert("bob", 87);\nlet val = scores.get("alice").copied().unwrap_or(0);',
            "Go": 'scores := map[string]int{"alice": 95, "bob": 87}\nscores["carol"] = 92\nval, ok := scores["alice"]',
            "Java": 'Map<String, Integer> scores = new HashMap<>(Map.of("alice", 95, "bob", 87));\nscores.put("carol", 92);\nint val = scores.getOrDefault("alice", 0);',
            "C++": 'std::unordered_map<std::string, int> scores = {{"alice", 95}, {"bob", 87}};\nscores["carol"] = 92;\nint val = scores.count("alice") ? scores["alice"] : 0;',
            "C#": 'var scores = new Dictionary<string, int> { ["alice"] = 95, ["bob"] = 87 };\nscores["carol"] = 92;\nscores.TryGetValue("alice", out int val);',
            "Ruby": 'scores = { "alice" => 95, "bob" => 87 }\nscores["carol"] = 92\nval = scores.fetch("alice", 0)',
            "Swift": 'var scores = ["alice": 95, "bob": 87]\nscores["carol"] = 92\nlet val = scores["alice"] ?? 0',
            "Kotlin": 'val scores = mutableMapOf("alice" to 95, "bob" to 87)\nscores["carol"] = 92\nval value = scores.getOrDefault("alice", 0)',
        },
    },
    {
        "category": "data-structures",
        "name": "Struct / Data Class",
        "desc": "Define a typed data container",
        "code": {
            "Python": 'from dataclasses import dataclass\n\n@dataclass\nclass Point:\n    x: float\n    y: float\n\np = Point(3.0, 4.0)\ndist = (p.x**2 + p.y**2) ** 0.5',
            "TypeScript": 'interface Point {\n    x: number;\n    y: number;\n}\n\nconst p: Point = { x: 3.0, y: 4.0 };\nconst dist = Math.sqrt(p.x ** 2 + p.y ** 2);',
            "Rust": 'struct Point {\n    x: f64,\n    y: f64,\n}\n\nlet p = Point { x: 3.0, y: 4.0 };\nlet dist = (p.x.powi(2) + p.y.powi(2)).sqrt();',
            "Go": 'type Point struct {\n    X float64\n    Y float64\n}\n\np := Point{X: 3.0, Y: 4.0}\ndist := math.Sqrt(p.X*p.X + p.Y*p.Y)',
            "Java": 'record Point(double x, double y) {}\n\nvar p = new Point(3.0, 4.0);\ndouble dist = Math.sqrt(p.x() * p.x() + p.y() * p.y());',
            "C++": 'struct Point {\n    double x;\n    double y;\n};\n\nPoint p{3.0, 4.0};\ndouble dist = std::sqrt(p.x * p.x + p.y * p.y);',
            "C#": 'record Point(double X, double Y);\n\nvar p = new Point(3.0, 4.0);\ndouble dist = Math.Sqrt(p.X * p.X + p.Y * p.Y);',
            "Ruby": 'Point = Struct.new(:x, :y)\n\np = Point.new(3.0, 4.0)\ndist = Math.sqrt(p.x**2 + p.y**2)',
            "Swift": 'struct Point {\n    let x: Double\n    let y: Double\n}\n\nlet p = Point(x: 3.0, y: 4.0)\nlet dist = sqrt(p.x * p.x + p.y * p.y)',
            "Kotlin": 'data class Point(val x: Double, val y: Double)\n\nval p = Point(3.0, 4.0)\nval dist = sqrt(p.x.pow(2) + p.y.pow(2))',
        },
    },
    # ── Functions ──
    {
        "category": "functions",
        "name": "Function Definition",
        "desc": "Define a function with parameters and return type",
        "code": {
            "Python": "def add(a: int, b: int) -> int:\n    return a + b",
            "TypeScript": "function add(a: number, b: number): number {\n    return a + b;\n}",
            "Rust": "fn add(a: i32, b: i32) -> i32 {\n    a + b\n}",
            "Go": "func add(a, b int) int {\n    return a + b\n}",
            "Java": "static int add(int a, int b) {\n    return a + b;\n}",
            "C++": "int add(int a, int b) {\n    return a + b;\n}",
            "C#": "static int Add(int a, int b) {\n    return a + b;\n}",
            "Ruby": "def add(a, b)\n  a + b\nend",
            "Swift": "func add(_ a: Int, _ b: Int) -> Int {\n    return a + b\n}",
            "Kotlin": "fun add(a: Int, b: Int): Int {\n    return a + b\n}",
        },
    },
    {
        "category": "functions",
        "name": "Lambda / Closure",
        "desc": "Anonymous function passed as argument",
        "code": {
            "Python": "nums = [3, 1, 4, 1, 5]\nsorted_nums = sorted(nums, key=lambda x: -x)",
            "TypeScript": "const nums = [3, 1, 4, 1, 5];\nconst sorted = nums.sort((a, b) => b - a);",
            "Rust": "let mut nums = vec![3, 1, 4, 1, 5];\nnums.sort_by(|a, b| b.cmp(a));",
            "Go": "nums := []int{3, 1, 4, 1, 5}\nsort.Slice(nums, func(i, j int) bool {\n    return nums[i] > nums[j]\n})",
            "Java": "List<Integer> nums = Arrays.asList(3, 1, 4, 1, 5);\nnums.sort((a, b) -> b - a);",
            "C++": "std::vector<int> nums = {3, 1, 4, 1, 5};\nstd::sort(nums.begin(), nums.end(), [](int a, int b) { return a > b; });",
            "C#": "var nums = new List<int> {3, 1, 4, 1, 5};\nnums.Sort((a, b) => b.CompareTo(a));",
            "Ruby": "nums = [3, 1, 4, 1, 5]\nsorted = nums.sort { |a, b| b <=> a }",
            "Swift": "var nums = [3, 1, 4, 1, 5]\nnums.sort { $0 > $1 }",
            "Kotlin": "val nums = mutableListOf(3, 1, 4, 1, 5)\nnums.sortWith { a, b -> b - a }",
        },
    },
    {
        "category": "functions",
        "name": "Map / Transform",
        "desc": "Transform each element in a collection",
        "code": {
            "Python": "nums = [1, 2, 3, 4]\nsquared = [x**2 for x in nums]  # or list(map(lambda x: x**2, nums))",
            "TypeScript": "const nums = [1, 2, 3, 4];\nconst squared = nums.map(x => x ** 2);",
            "Rust": "let nums = vec![1, 2, 3, 4];\nlet squared: Vec<i32> = nums.iter().map(|x| x * x).collect();",
            "Go": "nums := []int{1, 2, 3, 4}\nsquared := make([]int, len(nums))\nfor i, x := range nums {\n    squared[i] = x * x\n}",
            "Java": "List<Integer> nums = List.of(1, 2, 3, 4);\nList<Integer> squared = nums.stream().map(x -> x * x).toList();",
            "C++": "std::vector<int> nums = {1, 2, 3, 4};\nstd::vector<int> squared;\nstd::transform(nums.begin(), nums.end(), std::back_inserter(squared),\n    [](int x) { return x * x; });",
            "C#": "var nums = new[] {1, 2, 3, 4};\nvar squared = nums.Select(x => x * x).ToList();",
            "Ruby": "nums = [1, 2, 3, 4]\nsquared = nums.map { |x| x**2 }",
            "Swift": "let nums = [1, 2, 3, 4]\nlet squared = nums.map { $0 * $0 }",
            "Kotlin": "val nums = listOf(1, 2, 3, 4)\nval squared = nums.map { it * it }",
        },
    },
    {
        "category": "functions",
        "name": "Filter",
        "desc": "Select elements matching a predicate",
        "code": {
            "Python": "nums = [1, 2, 3, 4, 5, 6]\nevens = [x for x in nums if x % 2 == 0]",
            "TypeScript": "const nums = [1, 2, 3, 4, 5, 6];\nconst evens = nums.filter(x => x % 2 === 0);",
            "Rust": "let nums = vec![1, 2, 3, 4, 5, 6];\nlet evens: Vec<i32> = nums.into_iter().filter(|x| x % 2 == 0).collect();",
            "Go": "nums := []int{1, 2, 3, 4, 5, 6}\nvar evens []int\nfor _, x := range nums {\n    if x%2 == 0 {\n        evens = append(evens, x)\n    }\n}",
            "Java": "List<Integer> nums = List.of(1, 2, 3, 4, 5, 6);\nList<Integer> evens = nums.stream().filter(x -> x % 2 == 0).toList();",
            "C++": "std::vector<int> nums = {1, 2, 3, 4, 5, 6};\nstd::vector<int> evens;\nstd::copy_if(nums.begin(), nums.end(), std::back_inserter(evens),\n    [](int x) { return x % 2 == 0; });",
            "C#": "var nums = new[] {1, 2, 3, 4, 5, 6};\nvar evens = nums.Where(x => x % 2 == 0).ToList();",
            "Ruby": "nums = [1, 2, 3, 4, 5, 6]\nevens = nums.select { |x| x.even? }",
            "Swift": "let nums = [1, 2, 3, 4, 5, 6]\nlet evens = nums.filter { $0 % 2 == 0 }",
            "Kotlin": "val nums = listOf(1, 2, 3, 4, 5, 6)\nval evens = nums.filter { it % 2 == 0 }",
        },
    },
    {
        "category": "functions",
        "name": "Reduce / Fold",
        "desc": "Combine all elements into a single value",
        "code": {
            "Python": "from functools import reduce\nnums = [1, 2, 3, 4, 5]\ntotal = reduce(lambda acc, x: acc + x, nums, 0)  # or sum(nums)",
            "TypeScript": "const nums = [1, 2, 3, 4, 5];\nconst total = nums.reduce((acc, x) => acc + x, 0);",
            "Rust": "let nums = vec![1, 2, 3, 4, 5];\nlet total: i32 = nums.iter().fold(0, |acc, x| acc + x);",
            "Go": "nums := []int{1, 2, 3, 4, 5}\ntotal := 0\nfor _, x := range nums {\n    total += x\n}",
            "Java": "List<Integer> nums = List.of(1, 2, 3, 4, 5);\nint total = nums.stream().reduce(0, Integer::sum);",
            "C++": "std::vector<int> nums = {1, 2, 3, 4, 5};\nint total = std::accumulate(nums.begin(), nums.end(), 0);",
            "C#": "var nums = new[] {1, 2, 3, 4, 5};\nint total = nums.Aggregate(0, (acc, x) => acc + x);  // or nums.Sum()",
            "Ruby": "nums = [1, 2, 3, 4, 5]\ntotal = nums.reduce(0) { |acc, x| acc + x }  # or nums.sum",
            "Swift": "let nums = [1, 2, 3, 4, 5]\nlet total = nums.reduce(0, +)",
            "Kotlin": "val nums = listOf(1, 2, 3, 4, 5)\nval total = nums.fold(0) { acc, x -> acc + x }  // or nums.sum()",
        },
    },
    # ── Error Handling ──
    {
        "category": "error-handling",
        "name": "Try/Catch / Result",
        "desc": "Handle errors and exceptions",
        "code": {
            "Python": 'try:\n    result = int("abc")\nexcept ValueError as e:\n    print(f"Error: {e}")\nfinally:\n    print("done")',
            "TypeScript": 'try {\n    const result = JSON.parse("invalid");\n} catch (e) {\n    console.error(`Error: ${e}`);\n} finally {\n    console.log("done");\n}',
            "Rust": 'fn parse(s: &str) -> Result<i32, std::num::ParseIntError> {\n    s.parse::<i32>()\n}\n\nmatch parse("abc") {\n    Ok(n) => println!("{}", n),\n    Err(e) => println!("Error: {}", e),\n}',
            "Go": 'n, err := strconv.Atoi("abc")\nif err != nil {\n    fmt.Printf("Error: %v\\n", err)\n} else {\n    fmt.Println(n)\n}',
            "Java": 'try {\n    int result = Integer.parseInt("abc");\n} catch (NumberFormatException e) {\n    System.out.println("Error: " + e.getMessage());\n} finally {\n    System.out.println("done");\n}',
            "C++": 'try {\n    int result = std::stoi("abc");\n} catch (const std::exception& e) {\n    std::cerr << "Error: " << e.what() << std::endl;\n}',
            "C#": 'try {\n    int result = int.Parse("abc");\n} catch (FormatException e) {\n    Console.WriteLine($"Error: {e.Message}");\n} finally {\n    Console.WriteLine("done");\n}',
            "Ruby": 'begin\n  result = Integer("abc")\nrescue ArgumentError => e\n  puts "Error: #{e.message}"\nensure\n  puts "done"\nend',
            "Swift": 'do {\n    let data = try Data(contentsOf: url)\n} catch {\n    print("Error: \\(error)")\n}',
            "Kotlin": 'try {\n    val result = "abc".toInt()\n} catch (e: NumberFormatException) {\n    println("Error: ${e.message}")\n} finally {\n    println("done")\n}',
        },
    },
    {
        "category": "error-handling",
        "name": "Optional / Nullable",
        "desc": "Handle values that might not exist",
        "code": {
            "Python": 'from typing import Optional\n\ndef find(name: str) -> Optional[int]:\n    data = {"alice": 95}\n    return data.get(name)  # returns None if missing\n\nresult = find("bob")\nif result is not None:\n    print(result)',
            "TypeScript": 'function find(name: string): number | undefined {\n    const data: Record<string, number> = { alice: 95 };\n    return data[name];\n}\n\nconst result = find("bob");\nif (result !== undefined) {\n    console.log(result);\n}',
            "Rust": 'fn find(name: &str) -> Option<i32> {\n    let data = HashMap::from([("alice", 95)]);\n    data.get(name).copied()\n}\n\nif let Some(val) = find("bob") {\n    println!("{}", val);\n}',
            "Go": 'func find(name string) (int, bool) {\n    data := map[string]int{"alice": 95}\n    val, ok := data[name]\n    return val, ok\n}\n\nif val, ok := find("bob"); ok {\n    fmt.Println(val)\n}',
            "Java": 'Optional<Integer> find(String name) {\n    Map<String, Integer> data = Map.of("alice", 95);\n    return Optional.ofNullable(data.get(name));\n}\n\nfind("bob").ifPresent(System.out::println);',
            "C++": 'std::optional<int> find(const std::string& name) {\n    std::map<std::string, int> data = {{"alice", 95}};\n    auto it = data.find(name);\n    if (it != data.end()) return it->second;\n    return std::nullopt;\n}\n\nif (auto val = find("bob")) {\n    std::cout << *val;\n}',
            "C#": 'int? Find(string name) {\n    var data = new Dictionary<string, int> { ["alice"] = 95 };\n    return data.TryGetValue(name, out var val) ? val : null;\n}\n\nif (Find("bob") is int val) {\n    Console.WriteLine(val);\n}',
            "Ruby": 'def find(name)\n  data = { "alice" => 95 }\n  data[name]  # returns nil if missing\nend\n\nresult = find("bob")\nputs result unless result.nil?',
            "Swift": 'func find(_ name: String) -> Int? {\n    let data = ["alice": 95]\n    return data[name]\n}\n\nif let val = find("bob") {\n    print(val)\n}',
            "Kotlin": 'fun find(name: String): Int? {\n    val data = mapOf("alice" to 95)\n    return data[name]\n}\n\nfind("bob")?.let { println(it) }',
        },
    },
    # ── Async / Concurrency ──
    {
        "category": "async",
        "name": "Async / Await",
        "desc": "Asynchronous function execution",
        "code": {
            "Python": 'import asyncio\n\nasync def fetch_data(url: str) -> str:\n    await asyncio.sleep(1)  # simulate IO\n    return "data"\n\nasync def main():\n    result = await fetch_data("https://example.com")\n    print(result)\n\nasyncio.run(main())',
            "TypeScript": 'async function fetchData(url: string): Promise<string> {\n    const res = await fetch(url);\n    return await res.text();\n}\n\nconst result = await fetchData("https://example.com");\nconsole.log(result);',
            "Rust": 'async fn fetch_data(url: &str) -> Result<String, reqwest::Error> {\n    let body = reqwest::get(url).await?.text().await?;\n    Ok(body)\n}\n\n#[tokio::main]\nasync fn main() {\n    let result = fetch_data("https://example.com").await.unwrap();\n    println!("{}", result);\n}',
            "Go": 'func fetchData(url string) <-chan string {\n    ch := make(chan string)\n    go func() {\n        resp, _ := http.Get(url)\n        body, _ := io.ReadAll(resp.Body)\n        ch <- string(body)\n    }()\n    return ch\n}\n\nresult := <-fetchData("https://example.com")',
            "Java": 'CompletableFuture<String> fetchData(String url) {\n    return CompletableFuture.supplyAsync(() -> {\n        // HTTP call here\n        return "data";\n    });\n}\n\nString result = fetchData("https://example.com").join();',
            "C++": '// C++20 coroutines (simplified)\ntask<std::string> fetch_data(std::string url) {\n    auto response = co_await http_get(url);\n    co_return response.body();\n}',
            "C#": 'async Task<string> FetchData(string url) {\n    using var client = new HttpClient();\n    return await client.GetStringAsync(url);\n}\n\nstring result = await FetchData("https://example.com");',
            "Ruby": '# Ruby uses fibers/threads\nrequire "async"\n\nAsync do\n  result = Async::HTTP::Internet.new.get("https://example.com")\n  puts result.read\nend',
            "Swift": 'func fetchData(url: URL) async throws -> String {\n    let (data, _) = try await URLSession.shared.data(from: url)\n    return String(data: data, encoding: .utf8) ?? ""\n}\n\nlet result = try await fetchData(url: myURL)',
            "Kotlin": 'suspend fun fetchData(url: String): String {\n    return withContext(Dispatchers.IO) {\n        URL(url).readText()\n    }\n}\n\nrunBlocking {\n    val result = fetchData("https://example.com")\n    println(result)\n}',
        },
    },
    # ── File I/O ──
    {
        "category": "file-io",
        "name": "Read File",
        "desc": "Read entire file contents as string",
        "code": {
            "Python": 'with open("data.txt", "r", encoding="utf-8") as f:\n    content = f.read()',
            "TypeScript": 'import { readFileSync } from "fs";\nconst content = readFileSync("data.txt", "utf-8");',
            "Rust": 'use std::fs;\nlet content = fs::read_to_string("data.txt").expect("failed to read");',
            "Go": 'content, err := os.ReadFile("data.txt")\nif err != nil {\n    log.Fatal(err)\n}\ntext := string(content)',
            "Java": 'String content = Files.readString(Path.of("data.txt"));',
            "C++": 'std::ifstream file("data.txt");\nstd::string content((std::istreambuf_iterator<char>(file)),\n                     std::istreambuf_iterator<char>());',
            "C#": 'string content = File.ReadAllText("data.txt");',
            "Ruby": 'content = File.read("data.txt")',
            "Swift": 'let content = try String(contentsOfFile: "data.txt", encoding: .utf8)',
            "Kotlin": 'val content = File("data.txt").readText()',
        },
    },
    {
        "category": "file-io",
        "name": "Write File",
        "desc": "Write string to a file",
        "code": {
            "Python": 'with open("output.txt", "w", encoding="utf-8") as f:\n    f.write("Hello, file!")',
            "TypeScript": 'import { writeFileSync } from "fs";\nwriteFileSync("output.txt", "Hello, file!", "utf-8");',
            "Rust": 'use std::fs;\nfs::write("output.txt", "Hello, file!").expect("failed to write");',
            "Go": 'err := os.WriteFile("output.txt", []byte("Hello, file!"), 0644)\nif err != nil {\n    log.Fatal(err)\n}',
            "Java": 'Files.writeString(Path.of("output.txt"), "Hello, file!");',
            "C++": 'std::ofstream file("output.txt");\nfile << "Hello, file!";',
            "C#": 'File.WriteAllText("output.txt", "Hello, file!");',
            "Ruby": 'File.write("output.txt", "Hello, file!")',
            "Swift": 'try "Hello, file!".write(toFile: "output.txt", atomically: true, encoding: .utf8)',
            "Kotlin": 'File("output.txt").writeText("Hello, file!")',
        },
    },
    {
        "category": "file-io",
        "name": "JSON Parse",
        "desc": "Parse a JSON string into a native object",
        "code": {
            "Python": 'import json\n\ndata = json.loads(\'{"name": "Polly", "age": 1}\')\nprint(data["name"])',
            "TypeScript": 'const data = JSON.parse(\'{"name": "Polly", "age": 1}\');\nconsole.log(data.name);',
            "Rust": 'use serde_json::Value;\n\nlet data: Value = serde_json::from_str(r#"{"name": "Polly", "age": 1}"#).unwrap();\nprintln!("{}", data["name"]);',
            "Go": 'var data map[string]interface{}\njson.Unmarshal([]byte(`{"name": "Polly", "age": 1}`), &data)\nfmt.Println(data["name"])',
            "Java": 'var mapper = new ObjectMapper();\nvar data = mapper.readTree("{\\\"name\\\": \\\"Polly\\\", \\\"age\\\": 1}");\nSystem.out.println(data.get("name").asText());',
            "C++": '// Using nlohmann/json\nauto data = nlohmann::json::parse(R"({"name": "Polly", "age": 1})");\nstd::cout << data["name"];',
            "C#": 'using System.Text.Json;\nvar data = JsonDocument.Parse("{\\\"name\\\": \\\"Polly\\\", \\\"age\\\": 1}");\nConsole.WriteLine(data.RootElement.GetProperty("name"));',
            "Ruby": 'require "json"\n\ndata = JSON.parse(\'{"name": "Polly", "age": 1}\')\nputs data["name"]',
            "Swift": 'let json = Data(#"{"name": "Polly", "age": 1}"#.utf8)\nlet data = try JSONSerialization.jsonObject(with: json) as! [String: Any]\nprint(data["name"]!)',
            "Kotlin": 'import kotlinx.serialization.json.*\n\nval data = Json.parseToJsonElement("""{"name": "Polly", "age": 1}""")\nprintln(data.jsonObject["name"])',
        },
    },
    # ── OOP / Interfaces ──
    {
        "category": "oop",
        "name": "Interface / Trait / Protocol",
        "desc": "Define a contract that types must satisfy",
        "code": {
            "Python": 'from abc import ABC, abstractmethod\n\nclass Shape(ABC):\n    @abstractmethod\n    def area(self) -> float: ...\n\nclass Circle(Shape):\n    def __init__(self, r: float):\n        self.r = r\n    def area(self) -> float:\n        return 3.14159 * self.r ** 2',
            "TypeScript": 'interface Shape {\n    area(): number;\n}\n\nclass Circle implements Shape {\n    constructor(private r: number) {}\n    area(): number {\n        return Math.PI * this.r ** 2;\n    }\n}',
            "Rust": 'trait Shape {\n    fn area(&self) -> f64;\n}\n\nstruct Circle { r: f64 }\n\nimpl Shape for Circle {\n    fn area(&self) -> f64 {\n        std::f64::consts::PI * self.r.powi(2)\n    }\n}',
            "Go": 'type Shape interface {\n    Area() float64\n}\n\ntype Circle struct {\n    R float64\n}\n\nfunc (c Circle) Area() float64 {\n    return math.Pi * c.R * c.R\n}',
            "Java": 'interface Shape {\n    double area();\n}\n\nclass Circle implements Shape {\n    private double r;\n    Circle(double r) { this.r = r; }\n    public double area() {\n        return Math.PI * r * r;\n    }\n}',
            "C++": 'class Shape {\npublic:\n    virtual double area() const = 0;\n    virtual ~Shape() = default;\n};\n\nclass Circle : public Shape {\n    double r;\npublic:\n    Circle(double r) : r(r) {}\n    double area() const override {\n        return M_PI * r * r;\n    }\n};',
            "C#": 'interface IShape {\n    double Area();\n}\n\nclass Circle : IShape {\n    private double r;\n    public Circle(double r) => this.r = r;\n    public double Area() => Math.PI * r * r;\n}',
            "Ruby": 'module Shape\n  def area\n    raise NotImplementedError\n  end\nend\n\nclass Circle\n  include Shape\n  def initialize(r)\n    @r = r\n  end\n  def area\n    Math::PI * @r**2\n  end\nend',
            "Swift": 'protocol Shape {\n    func area() -> Double\n}\n\nstruct Circle: Shape {\n    let r: Double\n    func area() -> Double {\n        return .pi * r * r\n    }\n}',
            "Kotlin": 'interface Shape {\n    fun area(): Double\n}\n\nclass Circle(private val r: Double) : Shape {\n    override fun area(): Double = Math.PI * r * r\n}',
        },
    },
    {
        "category": "oop",
        "name": "Generics / Templates",
        "desc": "Write type-parameterized functions",
        "code": {
            "Python": 'from typing import TypeVar, List\n\nT = TypeVar("T")\n\ndef first(items: List[T]) -> T:\n    return items[0]',
            "TypeScript": "function first<T>(items: T[]): T {\n    return items[0];\n}",
            "Rust": "fn first<T: Clone>(items: &[T]) -> T {\n    items[0].clone()\n}",
            "Go": "func First[T any](items []T) T {\n    return items[0]\n}",
            "Java": "static <T> T first(List<T> items) {\n    return items.get(0);\n}",
            "C++": "template<typename T>\nT first(const std::vector<T>& items) {\n    return items[0];\n}",
            "C#": "static T First<T>(List<T> items) {\n    return items[0];\n}",
            "Ruby": "# Ruby is dynamically typed - no generics needed\ndef first(items)\n  items[0]\nend",
            "Swift": "func first<T>(_ items: [T]) -> T {\n    return items[0]\n}",
            "Kotlin": "fun <T> first(items: List<T>): T {\n    return items[0]\n}",
        },
    },
    # ── Testing ──
    {
        "category": "testing",
        "name": "Unit Test",
        "desc": "Write a basic unit test",
        "code": {
            "Python": 'import pytest\n\ndef add(a, b):\n    return a + b\n\ndef test_add():\n    assert add(2, 3) == 5\n    assert add(-1, 1) == 0\n    assert add(0, 0) == 0',
            "TypeScript": 'import { describe, it, expect } from "vitest";\n\nfunction add(a: number, b: number) { return a + b; }\n\ndescribe("add", () => {\n    it("adds two numbers", () => {\n        expect(add(2, 3)).toBe(5);\n        expect(add(-1, 1)).toBe(0);\n    });\n});',
            "Rust": '#[cfg(test)]\nmod tests {\n    fn add(a: i32, b: i32) -> i32 { a + b }\n\n    #[test]\n    fn test_add() {\n        assert_eq!(add(2, 3), 5);\n        assert_eq!(add(-1, 1), 0);\n    }\n}',
            "Go": 'func add(a, b int) int { return a + b }\n\nfunc TestAdd(t *testing.T) {\n    if add(2, 3) != 5 {\n        t.Error("expected 5")\n    }\n    if add(-1, 1) != 0 {\n        t.Error("expected 0")\n    }\n}',
            "Java": '@Test\nvoid testAdd() {\n    assertEquals(5, add(2, 3));\n    assertEquals(0, add(-1, 1));\n    assertEquals(0, add(0, 0));\n}',
            "C++": '// Using Google Test\nTEST(AddTest, BasicCases) {\n    EXPECT_EQ(add(2, 3), 5);\n    EXPECT_EQ(add(-1, 1), 0);\n    EXPECT_EQ(add(0, 0), 0);\n}',
            "C#": '[Fact]\npublic void TestAdd() {\n    Assert.Equal(5, Add(2, 3));\n    Assert.Equal(0, Add(-1, 1));\n    Assert.Equal(0, Add(0, 0));\n}',
            "Ruby": 'require "minitest/autorun"\n\nclass TestAdd < Minitest::Test\n  def test_add\n    assert_equal 5, add(2, 3)\n    assert_equal 0, add(-1, 1)\n  end\nend',
            "Swift": 'import XCTest\n\nclass AddTests: XCTestCase {\n    func testAdd() {\n        XCTAssertEqual(add(2, 3), 5)\n        XCTAssertEqual(add(-1, 1), 0)\n    }\n}',
            "Kotlin": '@Test\nfun testAdd() {\n    assertEquals(5, add(2, 3))\n    assertEquals(0, add(-1, 1))\n    assertEquals(0, add(0, 0))\n}',
        },
    },
    # ── HTTP ──
    {
        "category": "http",
        "name": "HTTP GET Request",
        "desc": "Make an HTTP GET request and read the response",
        "code": {
            "Python": 'import requests\n\nresponse = requests.get("https://api.example.com/data")\nif response.status_code == 200:\n    data = response.json()',
            "TypeScript": 'const response = await fetch("https://api.example.com/data");\nif (response.ok) {\n    const data = await response.json();\n}',
            "Rust": 'let response = reqwest::get("https://api.example.com/data").await?;\nif response.status().is_success() {\n    let data: serde_json::Value = response.json().await?;\n}',
            "Go": 'resp, err := http.Get("https://api.example.com/data")\nif err == nil && resp.StatusCode == 200 {\n    body, _ := io.ReadAll(resp.Body)\n    var data map[string]interface{}\n    json.Unmarshal(body, &data)\n}',
            "Java": 'var client = HttpClient.newHttpClient();\nvar request = HttpRequest.newBuilder()\n    .uri(URI.create("https://api.example.com/data")).build();\nvar response = client.send(request, BodyHandlers.ofString());\nif (response.statusCode() == 200) {\n    String body = response.body();\n}',
            "C++": '// Using cpr library\nauto response = cpr::Get(cpr::Url{"https://api.example.com/data"});\nif (response.status_code == 200) {\n    auto data = nlohmann::json::parse(response.text);\n}',
            "C#": 'using var client = new HttpClient();\nvar response = await client.GetAsync("https://api.example.com/data");\nif (response.IsSuccessStatusCode) {\n    string body = await response.Content.ReadAsStringAsync();\n}',
            "Ruby": 'require "net/http"\nrequire "json"\n\nuri = URI("https://api.example.com/data")\nresponse = Net::HTTP.get_response(uri)\ndata = JSON.parse(response.body) if response.is_a?(Net::HTTPSuccess)',
            "Swift": 'let url = URL(string: "https://api.example.com/data")!\nlet (data, response) = try await URLSession.shared.data(from: url)\nif let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {\n    let json = try JSONSerialization.jsonObject(with: data)\n}',
            "Kotlin": 'val client = HttpClient.newHttpClient()\nval request = HttpRequest.newBuilder()\n    .uri(URI.create("https://api.example.com/data")).build()\nval response = client.send(request, BodyHandlers.ofString())\nif (response.statusCode() == 200) {\n    val body = response.body()\n}',
        },
    },
    # ── String Operations ──
    {
        "category": "strings",
        "name": "String Split and Join",
        "desc": "Split a string by delimiter and rejoin",
        "code": {
            "Python": 'text = "one,two,three"\nparts = text.split(",")\nrejoined = "-".join(parts)',
            "TypeScript": 'const text = "one,two,three";\nconst parts = text.split(",");\nconst rejoined = parts.join("-");',
            "Rust": 'let text = "one,two,three";\nlet parts: Vec<&str> = text.split(",").collect();\nlet rejoined = parts.join("-");',
            "Go": 'text := "one,two,three"\nparts := strings.Split(text, ",")\nrejoined := strings.Join(parts, "-")',
            "Java": 'String text = "one,two,three";\nString[] parts = text.split(",");\nString rejoined = String.join("-", parts);',
            "C++": '// Using ranges (C++20) or boost\nstd::string text = "one,two,three";\n// split into vector, then join with "-"',
            "C#": 'string text = "one,two,three";\nstring[] parts = text.Split(",");\nstring rejoined = string.Join("-", parts);',
            "Ruby": 'text = "one,two,three"\nparts = text.split(",")\nrejoined = parts.join("-")',
            "Swift": 'let text = "one,two,three"\nlet parts = text.split(separator: ",")\nlet rejoined = parts.joined(separator: "-")',
            "Kotlin": 'val text = "one,two,three"\nval parts = text.split(",")\nval rejoined = parts.joinToString("-")',
        },
    },
    {
        "category": "strings",
        "name": "Regex Match",
        "desc": "Find pattern matches in a string",
        "code": {
            "Python": 'import re\n\ntext = "Call 555-1234 or 555-5678"\nmatches = re.findall(r"\\d{3}-\\d{4}", text)\n# ["555-1234", "555-5678"]',
            "TypeScript": 'const text = "Call 555-1234 or 555-5678";\nconst matches = text.match(/\\d{3}-\\d{4}/g);\n// ["555-1234", "555-5678"]',
            "Rust": 'use regex::Regex;\n\nlet re = Regex::new(r"\\d{3}-\\d{4}").unwrap();\nlet text = "Call 555-1234 or 555-5678";\nlet matches: Vec<&str> = re.find_iter(text).map(|m| m.as_str()).collect();',
            "Go": 'import "regexp"\n\nre := regexp.MustCompile(`\\d{3}-\\d{4}`)\ntext := "Call 555-1234 or 555-5678"\nmatches := re.FindAllString(text, -1)',
            "Java": 'Pattern p = Pattern.compile("\\\\d{3}-\\\\d{4}");\nMatcher m = p.matcher("Call 555-1234 or 555-5678");\nList<String> matches = new ArrayList<>();\nwhile (m.find()) matches.add(m.group());',
            "C++": '#include <regex>\n\nstd::regex pattern(R"(\\d{3}-\\d{4})");\nstd::string text = "Call 555-1234 or 555-5678";\nauto begin = std::sregex_iterator(text.begin(), text.end(), pattern);',
            "C#": 'var matches = Regex.Matches("Call 555-1234 or 555-5678", @"\\d{3}-\\d{4}");\nforeach (Match m in matches) {\n    Console.WriteLine(m.Value);\n}',
            "Ruby": 'text = "Call 555-1234 or 555-5678"\nmatches = text.scan(/\\d{3}-\\d{4}/)\n# ["555-1234", "555-5678"]',
            "Swift": 'let text = "Call 555-1234 or 555-5678"\nlet regex = try Regex(#"\\d{3}-\\d{4}"#)\nlet matches = text.matches(of: regex)',
            "Kotlin": 'val text = "Call 555-1234 or 555-5678"\nval matches = Regex("""\\d{3}-\\d{4}""").findAll(text)\nmatches.forEach { println(it.value) }',
        },
    },
    # ── Math ──
    {
        "category": "math",
        "name": "Euclidean Distance",
        "desc": "Compute distance between two points",
        "code": {
            "Python": 'import math\n\ndef distance(x1, y1, x2, y2):\n    return math.sqrt((x2-x1)**2 + (y2-y1)**2)',
            "TypeScript": 'function distance(x1: number, y1: number, x2: number, y2: number): number {\n    return Math.sqrt((x2-x1)**2 + (y2-y1)**2);\n}',
            "Rust": 'fn distance(x1: f64, y1: f64, x2: f64, y2: f64) -> f64 {\n    ((x2-x1).powi(2) + (y2-y1).powi(2)).sqrt()\n}',
            "Go": 'func distance(x1, y1, x2, y2 float64) float64 {\n    return math.Sqrt(math.Pow(x2-x1, 2) + math.Pow(y2-y1, 2))\n}',
            "Java": 'static double distance(double x1, double y1, double x2, double y2) {\n    return Math.sqrt(Math.pow(x2-x1, 2) + Math.pow(y2-y1, 2));\n}',
            "C++": 'double distance(double x1, double y1, double x2, double y2) {\n    return std::sqrt(std::pow(x2-x1, 2) + std::pow(y2-y1, 2));\n}',
            "C#": 'static double Distance(double x1, double y1, double x2, double y2) {\n    return Math.Sqrt(Math.Pow(x2-x1, 2) + Math.Pow(y2-y1, 2));\n}',
            "Ruby": 'def distance(x1, y1, x2, y2)\n  Math.sqrt((x2-x1)**2 + (y2-y1)**2)\nend',
            "Swift": 'func distance(_ x1: Double, _ y1: Double, _ x2: Double, _ y2: Double) -> Double {\n    return sqrt(pow(x2-x1, 2) + pow(y2-y1, 2))\n}',
            "Kotlin": 'fun distance(x1: Double, y1: Double, x2: Double, y2: Double): Double {\n    return sqrt((x2-x1).pow(2) + (y2-y1).pow(2))\n}',
        },
    },
]


# ─────────────────────────────────────────────
# SFT Record Generation
# ─────────────────────────────────────────────

SYSTEM = (
    "You are Polly, the SCBE-AETHERMOORE coding assistant. "
    "You help developers understand identical operations across programming languages."
)


def build_records() -> list[dict]:
    records = []

    for op in OPERATIONS:
        cat = op["category"]
        name = op["name"]
        desc = op["desc"]
        code = op["code"]

        # ── Record Type 1: Full Rosetta (all 10 languages) ──
        user_q = f"Show me how to {desc.lower()} in all major programming languages."
        answer = f"## {name}\n\n{desc}.\n\n"
        for lang in LANGS:
            if lang in code:
                answer += f"**{lang}:**\n```{lang.lower().replace('c++', 'cpp').replace('c#', 'csharp')}\n{code[lang]}\n```\n\n"

        records.append({
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user_q},
                {"role": "assistant", "content": answer},
            ],
            "tags": ["rosetta", cat, "all-languages"],
        })

        # ── Record Type 2: Per-language pair (user asks in one lang, gets another) ──
        lang_list = [l for l in LANGS if l in code]
        for i in range(len(lang_list)):
            for j in range(i + 1, len(lang_list)):
                src_lang = lang_list[i]
                tgt_lang = lang_list[j]
                user_q2 = (
                    f"I know how to {desc.lower()} in {src_lang}. "
                    f"How do I do the same thing in {tgt_lang}?"
                )
                answer2 = (
                    f"Here's the {name} operation translated from {src_lang} to {tgt_lang}:\n\n"
                    f"**{src_lang}:**\n```{src_lang.lower().replace('c++', 'cpp').replace('c#', 'csharp')}\n{code[src_lang]}\n```\n\n"
                    f"**{tgt_lang}:**\n```{tgt_lang.lower().replace('c++', 'cpp').replace('c#', 'csharp')}\n{code[tgt_lang]}\n```\n\n"
                    f"Key differences: {src_lang} and {tgt_lang} handle {cat} differently "
                    f"in syntax and idiom, but the operation is semantically identical."
                )
                records.append({
                    "messages": [
                        {"role": "system", "content": SYSTEM},
                        {"role": "user", "content": user_q2},
                        {"role": "assistant", "content": answer2},
                    ],
                    "tags": ["rosetta", cat, f"{src_lang}-to-{tgt_lang}"],
                })

        # ── Record Type 3: "What's different?" comparison ──
        user_q3 = f"What are the key differences in how languages handle {name.lower()}?"
        answer3 = f"## {name} across languages\n\n"
        # Group by paradigm
        answer3 += "**Key variations:**\n\n"
        for lang in lang_list:
            snippet_first_line = code[lang].split("\n")[0]
            answer3 += f"- **{lang}**: `{snippet_first_line}`\n"
        answer3 += (
            f"\nThe core operation ({desc.lower()}) is the same, "
            f"but syntax, type systems, and idioms differ. "
            f"Statically-typed languages (Rust, Go, Java) require explicit types. "
            f"Dynamic languages (Python, Ruby) infer everything. "
            f"The SCBE pipeline implements critical functions in both TypeScript and Python "
            f"with cross-language parity tests to ensure identical behavior."
        )
        records.append({
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user_q3},
                {"role": "assistant", "content": answer3},
            ],
            "tags": ["rosetta", cat, "comparison"],
        })

    return records


def main():
    records = build_records()

    out_file = OUT / "rosetta_code_primitives_sft.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Generated {len(records)} Rosetta Stone records")
    print(f"  Operations: {len(OPERATIONS)}")
    print(f"  Languages: {len(LANGS)}")
    print(f"  Categories: {len(set(op['category'] for op in OPERATIONS))}")
    print(f"Output: {out_file}")

    # Stats
    by_type = {"all-languages": 0, "pair": 0, "comparison": 0}
    for r in records:
        tags = r.get("tags", [])
        if "all-languages" in tags:
            by_type["all-languages"] += 1
        elif "comparison" in tags:
            by_type["comparison"] += 1
        else:
            by_type["pair"] += 1
    print(f"  Full Rosetta: {by_type['all-languages']}")
    print(f"  Language pairs: {by_type['pair']}")
    print(f"  Comparisons: {by_type['comparison']}")


if __name__ == "__main__":
    main()
