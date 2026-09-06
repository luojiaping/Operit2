# Operit2：Agent 不属于一台设备

> 让软件与硬件彼此成就，让上下文跨越终端，在设备组成的超级 Space 中持续流动。

> 当前版本：`2.0.0-preview.6`。这是预发布版本，后续版本可能产生破坏性更新；接口、数据结构、插件协议、平台行为和数据兼容性均可能变化。请勿将当前版本用于生产环境。

我们仍处在跨设备 Agent 的早期阶段：还没有一个能够自然跨越所有操作系统、终端和硬件的完全统一 Agent。Operit2 从这个缺口出发，尝试让 Agent 不再寄居于某一台设备，而是与由设备共同组成的空间一起存在。

基于 Operit Core、分布式数据管理和分布式任务调度，不同设备能够在 Agent 驱动下进行软硬件互助与资源共享，调用彼此的本地能力，并在终端之间延续上下文和任务，形成连续的跨终端 Agent 协同体验。

Flutter 应用、Rust CLI/TUI 和 Web Access 是 Agent 进入这个设备空间的不同界面；工作区、工具、插件和本地模型，则是它在不同节点上获得的能力。

## 目录

- [项目定位](#项目定位)
- [核心概念](#核心概念)
- [设计哲学](#设计哲学)
- [架构概览](#架构概览)
- [Agent 驱动的跨设备协作](#agent-驱动的跨设备协作)
- [节点能力](#节点能力)
- [支持的平台](#支持的平台)
- [仓库结构](#仓库结构)
- [快速开始](#快速开始)
- [CLI 使用入口](#cli-使用入口)
- [权限与安全边界](#权限与安全边界)
- [当前状态与预发布边界](#当前状态与预发布边界)
- [文档索引](#文档索引)
- [参与贡献](#参与贡献)
- [许可证](#许可证)

## 项目定位

Operit2 将 Agent 从单一应用窗口和单一设备中解耦出来。一个逻辑上的 Agent 可以拥有持续的聊天、记忆、配置、工具结果和恢复状态；这些状态由设备空间同步，下一步任务则根据 `Binding` 选择实际承接的 `CoreNode`。

Operit2 不是把所有设备伪装成一台机器，也不是把所有权限集中到一个中心服务。它建立的是一个对等的超级 Space：上下文与任务意图可以流动，设备能力彼此协作，权限与执行边界仍留在各自节点。

统一的是 Agent 的连续性、Core 语义和协作协议，而不是设备的硬件能力或系统权限。每台设备都可以把自己的存储、计算、网络、终端、浏览器和其他硬件能力带入协作，但这些能力仍由本地 Host 持有并执行。

## 核心概念

| 概念 | 含义 |
| --- | --- |
| `Agent` | 跨设备持续存在的逻辑上下文与任务意图，不等于某个正在运行的模型进程。 |
| `CoreNode` | 一台设备上的 Core、数据副本和本地 `HostManager`。 |
| `Space` | 多个对等 CoreNode 的协作与同步范围，不是执行容器、权限池或中心服务器。 |
| `Binding` | 某个业务 key 下一次执行所对应的目标 CoreNode。它决定执行位置，不搬迁数据。 |
| `PeerLink` | 已配对节点之间承载实时 call、watch、push、stream 和 continuation 的链路。 |
| `Host` | 节点本地的文件、终端、浏览器、网络、传感器、计算资源和操作系统权限。 |
| `Access Surface` | Flutter、CLI/TUI 和 Web Access 等访问或呈现界面，不是额外的 Core 业务树。 |
| `Task Routing` | 以 Binding、CoreNodeRouter 和 continuation 为基础的分布式任务交接，不等于进程热迁移。 |

## 设计哲学

### 上下文先于界面和设备

Agent 的持久化上下文属于 Core，而不是某个 Flutter 页面、CLI 进程或浏览器标签页。客户端可以展示、编辑和驱动上下文，但不应成为上下文唯一的拥有者。

### 上下文流动，能力留在节点

聊天、记忆、配置、工具结果以及其他已声明可同步的数据可以进入 Space 的持久化同步域。文件系统、终端、浏览器、操作系统权限、API key 和本地模型运行环境仍属于各自 CoreNode，不会因为加入 Space 就变成共享能力。

资源共享不是把多个设备合并成一个共享文件系统或权限池，而是同步明确声明的数据，并通过经过认证的节点调用使用目标设备的本地能力。

### Core 优先，宿主适配

业务能力属于 Rust Core，平台差异通过 `operit-host-api` 和 `hosts/` 中的实现注入。Flutter、CLI/TUI 和 Web Access 负责访问、输入、渲染和平台适配，不在各自侧重新组装一套业务 Core。

### 设备对等，信任显式建立

CoreNode 之间通过配对、认证和 PeerLink 建立连接。Space 没有主节点、从节点或中心调度器；PeerLink 可以形成多跳拓扑，中间节点负责转发，但不成为数据权威，也不伪装成目标节点。

### 持久化同步和实时流转是两条平面

持久化同步平面负责让 Agent 保持可恢复的上下文，使用操作日志、向量时钟和已声明的数据范围传播状态。实时执行平面负责传递任务意图、call、watch、push、stream 和 continuation；PeerLink 是传输载体，不是数据迁移器。

### 在工具边界交接，而不是热迁移运行时

当前设备流转发生在工具调用已经完成、工具结果已经持久化、下一轮模型请求尚未发起的边界。目标节点从同步后的上下文恢复下一轮执行；正在运行的模型请求、终端进程、浏览器会话和 Host 句柄不会被热迁移。

## 架构概览

Operit2 的整体架构由两个相互配合但职责不同的平面构成：

- 持久化同步平面：同步已声明的 Space 数据，形成各节点可恢复的本地副本。
- 实时任务平面：根据 Binding 和路由将任务意图、工具调用与 continuation 交给目标 CoreNode。

```text
                 Super Space（无主节点、无中心调度器）

  +------------+       +------------+       +------------+
  | CoreNode A |<----->| CoreNode B |<----->| CoreNode C |
  | Core + Host|       | Core + Host|       | Core + Host|
  | data copy  |       | data copy  |       | data copy  |
  +------+-----+       +------+-----+       +------+-----+
         |                    |                    |
         +--------------------+--------------------+
              declared Space data / task routing
```

上图只是示意拓扑。PeerLink 可以组成多跳网络，CoreNode B 不是中心节点；每个节点都保留自己的本地 Host 和权限。

```text
分布式数据管理：
Space data
  -> operation log / vector clock
  -> 每个成员节点的本地数据副本

分布式任务调度：
Agent task intent
  -> Binding
  -> CoreNodeRouter
  -> PeerLink
  -> 目标 CoreNode 的本地 Host
```

每个 `CoreNode` 内部由同一个 Core 组合入口管理：

```text
Flutter / CLI / TUI / Web Access
              |
       CoreApplication
        +-----+-----+----------------+
        |           |                |
     Runtime   NodeRouter       AccessServices
        |           |                |
     Chat       Binding         Pairing / PeerLink
     Workspace  Space           Discovery / Web
     Provider   Task routing
     Tools      Continuation
     Plugins
     Local Models
              |
       Host API + local platform Host
```

核心职责可以概括为：

- `foundation`：Host 契约、共享模型、通用工具和 Link 协议类型。
- `persistence`：本地持久化、Space 数据副本、操作日志、向量时钟、Binding 和断线恢复。
- `provider`：远程模型 Provider、聊天编排、STT/TTS、市场和本地模型能力。
- `tool`：工具注册和执行、权限判定、内置工具、Skill、Package、MCP 和工具脚本。
- `plugin`：插件 SDK、ToolPkg、Compose DSL、Wasm、JavaScript 运行时和代码生成。
- `runtime`：应用启动、聊天运行时、工作区、偏好、事件和跨领域服务编排。
- `node`：CoreNode 路由、Binding、Space 范围内的实时调用和同步调度；实际执行始终发生在目标节点。
- `access`：每个 CoreNode 的身份、配对、认证、session、PeerLink、发现和 Web 控制面。
- `proxy`：面向 Flutter/CLI 的本地调用投影和生成代码，不负责远程路由。
- `application`：组合 Core 树并管理生命周期。
- `command`：面向 CLI 的命令编排和输出适配。

当前部分领域仍以 aggregate crate 形式存在，目录拆分正在演进。目标 crate 结构见 [`core-module-crate-layout.md`](docs/core-module-crate-layout.md)，不代表所有目标 crate 已经完成迁移。

## Agent 驱动的跨设备协作

### 当前交接路径

当前实现围绕一个明确的工具边界完成 Agent 交接：

```text
1. Agent 在 CoreNode A 上发起工具调用。
2. 工具执行完成，工具结果在 A 上持久化。
3. Space 同步传播已提交的上下文和执行记录。
4. Binding 通过比较写入选择下一次执行的 CoreNode B。
5. B 校验同步状态并从上下文恢复下一轮模型请求。
6. 后续输出继续回到原有的逻辑响应流。
```

这是一种任务意图和 continuation 的跨节点交接。它不是把同一个模型线程、终端进程或浏览器会话从 A 搬到 B。

### 上下文的流动边界

| 可以在 Space 中流动 | 始终留在节点本地 |
| --- | --- |
| 聊天、配置、记忆、工具调用和工具结果等已接入同步域的数据 | 任意未声明的本地文件系统、缓存、临时目录和日志 |
| Binding、执行完成记录和可序列化的 Agent continuation 状态 | 正在运行的模型请求、终端进程、浏览器会话和 Host 句柄 |
| 明确声明为 Space 数据的 runtime 文件和同步 blob | API key、CoreNode 身份私钥、配对密钥、session 和本地平台权限 |

加入 Space 后，成员节点会拥有同步域数据的本地副本。离开 Space 不代表其他节点已经保存的副本会被自动删除；数据生命周期和删除策略仍需由具体业务与用户操作决定。

## 节点能力

### Agent 上下文和模型

- 支持流式对话、会话管理、消息分支、附件、角色卡、角色群组和提示词配置。
- Provider 层包含多种远程模型适配和 OpenAI-compatible 风格的连接配置；具体模型由节点上的 endpoint、凭据和模型服务决定。
- 支持模型参数、请求队列、工具调用、媒体输入、对话记忆和摘要相关服务。
- 支持 STT/TTS 配置、语音识别和语音合成；远程 Provider 与本地模型属于不同的节点能力。
- Provider 配置的可同步范围由数据模型决定，API key 和其他敏感凭据不因加入 Space 自动复制。

正在执行的模型请求属于发起执行的 CoreNode。任务可以交给已经具备相应模型和 Host 能力的节点，但当前不迁移正在运行的推理会话。

### 节点 Host 与工具

每个 CoreNode 通过自己的 `HostManager` 暴露本地能力。Agent 可以在经过认证和权限检查后使用：

- 文件系统、工作区、附件、模板、备份、导入和导出。
- 终端会话、PTY 输入、命令执行和终端输出流。
- HTTP 请求、网页访问、浏览器自动化和由运行时 Host 提供的 WebView 会话投影。
- 记忆、聊天、系统、音频和 Bluetooth 等内置工具。

这些能力是节点资源，不是 Space 的统一资源池。跨节点调用最终仍由目标 CoreNode 的 Host 执行，并使用目标节点自己的系统权限、工作区和运行环境。

### 插件、Skill、ToolPkg 和 MCP

- 使用 JavaScript/TypeScript 编写 ToolPkg，并通过插件运行时加载和管理。
- 使用 Skill 提供可导入、可见性可控的工作流和知识资源。
- 连接 MCP server，管理 MCP 配置、工具和本地 MCP 进程。
- 使用 Compose DSL、Wasm runtime、JavaScript SDK 和 SDK codegen 构建扩展。
- 插件、Skill、ToolPkg 和 MCP 默认按安装和执行它们的 CoreNode 管理，不会因为加入 Space 自动复制。
- 安装扩展不等于授予新的系统权限；扩展调用 Host 能力时仍受节点 Host、AI 能力模式和具体工具边界限制。

插件源码、类型声明、内置包、官方可选包和示例位于 [`plugins/`](plugins/)；作者入口见 [`plugins/docs/README.md`](plugins/docs/README.md)。

### 本地模型

`operit-local-models` 负责本地模型的 manifest、引擎标识、安装记录、存储路径、下载进度、校验和本地推理会话契约。

当前内置目录主要覆盖 Sherpa ONNX 语音模型，包括双语流式 STT、中文和英文 TTS，以及浏览器端 STT/TTS bundle。模型文件作为运行时数据安装，不打进应用二进制；每个 manifest 声明文件大小、SHA-256、来源 revision、兼容平台和模型许可证。

模型权重、引擎、下载状态和推理会话属于节点本地资源。Agent 可以把任务交给已经安装相应模型的节点，但当前不会热迁移模型或推理进程。本地模型接口也为本地聊天模型和其他推理引擎保留扩展方向，具体能力以当前目录和 manifest 为准。

### Web Access：CoreNode 的访问面

CLI 可以启动本机 Web Access 服务，让浏览器通过 token 和配对控制面访问启动服务的 CoreNode。浏览器默认是访问面，不是自动加入 Space 的独立 CoreNode；节点之间的协作由 CoreNodeRouter 和 PeerLink 完成。

Web Access 使用与原生客户端相同的认证和工具执行边界，不是集中式 Agent Server、远程桌面或绕过 Host 的执行入口。对外绑定监听地址时，应使用强 token、网络隔离、TLS 或防火墙策略，不要把 token 放入公开日志、URL 或截图。

Web Access 的本地模型和 WebAssembly runtime 需要跨源隔离响应头：

```text
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
Cross-Origin-Resource-Policy: same-origin
```

完整 Web Access 构建和 Flutter Web 开发方式见 [`apps/web_access/README.md`](apps/web_access/README.md)。

## 支持的平台

| 形态 | 在设备空间中的角色 | 当前目标平台和边界 |
| --- | --- | --- |
| Rust CLI/TUI | 可以承载一个 CoreNode，也是该节点的本地访问面 | Windows、Linux、macOS；部分查询或短生命周期命令会关闭 Space 同步 worker。 |
| Flutter App | 可以承载一个 CoreNode，也是移动端或桌面端访问面 | Android、Windows、Linux、macOS、iOS、OpenHarmony；各平台 Host 能力不同。 |
| Web Access | 访问某个已经运行的 CoreNode | 支持 WebAssembly 和跨源隔离的现代浏览器；默认不是独立 CoreNode，也不是中心 Server。 |
| WebAssembly/browser Host | 浏览器运行时能力和 Web bundle 的组成部分 | 与 Web Access 的访问面概念分开，具体本地运行能力以当前 Web 构建模式为准。 |
| Server | 当前不是可直接发布的产品形态 | Server host、企业部署和 Server Manager 属于架构扩展方向。 |

能构建某个平台不等于该平台已经完成跨设备互操作验证，也不等于该平台拥有其他节点的 Host 能力。OpenHarmony 目前主要走本地工具链构建；iOS 当前构建工作流产出未签名包。平台构建、签名和发布条件以 [`BUILDING.md`](BUILDING.md) 与对应 workflow 为准。

## 仓库结构

```text
apps/
├── cli/                 Rust CLI/TUI 入口，可承载 CoreNode
├── flutter/app/         Flutter 应用入口，可承载 CoreNode
└── web_access/          Web Access 访问面和共享 Web bundle

core/
├── crates/              Core 各领域 crate
├── CRATE_BOUNDARIES.md  crate 依赖方向和职责边界
└── examples/            Provider 和 Plugin SDK 示例

hosts/                   各平台 CoreNode Host 能力实现
plugins/                 ToolPkg、Skill、SDK 类型、示例和开发工具
tools/                   构建、发布、Web 和开发辅助脚本
docs/                    架构、权限、Link 和版本文档
```

目录与产品角色的关系是：`apps/` 提供访问和呈现面，`core/` 提供节点运行时，`hosts/` 提供节点本地能力，`plugins/` 提供节点侧扩展，`docs/` 记录当前边界和演进目标。当前仓库没有中心数据层或独立 Server 产品目录。

## 快速开始

### 环境要求

最小的 CLI 检查需要：

- Rust stable toolchain 和 `rustup`。
- Git。

构建 Flutter App 或 Web Access 还需要：

- Flutter SDK 和项目使用的 FVM 配置。
- Python 3 以及仓库的 `.venv` 环境。
- Node.js/npm；Web Access 构建还会使用 TypeScript、Terser、wasm-bindgen 和 WASI SDK。
- 目标平台的原生工具链、依赖库和签名材料。

运行两个 CoreNode 进行 Space 协作还需要：

- 两个设备或两个独立的运行实例，以及各自的身份和 Host 权限。
- 可互通的局域网地址、端口和防火墙配置。
- mDNS 或可手动输入的 Link 地址。
- 配对 token 和交互式配对验证码。
- 每个节点独立的模型 endpoint、API key 和本地模型环境。

平台差异和完整依赖见 [`BUILDING.md`](BUILDING.md)。

### 单节点检查和运行 CLI

以下命令从仓库根目录执行。它们只验证当前 CLI/CoreNode，不会自动把节点加入 Space：

```powershell
cargo check --manifest-path apps/cli/Cargo.toml
cargo run --manifest-path apps/cli/Cargo.toml --bin operit2 -- --help
cargo run --manifest-path apps/cli/Cargo.toml --bin operit2 -- cli version
cargo run --manifest-path apps/cli/Cargo.toml --bin operit2 -- tui
```

构建后，以上命令中的 `cargo run ... --bin operit2 --` 可以替换为已安装或当前目录中的 `operit2`。

### 两个 CoreNode 组成 Space

下面是当前 CLI 的最小协作路径。参数和具体输出以 `operit2 cli --help` 为准。

在设备 A 上启动一个 CoreNode 监听入口：

```powershell
operit2 cli link serve --bind 0.0.0.0:37192 --token <strong-token>
```

`link serve` 是设备 A 的监听角色，不是中心 Server。默认开发 token 只适合本地开发；局域网测试也应替换为随机强 token，并配置防火墙限制访问范围。

在设备 B 上发现、配对并加入设备空间：

```powershell
operit2 cli link discover
operit2 cli link connect <url> --token <strong-token> --save <session-name>
operit2 cli link space join <session-name>
operit2 cli link space show
```

`link connect` 会进入配对流程，验证码由设备 A 的服务端交互提供。`space join` 是加入同步和协作范围的明确动作；完成配对并不等于自动加入对方 Space。

这条流程验证的是身份、配对、Space 成员关系和同步拓扑。它不代表所有平台组合都已经完成互操作验证，也不代表当前支持任意后台任务的自动调度或运行时热迁移。

### 检查和运行 Flutter App

从 `apps/flutter/app` 执行：

```powershell
fvm install --skip-pub-get
fvm dart pub get --enforce-lockfile
fvm flutter analyze
fvm flutter test
fvm flutter run -d windows
```

`windows` 只是示例设备名；移动端、Linux、macOS 和 OpenHarmony 需要相应平台工具链。Flutter App 的本地运行只验证一个 CoreNode；跨设备验证仍需要另一个 CLI 或 Flutter CoreNode 完成配对、加入 Space 和任务交接。

### 构建 Web Access bundle

从仓库根目录执行：

```powershell
.\.venv\Scripts\python.exe tools\build_scripts\build_flutter_web_access.py --base-href /
```

生成的 bundle 位于 `apps/web_access/build/bundle`，并会同步到 Flutter 原生资源。它是 Web Access 的前端资源，不是中心后端，也不会单独创建一个跨设备调度器。

Flutter Web 开发不能直接依赖 `fvm flutter run -d edge` 提供跨源隔离响应头。推荐使用 Web Server 加隔离代理：

```powershell
# 终端一：apps/flutter/app
fvm flutter run -d web-server --web-hostname 127.0.0.1 --web-port 4835

# 终端二：仓库根目录
node tools/dev_web_access_proxy.mjs --upstream-port 4835 --listen-port 4836
```

然后打开 `http://127.0.0.1:4836`。代理只用于开发环境，会转发 Flutter 的 HTTP 和调试 WebSocket，并补充跨源隔离响应头；它不是产品中心网关。

### 本机构建 App 和 CLI

从仓库根目录执行环境检查：

```powershell
.\.venv\Scripts\python.exe tools\build_scripts\build_local.py --products all --cli-arches host --check
```

检查通过后构建当前主机可用的 App 和 CLI：

```powershell
.\.venv\Scripts\python.exe tools\build_scripts\build_local.py --products all --cli-arches host
```

只构建 App 或 CLI：

```powershell
.\.venv\Scripts\python.exe tools\build_scripts\build_local.py --products app --cli-arches host
.\.venv\Scripts\python.exe tools\build_scripts\build_local.py --products cli --cli-arches host
```

构建成功只说明当前产品面和平台工具链通过了对应检查，不代表 Host 能力完整、多节点同步可用、所有平台组合已验证或运行时支持热迁移。

### 预发布构建和发布

预发布版本、Git tag、更新通道、平台资产名称和发布脚本见 [`docs/release-versioning.md`](docs/release-versioning.md)。常用构建范围如下：

```powershell
# CLI/TUI
.\.venv\Scripts\python.exe tools\release\build_release.py --scope cli

# Flutter App
.\.venv\Scripts\python.exe tools\release\build_release.py --scope app

# App 和 CLI/TUI
.\.venv\Scripts\python.exe tools\release\build_release.py --scope full
```

这些资产对应 CoreNode 客户端或访问面，不对应中心 Server。`build_release.py` 只生成并暂存资产，不负责上传；发布前请阅读 [`BUILDING.md`](BUILDING.md) 中的签名、跨平台构建和 `publish_dist.py` 说明。

## CLI 使用入口

CLI 的完整命令列表以 `operit2 --help` 和 `operit2 cli` 输出为准。根 README 只保留能体现节点协作路径的常用入口，避免命令参数和实现同时变化时产生两份不一致的文档。

### 节点、配对和 Space

```powershell
# 当前节点
operit2 cli identity current
operit2 cli version
operit2 cli host show

# 节点监听、发现和配对
operit2 cli link serve --bind <addr:port> --token <strong-token>
operit2 cli link discover
operit2 cli link connect <url> --token <token> --save <name>
operit2 cli link sessions

# Space 成员关系
operit2 cli link space show
operit2 cli link space status <device-id>
operit2 cli link space join <session-name>
operit2 cli link space leave

# 某个节点的 Web Access 访问面
operit2 cli web open --bind 127.0.0.1:37194
operit2 cli web status
operit2 cli web close
```

`link serve` 的监听角色不等于中心 Server，`link connect` 的配对不等于加入 Space，`web open` 也只打开某个 CoreNode 的访问面。发起节点的权限不会传给目标节点，目标节点会重新检查自己的 Host 和工具边界。

### Agent 上下文和本地能力

```powershell
# 对话
operit2 cli chat new
operit2 cli chat list
operit2 cli chat shell
operit2 cli chat send --chat <chat-id> "hello"

# 模型和工作区
operit2 cli model provider-list
operit2 cli model list
operit2 cli workspace list
operit2 cli workspace commands <chat-id>

# 工具和节点侧扩展
operit2 cli tool list all
operit2 cli plugin list
operit2 cli package list
operit2 cli skill list
operit2 cli mcp list

# 本地模型和语音
operit2 cli local-models catalog
operit2 cli stt provider-list
operit2 cli tts config list
```

Agent 的任务交接由 Core 内部的 Binding、NodeRouter 和 continuation 路径负责；CLI 不建立另一套远程 Proxy 协议。CLI 支持面向脚本的 JSON 输出；具体命令是否支持 `--json` 以及参数格式，以该命令的 `--help` 和当前实现为准。

### 本地备份和同步的区别

```powershell
operit2 cli export snapshot <path>
operit2 cli import snapshot <path>
operit2 cli backup create <snapshot-zip-path>
operit2 cli backup restore <snapshot-zip-path>
```

`snapshot` 和 `backup` 是本地导入、导出或恢复工具，不等于 Space 的持续分布式同步；Space 同步由 CoreNode 的同步服务和已声明的数据范围负责。

## 权限与安全边界

跨设备协作包含身份信任、Space 成员关系和节点本地执行三种不同边界：

| 边界 | 作用 | 不代表 |
| --- | --- | --- |
| Identity / Pairing / Session | 证明节点身份并建立直接可信连接 | 不代表自动加入 Space，也不授予目标 Host 权限 |
| Space Membership | 确定协作范围、同步范围和可达节点 | 不代表共享文件系统、共享权限或数据不会形成副本 |
| Host Authorization | 说明目标节点实际拥有的系统能力 | 不会因远程调用或 AI 模式而提升权限 |
| AI Capability Limit | 限制当前 Agent 可启动的工具能力 | 不会创造 Host 没有的能力 |
| User Tool Approval | 对具体 AI 工具调用进行批准 | 不等于批准整个 ToolPkg、MCP server 或 Host |

工具执行从外到内遵循四层边界：

```text
0. App Runtime Sandbox      外部的 VM、容器、系统账号或系统应用沙盒
1. Host Authorization       当前 Host 实际拥有的系统能力
2. AI Capability Limit      用户为 AI 选择的能力模式
3. User Tool Approval       对具体 AI 工具调用的批准
```

当前用户可见的 AI 能力模式为：

- `ReadOnly`：允许读取；写操作需要用户批准。
- `WorkspaceWrite`：允许读写当前工作区；超出工作区或其他受限写操作需要用户批准。
- `Full`：在 Host 已有权限范围内允许读写，不表示提权，也不能绕过操作系统权限。

Web Access token 是访问某个 CoreNode 的凭据，PeerLink pairing 是节点间的身份信任，Space join 是加入同步和协作范围的动作。三者不能合并成一个笼统的“远程访问权限”。

远程调用到达目标节点后，会重新检查目标节点的 Host Authorization、当前 AI 能力模式、工具 effect 和用户批准状态。发起设备的管理员权限、文件路径权限或工具批准不会自动传给目标设备。

当前版本的应用内 sandbox 只定义了产品模型和 UI 位置，尚未形成可以承诺的真实执行隔离。特别是终端会话直接交给 Host shell，不能被描述为受到 VFS 路径检查保护的沙盒。

对外暴露 Web Access 或 Link listener 前，应限制监听地址和网络范围，使用强 token，并结合 TLS、防火墙和日志脱敏策略。不要将 API key、配对密钥、session、身份私钥或 Web Access token 提交到仓库、公开日志或截图中。

## 当前状态与预发布边界

| 层次 | 当前说明 |
| --- | --- |
| 产品愿景 | Agent 不被绑定在单一设备；多个 CoreNode 通过 Super Space 协作，让可同步上下文和任务意图跨终端延续，并调用各节点的本地软硬件能力。 |
| 当前基础 | CoreNode、Space、Binding、PeerLink、配对、发现、持久化同步和工具结果后的 continuation 已有基础实现。 |
| 当前限制 | 跨所有平台和设备的无缝 Agent 体验仍在演进；不同平台 Host 能力不同，部分 CLI 短生命周期操作不持有 Space 同步 worker。 |
| 明确非目标 | 当前不承诺模型请求、终端进程、浏览器会话或 Host 句柄热迁移，不承诺通用后台任务自动编排，也不承诺中心 Server 或多租户服务。 |

其他预发布注意事项：

- `2.0.0-preview.6` 的版本排序、tag 和更新通道遵循 [`docs/release-versioning.md`](docs/release-versioning.md)。
- 后续版本可能产生破坏性更新，Core API、生成的 Proxy、持久化结构、Link 协议和插件契约都可能调整；不要把当前数据目录或插件包格式视为稳定公共 API。
- Web Access bundle 需要先生成，部署服务器必须提供 `COOP`、`COEP` 和 `CORP` 响应头，否则浏览器端本地 STT/TTS 和相关 WebAssembly 能力可能无法启动。
- OpenHarmony 的云端发布工具链尚未具备可复现配置，当前应按本地构建路径处理。
- iOS 当前构建工作流产出未签名包；具备构建脚本不等于已经完成签名和商店发布。
- 当前仓库没有独立、可直接部署的 Server 产品；CLI 的 `link serve` 只是某个 CoreNode 的监听角色，CLI 的 Web Access 只是该节点的访问面。
- 应用内 sandbox 尚未实现，`Full` 不等于 root/admin，也不会绕过 Host Authorization。
- 请勿将当前预发布版本用于生产环境。

## 文档索引

- [构建和发布](BUILDING.md)
- [贡献指南](CONTRIBUTING.md)
- [平台 Host 实现边界](hosts/README.md)
- [版本、tag、渠道和资产规则](docs/release-versioning.md)
- [Core crate 边界](core/CRATE_BOUNDARIES.md)
- [Core 领域和 crate 结构](core/crates/README.md)
- [Core Application 组合根](core/crates/application/README.md)
- [Core 树和生命周期重构方向（演进目标）](docs/core-application-tree-refactor-plan.md)
- [Core 模块拆分目标结构（演进目标）](docs/core-module-crate-layout.md)
- [CoreNode、Space 和 Binding](docs/core-node-space-binding-architecture.md)
- [Link、Access 和 Space 调用边界](docs/link-access-architecture.md)
- [权限、AI 能力和 sandbox 边界](docs/permission-access-architecture.md)
- [插件开发入口](plugins/docs/README.md)
- [本地模型边界和模型目录](core/crates/provider/local-model/README.md)
- [Web Access 前端和部署要求](apps/web_access/README.md)

架构文档中标注为目标结构、演进方向或重构计划的内容，不代表所有平台均已实现。当前实际行为还应结合代码、命令的 `--help` 输出和平台构建结果判断。

## 参与贡献

欢迎提交问题、文档改进和代码贡献。开始前请阅读 [`CONTRIBUTING.md`](CONTRIBUTING.md)，其中说明：

- Rust Core、Host、Flutter、CLI 和构建工具的改动边界。
- 本地检查、平台验证和 Pull Request 要求。
- DCO 签署要求、第三方许可证和安全问题报告方式。
- 项目的开源贡献许可与商业化边界。

涉及跨设备能力的改动还应保持以下架构不变量：

- Host 能力和系统权限留在执行目标 CoreNode。
- Space 同步范围必须显式声明，不能把任意本地文件或缓存当成同步数据。
- 跨节点调用必须经过 CoreNodeRouter 和认证的 PeerLink。
- Flutter、CLI/TUI 和 Web Access 不重新承担远程 Proxy 或中心调度器职责。
- 工具结果持久化后才能交接下一轮 continuation；构建通过不等于跨平台协同已经验证。

## 许可证

本仓库项目主体的许可证以根目录 [`LICENSE`](LICENSE) 为准，当前为 **GNU Affero General Public License v3.0（AGPL-3.0）**。插件、Skill、ToolPkg、本地模型、Web bundle、Flutter third-party 目录、vendored 代码、第三方依赖和资源可能保留独立许可证；使用、分发或修改具体内容时，请同时查看对应目录、manifest、版权声明和来源许可证。

Space 同步的是业务数据副本和明确声明的运行时资源，不会改变用户数据、第三方模型或外部资源原有的版权和再分发条件。涉及网络服务部署时，请结合 AGPL-3.0 的适用义务和各组件许可证单独核对。
