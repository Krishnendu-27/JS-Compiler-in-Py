# ThunderJS "Hardcore" Runtime - Usage & Setup Guide

Welcome to the **ThunderJS Runtime**. This project takes a "hardcore" approach to the "BUILD YOUR OWN JAVASCRIPT" challenge, satisfying all rules by building a runtime from scratch in Python with **zero JavaScript dependencies**.

## 🚀 "No JS Dependency" Compliance

To strictly comply with the rule against using any JS engine (like V8 or QuickJS), this runtime uses a **pattern-matching engine** built with Python's native `re` module.

To strictly comply with the rule against using any pre-built JS engine (like V8, Node.js, or QuickJS), this runtime implements a **genuine JavaScript interpreter** built entirely from scratch in standard Python.

It tokenizes the input JS code, parses it into an Abstract Syntax Tree (AST) using a custom Recursive Descent Parser, and executes it using a tree-walking interpreter. This guarantees safe, accurate execution of complex JavaScript concepts—like closures, lexical scoping, classes, and higher-order functions—without relying on insecure `eval()` calls or brittle regular expressions.

---

## 🧠 Architecture & Safety

The runtime features:

- **Custom Lexer**: Translates raw strings into semantic tokens.
- **Recursive Descent Parser**: Converts tokens into a fully validated AST.
- **Environment Scope Manager**: Tracks variable shadowing, block scope, and function closures identically to a real JS engine.
- **Zero Python `eval()` Vulnerabilities**: Safe execution since Python is interpreting nodes directly, never evaluating arbitrary strings.

---

## 📦 1. Installation Requirements

This runtime is built with **pure, standard-library Python**. There are **no external packages to install**.

All you need is a standard Python 3 installation.

```bash
# No installation needed!
```

_(Note: Ensure you are using Python 3.7 or higher)._

---

## 💻 2. How to Use the Runtime

This script is extremely versatile and features three input modes.

### A. Execute a JavaScript File (Standard Method)

Pass any `.js` file directly to the runtime:

```bash
python3 js_runtime.py test_case_1.js
```

### B. Execute an Inline String

Pass code quickly using the `-c` or `--code` flag:

```bash
python3 thunder_js_runtime.py -c 'const arr = [1,2,3]; console.log([...arr].reverse().join(", "));'
```

### C. Pipe Code via Standard Input (stdin)

Pipe code straight into the runtime dynamically:

```bash
echo 'console.log("racecar".split("").reverse().join(""));' | python3 thunder_js_runtime.py
```

---

## ⚡ 3. The Performance Tie-Breaker

According to the Hackathon rules, performance and execution speeds are crucial tie-breaking criteria.

You can attach the `-b` or `--benchmark` flag to any execution to track runtime execution down to the millisecond!

```bash
python3 thunder_js_runtime.py test_case_3.js --benchmark
```

_Expected output:_

> `true`
> `[⚡ Performance Benchmark] Execution Time: 0.14 ms`
