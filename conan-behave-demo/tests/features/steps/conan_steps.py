"""
Step definitions for conan_package.feature.

These steps drive the real `conan` CLI: the "conan create" step actually
builds the "mathutils" recipe and installs it into the local Conan cache
(~/.conan2/p by default). The later steps then consume that same cached
package purely through a generated Conan "VirtualRunEnv" script
(conanrun.sh) - no rebuilding or relinking involved.
"""

import json
import os
import subprocess
import tempfile

from behave import given, when, then

DEMO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
PACKAGE_DIR = os.path.join(DEMO_ROOT, "package")

PACKAGE_REFERENCE = "mathutils/1.0.0"


def _run(command, cwd=None):
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def _package_binary_folder(reference):
    """Resolve the cache folder holding the built binaries for `reference`."""
    result = _run(["conan", "list", f"{reference}:*", "--format=json"])
    assert result.returncode == 0, f"conan list failed: {result.stderr}"

    data = json.loads(result.stdout)
    recipe = data["Local Cache"][reference]
    revision = next(iter(recipe["revisions"].values()))
    package_id = next(iter(revision["packages"].keys()))

    cache_path = _run(["conan", "cache", "path", f"{reference}:{package_id}"])
    assert cache_path.returncode == 0, f"conan cache path failed: {cache_path.stderr}"
    return cache_path.stdout.strip()


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


@when('I try to run "mathutils-cli" straight from the Conan cache without any environment script')
def step_run_cli_without_env(context):
    binary_folder = _package_binary_folder(PACKAGE_REFERENCE)
    binary = os.path.join(binary_folder, "bin", "mathutils-cli")
    assert os.path.isfile(binary), f"binary not found: {binary}"
    context.last_result = _run([binary, "2", "3"])


@when('I generate the Conan virtual run environment for "{reference}"')
def step_generate_virtual_run_env(context, reference):
    context.runenv_dir = tempfile.mkdtemp(prefix="mathutils-runenv-")
    result = _run(
        [
            "conan", "install",
            f"--requires={reference}",
            "--no-remote",
            "-g", "VirtualRunEnv",
            "--output-folder", context.runenv_dir,
        ],
    )
    assert result.returncode == 0, (
        f"conan install (VirtualRunEnv) failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    context.generate_runenv_result = result


@when('I run "mathutils-cli {a} {b}" using the generated virtual run environment')
def step_run_cli_with_env(context, a, b):
    script = os.path.join(context.runenv_dir, "conanrun.sh")
    assert os.path.isfile(script), f"conanrun.sh not found in {context.runenv_dir}"

    # Source the generated script in the same shell invocation so its
    # exported PATH / LD_LIBRARY_PATH apply to the "mathutils-cli" call.
    command = f'source "{script}" && mathutils-cli {a} {b}'
    context.last_result = subprocess.run(
        ["bash", "-c", command],
        capture_output=True,
        text=True,
    )


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


@then('it should fail because "{missing_lib}" cannot be found')
def step_check_run_failed_missing_lib(context, missing_lib):
    result = context.last_result
    assert result.returncode != 0, "expected the CLI to fail without the run environment"
    assert missing_lib in result.stderr, (
        f"Expected stderr to mention {missing_lib!r} but got: {result.stderr!r}"
    )


@then('a "{filename}" script should have been generated')
def step_check_script_generated(context, filename):
    path = os.path.join(context.runenv_dir, filename)
    assert os.path.isfile(path), f"{filename} was not generated in {context.runenv_dir}"


@then("the command should succeed")
def step_check_last_command_succeeded(context):
    result = context.last_result
    assert result.returncode == 0, (
        f"command failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


@then('the output should contain "{expected}"')
def step_check_output_contains(context, expected):
    stdout = context.last_result.stdout
    assert expected in stdout, (
        f"Expected output to contain {expected!r} but got:\n{stdout!r}"
    )
