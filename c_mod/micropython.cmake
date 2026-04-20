# 扩展名
add_library(usermod_lr INTERFACE)

# 扩展源文件
target_sources(usermod_lr INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/camera_lr.c
    ${CMAKE_CURRENT_LIST_DIR}/wifi_lr.c
    ${CMAKE_CURRENT_LIST_DIR}/rmt_lr.c
    ${CMAKE_CURRENT_LIST_DIR}/free_lr.c
    ${CMAKE_CURRENT_LIST_DIR}/adc_lr.c
)

# 扩展依赖
target_include_directories(usermod_lr INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}   # 当前路径
    ${CMAKE_CURRENT_LIST_DIR}/../open_code/esp32-camera/driver/include  # camera 依赖
    ${CMAKE_CURRENT_LIST_DIR}/../open_code/esp32-camera/conversions/include # camera 依赖
    ${MICROPY_PORT_DIR}/managed_components/espressif__esp_jpeg/include # camera 依赖
    
)

# 注册扩展
target_link_libraries(usermod INTERFACE
    usermod_lr
)
