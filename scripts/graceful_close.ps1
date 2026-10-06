# graceful_close.ps1 — 优雅关闭 Chrome 以触发 Cookie 落盘
# 关键：taskkill /F 不会触发 Chrome 的退出写盘流程，注入的 Cookie 会全部丢失。
#       必须先 CloseMainWindow()（等效用户点 ×），再兜底强杀残留。
# 用法：powershell -ExecutionPolicy Bypass -File graceful_close.ps1
#       注入完成、验证 LOGGED_IN 之后运行本脚本，然后才能回拷数据库。

# 1. 优雅关闭（触发落盘）
Get-Process chrome -ErrorAction SilentlyContinue |
    ForEach-Object { $_.CloseMainWindow() | Out-Null }
Start-Sleep -Seconds 6

# 2. 兜底：清理可能残留的进程
Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 3

# 3. 落盘验证（只读模式直读副本库）
$db = "C:\Temp\chrome_cdp\Default\Network\Cookies"
if (Test-Path $db) {
    python -c "
import sqlite3
db = r'$db'
con = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
s = con.execute('''SELECT count(*) FROM cookies
    WHERE host_key LIKE '%bilibili%'
    AND name IN ('SESSDATA','DedeUserID','bili_jct')''').fetchone()[0]
print('落盘凭证:', s, '/6')
"
}

# 4. 回拷真实配置（Chrome 必须已完全退出）
$dst = "$env:LOCALAPPDATA\Google\Chrome\User Data"
Copy-Item "C:\Temp\chrome_cdp\Default\Network\Cookies" "$dst\Default\Network\Cookies" -Force
Copy-Item "C:\Temp\chrome_cdp\Local State" "$dst\Local State" -Force
"已回拷真实配置，重启 Chrome 验证登录态"
