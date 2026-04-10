# ---------------------------------------------------------------------------
# Behave (Python BDD) test runner
# ---------------------------------------------------------------------------

find_program(BEHAVE_EXECUTABLE behave)

if(NOT BEHAVE_EXECUTABLE)
    message(WARNING "behave not found — run_behave target will not be available. "
                    "Install it with: pip install behave")
else()
    message(STATUS "Found behave: ${BEHAVE_EXECUTABLE}")
endif()

# Path to the compiled calculator binary
set(CALCULATOR_BIN "$<TARGET_FILE:calculator>")

# Custom target: run_behave
# Depends on the calculator executable so it is always built first.
add_custom_target(run_behave
    DEPENDS calculator
    COMMAND ${CMAKE_COMMAND} -E env
            "CALCULATOR_BIN=${CALCULATOR_BIN}"
        ${BEHAVE_EXECUTABLE}
            --no-capture
            ${CMAKE_CURRENT_SOURCE_DIR}/features
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    COMMENT "Running Behave BDD tests..."
    VERBATIM
)

# Also register as a CTest test so `ctest` works
add_test(
    NAME BehaveBDD
    COMMAND ${CMAKE_COMMAND} --build ${CMAKE_BINARY_DIR} --target run_behave
)
