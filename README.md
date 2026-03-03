### 目录结构
~~~ shell
├── LICENSE
├── README.md
├── build.ps1
├── build.sh
├── c_mod   -------- 封装了IDF函数
│   ├── camera_lr.c
│   ├── micropython.cmake
│   └── wifi_lr.c
├── dome -------- 测试示例脚本
│   ├── V6_公网监控
│   │   └── main.py
├── open_code -------- 没有被IDF默认包含的扩展
├── py_mod -------- 编译进固件的py文件
│   ├── cam_lsl.py
│   ├── manifest.py
│   ├── wifi.py
│   └── ws.py
└── sdkconfig --------   添加的sdkconfig配置
    ├── mpconfigboard.cmake
    ├── sdkconfig.board
    ├── sdkconfig-mpy
    └── sdkconfig-参考

~~~

