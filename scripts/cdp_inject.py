# cdp_inject.py — 通过 Chrome DevTools Protocol 注入 Cookie（跨浏览器登录迁移）
# 场景：Chrome 数据库损坏重建后，把从 Firefox 提取的 Cookie 恢复进去。
# 为什么走 CDP 而不是直接写 Cookies SQLite 库：
#   Chrome 新版有 App-Bound 加密（Local State 密钥前缀 DPA），
#   明文写入数据库的 cookie 会在启动时被清空；CDP Network.setCookie 写入的
#   是 Chrome 自己加密的，落盘后能存活。
# 关键坑：
#   1. 默认 User Data 目录禁止开调试端口 → 必须复制一份副本目录
#   2. 本机 Chrome 可能反复闪退 → 带重试循环抓窗口期
#   3. taskkill /F 不触发 Cookie 落盘 → 注入后必须优雅关闭（见 graceful_close.ps1）
# 依赖：pip install websockets
import subprocess, time, json, urllib.request, asyncio, websockets

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
UD = r"C:\Temp\chrome_cdp"          # 必须是复制出来的副本目录，不是真实 User Data
COOKIES_JSON = "cookies.json"       # ff_extract.py 的输出
VERIFY_URL = "https://www.bilibili.com"
VERIFY_EXPR = (
    "fetch('https://api.bilibili.com/x/web-interface/nav',{credentials:'include'})"
    ".then(r=>r.json()).then(j=>j.data.isLogin?'LOGGED_IN:'+j.data.uname:'NOT_LOGGED_IN')")


def port_up():
    try:
        return json.loads(urllib.request.urlopen(
            "http://127.0.0.1:9222/json/version", timeout=2).read())
    except Exception:
        return None


async def inject():
    targets = json.loads(urllib.request.urlopen(
        "http://127.0.0.1:9222/json/list", timeout=5).read())
    page = next(t for t in targets if t["type"] == "page")
    cookies = json.load(open(COOKIES_JSON, encoding="utf-8"))

    async with websockets.connect(page["webSocketDebuggerUrl"], max_size=10**7) as ws:
        mid = 0

        async def cmd(method, params):
            nonlocal mid
            mid += 1
            await ws.send(json.dumps({"id": mid, "method": method, "params": params}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == mid:
                    return msg

        await cmd("Network.enable", {})
        ok = 0
        for c in cookies:
            p = {"name": c["name"], "value": c["value"], "domain": c["domain"],
                 "path": c["path"], "secure": c["secure"], "httpOnly": c["httpOnly"]}
            if c.get("expires"):
                p["expires"] = c["expires"] / 1e6   # Chrome 微秒 → CDP Unix 秒
            r = await cmd("Network.setCookie", p)
            if r.get("result", {}).get("success"):
                ok += 1
        print(f"injected {ok}/{len(cookies)}")

        # 用真实业务接口验证（httpOnly Cookie 用 document.cookie 读不到）
        await cmd("Page.navigate", {"url": VERIFY_URL})
        await asyncio.sleep(8)
        ev = await cmd("Runtime.evaluate", {
            "expression": VERIFY_EXPR, "awaitPromise": True, "returnByValue": True})
        print("verify:", ev["result"]["result"].get("value"))


if __name__ == "__main__":
    for attempt in range(4):
        subprocess.Popen([CHROME, "--remote-debugging-port=9222",
                          f"--user-data-dir={UD}", "--no-first-run",
                          "--disable-features=RendererCodeIntegrity", "about:blank"])
        ver = None
        for _ in range(10):
            time.sleep(2)
            ver = port_up()
            if ver:
                break
        if not ver:
            print(f"attempt {attempt + 1}: chrome crashed, retrying")
            subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
            time.sleep(3)
            continue
        asyncio.run(inject())
        break
    else:
        print("ALL_ATTEMPTS_FAILED")
