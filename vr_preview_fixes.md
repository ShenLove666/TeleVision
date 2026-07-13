# VR Preview 问题修复总结

## 问题概述

在使用 ZED Mini → PICO VR 头显通过 WebRTC 实时串流时，遇到以下问题：
1. 画面有网格线（Grid）
2. 画面有 XYZ 坐标轴
3. WebSocket 连接失败
4. PICO 浏览器缓存旧 JS 文件

## 环境信息

- 服务器 IP：`192.168.31.196`（注意：IP 可能变化，需更新代码中的硬编码地址）
- Vuer 服务端口：`8012`（默认）
- WebRTC 服务端口：`8080`
- Vuer 版本：`0.0.32rc7`
- PICO 浏览器访问地址：`https://192.168.31.196:8012`

---

## 问题 1：网格线（Grid）移除

### 原因
Vuer 的 `DefaultScene` 组件在 `bgChildren` 中硬编码了 `Grid()` 组件。当使用 `session.set @ Scene(bgChildren=[])` 时，由于 `Scene.serialize()` 中 `if self.bgChildren:` 的判断，空列表 `[]` 为 falsy，客户端会使用默认值（包含 Grid）。

### 解决方案
使用 `bgChildren=[GrabRender()]` 代替空列表，非空列表不会触发默认值逻辑：

```python
# TeleVision.py - main_webrtc 函数
session.set @ Scene(
    rawChildren=[
        AmbientLight(intensity=1.0),
        DirectionalLight(intensity=1),
    ],
    bgChildren=[GrabRender()],  # 非空，避免客户端使用默认 Grid
    frameloop="always",
)
```

---

## 问题 2：XYZ 坐标轴移除

### 原因
XYZ 坐标轴**不是** Hands 组件，而是 `Scene` 组件（minified 名称 `yk`）内部硬编码的 `qce` 组件。该组件在场景中直接渲染三条轴线和 X/Y/Z 标签，无法通过 Python 端的 props 控制。

### 解决方案
直接修改 Vuer 客户端 JS 文件，将 `qce` 函数替换为空函数：

**修改文件**：
```
vuer/client_build/assets/chunks/chunk-dc0a8b73.js
```

**修改内容**：
```javascript
// 原始代码（约 234 字符）：
const qce=({hideNegativeAxes:t,hideAxisHeads:e,disabled:n,font:r="18px Inter var, Arial, sans-serif",axisColors:i=["#ff2060","#20df80","#2080ff"],axisHeadScale:s=1,axisScale:o,labels:a=["X","Y","Z"],labelColor:l="#000",onClick:c,...u})=>{...}

// 替换为：
const qce=()=>null
```

**查找方法**：在 chunk 文件中搜索 `labels:a=["X","Y","Z"]` 即可定位。

---

## 问题 3：Hands 组件移除

### 原因
`Hands` 组件（minified 名称 `Wie`）用于手部追踪渲染，不需要此功能。

### 解决方案
将 `Wie` 函数替换为返回 null：

**修改文件**：
```
vuer/client_build/assets/chunks/chunk-dc0a8b73.js
```

**修改内容**：
```javascript
// 原始代码（约 1976 字符）：
function Wie({_key:t="hands",children:e,fps:n=30,left:r,right:i,showLeft:s=!0,showRight:o=!0,stream:a=!1,...l}){...完整函数体...}

// 替换为：
function Wie({_key:t="hands",children:e,fps:n=30,left:r,right:i,showLeft:s=!0,showRight:o=!0,stream:a=!1,...l}){return null}
```

**查找方法**：搜索 `function Wie(` 即可定位。

---

## 问题 4：WebSocket 连接失败

### 原因
Vuer 客户端 JS 中的 `sK` 函数用于解析 WebSocket 连接地址。该函数对 HTTPS 页面硬编码不包含端口号：

```javascript
// 原始逻辑：
window.location.protocol == "https:"
    ? `wss://${window.location.hostname}`          // ← 缺少端口号！
    : `ws://${window.location.hostname}:${window.location.port||w6}`
```

导致客户端尝试连接 `wss://192.168.31.196`（端口 443），而 Vuer 服务端实际在端口 8012。

### 解决方案
修改 `sK` 函数，让 HTTPS 也包含端口号：

**修改文件**：
```
vuer/client_build/assets/chunks/chunk-dc0a8b73.js
```

**修改内容**：
```javascript
// 原始：
window.location.protocol=="https:"?`wss://${window.location.hostname}`:

// 替换为：
window.location.protocol=="https:"?`wss://${window.location.hostname}:${window.location.port||w6}`:
```

**查找方法**：搜索 `function sK(` 定位函数，然后找到 HTTPS 分支修改。

---

## 问题 5：PICO 浏览器缓存

### 原因
PICO 浏览器对 JS 文件缓存非常激进，修改服务端文件后浏览器仍加载旧版本。

### 解决方案
在 HTML 和 JS 文件的 import 路径中添加版本号参数，强制浏览器重新下载：

**1. 修改 index.html**（`vuer/client_build/index.html`）：
```html
<!-- 给所有 /assets/ 引用添加 ?v=时间戳 -->
<script type="module" src="/assets/entries/entry-client-routing.fd8d1a7e.js?v=1783943997" defer></script>
<link rel="modulepreload" href="/assets/chunks/chunk-dc0a8b73.js?v=1783943997" ...>
<!-- ...其他引用同理 -->
```

**2. 修改 entry-client-routing.js**（`vuer/client_build/assets/entries/entry-client-routing.fd8d1a7e.js`）：
```javascript
// 动态 import 添加版本号
import("./pages_video_plane.page.35550a3d.js?v=1783943997")
```

**3. 修改页面 JS**（如 `pages_video_plane.page.35550a3d.js`）：
```javascript
// 静态 import 添加版本号
import{...}from"../chunks/chunk-dc0a8b73.js?v=1783943997";
import"../chunks/chunk-d9bdcef8.js?v=1783943997";
```

**注意**：每次修改 chunk 文件后，需要更新版本号（使用新的时间戳）。

---

## 问题 6：服务器 IP 地址

### 原因
代码中硬编码了 `192.168.3.8`，但服务器实际 IP 是 `192.168.31.196`。

### 解决方案
修改 `TeleVision.py` 中的 WebRTC 视频源地址：

```python
session.upsert @ WebRTCStereoVideoPlane(
    src="https://192.168.31.196:8080/offer",  # 改为正确 IP
    key="zed",
    aspect=1.778,
    height=8,
    position=[0, 0, -0.3],
)
```

---

## 修改的文件清单

| 文件 | 修改内容 |
|------|----------|
| `teleop/TeleVision.py` | WebRTC src 地址改为 192.168.31.196 |
| `vuer/client_build/index.html` | 所有 JS/CSS 引用添加 `?v=版本号` |
| `vuer/client_build/assets/entries/entry-client-routing.fd8d1a7e.js` | 动态 import 添加版本号 |
| `vuer/client_build/assets/entries/pages_video_plane.page.35550a3d.js` | 静态 import 添加版本号 |
| `vuer/client_build/assets/chunks/chunk-dc0a8b73.js` | ① `sK` 函数 HTTPS 分支添加端口<br>② `qce` 函数替换为 `()=>null`<br>③ `Wie` 函数替换为 `{return null}` |
| `vuer/base.py` | 添加 `Cache-Control: no-cache` 响应头 |

---

## 快速恢复方法

如需恢复原始文件，从 wheel 包提取：

```bash
cd /tmp
pip download vuer==0.0.32rc7
unzip vuer-0.0.32rc7-py3-none-any.whl -d vuer_pkg

# 恢复特定文件
cp vuer_pkg/vuer/client_build/assets/chunks/chunk-dc0a8b73.js \
   /home/zhs/miniforge3/envs/tv/lib/python3.10/site-packages/vuer/client_build/assets/chunks/

cp vuer_pkg/vuer/client_build/assets/entries/pages_video_plane.page.35550a3d.js \
   /home/zhs/miniforge3/envs/tv/lib/python3.10/site-packages/vuer/client_build/assets/entries/

cp vuer_pkg/vuer/client_build/index.html \
   /home/zhs/miniforge3/envs/tv/lib/python3.10/site-packages/vuer/client_build/
```

---

## 运行命令

```bash
# 启动服务器
python teleop/teleop_yuntai.py

# PICO 浏览器访问
https://192.168.31.196:8012
```
