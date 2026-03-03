# 修改 boards/lr/mpconfigboard.cmake####
set(IDF_TARGET esp32s3)

set(SDKCONFIG_DEFAULTS
    boards/sdkconfig.base          # 提供 MicroPython 必需配置
    boards/sdkconfig.ble           # 提供 BLE 配置
    boards/sdkconfig.spiram_sx     # 提供 PSRAM 配置
    boards/ESP32_GENERIC_S3_LTLSL/sdkconfig.board      # 您的配置最后加载，覆盖冲突项
)
