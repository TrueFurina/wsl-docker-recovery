# sqlite_check.py — SQLite 结构性损坏检测
# 用途：判断任意 SQLite 文件是"真损坏"还是"表结构清零"（处置方式完全不同）
# 背景：NTFS 文件系统损坏可致 Chrome 数据库文件头合法、但 sqlite_master 表清零，
#       此时浏览器"打开正常、写入落空"，登录态关浏览器即蒸发。
# 用法：python sqlite_check.py <file1> [file2 ...]
import sqlite3, sys


def check(path: str) -> bool:
    with open(path, "rb") as f:
        head = f.read(65536)
    ok_header = head[:16] == b"SQLite format 3\x00"
    nonzero = sum(1 for b in head if b) / len(head)
    print(f"文件头: {head[:16]}  合法={ok_header}")
    print(f"前64K非零字节占比: {nonzero:.1%}   (<30% 高度可疑)")
    try:
        con = sqlite3.connect(path)
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")]
        print(f"表: {tables}")
    except Exception as e:
        print(f"打开失败: {e}")
        return False
    return ok_header and len(tables) > 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for p in sys.argv[1:]:
        print(f"\n=== {p} ===")
        print("健康" if check(p) else "★结构性损坏（表清零）★")
