#!/usr/bin/env bash
# ~/build-mpy.sh

set -e  # 出错即退出

# mpy项目目录
mpy_prj="$HOME/mpy/micropython"
# 远程Cmod目录
c_mod="USER_C_MODULES=$HOME/test_build/camera_lr/c_mod/micropython.cmake"
# 远程py_mod目录
py_mod="FROZEN_MANIFEST=$HOME/test_build/camera_lr/py_mod/manifest.py"
# 本地Cmod目录
c_mod_lod="/mnt/c/Users/82542/code/py/Micropython/mod/camera_lr/"





echo "激活 ESP-IDF 环境..."
cd ~/mpy/esp-idf
. ./export.sh

echo "生成S3板级配置"
cd  ${mpy_prj}/ports/esp32/boards/
mkdir -p ESP32_GENERIC_S3_LTLSL
cp ESP32_GENERIC_S3/* ESP32_GENERIC_S3_LTLSL/

echo "拷贝自定义板级配置"
cp $HOME/test_build/camera_lr/sdkconfig/* ESP32_GENERIC_S3_LTLSL/


echo "添加第三方组件"
cd ${mpy_prj}/ports/esp32
mkdir -p components
rsync -av --exclude='.git' -r $HOME/test_build/camera_lr/open_code/ components/


echo "编译固件"
make clean 
rm -rf build-*
make -j40 BOARD=ESP32_GENERIC_S3_LTLSL BOARD_VARIANT=SPIRAM_OCT ${c_mod} ${py_mod} 
# make -j40 BOARD=ESP32_GENERIC_S3_LTLSL BOARD_VARIANT=SPIRAM_OCT


echo "拷贝智能提示到本地"
cp -r build-ESP32_GENERIC_S3_LTLSL-SPIRAM_OCT/genhdr /mnt/c/Users/82542/test_include/include

echo "拷贝固件到本地"
cp build-ESP32_GENERIC_S3_LTLSL-SPIRAM_OCT/firmware.bin  ${c_mod_lod}
