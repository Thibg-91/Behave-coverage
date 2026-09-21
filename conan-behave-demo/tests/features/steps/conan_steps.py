"""
Step definitions for conan_package.feature.

These steps drive the real `conan` CLI: the "When I run conan create ..."
step is what actually builds the "mathutils" recipe and installs it into
the local Conan cache (~/.conan2/p by default). Nothing here is mocked.
"""

import os
import shutil
import subprocess

from behave import given, when, then

DEMO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
PACKAGE_DIR = os.path.join(DEMO_ROOT, "package")
CONSUMER_DIR = os.path.join(DEMO_ROOT, "consumer")

PACKAGE_REFERENCE = "mathutils/1.0.0"


def _run(command, cwd=None):
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------

@given('the local Conan cache does not contain "{reference}"')
def step_clean_cache(context, reference):
    # "-c" skips the interactive confirmation prompt. It is not an error if
    # the reference was never in the cache to begin with.
    _run(["conan", "remove", "-c", reference])


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------

@when('I run "conan create" on the "{reference}" package recipe')
def step_conan_create(context, reference):
    assert reference == PACKAGE_REFERENCE, (
        f"This demo only packages {PACKAGE_REFERENCE}, got {reference!r}"
    )
    context.conan_create_result = _run(
        ["conan", "create", PACKAGE_DIR, "--build=missing", "--no-remote"],
    )


@when("I install the consumer project dependencies from the local Conan cache")
def step_conan_install_consumer(context):
    result = _run(
        ["conan", "install", ".", "--build=missing", "--no-remote"],
        cwd=CONSUMER_DIR,
    )
    assert result.returncode == 0, (
        f"conan install failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    context.conan_install_result = result


@when("I configure and build the consumer project with CMake")
def step_cmake_configure_and_build(context):
    configure = _run(
        ["cmake", "--preset", "conan-release"],
        cwd=CONSUMER_DIR,
    )
    assert configure.returncode == 0, (
        f"cmake configure failed:\nstdout: {configure.stdout}\nstderr: {configure.stderr}"
    )

    build = _run(
        ["cmake", "--build", "--preset", "conan-release"],
        cwd=CONSUMER_DIR,
    )
    assert build.returncode == 0, (
        f"cmake build failed:\nstdout: {build.stdout}\nstderr: {build.stderr}"
    )
    context.cmake_build_result = build


@when("I run the consumer executable")
def step_run_consumer_executable(context):
    candidates = [
        os.path.join(CONSUMER_DIR, "build", "Release", "mathutils_consumer"),
        os.path.join(CONSUMER_DIR, "build", "mathutils_consumer"),
    ]
    binary = next((path for path in candidates if os.path.isfile(path)), None)
    assert binary, f"consumer executable not found, looked in: {candidates}"

    result = _run([binary])
    assert result.returncode == 0, f"consumer executable failed: {result.stderr}"
    context.consumer_stdout = result.stdout


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------

@then('the "conan create" command should succeed')
def step_check_conan_create_succeeded(context):
    result = context.conan_create_result
    assert result.returncode == 0, (
        f"conan create failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


@then('the local Conan cache should contain "{reference}"')
def step_check_cache_contains(context, reference):
    result = _run(["conan", "list", f"{reference}:*"])
    assert result.returncode == 0, f"conan list failed: {result.stderr}"
    assert reference in result.stdout, (
        f"{reference} not found in local Conan cache.\n"
        f"conan list output:\n{result.stdout}"
    )


@then('the consumer output should contain "{expected}"')
def step_check_consumer_output(context, expected):
    assert expected in context.consumer_stdout, (
        f"Expected consumer output to contain {expected!r} but got:\n"
        f"{context.consumer_stdout!r}"
    )
