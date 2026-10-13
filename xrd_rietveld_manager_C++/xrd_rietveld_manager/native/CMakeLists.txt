# SPDX-License-Identifier: GPL-2.0-or-later
cmake_minimum_required(VERSION 3.18)
project(xrd_native LANGUAGES CXX)

add_library(xrd_native SHARED xrd_native.cpp)
target_compile_features(xrd_native PRIVATE cxx_std_17)

if(MSVC)
    target_compile_options(xrd_native PRIVATE /O2 /EHsc /W4)
    set_property(TARGET xrd_native PROPERTY
        MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
else()
    target_compile_options(xrd_native PRIVATE -O3 -Wall -Wextra -Wpedantic)
endif()

set_target_properties(xrd_native PROPERTIES
    PREFIX ""
    OUTPUT_NAME "xrd_native"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
    RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_CURRENT_SOURCE_DIR}"
    LIBRARY_OUTPUT_DIRECTORY_RELEASE "${CMAKE_CURRENT_SOURCE_DIR}"
)
