cmake_minimum_required(VERSION 3.16)
project(mathutils LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(mathutils src/mathutils.cpp)
target_include_directories(mathutils PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

install(TARGETS mathutils)
install(DIRECTORY include/ DESTINATION include)
