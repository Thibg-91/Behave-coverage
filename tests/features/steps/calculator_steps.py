"""
Step definitions for calculator.feature.

The compiled calculator binary is located via the CALCULATOR_BIN environment
variable (set by the CMake run_behave target) or falls back to a path relative
to a typical out-of-source build directory.
"""

import os
import subprocess
import shutil

from behave import given, when, then


def _find_binary():
    """Return the path to the calculator executable."""
    # 1. CMake sets this when invoking `make run_behave`
    env_bin = os.environ.get("CALCULATOR_BIN")
    if env_bin and os.path.isfile(env_bin):
        return env_bin

    # 2. Common out-of-source build locations (for running behave directly)
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "build", "calculator"),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "build", "Debug", "calculator"),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "build", "Release", "calculator"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return os.path.abspath(path)

    # 3. Fall back to PATH
    found = shutil.which("calculator")
    if found:
        return found

    raise FileNotFoundError(
        "calculator binary not found. "
        "Build the project first (cmake + make) and set CALCULATOR_BIN or "
        "ensure the binary is in PATH."
    )


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------

@given("the calculator binary is available")
def step_binary_available(context):
    context.calculator_bin = _find_binary()


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------

@when('I run the calculator with arguments "{a}" "{op}" "{b}"')
def step_run_calculator(context, a, op, b):
    result = subprocess.run(
        [context.calculator_bin, a, op, b],
        capture_output=True,
        text=True,
    )
    context.stdout = result.stdout.strip()
    context.stderr = result.stderr.strip()
    context.exit_code = result.returncode


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------

@then('the output should be "{expected}"')
def step_check_output(context, expected):
    assert context.stdout == expected, (
        f"Expected stdout {expected!r} but got {context.stdout!r}\n"
        f"stderr: {context.stderr}"
    )


@then("the exit code should be non-zero")
def step_check_nonzero_exit(context):
    assert context.exit_code != 0, (
        f"Expected non-zero exit code but got {context.exit_code}\n"
        f"stdout: {context.stdout}\nstderr: {context.stderr}"
    )


@then('the error output should contain "{substring}"')
def step_check_stderr(context, substring):
    assert substring in context.stderr, (
        f"Expected stderr to contain {substring!r} but got {context.stderr!r}"
    )
