# cpp-behave-coverage-demo

A minimal C++17 command-line calculator demonstrating:

- **CMake** build system (≥ 3.16)
- **Behave** (Python BDD) integration tests with Gherkin scenarios
- **gcov / lcov** code-coverage reporting

---

## Project layout

```
.
├── CMakeLists.txt
├── src/
│   ├── main.cpp          ← CLI entry-point
│   └── calculator.cpp    ← arithmetic implementation
├── include/
│   └── calculator.h
├── tests/
│   ├── CMakeLists.txt    ← defines the run_behave target
│   ├── behave.ini
│   └── features/
│       ├── calculator.feature       ← Gherkin scenarios
│       └── steps/
│           └── calculator_steps.py  ← Behave step definitions
└── README.md
```

---

## Prerequisites

| Tool | Minimum version |
|------|----------------|
| GCC  | 7+ (C++17 support) |
| CMake | 3.16 |
| Python | 3.8 |
| behave | 1.2.6 — `pip install behave` |
| lcov  | 1.14 (optional, for HTML report) |

---

## Build

```bash
# 1. Configure — Debug mode enables coverage instrumentation automatically
cmake -B build -DCMAKE_BUILD_TYPE=Debug

# 2. Compile the library and binary
cmake --build build          # or:  cd build && make
```

The build produces:
- `build/calculator`          — CLI binary
- `build/libcalculator.so`    — shared library (usable via ctypes)

---

## Run the calculator

```bash
./build/calculator 10 + 5    # → 15
./build/calculator 6  '*' 7  # → 42  (quote * in the shell)
./build/calculator 10 / 4    # → 2.5
./build/calculator 9  / 0    # → Error: Division by zero  (exit 1)
```

---

## Run Behave BDD tests

### Via CMake target (recommended)

```bash
cmake --build build --target run_behave
# or, from the build directory:
make run_behave
```

This target:
1. Rebuilds the binary if needed.
2. Sets `CALCULATOR_BIN` to the exact binary path.
3. Runs `behave` against `tests/features/`.

### Via CTest

```bash
cd build
ctest --output-on-failure
```

### Directly (binary must be built first)

```bash
export CALCULATOR_BIN=$(pwd)/build/calculator
cd tests
behave
```

---

## Code coverage

After running the tests, `.gcda` files are written next to the compiled objects.

### Quick report with gcov

```bash
cd build
gcov -r ../src/calculator.cpp
```

### Full HTML report with lcov + genhtml

```bash
# 1. Collect coverage data
lcov --capture \
     --directory build \
     --output-file build/coverage.info

# 2. Remove system / third-party headers from the report
lcov --remove build/coverage.info \
     '/usr/*' \
     --output-file build/coverage_filtered.info

# 3. Generate HTML
genhtml build/coverage_filtered.info \
        --output-directory build/coverage_html

# 4. Open the report
xdg-open build/coverage_html/index.html   # Linux
# open build/coverage_html/index.html     # macOS
```

The `index.html` shows line-by-line coverage for every source file.

---

## One-liner workflow

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Debug && \
cmake --build build && \
cmake --build build --target run_behave && \
lcov --capture --directory build --output-file build/coverage.info && \
lcov --remove build/coverage.info '/usr/*' --output-file build/coverage_filtered.info && \
genhtml build/coverage_filtered.info --output-directory build/coverage_html && \
echo "Report ready at build/coverage_html/index.html"
```

---

## License

MIT
