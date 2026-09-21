cmake_minimum_required(VERSION 3.16)
project(mathutils_consumer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(mathutils REQUIRED CONFIG)

add_executable(mathutils_consumer main.cpp)
target_link_libraries(mathutils_consumer PRIVATE mathutils::mathutils)
