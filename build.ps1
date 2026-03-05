# Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

$ErrorActionPreference = "Stop"
function Check-ExitCode {
    if ($LASTEXITCODE -ne 0) {
        Write-Host "命令执行失败，退出码：$LASTEXITCODE" -ForegroundColor Red
        exit 1
    }
}

Write-Host "拷贝项目到linux"
# wsl cp -r ../camera_lr ~/test_build
wsl rsync -av --delete --exclude='.git' --exclude='build' ./ /home/luorong/test_build/camera_lr/
Check-ExitCode 


Write-Host "执行远程脚本"
wsl ./build.sh
Check-ExitCode

Write-Host "擦除"
esptool --chip esp32S3 --port COM36  erase_flash 
Check-ExitCode

Write-Host "烧录"
esptool --chip ESP32S3 --port COM36 write_flash -z 0x0  ./firmware.bin
Check-ExitCode