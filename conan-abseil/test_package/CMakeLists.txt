cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(absl REQUIRED CONFIG)

add_executable(test_package test_package.cpp)
# Memes cibles que le abslConfig.cmake officiel
target_link_libraries(test_package PRIVATE
    absl::strings
    absl::str_format
    absl::flat_hash_map
    absl::log
    absl::time
)
