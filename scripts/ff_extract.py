# ff_extract.py — Firefox Cookie 提取（含多容器去重 + 凭证有效期校验）
# 用途：Firefox 还登录着、Chrome 登录态损坏时，提取 Cookie 供 CDP 注入迁移
# 注意：Firefox 运行中库被锁，先复制（连同 WAL）再读
import sqlite3, json, shutil, sys, time

PROF = r"C:\Users\<用户名>\AppData\Roaming\Mozilla\Firefox\Profiles\<profile>"
TARGET = "%bilibili%"          # 目标域，LIKE 模式
OUT = "cookies.json"


def main():
    shutil.copyfile(PROF + r"\cookies.sqlite", r"ff_copy.db")
    con = sqlite3.connect(r"ff_copy.db")
    con.row_factory = sqlite3.Row

    # ---- 1. 前置校验：关键凭证是否存在且未过期 ----
    now = time.time()
    print("=== 关键凭证校验 ===")
    for n, h, v, e in con.execute(
        "SELECT name,host,value,expiry FROM moz_cookies "
        "WHERE host LIKE ? AND name IN ('SESSDATA','DedeUserID','bili_jct')", (TARGET,)):
        print(f"{h} {n}: len={len(v)} {'有效' if e > now else '★已过期'}")

    # ---- 2. 提取 + 去重（Firefox 多容器产生同名副本）----
    rows = con.execute(
        "SELECT * FROM moz_cookies WHERE host LIKE ?", (TARGET,)).fetchall()
    seen = {}
    for r in rows:
        seen[(r['host'], r['name'], r['path'])] = dict(r)

    out = [{
        "domain": r['host'], "name": r['name'], "value": r['value'],
        "path": r['path'],
        # Firefox 存 Unix 秒 → Chrome/CDP 用微秒（1601 纪元偏移 11644473600 秒）
        "expires": r['expiry'] * 1000000 + 11644473600000000 if r['expiry'] else 0,
        "secure": bool(r['isSecure']), "httpOnly": bool(r['isHttpOnly']),
    } for r in seen.values()]

    json.dump(out, open(OUT, "w"), ensure_ascii=False)
    print(f"\n导出 {len(out)} 条 → {OUT}")


if __name__ == "__main__":
    main()
