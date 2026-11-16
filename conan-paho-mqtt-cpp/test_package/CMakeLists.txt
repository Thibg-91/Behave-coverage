cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(PahoMqttCpp REQUIRED CONFIG)

add_executable(test_package test_package.cpp)
target_compile_features(test_package PRIVATE cxx_std_17)
# Meme cible que le PahoMqttCppConfig.cmake officiel
target_link_libraries(test_package PRIVATE PahoMqttCpp::paho-mqttpp3)
