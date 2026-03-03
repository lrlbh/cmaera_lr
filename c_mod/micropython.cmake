# micropython.cmake

add_library(usermod_esp32camera INTERFACE)

target_sources(usermod_esp32camera INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/camera_lr.c
    ${CMAKE_CURRENT_LIST_DIR}/wifi_lr.c
)

target_include_directories(usermod_esp32camera INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}

    # 👇 手动加 include 路径（关键）
    ${CMAKE_CURRENT_LIST_DIR}/../open_code/esp32-camera/driver/include
    ${CMAKE_CURRENT_LIST_DIR}/../open_code/esp32-camera/conversions/include
    $ENV{HOME}/mpy/micropython/ports/esp32/managed_components/espressif__esp_jpeg/include
    
)

target_link_libraries(usermod INTERFACE
    usermod_esp32camera
)
