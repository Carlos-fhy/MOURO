# Solomon VRPTW 标准算例下载脚本
import os
import urllib.request
import sys

# 多个下载源（按优先级尝试）
SOURCES = [
    "https://www.sintef.no/globalassets/project/top/vrptw/solomon/",
    "https://neo.lcc.uma.es/vrp/wp-content/data/solomon/",
]

# 需要下载的6个算例文件
INSTANCES = ["c101", "c201", "r101", "r201", "rc101", "rc201"]


def download_solomon(target_dir=None):
    """
    从多个镜像站尝试下载 Solomon 算例文件

    参数:
        target_dir: 目标目录，默认为脚本所在目录
    """
    if target_dir is None:
        target_dir = os.path.dirname(os.path.abspath(__file__))

    os.makedirs(target_dir, exist_ok=True)
    success = 0
    failed = []

    for name in INSTANCES:
        filename = f"{name}.txt"
        filepath = os.path.join(target_dir, filename)

        if os.path.exists(filepath):
            print(f"[跳过] {filename} 已存在")
            success += 1
            continue

        downloaded = False
        for base_url in SOURCES:
            url = f"{base_url}{name}.txt"
            print(f"[尝试] {url} ...", end=" ")
            try:
                urllib.request.urlretrieve(url, filepath)
                print("成功")
                downloaded = True
                break
            except Exception as e:
                print(f"失败: {e}")

        if downloaded:
            success += 1
        else:
            failed.append(name)

    print(f"\n下载完成: {success}/{len(INSTANCES)} 个文件")

    if failed:
        print("\n" + "=" * 50)
        print("以下文件自动下载失败，请手动下载:")
        print("=" * 50)
        print("\n方法1: 访问 SINTEF 官网")
        print("  https://www.sintef.no/projectweb/top/vrptw/solomon-benchmark/")
        print("\n方法2: 访问 NEO 镜像")
        print("  https://neo.lcc.uma.es/vrp/vrp-instances/capacitated-vrp-with-time-windows-instances/")
        print("\n需要下载的文件（文件名请用小写）:")
        for name in failed:
            print(f"  - {name}.txt")
        print(f"\n下载后放入目录: {target_dir}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    download_solomon(target)
