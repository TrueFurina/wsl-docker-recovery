# vss_extract.ps1 — 从 Windows 卷影副本（VSS）提取文件
# 用途：文件被损坏/覆盖后，尝试从系统还原点快照里捞回旧版本。
# 教训：文件系统损坏是渐进的——快照提取成功不代表内容健康，
#       提取后必须用 sqlite_check.py 验证快照版本！
# 前提：管理员权限；系统保护已开启（vssadmin list shadows 有输出）
# 用法：管理员 PowerShell -ExecutionPolicy Bypass -File vss_extract.ps1

# ---- 参数区（按需修改）----
$ShadowCopy = 1        # HarddiskVolumeShadowCopy<N> 的 N
$RelPath = "Users\<用户名>\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies"
$Dest = "D:\recover\Cookies_snapshot"
# ---------------------------

# 1. 列出快照（人工核对 Creation Time 是否早于损坏时间）
vssadmin list shadows

$src = "\\?\GLOBALROOT\Device\HarddiskVolumeShadowCopy$ShadowCopy\$RelPath"
New-Item -ItemType Directory -Force -Path (Split-Path $Dest) | Out-Null

# 2. cmd 的 copy 会把 \\?\ 路径反斜杠转义吃掉，必须用 PowerShell -LiteralPath
try {
    Copy-Item -LiteralPath $src -Destination $Dest -Force -ErrorAction Stop
    Write-Output "COPY_OK → $Dest"
} catch {
    Write-Output "COPY_FAIL: $($_.Exception.Message)"
    exit 1
}

# 3. ★必做：验证快照版本健康度
python sqlite_check.py $Dest
