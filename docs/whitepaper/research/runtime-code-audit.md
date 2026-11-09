# Runtime、上下文、扩展与平台代码审查

审查日期：2026-11-07（Asia/Shanghai）。代码基线：`1ef788456713e0502688dc0b7928511d98b813ec`。

本报告仅记录静态源代码与已有测试源的观察；没有运行编译、构建、测试或推送。下列文件行号对应审查时工作树，供正文交叉核对，不能用作测试通过声明。用户已有 `tools/prune_build_caches.py` 修改未接触。

## 1. 优先纠正的陈旧说法

1. **Native 插件 JavaScript 引擎当前是 V8。** `hosts/common/operit-host-native-scheduler/Cargo.toml:10-11,20` 默认 `javascript` feature 依赖 V8 152.2.0；`src/javascript_runtime.rs:33-40,69-75` 明确由 Native Host 管理 V8。不要沿旧文档或类名把实现称为 QuickJS。
2. **独立插件 context 不等于 OS 沙箱。** `hosts/common/operit-host-native-scheduler/src/javascript_engine.rs:20-43` 描述 affine workers 共享一个 V8 heap，插件持有独立 context 和 job queue。权限还取决于暴露的 Host bridge、插件身份、存储与路由边界。
3. **上下文摘要并非完整检查点机制。** 当前代码仍生成 `sender="summary"` 的 Markdown 消息，仍附加“【对话回顾】”，没有独立保留组与 boundary 元数据。`docs/compact-boundary-design.md` 有明确未完成段，不能整体作为实现证明。
4. **摘要存在异步快照路径。** 发送前可提交 Host-owned summary task 而不等待；回复后也有检查。不能声称摘要已完全收敛为同步 pre-turn/overflow/manual 三相位。
5. **记忆主要属于内建角色插件的业务。** 当前 `com.operit.character_cards` 自有 memory source、索引、召回和候选任务；不要把所有记忆语义说成 Rust Core 固有的统一认知内存。
6. **本地 LLM 与远程推理可分离于会话执行。** 对话、工具可留在调用节点，仅 prompt、参数与模型引用通过 inference Binding 路由到模型所在设备。不是必须先迁移整个聊天。
7. **AI 权限模式并非不可覆盖的 OS 强制限制。** ReadOnly 写操作和 WorkspaceWrite 越界操作可通过显式用户审批；Direct 插件/应用调用有意不经过 AI preflight。应分别解释 AI admission、Host 能力与平台沙箱。

## 2. Agent 执行管线

### 2.1 组成与抽象

- `core/crates/provider/services/src/chat/llmprovider/AIService.rs:23-43` 定义结构化请求；`:126-183` 定义模型服务 trait，包括 send、token 估算、连接检查等。具体 provider 可以返回明确的未实现错误；统一 trait 不表示所有模型具备同样工具或多模态能力。
- `core/crates/provider/services/src/chat/EnhancedAIService.rs:1284-1338` 将用户发送请求送入配置解析、provider 与工具循环；`:1459-1560` 将执行 context 注册与调度分开，以便取消覆盖尚未启动的工作。
- `core/crates/provider/services/src/chat/llmprovider/StructuredToolCallBridge.rs:41-75` 区分 provider 可见 function name 与实际 executable tool target，解析 package/CLI proxy envelope。工具协议兼容是 provider/bridge 的工作，不能推导出模型输出一定可靠。
- `core/crates/runtime/application/src/services/core/MessageProcessingDelegate.rs:1959-1970` 提交 user message；`:2144-2157` 接通持久化 assistant segment；`:2237-2266` 在流期间保存 snapshot；`:2436-2462,2524-2545` 在失败/完成时提交最终片段并传播提交错误。

### 2.2 模型—工具循环

`EnhancedAIService.rs:2641-2734` 的 `processStreamCompletion` 使用显式迭代循环，每一轮先检查 execution context 有效性，再把本轮分类为完成、继续或执行工具。`:2738-2913` 的 `completeResponseRound` 规范化并提取工具调用，把 assistant turn 放入本次内存历史，有工具则交给执行器，无工具则结束。`:2917-3060` 执行工具、记录待切换路由意图并发出结果；有 route-change target 时暂停当前循环。

`core/crates/tool/services/src/ToolExecutionManager.rs:358-513` 的工具批次是**串行执行**，逐个等待 invocation，整理最终展示/历史结果。不能因为一个模型响应含多个 tool call 就称为自动并行规划或并行工具执行。每个 invocation 可能有多个执行结果，batch 以最后状态和聚合文本形成对应终结结果。

### 2.3 取消与观察

- `EnhancedAIService.rs:203-217` 为每次发送提供单调取消门；`:3121-3141` 使 execution context 失效并取消 provider streaming。
- `core/crates/runtime/application/src/core/chat/AIMessageManager.rs:100-107,1125-1162` 以 operation identity 持有取消 token 与响应流，防止旧操作清理或取消更新操作。
- `core/crates/runtime/application/src/services/core/ChatSendStream.rs:93-140` 明确区分执行权与观察权：pull stream dispose 释放观察与唤醒等待，不具有取消模型执行的权限。
- 取消已等待的 future、终止观察或网络超时，都不能回滚已提交文件写入、终端命令或硬件副作用。

## 3. 上下文与摘要：当前实现

### 3.1 历史投影

`AIMessageManager.rs:684-751` 从最后一条 summary 开始组装 provider turns。assistant 的结构化 parts 按 Markdown、Thinking、ToolCall、ToolResult 等保留边界（`:753-810`）。角色隔离策略使用持久化 participant identity；缺少作者或展示身份会报错，不以当前显示名猜测历史归属（`:698-718`）。其他角色的普通发言可投影为带角色标签的 USER turn。

`core/crates/persistence/store/src/repository/ChatHistoryManager.rs:1701-1755` 用最后 summary 的 timestamp 查询后续历史，当前没有 `preservedFrom` 范围或单独保留组。摘要影响送入模型的活动上下文，不能理解成删除历史数据库或永久归档证明。

### 3.2 摘要内容

`AIMessageManager.rs:522-620` 的 `summarizeMemory` 找到上一 summary，只对其后的 user/ai 消息形成新摘要输入；调用会话配置对应模型生成摘要，再附“【对话回顾】”。`autoContinue` 加入继续任务提示。最后返回普通 summary Markdown 消息；代码使用字符串长度估算输入/输出 token，而非统一精确 tokenizer。

`core/crates/provider/services/src/chat/enhance/ConversationService.rs:414-649` 在摘要请求中处理 hooks 与 checkpoint 文本模板；`:542-624` 会校验必需标题/段落并在无法获得合格摘要时返回错误。模板约束只是文本结构约束，不能证明摘要事实完整或避免模型幻觉。

### 3.3 触发与执行

- `core/crates/foundation/model/src/ModelConfigData.rs:147,320-347` 当前默认 summary threshold 为 0.85，并兼容 ratio/旧百分比配置。
- `MessageCoordinationDelegate.rs:60-86` 的 `SummarySendPolicy` 将摘要总开关、persistTurn、背景发送、deferSummary 与 token guard 分别处理。
- `MessageCoordinationDelegate.rs:808-875` 发送前满足阈值时 `launchSummary`，本函数不等待 completion，dispatch 可继续。
- `:878-910` 回复后检查各当前 participant 的阈值并提交摘要。
- `:912-1013` 摘要由 Host scheduler 执行，有每 chat task 注册、共享 completion、取消与清理；不是 UI future 的生命周期。
- `:1016-1060` 对捕获历史生成 summary，按原 timestamp 邻居锚点插入，再重算稳定窗口。
- `:1063-1120` 手动摘要等待 completion。
- `:1133-1201` token-limit continuation 等待进行中的摘要、校验本 turn 仍有效、生成并等待 autoContinue summary，再保留原 executionLease 续跑同一已提交 user turn。

**尚不能写成实现的内容：** structured boundary metadata、独立保留组、基于 `originDeviceId:sequence` 的 boundary 接管水位验证、自动恢复 read-state、所有 route change 必先压缩、已删除异步摘要或“对话回顾”。这些需逐项找到生产调用点后才能升级状态。

## 4. 记忆系统是插件业务

### 4.1 所有权与数据

`plugins/packages/buildin/character_cards/src/storage/` 管理角色配置和 memory repository；`src/search/state.ts` 管理派生索引；`src/search/usearch.ts` 管理插件自有 USearch WASM。原始记录、source embedding 与派生索引应区别对待。

`src/search/usearch.ts:7-28` 通过 `ToolPkg.wasm.open("usearch", imports)` 装载模块与实例；`:45-68` 验证维度并执行带 allow/exclude 过滤的近邻查询；`:70-78` 支持指定候选精确重排与显式释放。

### 4.2 检索机制

`src/memory-search.ts:9-21` 从 Unicode 词项和汉字 bigram/unigram 派生最多 32 个词项；`:24-25` 只为当前 query 请求临时 embedding；`:28-34` 的词项/标签排名使用 importance、命中数与类似 reciprocal-rank 的权重；`:36-90` 融合关键词、标签、语义和单跳关系分数。seed 仅取前 10，关系传播不递归放大当前 query。`:49-55` 对 ANN 命中之外的强词项候选做有界精确重排。

`:94-123` 刷新派生索引、查询、仅 hydrate 当前页，并在 source version 改变时重试/最终报错。`src/search/state.ts:166-172` 对缺失/过期 source vectors 和 provider/dimension 变化显式报错并要求重建。启用 embedding 不等于可以自动补齐历史语料向量。

### 4.3 召回与任务

`src/memory-recall.ts:14-27` 从 authored user text 派生 query；`:30-37` 按明确 execution participant 与 chat 取 scope，普通 `model:chat` 不触发角色记忆；`:40-57` 将有界标题/内容/标签格式化为 `<memory_context>`；`:60-83` 在 `before_send_to_model` hook 注入临时模型请求，不持久化为聊天消息。应如实说明该可选 hook 的异常会记录 console error 并返回 null（`:76-80`）；业务直接查询/重建路径报错与可选 recall hook 的错误传播行为不同。

`src/memory-jobs/{hooks,producer,scheduler,analysis,embeddings}.ts` 承担持久候选、提取与重建。下列测试源对 producer ownership、lease 回收、候选版本与失败保留有针对性覆盖；本次没有执行这些测试。

不能把摘要、检索记忆、原始聊天、USER.md 与模型权重统称为一种“永久记忆”；它们的来源、持久化、同步与错误语义不同。

## 5. 工具权限与安全边界

### 5.1 AI admission

`core/crates/tool/services/src/tools/ToolPermissionSystem.rs:16-48` 定义 ReadOnly、WorkspaceWrite、Full。`AIToolHandler.rs:856-950` 实际执行逻辑：不允许的 effect 或越界会请求用户批准；用户拒绝时返回工具失败。WorkspaceWrite 对非文件 WRITE 且没有前一次 override approval 时也申请批准。因此 ReadOnly 是默认决策策略，可被用户批准覆盖，不能说其绝对无法写入。

`AIToolHandler.rs:952-1059` 的 workspace boundary 仅检查写路径，读取直接通过。Full 跳过这层 workspace 检查。跨 `node:` qualified path 由目标设备自身策略执行，本地 workspace 限制不代替远端授权。

`ToolPermissionSystem.rs:207-250` 的 ALLOW_SESSION 以 **tool.name** 存储在 runtime-session set，非路径/参数/单 chat 精确授权；无 interactive requester 时默认 DENY。

### 5.2 Direct 调用与可信扩展

`ToolExecutionManager.rs:285-292` 由 native `ToolExecutionPolicy` 区分 Ai 和 Direct。`AIToolHandler.rs:1095-1154` 仅 Ai 执行 exposure、AI hook 与 access preflight；Direct 是普通 JS/application 请求，跳过这些 AI 层。`:1199,1385` 是 Direct 调用点。白皮书应把插件信任、已授权桥接与 AI 审批分开，不声称所有 JS 内部调用都会再次弹审批。

`ToolExecutionManager.rs:67-107,187-245` 捕获并验证 authenticated extension context、task-local turn snapshot，避免只信任 JS 传入的身份或全局当前选择。`AIToolHandler.rs:1610-1634` 浮窗 route 核验当前 authenticated extension owner、启用状态和 route 归属；`:1765-1790` package route 同样携带 native owner。

### 5.3 Host 与 OS

`core/crates/foundation/host-api/src/HostManager.rs:139-175` 持有具体能力 trait handles 与环境描述。host-api README 的 capability tag 明确是描述性元数据，实际约束在 runtime/Host/OS。Host 带有某 trait 或 capability tag 不能视作获得系统权限、浏览器跨域豁免或 Root。

威胁模型至少包含：恶意模型输出/网页 prompt injection、恶意扩展、被接纳但被攻陷节点、凭据泄漏、非幂等副作用重放、资源耗尽。现有静态检查不能证明抵抗任意插件攻击或多租户对抗；独立 context/worker 并不是独立 OS 安全域。

## 6. 扩展协议与引擎

### 6.1 ToolPkg 与 JavaScript

`core/crates/plugin/javascript-bridge/src/javascript/JsEngine.rs:309-377` 通过 HostJavaScriptRuntimeHost 创建并调度 execution state；`:397-620` 处理 cancel、deadline 与 runtime release。Host trait 承担引擎选择，而非 Rust provider 固定某 JS 引擎。

Native V8 的 `javascript_engine.rs:20-43,126-163` 分别管理共享 isolate 和独立 realm/microtask queue；`javascript_runtime.rs:69-90` 创建 affine state 与任务通道。Web 的 `hosts/web/src/javascript_runtime.rs:132-193,431-466` 经浏览器 worker 消息与 shared memory 调用；`apps/flutter/app/web/runtime/src/operit_javascript_runtime.ts` 由浏览器原生 JS 引擎执行。浏览器取消可能终止 worker；不能把 native realm 保留和 Web worker 销毁说成完全相同的恢复语义。

### 6.2 WASM

生产 `core/crates/plugin/sdk/src/toolpkg/ToolPkgWasmApi.js:3-6,67-92` 以 package identity + module id 缓存 bytes 与编译模块，在 realm 内用 `WebAssembly.Module/Instance`；`:33-64` 保留实例 memory 并核验导出白名单和内存读写范围。模块可声明 imports，由调用方提供。USearch 就使用该接口。

SDK 同时有 `ToolPkgWasmRuntime.rs:9-75` 的 scalar wasmi 路径（当前 wasm32 返回 unavailable）。这不能概括整个 ToolPkg WASM。当前审查未发现这一 scalar 路径配置 fuel、memory limiter；不可承诺所有 WASM 都有严格 CPU/内存配额或完整 WASI。

### 6.3 Skill / MCP

`core/crates/tool/services/src/tools/skill/SkillManager.rs:156-181,385-430` 发现/读取 SKILL.md 并形成提示与资源路径。Skill 是可见知识/工作流内容，不是经过形式验证的可执行安全策略。

`core/crates/tool/services/src/tools/mcp_runtime/plugins/MCPBridgeClient.rs:43-117` 分别注册 local command 与 remote endpoint/token。`MCPStreamableHttp.rs:21-54,57-106` 通过 Host HTTP byte-stream 执行增量 POST，并跟踪 session；`:64-65` 保留 legacy SSE 传递差异；`:161-260` 解析分帧及响应 id。不应把支持 MCP 等同于其服务可信、拥有全部资源权限或完整支持协议所有扩展。

## 7. Local model 推理

`core/crates/provider/local-model/src/LocalLlmInference.rs:7-35` 按精确已安装 selection 解析驱动和文件路径；`:37-94` 校验 request、token/thread/context/batch 上限并拒绝 GPU 设置；`:98-141` 经过 C ABI 调用或返回未编译错误。

`core/crates/provider/local-model/native/inference.cpp:23-26,271-280` 用 mutex 串行化本地推理，按 engine/model key 更换单一缓存；`:292-295` 显式卸载权重。llama.cpp 和 MNN 为当前内嵌 CPU text drivers，不能宣称 GPU、多模态或并行多模型缓存已提供。

`core/crates/provider/services/src/chat/llmprovider/LocalModelProvider.rs:63-92` 把请求 stream 设为 false，经 runtime support 调 inference Binding，返回完整 text 后构造一块响应；不是 token streaming。Native generation 接口当前没有传入取消 token，不能保证 UI 取消会立即停止底层推理。

`core/crates/runtime/application/src/services/LocalLlmService.rs:12-32` 建立 `local-llm:{node}:{modelBinding}` Binding；`:35-94` 使用既有 route；`:97-127` 在 native spawn_blocking 执行，Web 本地执行返回明确错误。Web 仍可通过相同 Binding 调用 native 节点。模型文件/registry 是节点本地资产，不能由同步一个 model reference 推导出对端已安装权重。

## 8. Proxy、Web 与设备形态

- `core/crates/proxy/local/build.rs:25-29` 扫描 application 与 node facade；`src/lib.rs:22` 导入生成 dispatch；`:293-367` 提供同一 Call/Watch/Push Link client surface。Proxy 负责投影和 transport integration，不应承载第二份 runtime 业务规则。
- `apps/flutter/app/lib/core/bridge/PlatformCoreProxyWeb.dart:3-6` 当前 Web 默认为 `WebWasmCoreProxy`；`WebWasmCoreProxy.dart:13-30` 有独立 browser maintenance worker。浏览器可运行本地 WASM Core 是确实存在的工程路径，不能一概称 Web 只是远程显示器；Web Access 连接远端与 browser-local Core 仍应分开。
- `hosts/web/src/tools/storage/mod.rs` 与 `apps/flutter/app/web/runtime/src/operit_runtime_bridge.ts` 实现浏览器 Host 存储路径。README 对 OPFS、Web Locks、COOP/COEP/SharedArrayBuffer 的部署约束应列为浏览器特有条件，而非所有平台一样。
- Web terminal 以 v86 Linux guest 为工程路径，不是获得宿主 OS 任意终端。Host traits 完备不代表浏览器权限与 native 等价。
- `hosts/ios/README.md:5-24` 的终端通过 ARM64 Linux runtime 使用持久 rootfs 与同路径 bind mounts；iOS serial 无 native accessory provider（`:35-40`）。独立 runtime 的 macOS benchmark 不能当 iOS 真机或整个 Flutter App 的性能结论。
- `edge/boards/pb_sbc01_h3/src/app.rs:16-29` 明确启动完整 CoreApplication。应与 ESP32 轻量 capability node 分开。`edge/sdk/node`、固件与 Edge Services 不含完整聊天/ToolPkg 业务副本；能力节点当前不能作为任意聊天的完整 Core 执行器。

## 9. 已有测试源可支撑的证据类型

以下均为**静态读取测试源**，本轮未执行：

| 代码证据 | 测试名 / 行 | 能说明的设计意图 |
| --- | --- | --- |
| `core/crates/tool/services/src/ToolExecutionManager.rs` | `concurrent_execution_snapshots_remain_task_local`:844；`execution_snapshot_requires_exact_authenticated_identity`:881 | turn snapshot 与身份精确匹配 |
| `core/crates/tool/services/src/tools/AIToolHandler.rs` | `:2772-2789` 的 Ai 拒绝/Direct 允许断言；`:3028-3034` exposure 断言 | Ai 与 Direct 的真实边界 |
| `core/crates/provider/services/src/chat/EnhancedAIService.rs` | `cancelled_send_cannot_register_even_if_it_captures_the_latest_generation`:4012；`per_send_gate_stops_execution_before_provider_cancellation_completes`:4029 | 取消竞态防护 |
| `core/crates/runtime/application/src/services/core/ChatSendStream.rs` | `disposal_ends_pending_observation`:195；`rejects_snapshot_overflow_without_fabricating_a_part`:206 | observation 与 execution 分权、有界快照 |
| `core/crates/runtime/application/src/services/core/MessageCoordinationDelegate.rs` | `continued_and_background_tool_loops_keep_the_configured_token_guard`:1241；`disabled_summaries_and_ephemeral_turns_disable_both_checks`:1290 | 摘要触发策略 |
| `core/crates/runtime/application/src/services/core/MessageProcessingDelegate.rs` | `summary_continuation_receipt_preserves_original_submission`:3385；`summary_continuation_receipt_propagates_failure`:3419 | 续跑保留 user submission、传播失败 |
| `core/crates/runtime/application/tests/chat_summary_editing.rs` | `summary_memory_edits_are_persisted`:59 | summary 可编辑并持久化 |
| `plugins/packages/buildin/character_cards/tests/memory-database.test.mjs` | `database vectors belong to source records...`:50；`provider dimension changes require an explicit rebuild`:128；`warm ANN queries reuse WASM...`:198；`ANN filtering finds scoped memories...`:239 | 记忆向量、索引与过滤契约 |
| `plugins/packages/buildin/character_cards/tests/memory-jobs.test.mjs` | `producer ownership: independent devices process only the replies they produced`:554；`...remote rebuild is read-only...`:578 | 跨设备任务来源所有权 |
| `plugins/packages/buildin/character_cards/tests/memory-recall.test.mjs` | `prompt finalize hook skips non-character requests...`:48；`recall injects matched participant memories once per chat snapshot`:60 | 插件召回 scope 与去重 |
| `core/crates/runtime/application/src/services/LocalLlmService.rs` | `inference_routes_without_local_weights_or_chat_migration`:166；`unavailable_remote_inference_never_falls_back_to_this_device`:195 | 推理与聊天执行分离、不可达报错 |
| `core/crates/provider/local-model/src/LocalLlmInference.rs` | `nativeLlamaCppGeneratesText`:163；`nativeMnnGeneratesText`:179（real weights smoke）；`rejectsUnboundedOrInvalidInferenceRequests`:221 | 原生推理与参数约束，前二者是选择性真实权重用例 |
| `hosts/common/operit-host-native-scheduler/src/javascript_runtime.rs` | `execution_deadline_terminates_busy_v8_and_preserves_the_realm`:679 | V8 deadline 与 realm 生命周期 |
| `tools/tests/web_javascript_runtime.test.mjs` | `loads binary WASM through the production worker transport and retains instance memory`:99；`cancellation notifications wake a blocked caller and terminate a busy worker`:150 | 浏览器 JS/WASM 与中断契约 |

## 10. 可用于正文的评估与局限

当前证据足以描述模块边界、调用流程、状态结构和已有回归意图；不足以给出跨平台产品可靠性、恶意插件隔离、端到端任务成功率、统一尾延迟或大规模调度性能。推荐白皮书把评价分为：代码可追踪性表、已有测试源覆盖矩阵、待执行的故障注入/平台矩阵、待测性能方法。避免填充没有原始采样与固定环境的成功率和速度。

建议未来测量：模型首 token/完整响应、持久化 segment 延迟、工具审批等待、tool result 到下一模型请求的间隔、摘要耗时/压缩比/事实保留率、记忆召回 Recall@k/NDCG 与来源正确率、冷/热插件加载及 WASM 内存、Web worker 传输开销、native generation 取消响应、端到端 UI frame latency。所有指标需明确 baseline、设备、provider/model、语料、并发、样本数、百分位和失败分类。

## 附录 A：可改写进入白皮书正文的技术段落

以下为正文建议，不表示新增实现，也不含本轮未运行的测量结果。文中的“当前”均指本报告代码基线。

### A.1 执行运行时与能力适配

Operit2 将 Agent 应用的执行拆为模型服务、会话协调、工具执行与平台能力四个层次。模型服务通过 `AIService` 接口接收历史、工具描述与生成参数，并返回可观察的响应流。会话协调负责确定执行参与者和会话配置、提交消息、维护执行生命周期以及接续上下文。工具执行器将模型生成的工具描述解析为受类型与参数约束的调用，再由具体工具经 Host 接口访问文件、网络、终端或浏览器。Host 提供平台相关的资源句柄和错误语义，因此相同的 Core 操作可以在不同平台使用统一契约；实际能否完成操作仍取决于该设备的实现、系统授权与资源状态。

单次 Agent 任务由连续的模型响应轮组成。运行时在完成一轮响应后，判断是否存在待执行工具；存在时按当前工具暴露策略执行调用，将结果添加到后续模型输入，再开始下一轮。当前同一响应中的工具批次按序执行。代码中的迭代循环使已完成轮次的异步任务可以结束并释放相应状态，但这项实现选择不构成所有资源均无泄漏的证明。多个会话、模型 Provider 的并发配额与本地推理锁分别处于不同调度边界，不能以“支持多任务”概括为任意工具或推理后端均可并行。

执行与观察具有不同的所有权。会话执行由 native context、operation identity 和取消 token 管理；界面或插件取得的响应流是该执行的一个观察投影。关闭观察流使消费者结束等待并释放观察资源，不自动终止已经受理的模型或工具工作。显式取消会使后续轮次失效并请求停止相应流，但取消不等价于撤销已经发生的外部副作用。文件写入、终端程序、网络请求和硬件动作需要各自的结果记录和恢复策略，不能从一个通用取消按钮推导出跨系统事务回滚。

### A.2 历史、活动上下文与检索记忆

本文区分原始会话记录、活动模型上下文、摘要消息和检索记忆。原始记录以结构化消息及消息片段保存，为用户查看和后续历史投影提供来源。活动上下文是面向某次模型请求的投影，其内容受到当前参与者身份、历史隔离策略、摘要位置、工具协议与模型能力的共同影响。摘要是用来降低活动历史长度的模型生成内容；它可以保留任务目标、约束和已完成工作，但在没有独立事实验证时，不能视为原始历史的无损编码。检索记忆则由业务插件管理，可从持久来源中选择少量内容临时加入请求。四者分别处理保存、预算、压缩与召回问题，不能互相替代。

当前上下文投影从最近的 summary 消息开始，并保留其后的消息。assistant 消息中的普通文本、思考、工具调用和工具结果被重新映射为 Provider 所需的协议顺序。角色隔离使用持久化的参与者标识，而不以当前界面中的显示名推断作者；缺少必要身份时返回错误。这一规则将历史解释绑定到消息产生时的身份事实，降低重新命名或角色列表变化造成的歧义，但并不保证模型一定正确理解多参与者话语。

摘要触发依据配置的 token 占用比例或用户消息计数。当前发送前可以对捕获历史提交后台摘要，发送本身继续进行；回复后也可检查是否需要摘要。摘要任务由 Host 调度并具有显式取消与完成通知，其插入位置使用捕获时的消息时间戳邻居，以便避免直接覆盖并发产生的新记录。工具循环遇到上下文限制时，可以等待摘要完成、检查当前 turn 的有效性，再持有原执行租约继续同一 user turn。当前 summary 仍为 Markdown 消息，尚不包含独立保留组、可验证的摘要边界操作水位或完整资源检查点。因此“可继续会话”应理解为基于已保存上下文重新发起后续请求，不能称为模型进程或所有运行中资源的迁移。

角色记忆位于内建 `com.operit.character_cards` ToolPkg 内。该插件保存来源记录及其 embedding，并维护可重建的派生检索索引。检索结合 Unicode 词项与汉字片段、标签、USearch WASM 向量近邻，以及有界的一跳关系扩展。向量匹配与词项排名是不同的证据来源，当前实现根据用户权重融合分数，并对部分候选进行精确重排。索引校验源记录版本、embedding 提供者和维度；源向量不完整或过期时，查询要求显式重建。查询向量只服务于本次请求，不充当历史来源向量。上述机制为检索可追踪性提供工程基础，但其召回质量仍需在固定语料和标注数据上测量。

记忆召回 hook 在模型请求最终组装时，按明确的角色参与者、记忆所有者与会话去重范围查询，将有界结果作为临时 `memory_context` 加入输入。该内容不作为新的用户消息写回聊天。可选召回 hook 的失败目前会记录错误并放弃此次注入，因此正文应避免“每次请求必定成功装载记忆”之类绝对说法。记忆的直接查询、编辑与重建仍有各自的错误返回和持久任务状态。

### A.3 插件执行与平台异构

ToolPkg 将插件元数据、JavaScript 入口、资源、UI 与可选 WASM 模块组合为一个可管理扩展。插件的 JavaScript 执行经 `HostJavaScriptRuntime` 契约完成，具体引擎属于 Host。当前 Native Host 使用 V8，并为插件提供独立 context 与任务队列；浏览器 Host 使用专用 Worker 上的浏览器原生 JavaScript 引擎。两条路径共享上层调用契约，但中断与资源回收的具体机制不同：native 可以在引擎边界处理终止状态，浏览器可能终止整个 worker。独立 context 或 worker 有助于控制全局变量与生命周期，并不自动形成经过验证的恶意代码隔离边界。

WASM 模块通过插件声明及包身份读取，在所属 realm 内编译、实例化并保留 memory，API 核验公开导出与内存读写范围。插件可以为模块提供明确 imports，USearch 检索就是这一机制的实例。WASM 的线性内存与显式导入减少了接口歧义；插件对 Host 能力的访问仍由 JavaScript bridge、身份和授权共同决定。不能仅凭采用 WASM 就宣称具有统一 CPU 配额、完整 WASI 兼容或对任意扩展攻击的抵抗能力。

平台差异还体现在终端、存储和推理。浏览器本地 Core 由 WebAssembly 执行，文件与数据库依赖浏览器存储机制，终端使用 Linux guest 而不是宿主操作系统终端；其部署需要满足 shared memory 和跨源隔离等浏览器条件。iOS 的 Linux runtime 则处理特定指令集与 Linux ABI，并将应用有权访问的目录映射给终端；这不扩大 iOS 沙箱权限。完整 Linux 板卡可启动 CoreApplication，ESP32 能力节点主要提供原生设备服务和有界交互，不承担完整聊天与插件业务副本。统一协议因此意味着可组合的接口，而非各设备资源与系统权限相同。

### A.4 本地推理与执行位置的解耦

本地模型作为安装在某个 CoreNode 上的版本化资产管理，模型清单记录驱动、文件与校验信息。当前文本推理内嵌 llama.cpp 和 MNN CPU 后端，并在 native blocking worker 上运行；进程内互斥锁串行化推理，缓存随选中的 engine/model key 更换。模型权重、安装清单与派生缓存具有明确的设备所有权。空间中传播一个模型引用并不复制权重，也不证明其他设备能提供该模型。

每个可调用的本地模型对应 inference Binding。调用节点可以保留聊天、工具和会话持久化，只将推理请求路由到持有模型资产的节点。这为“计算位置”和“会话执行位置”提供了独立选择，但同时要求将 prompt 发送给所选推理节点，数据可见性应据此评估。当前 Provider 在完整推理结束后返回一段文本，没有逐 token 发送与 native generation 取消接口。远端推理节点不可达时返回错误；不能把界面的通用 streaming 或 cancellation 能力外推到这一后端。

### A.5 安全模型与证据边界

Operit2 的安全模型需要区分操作系统允许 Host 做什么、已认证调用者能够访问什么，以及 AI admission policy 对模型建议动作作何决定。ReadOnly、WorkspaceWrite 和 Full 是第三类策略；ReadOnly 默认阻止写效果，WorkspaceWrite 对文件写入检查 workspace，对非文件写入申请批准，用户也可以显式批准本次或本会话的越界动作。当前 session approval 以工具名匹配，并非针对每组参数签发的能力票据。普通应用或插件的 Direct 调用则有意跳过 AI preflight，由其自身可信接口与 Host 边界约束。任何对“统一工具审批”的描述都应带上这一区分。

静态代码能够证明存在何种分支、数据字段、调用顺序和校验入口，已有测试源能够证明维护者针对哪些情形写出了断言；两者都不能代替当前平台上的测试执行、长期运行观察或对抗评估。本文因此将模块机制作为已实现内容，将可重复的评价方案与尚未验证的保证单独列出。后续应以持久化后的会话续跑、取消竞态、权限覆盖、插件资源耗尽、索引失配与平台 Host 差异作为故障注入场景，并公开设备、版本、输入、样本数、延迟分布与失败结果，而不是使用没有实验协议的整体可靠性或性能形容词。
