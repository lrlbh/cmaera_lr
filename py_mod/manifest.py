# 继承 ESP32 官方默认 frozen 配置
include("$(PORT_DIR)/boards/manifest.py")

# 1. 冻结单个顶层模块
module("wifi_lsl.py")
module("ws_lsl.py")
module("ul.py")

# 2. 冻结包 (Package)
# package 会自动递归处理目录下所有 .py 文件，并保留文件夹作为包名
# base_path="." 确保它从当前目录开始计算路径
package("cam_lsl", base_path=".")
package("lcd_lsl", base_path=".")


# # 继承 ESP32 官方默认 frozen 配置
# include("$(PORT_DIR)/boards/manifest.py")

# freeze(
#     ".",
#     (
#         "wifi.py",
#         "ws.py",
#         "udp.py",
#         "cma_lsl/__init__.py",
#         "cma_lsl/cam.py",
#     ),
# )
# freeze("lcd")
# freeze("cam_lsl")
