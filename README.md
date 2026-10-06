# wsl-docker-recovery

WSL / Docker Desktop / 浏览器登录态 故障恢复工具集。

来源：一次真实的 3 个月排障经历——NTFS 文件系统损坏引发连锁故障（Docker vhd 损坏 → WSL 服务卡死 → Chrome SQLite 库表结构清零）。本仓库收录其中的实测脚本，按故障阶段组织。

## 背景：故障链

```
NTFS 文件系统损坏 (0x80070570)
 ├─ Docker ext4.vhdx 损坏    → 引擎无法启动（chkdsk 修复）
 ├─ WSL system.vhd 损坏      → 换盘后服务卡死（幽灵注册表键）
 └─ Chrome SQLite 库表清零   → 登录态丢失（CDP 跨浏览器迁移恢复）
```

## 脚本清单

| 脚本 | 用途 | 阶段 |
|------|------|------|
| `scripts/sqlite_check.py` | 检测 SQLite 文件是否"表结构清零"（文件头合法但表为 0） | 定性 |
| `scripts/vss_extract.ps1` | 从卷影副本（VSS）提取文件并验证健康度 | 恢复 |
| `scripts/ff_extract.py` | 从 Firefox 提取 Cookie（多容器去重 + 凭证有效期校验） | 恢复 |
| `scripts/cdp_inject.py` | 通过 CDP 向 Chrome 注入 Cookie（绕过 App-Bound 加密） | 恢复 |
| `scripts/graceful_close.ps1` | 优雅关闭 Chrome 触发 Cookie 落盘 + 回拷真实配置 | 恢复 |

## 快速使用

### 场景 A：怀疑浏览器数据库损坏

```bash
python scripts/sqlite_check.py ^
  "%LOCALAPPDATA%\Google\Chrome\User Data\Default\Network\Cookies" ^
  "%LOCALAPPDATA%\Google\Chrome\User Data\Default\History"
```

判读：文件头合法 + 表数量 0 = 结构性损坏。

### 场景 B：Cookie 跨浏览器迁移（Firefox → Chrome）

```bash
# 1. 提取（先改脚本里的 PROFILE 路径）
python scripts/ff_extract.py

# 2. 复制 Chrome User Data 到 C:\Temp\chrome_cdp（脚本默认读取该副本）

# 3. 注入（依赖：pip install websockets）
python scripts/cdp_inject.py          # 看到 LOGGED_IN:<用户名> 即成功

# 4. 优雅关闭 + 落盘验证 + 回拷（管理员 PowerShell）
powershell -ExecutionPolicy Bypass -File scripts/graceful_close.ps1
```

### 场景 C：WSL 服务卡 START_PENDING

```bat
:: 排查幽灵发行版注册键（指向已删除 vhd 的残留键会让 WslService 挂死）
reg query "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Lxss" /s
:: 逐个核对 BasePath + VhdFileName 指向的文件是否存在，不存在的直接删：
reg delete "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Lxss\{GUID}" /f
taskkill /F /IM wslservice.exe && sc start WslService
```

## 关键经验（详细复盘见博客文章）

1. **GUI 错误码一文不值**：MSI `/l*v`、Docker `com.docker.backend.exe.log` 才是真相
2. **"文件+注册表"双状态组件**（WSL/MSI），挂死先查注册表残留
3. **落盘判成功**：CDP 返回 success ≠ 数据在磁盘；`taskkill /F` 不触发浏览器退出写盘
4. **文件系统损坏是连环事故**：修好一个要防一串，`chkdsk` 后必须全盘体检
5. **卷影快照要验证健康**：文件系统渐进损坏时，快照可能同样已坏

## 免责声明

- Cookie 迁移仅限**恢复自己账号的登录态**，请勿用于他人设备或账号
- 注册表删除操作请先备份键值（`reg export`）
- 所有脚本以"现状"提供，运行前请阅读源码确认参数（`<用户名>` 等占位符需替换）

## 环境

Windows 11 24H2 · Docker Desktop 4.83 · WSL 3.0.1 · Python 3.x（`websockets`）· PowerShell 5.1+
