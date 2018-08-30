cmake_minimum_required(VERSION 3.8)
project(hiredis VERSION 0.13.2)

string(SUBSTRING ${CMAKE_SHARED_LIBRARY_SUFFIX} 1 -1 SHARED_LIBRARY_SUFFIX)
string(SUBSTRING ${CMAKE_STATIC_LIBRARY_SUFFIX} 1 -1 STATIC_LIBRARY_SUFFIX)

add_custom_command(OUTPUT "${CMAKE_CURRENT_SOURCE_DIR}/libhiredis${CMAKE_SHARED_LIBRARY_SUFFIX}" "${CMAKE_CURRENT_SOURCE_DIR}/libhiredis${CMAKE_STATIC_LIBRARY_SUFFIX}"
        COMMAND $(MAKE) DYLIBSUFFIX=${SHARED_LIBRARY_SUFFIX} STLIBSUFFIX=${STATIC_LIBRARY_SUFFIX}
        WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}")

add_custom_target(hiredis ALL DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/libhiredis${CMAKE_SHARED_LIBRARY_SUFFIX}" "${CMAKE_CURRENT_SOURCE_DIR}/libhiredis${CMAKE_STATIC_LIBRARY_SUFFIX}")

install(FILES libhiredis${CMAKE_STATIC_LIBRARY_SUFFIX} DESTINATION lib)
install(DIRECTORY . DESTINATION include/hiredis FILES_MATCHING PATTERN "*.h")