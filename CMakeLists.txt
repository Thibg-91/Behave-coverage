cmake_minimum_required(VERSION 3.16)

project(Calculator VERSION 1.0.0 LANGUAGES CXX)

# ---------------------------------------------------------------------------
# C++ standard
# ---------------------------------------------------------------------------
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Fallback: if the compiler does not support C++17, try C++14
include(CheckCXXCompilerFlag)
check_cxx_compiler_flag("-std=c++17" COMPILER_SUPPORTS_CXX17)
if(NOT COMPILER_SUPPORTS_CXX17)
    message(WARNING "C++17 not supported, falling back to C++14")
    set(CMAKE_CXX_STANDARD 14)
endif()

# ---------------------------------------------------------------------------
# Coverage flags (Debug build only)
# ---------------------------------------------------------------------------
option(ENABLE_COVERAGE "Enable gcov code coverage instrumentation" OFF)

if(CMAKE_BUILD_TYPE STREQUAL "Debug" OR ENABLE_COVERAGE)
    set(ENABLE_COVERAGE ON)
    message(STATUS "Coverage instrumentation enabled")
    set(COVERAGE_FLAGS "-fprofile-arcs -ftest-coverage")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${COVERAGE_FLAGS}")
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} --coverage")
    set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} --coverage")
endif()

# ---------------------------------------------------------------------------
# Include directories
# ---------------------------------------------------------------------------
include_directories(${CMAKE_SOURCE_DIR}/include)

# ---------------------------------------------------------------------------
# Shared library  (calculator_lib) — can be linked by Python via ctypes
# ---------------------------------------------------------------------------
add_library(calculator_lib SHARED
    src/calculator.cpp
)

target_include_directories(calculator_lib PUBLIC
    ${CMAKE_SOURCE_DIR}/include
)

set_target_properties(calculator_lib PROPERTIES
    OUTPUT_NAME "calculator"
    POSITION_INDEPENDENT_CODE ON
)

# ---------------------------------------------------------------------------
# Main executable
# ---------------------------------------------------------------------------
add_executable(calculator
    src/main.cpp
)

target_link_libraries(calculator PRIVATE calculator_lib)

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------
enable_testing()
add_subdirectory(tests)
