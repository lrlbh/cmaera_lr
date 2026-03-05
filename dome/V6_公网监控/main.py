import cam_lsl
import wifi_lsl
import ws_lsl
import time


html = """<!DOCTYPE html>
<html>

<head>
    <meta charset="utf-8">
    <title>ESP32 JPEG Stream</title>
    <style>
        body {
            background: black;
            margin: 0;
            text-align: center;
        }

        img {
            width: 95vw;
        }

        div {
            color: white;
            padding: 10px;
            font-size: 4vw;
        }
    </style>
</head>

<body>
    <div id="status">Connecting...</div>
    <img id="video">
    <div id="fps">FPS: XX.XX</div>
    <div id="szie_n">ASDFASDFA</div>

    <script>

        const status = document.getElementById("status");
        const img = document.getElementById("video");
        img.style.transform = "scaleY(-1)";
        const fps = document.getElementById("fps");
        const szie_n = document.getElementById("szie_n");

        var protocol = (location.protocol === "https:") ? "wss://" : "ws://";
        var wsUrl = protocol + location.host;

        const ws = new WebSocket(wsUrl);

        ws.binaryType = "arraybuffer";

        ws.onopen = () => status.innerText = "连接中...";

        ws.onclose = () => status.innerText = "连接断开了...";

        ws.onerror = (e) => {
            status.innerText = "Error";
            console.log(e);
        };

        let s_time = Date.now();
        let img_n = 0;
        let 图片总量 = 0;

        ws.onmessage = (event) => {

            const blob = new Blob([event.data], { type: "image/jpeg" });

            const url = URL.createObjectURL(blob);

            img.src = url;

            img.onload = () => URL.revokeObjectURL(url);
            
            img_n += 1;
            let e_time = Date.now() - s_time;
            if (e_time >= 2000) {

                fps.innerHTML = "FPS: " + (img_n / (e_time / 1000)).toFixed(2);
                s_time = Date.now();
                img_n = 0;
            }
            图片总量 += 1;
            szie_n.innerHTML = "接收图片总数: " + 图片总量 + " ======= ";
            szie_n.innerHTML += "图片大小: " + (blob.size / 1024).toFixed(2) + "KiB";

        };

    </script>

</body>

</html>""".encode("utf-8")

html_data = (
    b"HTTP/1.1 200 OK\r\n"
    b"Content-Type: text/html; charset=utf-8\r\n"
    b"Content-Length: " + str(len(html)).encode() + b"\r\n"
    b"Connection: close\r\n"
    b"\r\n" +
    html
)

"""
    代码开始
    代码开始
    代码开始
"""

# 初始化摄像头
print("开始初始化摄像头....")
cam = cam_lsl.Cam()
cam.set_分辨率(cam_lsl.t参数.t图片分辨率.t_1280x720)
print(f"hts: {cam.get_hts()}  vts: {cam.get_vts()}")
try:  # 开启自动对焦
    cam.af_run()
except Exception as e:
    print(e)
# cam.set_水平镜像(True)
# cam.set_垂直翻转(True)


# 连接WiFi
print("开始连接wifi,协商ipv6公网地址....")
wifi_lsl.WIFI(account={
    "CMCC-Ef6Z": "ddtzpts9"
}, v6公网=True).conn_thr()


# 等待ipv6公网连接成功
print("等待V6公网协商成功,打印URL....")
for v6 in wifi_lsl.WIFI.get_v6_str_阻塞():
    print(f"http://[{v6}]:30000")


# 创建 ws server ||  run_thr自动处理连接
print("创建服务器....")
s = ws_lsl.Server("::", 30000, 3).run_thr()


print("开始工作....")
conn = None
while True:

    # http请求 回复网页
    while len(s.http):
        print("http连接处理 -> ", end="")
        client, _ = s.http.pop(0)
        try:
            client.settimeout(3)
            client.sendall(html_data)
            print("成功!")
        except Exception as e:
            print(f"失败: \n{e}")
            pass
        client.close()

    # ws请求 断开上一个连接,只向最新的连接发送
    while len(s.ws):
        print(f"新的视频请求到达{time.time()}")
        if conn is not None:
            conn.socket.close()
        conn, _ = s.ws.pop(0)
        conn.socket.settimeout(1)

    # 重复发送图片
    if conn is not None:
        try:
            conn.send(cam.get_img_p())
            cam.free_img_p()
            # time.sleep(0.1)
        except Exception as e:
            # print(f"发送失败{e}")
            conn.socket.close()
            conn = None
            pass

    # print(f"size(MB): {len(data)/1024/1024}",
    #       f"fps:{1000 / (time.ticks_ms() - ss): 2f}")
