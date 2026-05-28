"""测试运行脚本 — 运行全部测试并生成覆盖率报告。"""

import subprocess
import sys


def main():
    print("=" * 50)
    print("  小说世界模拟器 — 自动化测试")
    print("=" * 50)

    # 1. 运行 pytest + 覆盖率
    print("\n[1/2] 运行 pytest + 覆盖率报告...\n")
    ret = subprocess.run([
        sys.executable, "-m", "pytest", "tests/",
        "--cov=.", "--cov-report=term-missing", "--cov-branch",
        "-q", "--tb=short",
    ], cwd=".")

    # 2. 运行原集成测试
    print("\n[2/2] 运行原集成测试...\n")
    ret2 = subprocess.run([sys.executable, "test_all.py"], cwd=".")

    # 总结
    print("\n" + "=" * 50)
    if ret.returncode == 0 and ret2.returncode == 0:
        print("  全部测试通过 ✓")
    else:
        print("  存在失败的测试 ✕")
    print("=" * 50)

    return 0 if ret.returncode == 0 and ret2.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
