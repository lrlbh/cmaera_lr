# 继承 ESP32 官方默认 frozen 配置
include("$(PORT_DIR)/boards/manifest.py")

freeze(
    ".",
    (
        "cam_lsl.py",
        "wifi.py",
        "ws.py",
    ),
)

