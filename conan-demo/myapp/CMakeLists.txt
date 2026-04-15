cmake_minimum_required(VERSION 3.15)
project(myapp CXX)

# Find the mymath package exported by Conan (via CMakeDeps generator)
find_package(mymath REQUIRED)

add_executable(myapp src/main.cpp)
target_link_libraries(myapp PRIVATE mymath::mymath)
