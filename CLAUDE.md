# CLAUDE.md — AI Assistant Guide for cpp-behave-coverage-demo

This file describes the project structure, build workflow, testing conventions,
and key patterns for AI assistants working in this codebase.

---

## Project Overview

**cpp-behave-coverage-demo** is a minimal C++17 command-line calculator used as
a reference project demonstrating:

- **CMake** (≥ 3.16) as the build system
- **Behave** (Python BDD) integration tests written in Gherkin
- **gcov / lcov** code-coverage instrumentation and reporting

The project is intentionally small — every component exists to show how these
three tools wire together, not to implement a feature-rich calculator.

---

## Repository Layout

```
.
├── CMakeLists.txt               # Root build: targets, coverage flags, subdirs
├── include/
│   └── calculator.h             # Public API — namespace calc
├── src/
│   ├── calculator.cpp           # Arithmetic implementation
│   └── main.cpp                 # CLI entry-point
├── tests/
│   ├── CMakeLists.txt           # run_behave custom target + CTest registration
│   ├── behave.ini               # Behave runtime configuration
│   └── features/
│       ├── calculator.feature   # Gherkin scenarios (5 scenarios)
│       └── steps/
│           └── calculator_steps.py  # Behave step definitions
├── README.md
└── CLAUDE.md                    # This file
```

---

## Build System

### Prerequisites

| Tool    | Minimum version | Install                |
|---------|----------------|------------------------|
| GCC     | 7+             | system package manager |
| CMake   | 3.16           | system package manager |
| Python  | 3.8            | system package manager |
| behave  | 1.2.6          | `pip install behave`   |
| lcov    | 1.14           | optional, for HTML report |

### Build Commands

```bash
# Configure — Debug mode automatically enables gcov coverage instrumentation
cmake -B build -DCMAKE_BUILD_TYPE=Debug

# Compile
cmake --build build
```

Build outputs:
- `build/calculator`         — CLI binary (takes three args: number op number)
- `build/libcalculator.so`   — Shared library (usable via Python ctypes)

### Coverage Flag Logic

Coverage instrumentation (`-fprofile-arcs -ftest-coverage`) is enabled when
either `CMAKE_BUILD_TYPE=Debug` OR the `ENABLE_COVERAGE` CMake option is `ON`.
The root `CMakeLists.txt` sets both `CMAKE_CXX_FLAGS` and
`CMAKE_EXE_LINKER_FLAGS`/`CMAKE_SHARED_LINKER_FLAGS` with `--coverage`.

To force coverage on a Release build:
```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release -DENABLE_COVERAGE=ON
```

---

## Running Tests

### Preferred: CMake target (rebuilds binary automatically)

```bash
cmake --build build --target run_behave
# or from inside the build directory:
make run_behave
```

This target (defined in `tests/CMakeLists.txt`):
1. Depends on the `calculator` executable — rebuilds it if stale.
2. Sets the `CALCULATOR_BIN` env var to the exact binary path.
3. Runs `behave --no-capture tests/features` from `tests/`.

### Via CTest

```bash
cd build
ctest --output-on-failure
```

### Direct Behave invocation (binary must be pre-built)

```bash
export CALCULATOR_BIN=$(pwd)/build/calculator
cd tests
behave
```

---

## Code Coverage Workflow

After running the Behave tests, `.gcda` files appear alongside compiled objects.

### Quick per-file report

```bash
cd build
gcov -r ../src/calculator.cpp
```

### Full HTML report with lcov + genhtml

```bash
# Collect
lcov --capture --directory build --output-file build/coverage.info

# Filter out system headers
lcov --remove build/coverage.info '/usr/*' --output-file build/coverage_filtered.info

# Render HTML
genhtml build/coverage_filtered.info --output-directory build/coverage_html

# Open
xdg-open build/coverage_html/index.html   # Linux
# open build/coverage_html/index.html     # macOS
```

### One-liner end-to-end

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

## C++ Code Conventions

- **Standard**: C++17 (`-std=c++17`), no compiler extensions (`EXTENSIONS OFF`).
  Falls back to C++14 with a CMake warning if the compiler lacks C++17 support.
- **Header guards**: `#pragma once` (not `#ifndef` guards).
- **Namespace**: All library symbols live in `namespace calc`.
- **Error handling**: Throw `std::invalid_argument` for invalid inputs
  (unknown operator, division by zero). Catch `std::exception` broadly in `main`.
- **Output formatting**: Print as integer when the result has no fractional part
  (`static_cast<long long>(result) == result`), otherwise print the double.
- **Error output**: Errors go to `stderr`; results go to `stdout`.
- **Exit codes**: `EXIT_SUCCESS` (0) on success, `EXIT_FAILURE` (1) on error.

### Source files

| File                    | Responsibility                                  |
|-------------------------|-------------------------------------------------|
| `include/calculator.h`  | Public API declarations only — no implementation |
| `src/calculator.cpp`    | Arithmetic functions + `evaluate()` dispatcher  |
| `src/main.cpp`          | Argument parsing, calls `calc::evaluate()`, output formatting |

---

## Python / Behave Test Conventions

### Step definitions (`tests/features/steps/calculator_steps.py`)

- `@given` — locate and validate the binary path; store in `context.calculator_bin`.
- `@when`  — invoke the binary with `subprocess.run(capture_output=True, text=True)`;
  store `context.stdout`, `context.stderr`, `context.exit_code`.
- `@then`  — assert against stored context values; include both expected and actual
  values in assertion messages.

### Binary resolution order (implemented in `_find_binary()`)

1. `CALCULATOR_BIN` environment variable (set by CMake target).
2. Relative paths to common out-of-source build directories:
   `build/`, `build/Debug/`, `build/Release/`.
3. `shutil.which("calculator")` — PATH lookup as last resort.

### Behave configuration (`tests/behave.ini`)

- `paths = features` — features directory relative to `tests/`.
- Capture is disabled (`stdout_capture`, `stderr_capture`, `log_capture = false`)
  so subprocess output is visible during test runs.
- `stop = false` — all scenarios run even if one fails.
- `show_timings = true` — execution time per step is displayed.

### Gherkin feature file (`tests/features/calculator.feature`)

Scenarios follow the pattern:
```gherkin
Given the calculator binary is available
When I run the calculator with arguments "<a>" "<op>" "<b>"
Then the output should be "<expected>"
```

Error scenarios additionally assert:
```gherkin
Then the exit code should be non-zero
And the error output should contain "<substring>"
```

---

## Adding New Functionality

### Adding a new arithmetic operation

1. Declare the function in `include/calculator.h` inside `namespace calc`.
2. Implement it in `src/calculator.cpp`.
3. Add the operator string branch inside `calc::evaluate()` in `calculator.cpp`.
4. Add a Gherkin scenario in `tests/features/calculator.feature`.
5. No new step definitions needed — the existing `When/Then` steps are generic.

### Adding a new test scenario

- Add a `Scenario:` block to `calculator.feature` using the existing step phrases.
- New step phrases require a matching `@given/@when/@then` decorated function in
  `calculator_steps.py`.

---

## Key Files for AI Assistants

When asked to modify, extend, or debug this project, these are the primary files:

| Task                          | Files to read/edit                                        |
|-------------------------------|-----------------------------------------------------------|
| Add/change arithmetic logic   | `include/calculator.h`, `src/calculator.cpp`              |
| Change CLI behaviour          | `src/main.cpp`                                            |
| Add/change BDD tests          | `tests/features/calculator.feature`                       |
| Add/change step definitions   | `tests/features/steps/calculator_steps.py`                |
| Change build configuration    | `CMakeLists.txt`, `tests/CMakeLists.txt`                  |
| Change Behave runtime options | `tests/behave.ini`                                        |

---

## What NOT to Do

- Do not add `.gcda`, `.gcno`, `.gcov`, `coverage.info`, or `coverage_html/`
  to the repository — they are gitignored build artifacts.
- Do not commit the `build/` directory.
- Do not change `CMAKE_CXX_STANDARD` below 17 without also updating fallback logic.
- Do not use `using namespace calc;` inside header files.
- Do not catch exceptions silently — always surface errors to stderr and exit 1.
