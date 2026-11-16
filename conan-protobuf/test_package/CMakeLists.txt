cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(protobuf REQUIRED CONFIG)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE protobuf::libprotobuf)

# Genere person.pb.h / person.pb.cc avec protoc, puis les ajoute a la cible
protobuf_generate(
    TARGET test_package
    LANGUAGE cpp
    PROTOS ${CMAKE_CURRENT_SOURCE_DIR}/person.proto
    IMPORT_DIRS ${CMAKE_CURRENT_SOURCE_DIR}
    PROTOC_OUT_DIR ${CMAKE_CURRENT_BINARY_DIR}
)
target_include_directories(test_package PRIVATE ${CMAKE_CURRENT_BINARY_DIR})
