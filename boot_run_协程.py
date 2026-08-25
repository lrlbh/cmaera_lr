# 扫描后，优先连接信号最好的wifi
wifi信息组 = {
    "12345678": "12345678",
    "CMCC-Ef6Z": "ddtzpts9",
    "CMCC-vKWf": "7vzpycp6",
    "CMCC-luoyuan": "A13466179775",
}

# 直接连接指定wifi，不扫描可以加快连接速度
# 不指定传None
ssid = "CMCC-Ef6Z"
pwd = "ddtzpts9"

# 强烈建议配置静态IP，开发时加快重启后wifi连接速度
静态ip = True
ip = "192.168.1.188"
dns_server = "192.168.1.1"
网关 = "192.168.1.1"
子网掩码 = "255.255.255.0"

# 默认文件读写速度只有1MiB左右
# 为了避免启动时，字库、图片之类资源，计算本地hash浪费太多时间
# 同时避免大文件重复同步浪费时间
忽略的文件和目录 = [
    "lib_lsl",
    # "boot.py",
    # "boot_run.py",
    "no_sync",
    "__pycache__",
    ".vscode",
    "Readme.md",
    "readme.md",
    "README.md",
    "LICENSE",
    ".gitignore",
]

# 广播端口,用于自动发现服务器地址，然后获取其他必备数据
广播端口 = 50000

# 更新任务发送,用于服务器判断单片机是否在线
更新任务心跳间隔ms = 500

# boot_pin 本功能
#   1.判断是否运行boot.py
#       强上拉运行boot.py
#       浮空不运行boot.py
#       下拉进入下载模式,与此脚本无关
#       可用其他引脚,不过和boot引脚无冲突
#   2.简单驱动rgb灯珠,用于判断boot.py运行状态
boot_pin = 0


# rgb 提示色彩
class rgb_msg:
    连接wifi中 = (0, 0, 1)  # 蓝
    获取服务器地址中 = (0, 1, 0)  # 绿  此步之后开始运行main.py
    获取md5中 = (1, 1, 1)  # 全色
    连接更新服务器中 = (1, 0, 0)  # 红