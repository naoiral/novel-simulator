"""打包脚本 — 将小说世界模拟器打包成 .exe"""

import subprocess
import sys
import os

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    spec_path = os.path.join(base_dir, "build.spec")

    print("=" * 50)
    print("  开始打包：小说世界模拟器")
    print("=" * 50)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--distpath", os.path.join(base_dir, "dist"),
        "--workpath", os.path.join(base_dir, "build"),
        spec_path,
    ]

    result = subprocess.run(cmd, cwd=base_dir)

    if result.returncode == 0:
        exe_path = os.path.join(base_dir, "dist", "小说世界模拟器.exe")
        print()
        print("=" * 50)
        print("  打包成功！")
        print(f"  文件位置：{exe_path}")
        print("  双击即可运行，不需要浏览器")
        print("=" * 50)
    else:
        print("\n打包失败，请检查错误信息。")
        sys.exit(1)


if __name__ == "__main__":
    main()
