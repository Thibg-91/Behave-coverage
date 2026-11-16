cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

find_package(eclipse-paho-mqtt-c REQUIRED CONFIG)

add_executable(test_package test_package.c)
# Cible globale : pointe vers la variante choisie (3a, 3c, 3as ou 3cs)
target_link_libraries(test_package PRIVATE eclipse-paho-mqtt-c::eclipse-paho-mqtt-c)
