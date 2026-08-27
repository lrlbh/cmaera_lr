# 内部命令,出错退出
$ErrorActionPreference = "Stop"

# 外部程序,出错退出
function Test-ExitCode {
    if ($null -ne $LASTEXITCODE -and $LASTEXITCODE -ne 0) {
        Write-Host "命令执行失败，退出码：$LASTEXITCODE" -ForegroundColor Red
        exit 1
    }
}
# 自动获取串口
function Get-SerialPort {

    # 接收脚本传入的串口参数
    param(
        [string]$ManualPort
    )

    # 手动指定
    if ($ManualPort) {
        return $ManualPort.ToUpper()
    }

    # 自动查找
    $ports = @(Get-CimInstance Win32_SerialPort |
        Where-Object {
            $_.Name -notmatch "蓝牙链接上的标准串行"
        })

    if ($ports.Count -eq 1) {
        return $ports[0].DeviceID
    }

    Write-Host "无法自动确定串口，当前可用串口：" -ForegroundColor Yellow

    if ($ports.Count -eq 0) {
        Write-Host "没有非蓝牙的串口连接"
    }
    else {
        $ports | Select-Object DeviceID, Name | Format-Table
    }

    exit 1
}

Write-Host "拷贝项目到linux"
# wsl cp -r ../camera_lr ~/test_build
wsl rsync -av --delete --exclude='.git' --exclude='build' ./ /home/luorong/test_build/camera_lr/
Test-ExitCode 

Write-Host "执行远程脚本"
wsl ./build.sh
Test-ExitCode

$port = Get-SerialPort $args[0]
Write-Host "使用串口: $port" -ForegroundColor Green

Write-Host "擦除"
esptool --port $port  erase-flash 
Test-ExitCode

Write-Host "烧录"
esptool --port $port write-flash -z 0x0  ./firmware.bin
Test-ExitCode