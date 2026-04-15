#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# build_library.sh
# Compile the mymath library manually (outside of Conan).
# Run this script BEFORE running "conan export-pkg".
# ---------------------------------------------------------------------------
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[mymath] Compiling source..."
g++ -std=c++17 -O2 \
    -I"${SCRIPT_DIR}/include" \
    -c "${SCRIPT_DIR}/src/mymath.cpp" \
    -o "${SCRIPT_DIR}/mymath.o"

echo "[mymath] Archiving static library..."
ar rcs "${SCRIPT_DIR}/lib/libmymath.a" "${SCRIPT_DIR}/mymath.o"

rm -f "${SCRIPT_DIR}/mymath.o"

echo "[mymath] Done. Library is at: ${SCRIPT_DIR}/lib/libmymath.a"
