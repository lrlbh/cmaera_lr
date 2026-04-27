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



### 待处理

#### rmt

new失败时,释放资源

提高渐变精度，具体方法见代码注释

​	问题主要源头是，传入IDF tick 小于2的数据，驱动会乱处理，所以填充数据里面做了偏移，没修正

​	另外除法可引入细微不对齐
