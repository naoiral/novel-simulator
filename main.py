"""小说世界模拟器 — 桌面应用入口。"""

import threading
import webview
from app import app


def start_server():
    """在后台线程启动 Flask 服务。"""
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    # 启动 Flask 后台服务
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # 打开桌面窗口
    window = webview.create_window(
        title="小说世界模拟器",
        url="http://127.0.0.1:5000",
        width=1200,
        height=800,
        min_size=(800, 600),
        text_select=True,
    )
    webview.start()
