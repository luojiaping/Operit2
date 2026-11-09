# 阶段三：研究框架与技术模型

| 项目 | 内容 |
| --- | --- |
| 日期 | 2026-11-10 |
| 代码基线 | upstream/main `0c53fae1811b1731e43a0386bd4f42106fe422e7` |
| 形式化工具 | TLA+，TLC 模型检查器 v1.7.4（`tla2tools.jar`，SHA-256 `936a2620…01e050e88`），OpenJDK 21 |
| 产物 | [`model/TurnHandoff.tla`](model/TurnHandoff.tla)、[`model/experiments.txt`](model/experiments.txt)、[`model/cfg/`](model/cfg/)、[`model/results/`](model/results/)、[`model/run_tlc.sh`](model/run_tlc.sh)、[`model/trace_summary.py`](model/trace_summary.py) |
| 证据性质 | 有界穷举模型检查 [T]，加上与之对照的源码事实 [C]。没有运行项目本身的构建或测试 |

## 1. 模型的对象与抽象

模型只描述一个会话 k 的执行位置。它刻画的是 Binding 记录、本地执行保护、路由解析、交接过程、持久事实与环境故障的交错，不刻画模型输出的内容、工具的具体语义与界面。

| 抽象 | 模型中的表示 | 舍弃的细节 |
| --- | --- | --- |
| CoreNode | 节点 1..N；节点 1 最初拥有会话 | Host 能力差异；身份与配对 |
| Binding 操作 | 记录 `[owner, gen, ts, origin, kind]`，每个节点有持久日志 `log`、内存缓存 `cache` 与已应用版本 `ver` | 来源序号 sequence（同一节点的 ts 已严格递增，可以替代它作为次序） |
| 冲突规则 | `current`：按 `(createdAt, originDeviceId)` 比较；`fenced`：按 `(generation, createdAt, originDeviceId)` 比较 | —— |
| 本地执行保护 | 每个节点一个布尔 `lease` | revision 保护与执行 id |
| 回合 | `run[n] = g` 表示 n 正在以代次 g 执行；回合结束时产生一条带代次的事实 | 回合内部的多轮模型请求与工具调用 |
| 持久事实 | 事实 `[gen, id]`，每个节点有持久集合 `facts` | 事实的内容与顺序 |
| 同步 | 两个节点之间的一次双向完整交换：日志取并集，缓存按冲突规则更新 | 分页、收据空洞与 owner 就绪 |
| 生命周期调用 | `BeforeChangeRoute`、提交前同步、即时安装视为同步的 RPC 步骤；`AfterChangeRoute` 视为异步消息，可以延迟或重复投递 | 实际 RPC 的超时与错误码 |
| 环境 | 节点崩溃与重启（易失状态丢失，持久状态保留）、链路断开与恢复、时钟偏差（初始时钟可以不同） | 消息永久丢失；拜占庭行为 |

## 2. 性质

| 模型中的性质 | 含义 | 对应阶段一的性质 |
| --- | --- | --- |
| `Mutex` | 任一时刻至多一个节点在执行该会话 | S1 ∧ S2 的可观察后果 |
| `SingleGen` | 每个代次只由一个节点推进 | S1 |
| `NoStaleStart` | 不会在比已开始的代次更旧的代次下开始执行 | S2 |
| `NoUnfencedCommit` | 节点得知自己不再是 owner 之后，不再提交该回合的结果 | S2 |
| `FactsComplete` | 代次 g 的每次执行都能看到所有更早代次的已提交事实 | S3 |
| `ContOnce` | 每个代次至多启动一次续跑 | S4 |
| `ConvergedRoutes` | 所有节点在线且连通、日志相同、没有在途消息时，所有节点选中同一条 Binding，并且路由都能解析到 owner | 收敛与可用 |
| `NoProgressWhileOwnerDown` | 最新代次的 owner 下线期间，任何节点都不能开始执行 | L1 的否定。成立即说明“阻塞” |
| `SingleGenUnlessTakeover`、`ForkOnlyAtTakeover` | 违反 S1 或 S3 的情形，只出现在显式接管之后，并且可以由代次标签识别 | 接管策略下的可检测性 |

S5（效果可判定）依赖工具语义，不在模型之内，由 §7 以设计模型处理。

## 3. 动作与源码的对应

| 模型动作 | 源码（upstream/main 0c53fae18） |
| --- | --- |
| `UserSend`，以及 `Route` 的逐跳解析 | `core/crates/node/runtime/src/CoreNodeRouter.rs:976-1024`（`callSpaceWithOrigin`：每个节点按本地 Binding 决定本地执行或转发） |
| `AgentSwitch` | `core/crates/runtime/application/src/services/core/MessageProcessingDelegate.rs:2642-2700`（提交 assistant 段，构造续跑上下文）；`:987-994`（在提交 Binding 之前释放执行保护） |
| `UserChange` | `core/crates/node/runtime/src/RuntimeRemoteLinkService.rs:933-940`（`changeChatExecutionDevice`，在发起节点上执行 `changeRoute`） |
| `Probe` | `RuntimeRemoteLinkService.rs:976-984`；`core/crates/runtime/application/src/services/ChatServiceCore.rs:859-875`（取得执行保护后立即释放） |
| `PreSync` | `RuntimeRemoteLinkService.rs:1014-1042`；`core/crates/node/runtime/src/SpacePersistenceSyncService.rs:495-509` |
| `CAS` | `core/crates/persistence/store/src/CoreNodeBindingStore.rs:180-211`（只比较 `expectedNodeId`；代次加一） |
| `Install` | `RuntimeRemoteLinkService.rs:1110-1130`；`CoreNodeBindingStore.rs:261-281`（`applyImmediateOperation` 同样经过 `shouldApplyOperation`） |
| `SendAfter`、`DeliverAfter` | `RuntimeRemoteLinkService.rs:1082-1105, 1134-1166`（目标为 `CORE_INTERNAL_TARGET`，经 `callNodeSpace` 发送）；`ChatServiceCore.rs:796-856`（目标端以传入历史续跑）；`MessageCoordinationDelegate.rs:486-546`（续跑在调用返回前一直等待回合发送结束） |
| `DeliverAfter` 的 `keep` 分支 | `core/crates/node/runtime/src/route_forwarding.rs:82-86, 113-124`（非 `device.tools`/`edge.*` 目标在特定传输错误下经另一首跳重提） |
| `current` 的冲突次序 | `core/crates/persistence/store/src/SyncOperationStore.rs:292-326`（`SyncOperationOrder` = `createdAt, originDeviceId, sequence`）；`:1060-1091`（`shouldApplyOperations`）；`:1816`（`createdAt` 取 `currentTimeMillis()`） |
| `Recover` | `CoreNodeBindingStore.rs:283-320`（`materializeBindingRecords` 选出次序最大的操作） |
| `Sync` | `SpacePersistenceSyncService` 的后台同步轮次（2.0 C22） |

模型中的 `Relinquish`、`DeliverHandoff`、`DeliverXfer` 与 `TakeoverAt` 属于本文提出的协议，代码中没有对应实现。

## 4. 当前实现的检查结果

实验参数见 `model/experiments.txt`，每个实验只打开复现该异常所需的行为。TLC 按广度优先搜索，给出的反例轨迹是该配置下最短的。

| 编号 | 实验 | 违反的性质 | 最短反例长度 |
| --- | --- | --- | ---: |
| X1 交接窗口 | `cur_x1_window` | `Mutex` | 10 |
| X2 第三方切换 | `cur_x2_thirdparty` | `Mutex` | 7 |
| X3 重复续跑 | `cur_x3_duplicate` | `ContOnce` | 13 |
| X4 同代双 owner | `cur_x4_samegen` | `SingleGen` | 11 |
| X5 历史缺失 | `cur_x5_history` | `FactsComplete` | 8 |
| X6 时钟偏差 | `cur_x6_skew` | `ConvergedRoutes` | 17 |
| X7 过期续跑 | `cur_x7_stalecont` | `NoStaleStart` | 17 |
| X7（打补丁后） | `cur_x7_patched` | `ContOnce` | 18 |
| X1 补丁对照 | `cur_x1_patched` | 无违规；穷举完成，生成 119 个状态，其中不同状态 57 个 | —— |

每项检查用时 3–10 秒。最短反例长度由广度优先搜索决定，两次独立运行完全一致。违规实验在找到第一个反例时停止；8 个 worker 并行时，停止前探索的状态数随线程调度变化（例如 X2 两次运行分别为 821 与 594 个不同状态），所以不作为结果报告。

### 4.1 反例轨迹

以下以“步号 动作：效果”的形式给出 TLC 轨迹的要点，完整轨迹见 `model/results/*.log`，可以用 `trace_summary.py` 重现摘要。

**X1 交接窗口（2 个节点）。**
1. 节点 1 开始回合（g1）。
2. 模型调用 `switch_core(2)`；回合结果提交，执行保护释放。
3. `BeforeChangeRoute` 探测节点 1：空闲，通过。
4. 节点 1 上来了一条新的用户消息。本地 Binding 仍指向节点 1，于是以 g1 开始新回合。
5. 提交前同步；节点 1 本地比较写入 (2, g2)；即时安装到节点 2。
6. `AfterChangeRoute` 到达节点 2，节点 2 开始续跑。此时节点 1、2 同时执行。

**X2 第三方切换（3 个节点）。**
1. 节点 2 上的用户把执行设备改为节点 2。
2. 探测原 owner 节点 1：空闲，通过。
3. 节点 1 上的用户发送消息，节点 1 开始回合。
4. 节点 2 本地写入 (2, g2)。
5. 节点 2 上的用户发送消息，节点 2 开始回合。节点 1 的视图尚未更新，两者并发。

**X3 重复续跑（2 个节点）。** 1→2 交接正常完成，节点 2 的续跑开始并结束；`AfterChangeRoute` 被再次投递（例如响应丢失后经另一首跳重提），节点 2 的执行保护已经空闲，于是第二次以同一份传入历史续跑。

**X4 同代双 owner（3 个节点）。** 节点 2、3 上的用户先后把执行设备改为各自所在的节点。两次探测都通过（节点 1 空闲），两次比较写入都基于 (1, g1)，得到 (2, g2) 与 (3, g2)。两边随后都在 g2 下执行。代次因此不是全网唯一的执行身份。

**X5 历史缺失（3 个节点）。** 节点 1 的回合结束并提交了事实，随后节点 2 上的用户把执行设备改为节点 2。提交前同步只在发起者与目标之间进行，这里两者都是节点 2，节点 1 的事实没有同步过来，因此节点 2 在缺少它的情况下开始执行。

**X6 时钟偏差（3 个节点，打补丁）。** 节点时钟为 (3, 2, 2)。
1. 节点 1 交接给节点 2，记录 (2, g2) 的 `createdAt = 3`。
2. 节点 2 交接给节点 1，记录 (1, g3) 的 `createdAt = 2`。
3. 安装 g3 时节点 1 已崩溃。节点 3 同步后，按 `createdAt` 选中 g2；节点 1 重启后从日志里同样选中 g2。
4. 三个节点日志相同，但节点 1、3 认为 owner 是 2，节点 2 认为 owner 是 1。路由在 1、2 之间循环，会话不可达，代次从 g3 回退到 g2。

**X7 过期续跑（3 个节点）。** 第一次交接 1→2 的 `AfterChangeRoute` 在途中被延迟；第二次交接（1→3，g3）先完成，节点 3 开始续跑。迟到的第一条消息随后到达节点 2，节点 2 的视图仍为 g2，于是在旧代次下开始执行。打补丁后的变体中，迟到消息按 Binding 被路由到当前 owner，以第一次交接的旧历史又启动了一次 g3 续跑。

### 4.2 最小补丁的作用范围

`HoldLease` 让源端持有执行保护，直到 Binding 提交，不再提前释放。`cur_x1_patched` 在 X1 的配置下穷举完成、没有违规，说明这个补丁关闭了 X1 的窗口。但 X6 与 X7 的检查都是在打开补丁的条件下得到反例的：X2–X5 与这个窗口无关，X6、X7 也不能靠它修复。单靠调整释放时机不足以得到 S1–S4。

## 5. 带代次隔离的续跑协议（FCP）

### 5.1 机制

| 机制 | 内容 | 针对的异常 |
| --- | --- | --- |
| M1 代次优先合并 | Binding 冲突次序改为 `(generation, createdAt, originDeviceId, sequence)`；即时安装与重启重建使用同一次序 | X6 |
| M2 仅 owner 让出 | 只有本地视图显示自己是 owner 的节点，才能写入下一代次；其他节点发起的切换变为发给 owner 的转移请求 | X2、X4、X5 |
| M3 持有保护让出 | owner 在仍持有执行保护时写入 (target, g+1)，写入之后再释放；源端此后的本地请求按新 Binding 转发 | X1 |
| M4 事实随交接传递 | 交接消息携带让出时 owner 已提交的事实，目标端先持久化，再开始续跑 | X5，以及 S3 |
| M5 按代次幂等续跑 | 交接消息携带代次；目标端持久记录已接受的最高代次，只在“视图中 owner 是自己、代次等于消息代次、尚未接受”时开始续跑 | X3、X7 |
| M6 提交时自隔离 | 回合结果只有在节点仍是该代次 owner 时才提交，否则丢弃并标记 | 分区与接管下的 S2 |

M5 所需的持久字段已经存在：消息模型与数据库中有 `completedExecutionGeneration`（`core/crates/foundation/model/src/ChatMessage.rs:31`），当前只被复制，从未写入实际代次。设计文档 §7.1 的去重意图因此可以落在既有 schema 上。

FCP 不引入分布式租约，也没有新的放置概念。代次本身就是隔离令牌：它已经存在于 Binding 记录中，本地执行保护也已经存在。这与架构文档“不引入 Lease、Placement”的约束一致（`docs/core-node-space-binding-architecture.md:34-35`）。

### 5.2 验证结果

| 实验 | 设置 | 结果 |
| --- | --- | --- |
| `fen_safe` | 3 个节点；智能体切换与用户切换都打开；允许时钟偏差、1 次崩溃、1 次断链、1 次重复投递；不允许接管 | 穷举完成，8 条性质（`ConvergedRoutes`、`Mutex`、`SingleGen`、`NoStaleStart`、`NoUnfencedCommit`、`FactsComplete`、`ContOnce`、`NoProgressWhileOwnerDown`）全部成立。生成 34,499,016 个状态，其中不同状态 6,335,440 个，最大深度 21，用时 4 分 8 秒 |
| `fen_takeover_mutex` | 同上，允许用户接管 | `Mutex` 被违反（4 步）：节点 1 执行中，链路 1–2 断开，节点 2 的用户确认接管 |
| `fen_takeover_progress` | 同上 | `NoProgressWhileOwnerDown` 被违反（3 步）：节点 1 崩溃，节点 2 接管并开始执行 |
| `fen_takeover_safe` | 同上；检查 `SingleGenUnlessTakeover`、`NoUnfencedCommit`、`ForkOnlyAtTakeover`、`ContOnce` | 穷举完成，4 条性质全部成立。生成 163,747,786 个状态，其中不同状态 36,017,850 个，最大深度 22，用时 21 分 24 秒 |

这些结论只在上述界限内成立（N = 3、代次 ≤ 3、发送 ≤ 2、交接 ≤ 2、崩溃 ≤ 1、断链 ≤ 1、重复 ≤ 1）。它们是有界模型检查的结果，不是对任意规模的证明，也不是对实现的验证。

### 5.3 安全与可用的取舍

`fen_safe` 中 `NoProgressWhileOwnerDown` 成立，而接管实验中它被违反。两组结果合起来，说明了在本模型中不可同时兼得的两件事：

- **不允许接管**：S1–S4 全部成立，但 owner 下线或被隔离时，会话无法推进。
- **允许显式接管**：会话可以继续，但会出现 `Mutex` 违规，即分区期间两个节点同时执行。

这与异步系统中的一般结论一致：节点无法区分“owner 已崩溃”与“owner 被分区”[GL02, FLP85]。依赖多数派的方案（PS03 的每阶段共识、Paxos 的 quorum [Lam98]）要求至少三个可以投票的节点；租约要求有界的时钟偏差 [GC89]。FCP 选择“默认阻塞，接管由用户显式确认”，并把接管的代价限制在可检测的范围内（§5.4）。

### 5.4 接管下的可检测性

`fen_takeover_safe` 在 §5.2 的界限内穷举完成，以下四条性质全部成立：
- 一个代次由两个节点推进的情形，只出现在某次接管之后（`SingleGenUnlessTakeover`）；
- 节点得知自己已被取代之后，不再提交结果（`NoUnfencedCommit`）；
- 缺失事实一定能由某次接管解释（`ForkOnlyAtTakeover`）；
- 续跑仍然至多一次（`ContOnce`）。

因此在本模型中，接管的代价被限制为“分区期间的并发执行”，以及“带旧代次标签、因而可识别的分叉事实”。续跑重复与静默提交没有出现。

## 6. RQ1：回合边界上的状态划分

| 状态类别 | 例子 | 回合边界上的去向 | 当前机制 |
| --- | --- | --- | --- |
| 持久事实 | 消息、assistant 段、工具调用与结果 | 随同步复制；FCP 还随交接传递 | 同步；`runtimeChatHistory` 随请求传递 |
| 执行配置 | 参与者、模型覆盖、提示类型、回合选项 | 随续跑上下文传递 | `CoreRouteResumeContext`（`core/crates/tool/services/src/runtime_support.rs:21-35`） |
| 位置与授权 | Binding、成员、能力 | 复制与控制面传播 | Binding 同步；控制交换 |
| 节点资源 | 工作区挂载、已安装模型、凭据、Host 权限 | 不迁移，由目标独立满足 | 目标端重新解析配置与工作区 |
| 暂态执行 | 在途模型请求、PTY、WebView、MCP 会话、JS realm | 不存在（回合边界上没有在途请求），或留在源端 | 不迁移 |
| 上下文中的环境陈述 | “终端 3 中的开发服务器正在运行”“刚修改了 a.rs” | 作为文本随历史迁移，但在目标端可能为假 | 未处理 |

前五类说明：在回合边界上，执行所需的控制状态可以由持久事实与有界配置完整表示，交接因此属于弱迁移 [CPV07]。最后一类说明弱迁移的代价：迁移的是数据，被陈述的环境却没有随之迁移。

**定义（信念—环境一致性）。** 设 H 为续跑所用的历史，E(n) 为节点 n 上可观测的环境。H 中关于环境的陈述集合记为 Claims(H)。在目标节点 t 上续跑时，要求对每个 c ∈ Claims(H)，要么 c 在 E(t) 上成立，要么续跑上下文中包含一条说明 c 可能不成立的显式提示。

当前实现不满足这一要求。目标端的续跑请求 `messageText` 为空、`isResume` 为真（`core/crates/runtime/application/src/services/core/MessageCoordinationDelegate.rs:519-537`），系统提示只在附件场景下说明“先检查当前节点”（`core/crates/provider/services/src/chat/config/SystemPromptConfig.rs:555-557`），`switch_core` 的说明也没有列出不随迁移的资源（`SystemToolPrompts.rs:842-851`）。

**设计假设 [H]：环境差异说明。** 续跑开始时，目标端由运行时生成一条结构化说明，由运行时本身判断，不依赖模型。说明包括：
- 执行节点从 A 换成了 B；
- 源端仍持有、不会随迁移的会话资源清单，如终端会话、浏览器会话与 MCP 会话；
- 工作区路径在 B 上能否解析；
- 相关文件在 B 上的版本是否与源端一致。

这与 Tam26 所指的“观察与持久的混同”相对应：运行时知道哪些资源是暂态的，模型不知道。评价方法见阶段五第 11 节。

## 7. RQ4：外部效果的设计模型

现有效果分类只有两档：`ToolEffect = {READ, WRITE}`（`core/crates/tool/services/src/ToolExecutionManager.rs:776-779`）。`switch_core` 本身注册为 `WRITE`（`core/crates/tool/services/src/tools/ToolRegistration.rs:214`）。

**设计假设 [H]：四类效果。**

| 类别 | 定义 | 重试 | 交接边界上的要求 |
| --- | --- | --- | --- |
| E0 观察 | 不改变外部状态 | 可以 | 结果可能陈旧（§6） |
| E1 幂等 | 带运行时分配的效果身份，重复执行与执行一次等价 | 可以，但必须重用同一身份 | 身份与状态已持久化 |
| E2 可补偿 | 存在已知的补偿操作 | 不自动重试；失败时补偿 | 补偿信息已持久化 |
| E3 不可逆 | 付款、发信、设备动作等 | 永不自动重试 | 结果必须是“已完成”或“已确认失败”；“未知”状态阻止自动交接，交由用户处理 |

规则一：效果身份在调用之前由运行时分配并持久化，不能从模型重新生成的请求中推导。LLM 在恢复后会重新合成内容不同的请求，服务端的幂等键因此会失效 [ACR26]。

规则二：交接边界的定义需要加强。原定义是“工具结果已持久化、下一次模型请求尚未开始”，现在改为：工具结果已持久化，并且所有 E3 效果的状态已确定。超时的 E3 调用即使已经记录了“超时”这一结果，其效果状态仍是未知，不构成可以自动交接的边界。

这一模型与 Atomix 的效果类别 [Atx26]、Temporal 的幂等键要求 [Tmp26]、Sagas 的补偿 [GS87] 一致，差别在于本文把它与执行位置的转移联系起来：效果身份必须随交接传递，目标端不得为同一意图分配新身份。

## 8. 模型的局限

1. **有界：** 结论只在 §5.2 的界限内成立。更大的 N、更多次交接或更多故障，可能暴露新的交错。
2. **抽象：** 回合被视为一个原子单位，一个回合内的多次模型请求与工具调用、事实的内容与顺序都被省略；同步被视为一次完整交换，没有建模分页上限与 owner 未就绪。
3. **协议步骤被理想化：** 探测、同步与安装被视为原子 RPC。真实 RPC 的中间状态（例如安装请求已执行、响应丢失）只通过 `AfterChangeRoute` 的重复投递部分覆盖。
4. **消息不会永久丢失：** 模型检查的是安全性；活性只以 `NoProgressWhileOwnerDown` 这类可达性见证给出，没有检查带公平性的时序性质。
5. **映射需要复核：** 反例说明模型中的交错可以发生。它们在真实系统中能否复现，还取决于界面与时序等模型之外的因素，需要用阶段五第 11 节的故障注入实验确认。
6. **FCP 尚未实现：** §5 的结论是对设计的检查，不是对代码的验证。
