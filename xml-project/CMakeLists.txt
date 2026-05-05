cmake_minimum_required(VERSION 3.16)
project(XmlValidator VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(LibXml2 REQUIRED)

add_executable(validate src/validate.cpp)
target_link_libraries(validate PRIVATE LibXml2::LibXml2)

# Copie les données et les schémas dans le répertoire de build
# afin que l'exécutable puisse les trouver avec les chemins relatifs par défaut.
file(COPY ${CMAKE_CURRENT_SOURCE_DIR}/data    DESTINATION ${CMAKE_CURRENT_BINARY_DIR})
file(COPY ${CMAKE_CURRENT_SOURCE_DIR}/schemas DESTINATION ${CMAKE_CURRENT_BINARY_DIR})
