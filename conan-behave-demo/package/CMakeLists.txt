cmake_minimum_required(VERSION 3.16)
project(mathutils LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Built as a shared library on purpose: at runtime the "mathutils-cli" tool
# below must locate libmathutils via the dynamic linker (no rpath is set),
# which is exactly the problem the generated Conan VirtualRunEnv script
# (conanrun.sh) solves by exporting LD_LIBRARY_PATH.
add_library(mathutils SHARED src/mathutils.cpp)
target_include_directories(mathutils PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

add_executable(mathutils-cli src/mathutils_cli.cpp)
target_link_libraries(mathutils-cli PRIVATE mathutils)

install(TARGETS mathutils mathutils-cli)
install(DIRECTORY include/ DESTINATION include)
