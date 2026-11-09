# Operit2 分布式运行与持久同步：代码证据审查

审查日期：2026-11-07。代码基线：`1ef788456713e0502688dc0b7928511d98b813ec`。本报告服务于中文版技术白皮书重写，覆盖 CoreNode、Space、Binding、路由、交接、事务同步与内容校正。依据为静态阅读实际 Rust 实现和测试源文件；本次没有执行编译、构建、测试、CI 或推送。测试源文件证明的是仓库表达了哪些验收条件，不能在白皮书中写成本次验证通过。

## 1. 可用于白皮书的核心结论

Operit2 当前是一套将本地 Agent 运行、节点能力、经过授权的多节点通信，以及个人业务数据持久复制组合起来的系统。其设计围绕业务持久状态和后续执行位置分离展开：Space 限定成员、策略、拓扑与同步范围，Binding 将不透明业务 key 映射到执行节点；不同平台的本地 Host 仍拥有本机实际系统能力。

实现中的关键约束是：**业务数据同步不等于进程迁移，Binding 收敛不等于全局唯一执行，本地事务原子性不等于分布式 ACID，重复投递识别不等于任意外部副作用恰好执行一次。** 这些是代码本身要求的区分，不只是保守措辞。

当前确有较完整的生产事务管线，包括 SQL 保存不可变原文、精确收据、owner 定位与迁移、持久待处理状态、Preference 重放与文件提交意图、SQL owner 同库提交、初始化事务、覆盖指纹和压缩，以及部分 owner 的摘要比较与完整快照校正。它不应笼统归类为“纯 CRDT 系统”，也没有证据支持将它描述为 Raft/Paxos 式共识系统。

## 2. 实际对象和装配边界

### 2.1 CoreNode 是装配单位

- `core/crates/application/core/src/lib.rs:126–188`：从同一 `LocalCoreProxy` 取 `CoreNodeLocalRuntime`，构造 `CoreNodeRouter`，绑定设备工具运行时、`RuntimeRemoteLinkService`、路由变更回调及插件 SDK IPC。具体应用运行时、路由器与本机能力在此装配。
- `core/crates/application/core/src/lib.rs:192–199`：装配 `NodeServices` 后才启动 Space 同步服务。服务能否正常运行依赖实际 Host 及通信服务，不是类型定义即等于部署就绪。
- `core/crates/node/runtime/src/CoreNodeRouter.rs:77–93` 和 `95–130`：本地运行时持有 storage、generated dispatch 等访问能力；Router 通过这些能力调度本地或远端请求。

建议正文采用“运行 Core 的应用实例是 CoreNode；Host 提供该实例可用的本机能力”。不要把 Space 画成包含所有 Agent 进程、终端和浏览器状态的统一执行容器。

### 2.2 Binding 的精确定义与本地并发约束

`core/crates/persistence/store/src/CoreNodeBindingStore.rs:84–95`：

```rust
CoreNodeBindingRecord { key: String, nodeId: String, generation: i64 }
CoreNodeBindingCommit { binding: CoreNodeBindingRecord, operation: SyncOperation }
```

- `145–158`：新记录的 generation 为 1；同一 key 已存在则创建失败。
- `180–210`：`compareAndSet` 在**进程内全局 Mutex** 下读取当前记录，只比较 `expectedNodeId`，目标变化时将 generation 加 1。若当前节点已经是目标节点，返回既有操作，**不增加 generation**。
- `229–253`：普通同步应用先用 `SyncOperationStore::shouldApplyOperation` 判断冲突顺序，保存原文，并按胜出结果更新本地缓存与已应用记录。
- `261–281`：直接安装 Binding 使用 `appendUnobservedOperation`，不推进普通持久同步时钟，避免一次实时交接将更早未收到的原文误判为已经齐备。

能够说明的性质：单进程共享存储访问者之间的互斥修改、同步后基于冲突顺序的记录选择、世代号标识一次执行位置变化。

不能由此推出：跨节点线性化 CAS、法定人数、单写主授权、分区期间全球唯一执行权、跨节点 ABA 防护。API 比较的是 nodeId，未比较调用方观察到的 generation；两台尚未同步的设备可以各自基于旧本地状态提交不同变化。后续记录选择可以收敛，但外部副作用不会因此撤销。

### 2.3 ChatExecutionLease 是本地保护，不是分布式租约

`core/crates/persistence/store/src/ChatExecutionLease.rs:7–17`：状态是 `Arc<Mutex<ChatExecutionLeaseState>>` 下的 `BTreeMap<chatId, ActiveExecution>`，包含本地递增 id 和 dirty revision 集合。

- `111–152`：同一 store 已有活动执行则拒绝新的本地执行，并确认聊天真实存在。
- `44–57`：释放时只删除自己的 id，旧异步回调不能释放较新的执行。
- `76–100`、`154–184`：保护精确消息 revision/插件元数据，执行期间拒绝相关更改。
- `188–209`：请求失败、future 取消等路径由 guard 释放其持有的一代保护。

该结构不携带网络仲裁、续约、到期或 fencing token 的远程验证逻辑。可以写“本地执行排他与 revision 保护”，不能写“分布式 lease 保证同一任务全局只执行一次”。

## 3. 实时协议和路由

### 3.1 原始协议与外层路由信封

`core/crates/foundation/link/src/protocol.rs:732–768` 定义 Call request/response；`863–903` 定义 Watch/Push request；`963–990` 定义 PushItem 与 `RoutedCoreRequest<T>`。路由信封实际包括：

```text
spaceId, originNodeId, targetNodeId, ttl, routeKind, payload
```

因此白皮书配图不能只画 `spaceId + targetNodeId + payload`；原调用者身份和 route kind 是权限判断及分发的重要输入。它不是额外的 Agent 身份体系。

`core/crates/node/runtime/src/CoreNodeRouter.rs:975–1023` 表明，Space call 先查 generated route、解析 Binding key，必要时只在显式创建命令下分配 Binding，再检查 origin→target 权限，最后本地执行或发送到选定节点。

`937–970` 还表明创建 Binding 可选择具有 CoreVersion、所需 capability 且可达的节点，并即时安装到远端。不能把“所有聊天一定先绑定本机、每次均由模型自行选择”写成普遍事实。

### 3.2 路由算法与实时事实来源

`core/crates/persistence/store/src/CoreSpaceStore.rs:1001–1118` 是 Dijkstra 风格的加权最短路径搜索：

1. 目标必须是当前 Space 成员。
2. 起点的第一跳只来自当前提供的活跃直连 peer 集合。
3. 后续扩展只允许具有 transit 许可的节点。
4. 拓扑边需未过期、目标仍为成员、同时存在于该公告的 peers 集合。
5. 相同代价按第一跳和节点 id 确定次序。

`CoreSpaceStore.rs:1663–1667` 的整数代价为：

```text
1000 + 10 × smoothedRttMs + 25 × lossPermille + 10 × congestionPermille
```

**实现能力与当前数据采集必须区分。** `core/crates/node/runtime/src/peer/space_topology.rs:15–20` 明确说实时邻接公告尚未携带测得的链路质量，普通公告仍表现为按跳数选路。`10–12` 的公告生命周期为 600 秒，刷新边界为剩余 300 秒。不能直接声称系统已持续测量全网 RTT/拥塞并进行最优自适应调度。

`CoreNodeRouter.rs:721–745` 每次转发减少 ttl；`750–781` 排除上游和失败第一跳并基于活跃 peers 重选；`797–811` 对接收信封校验 Space、上游、原发起者和目标的成员/撤销状态。初始 ttl 为成员数，见 `1867–1872`。TTL 限制转发链长度，不是无限环路不存在的形式化证明。

### 3.3 重提与副作用边界

`core/crates/node/runtime/src/route_forwarding.rs:81–128` 是尤其需要在白皮书写清楚的行为：

- `device.tools` 和 `edge.*` 目标不允许这层自动重提；注释说明“没有回复不等于动作从未运行”。
- 其他目标在 `CORE_NODE_UNREACHABLE`、`PEER_LINK_CLOSED`、`PEER_RESPONSE_CLOSED`、`PEER_SEND_FAILED`、`PEER_WATCH_SOURCE_CLOSED` 等错误下，排除失败第一跳后可重新提交。
- Call、WatchSnapshot、Watch 和 Push 建立都共用该 forwarding loop（`130–172`）。

因此可靠表述是“路由层对特定传输失败有受目标类型限制的重提策略；副作用语义仍依赖业务服务和工具”。不能声称 requestId 自动使所有远程调用恰好一次，也不能从部分类型不重提推导整套系统具有 at-most-once。

Watch 和 Push 是实时订阅/输入通道，持久复制日志是另一条路径。断开后的实时流、进程句柄或浏览器会话不能靠日志复制自动迁移。

## 4. 任务交接：实际顺序与缺口

### 4.1 源端工具回合边界

`core/crates/runtime/application/src/services/core/MessageProcessingDelegate.rs:2541–2565` 在完成 assistant 段的持久提交失败时结束本轮并报告错误；`2633–2658` 在该段提交后取 pending route change，并构造 `CoreRouteResumeContext`；`2660–2685` 释放本地执行保护后发起路由变更。

上下文的数据结构在 `core/crates/tool/services/src/runtime_support.rs:18–35`，包括 runtime chat history、workspacePath、promptFunctionType、thinking 开关、participantId、extensionOwner、provider/model override 与 turn options。它不是模型 KV cache、操作系统进程镜像或浏览器会话快照。workspacePath 是标识路径，不能据此推断目标文件和环境自动存在。

`MessageProcessingDelegate.rs:947–964` 按当前 turnId 和取消状态确认源端所有权，并释放本机 lease；不会触发必需的摘要压缩。压缩是其它机制，不应作为交接定义。

### 4.2 changeRoute 的实际协议

`core/crates/node/runtime/src/RuntimeRemoteLinkService.rs:940–1101`：

1. 校验 chatId/targetNodeId 非空、目标为成员、有 CoreVersion 和 `runtime.execute`、远端目标当前可达（`946–970`）。
2. 读取本地 Binding，在当前 owner 调用 `BeforeChangeRoute`（`972–980`）。
3. 目标为远端时先调用 `synchronizeReachablePeerForReason`，完成一次显式同步过程（`1010–1037`）。
4. 本地 `compareAndSet(currentBinding.nodeId, targetNodeId)` 并记录 Binding 操作（`1040–1058`）。
5. 用独立即时方法把该操作安装到目标（`1060–1061`、`1106–1125`）。
6. 若只改变后续执行设备而无 resume context，则返回；否则在目标调用 `AfterChangeRoute` 并携带上下文（`1063–1101`）。

目标端 `core/crates/runtime/application/src/services/ChatServiceCore.rs:794–855` 打开目标本地聊天历史、取得新的本地执行 lease、解析配置并发送 routed continuation。`858–874` 的 before callback 通过取得再释放本地 lease 确认当前未执行；`877–889` 的 after callback 实际启动续跑。

### 4.3 不能包装为完备原子迁移协议

- 源释放、同步、Binding 本地提交、远端安装、续跑是分开的 await/持久步骤，没有统一分布式事务。
- `changeRoute`/`CoreRouteResumeContext` 中未见显式 requiredClock 或 expected Binding generation 参数，不能照旧文档写成每次交接都由持久化 vector-clock fencing 屏障强制证明状态齐备。
- 本地 Binding 已提交后，目标安装或 after callback 仍可失败；代码把错误返回，不构成自动恢复所有副作用的保证。
- 目标取得本地 lease只能排除目标进程已知的并发执行，无法单独排除另一个分区节点。
- 一个同步 pass 有分页上限、pending owner/Blob 与版本不兼容边界；完成调用不应被概括成“所有业务数据在全球同时一致”。

建议正文写成“在已保存的回合边界切换后续执行节点”，并把全局 fencing、重复 continuation 识别、故障窗口与长期恢复演练列为需验证的问题。

## 5. 持久同步与事务 owner 管线

### 5.1 原文、知识和业务应用是三个维度

`core/crates/persistence/store/src/SyncOperationStore.rs:238–250` 的原文信封：

```text
opId, originDeviceId, sequence, domain, entityType, entityId,
operation, semantics, payload, createdAt, schemaVersion
```

`252–255` 校验重复 ID 必须对应相同不可变原文。`SyncOperationSemantics` 区分可替换实体状态与有序 transaction；该 flag 的注释明确不承诺跨数据集原子性（`207–220`）。

`SyncClock`（`43–89`）表达每个 origin 已观察序列及 includes 判断。`SyncReceipt`（`124–207`）表达**精确连续区间集合**，能在收到后序操作时保留早期空洞：例如已收到 2，不应声明 1 已收到。SQL 导出会利用 receipt 而不只是每个作者最高序号。

该区分非常值得配图：收到并持久保存原文 ≠ owner 已能解码并成功应用 ≠ 最终物化内容一致。

### 5.2 顺序的准确边界

`SyncOperationOrder`（`292–326`）是 `createdAt, originDeviceId, sequence` 的确定顺序；Preference 契约 1 可使用 payload 中的 logicalTime，runtime_file 初始化采用特定较早顺序。

`core/crates/persistence/store/src/Transaction.rs:20–27` 的 `newer` 对同 origin 直接使用 sequence，抵抗该作者墙钟回退；`39–85` 的 `ordered` 先按不可变身份并集，再形成同 origin 的 sequence 队列，每次从各队头按 Revision 选择下一条。

能够说明“保留同作者序列，并对跨作者冲突建立确定顺序”。不能只凭 vector clock 术语宣称完整的跨作者因果排序、可串行化或线性一致。当前 Revision 并不携带完整依赖向量。

### 5.3 owner Registry 是生产装配入口

`core/crates/runtime/application/src/core/application/SyncConsistency.rs:25–120` 实际装配 Preference、聊天 SQL、插件 SQL，以及 Binding/控制/runtime_file 等动态 owner。`core/crates/persistence/store/src/transaction/Kernel.rs:77–104` 的 Participant 具有 prepare、validate、apply、project、snapshot、coverage、content_digest、repair 等能力，Source 负责 receipt/export/inventory。

`Kernel.rs:185–191` 先把原文持久接收，再处理 pending。`195–279`：按 owner 分组；退休路径按空效果确认；未知或不可识别文件来源标记跳过；已覆盖原文不再生效；owner prepare/validate/apply 失败按错误类型保留待重试或进入内容校正路径；其它 owner 继续处理。Preference aliases 仅从已经提交的 owner 向引用 owner 投影。

关键限制：Registry 组织独立 owner 生命周期，不是把所有 owner 放进一次跨库大事务。用户数据文件、聊天数据库、插件数据库是不同提交载体。

### 5.4 Preference replay 与持久提交意图

`core/crates/persistence/store/src/transaction/PreferenceOwner.rs:503–559`：持有该文件的 transaction lock，加载并迁移本地表示，初始化 owner，从已归档历史及传入原文做身份合并和有序重放，按初始化覆盖集合过滤，执行 owner 声明的规则，形成新 Snapshot，并保存。

`179–205` 先在文件中保存 `FileCommit` 意图，包括 originals、retired/completed/covered 身份、aliases、删除、revision、versions/additions、generation 以及必要的完整文件内容；`97–165` 的 recover 将原文与 owner/checkpoint/收据/覆盖退休提交到 SQL，再清理文件意图。完成意图未能移除时，重新打开可以重复同一 SQL 提交。

这是跨文件与 SQL 的**可恢复提交过程**。可以讲清楚故障窗口如何记录恢复依据；不能称成数据库底层提供了文件与 SQLite 间的原生单事务。

### 5.5 SQL owner 的本地原子边界

`core/crates/persistence/store/src/sync/SqlChatSyncStore.rs:664–695` 把 authoritative business mutation、sync payload、origin sequence 和观察记录放到同一 SQLite transaction。`599–629` 对远端原文先检查压缩覆盖和重复身份，再在同库事务中应用 payload、插入 operation、记录 receipt。聊天删除也在 SQL transaction 内删除并记录删除事实（`342–362`）。

插件 SQL 通过同一 Registry Source/Participant 组织，但每个插件数据集仍有自己的 owner/路径，见 application `SyncConsistency.rs:59–88`；需要具体 owner 的 schema/merge rule 来判断其语义。

### 5.6 迁移与压缩确有实现，但不是任意数学变换保证

- `transaction/Migration.rs:1–23` 保存完整 before/after、源/目标 owner、原始 transaction 与历史 context；`45–155` 对兼容 codec 约束修改 scope，不允许在没有显式规则时丢失结构和 additive contribution。
- `PreferenceMerge.rs:375–394` 先检查初始化 backend、加密策略、未来格式，再由 owner 路径应用；`516–545` 迁移旧 entries、解析 aliases/references，然后调用 `PreferencesSyncedEntry::replay`。
- `transaction/Compaction.rs:32–86` 将完整 Snapshot 和 covered 身份编码成可导出的初始化 transaction，ID 由内容摘要确定。
- `Compaction.rs:89–130` 的普通 superseded 选择只处理明确支持的绝对 Set/Delete scope；复杂作用、不完整覆盖或无法证明等价的业务规则保留。`132–170` 保留 retired identity/fingerprint 并在重复冲突时拒绝。
- 通用 `History` 确实能表达高阶 transaction 修改另一 transaction 的 edits，并检测循环和缺失目标，见 `Transaction.rs:1004–1100`。这说明内核有表达能力；未逐项证明所有 Preference/聊天/插件 SQL 写入口已把任意高阶语义作为公开产品接口。

因此正文可以给“保持身份、顺序、覆盖证据”的设计原则和具体算例，不能将 `transaction-model.md` 所有等价公式当作已经形式证明、所有 owner 全覆盖的结论。

## 6. 同步调度、分页和内容校正

### 6.1 控制交换与业务复制分离

`core/crates/node/runtime/src/SpacePersistenceSyncService.rs:541–629` 先交换 authority/control，接着交换 device-owned preferences，最后检查双方 storage provider 条件后才交换业务 domains。`643–650` 调用 `requirePeerStorageProviders`，不满足授权时不开展业务复制。

非 storage 成员仍需接收授予/撤销等控制信息，且该控制传播不推进业务复制时钟（`576–577`）；轻量 endpoint 不应积累其他设备的配置副本（`604–609`）。这是成员、网络连通、存储授权三种状态必须分离的代码依据。

双方都有存储能力时，nodeId 的字典序决定发起完整 pass 的一方，以避免两端同时重复工作（`547–574`）。这只是每对节点每次交换的协调，不是固定主节点选举。

### 6.2 调度与成本边界

- `SpacePersistenceSyncService.rs:65–91,666–735`：每 peer 有独立 gate、互斥执行、上次本地/远端摘要、pending 标记与失败计数。摘要改变、尚有 pending、失败退避到期等触发完整交换。
- `43–46,103–108`：失败退避从 2 秒开始、指数增加、上限 60 秒。
- `47–54`：工作区外部改动扫描活跃期 2 秒、空闲最长 60 秒；不是每次编辑都由系统事件瞬时发现。
- `SyncOperationStore.rs:39`：默认导出页预算 4 MiB；`SpacePersistenceSyncService.rs:40–42`：单 pass 最多 64 页。
- `SpacePersistenceSyncService.rs:826–958`：先交换 receipt，再导出双方缺失原文，传输并应用；空页或重复页进入 consistency 检查。持续写入导致超过页数上限时保留 pending，交给后续 pass。

这些常量可作为实现配置说明，不能在未测量时转化为吞吐率、时延上界、能耗或可扩展节点数。

### 6.3 内容比较/校正已实现，覆盖范围有限

`core/crates/node/runtime/src/SyncConsistency.rs:19–27` 要求双方 `consistencyVersion == 6`。`48–60` 检查双方各自 report 与本轮导出 receipt 边界是否相同；期间有新事务则本轮不报告完成。`64–148`：比较 manifest，选择来源、传完整快照及覆盖依据，检查 snapshot token，分别安装到两端，再重新比较；变化中的 owner 可暂缓，不阻挡独立 owner。

`core/crates/runtime/application/src/core/application/SyncConsistency.rs:123–138` 的实际 manifest 来源是 Registry 中提供 snapshot 的 owner。该文件 `39–53` 给聊天 SQL 提供 snapshot/repair，`78–88` 给已安装插件数据集提供 snapshot/repair，Preference owner 在 `PreferenceMerge.rs:375–401` 提供。

**反例边界**：application `SyncConsistency.rs:99` 的动态 Binding、控制、普通 runtime_file Participant 是 `snapshot: None, repair: None`。所以不能声称“任何同步对象，包含所有普通文件，都经过统一摘要校正后保证完全一致”。普通文件和 workspace 文件另有整文件操作、winner 选择、Blob 与本地 inventory 管线。

该校正路径以业务 revision/owner 策略选定完整内容，可替代不一致的物化状态；这应当作为恢复语义如实描述，不能只说“完全无损保留所有并发意图”。

### 6.4 普通文件与 Blob

`core/crates/persistence/store/src/RuntimeFileSyncStore.rs:315–369` 为大载荷使用引用、transport preparation 与 hydrate；`403–424` 保存和读取内容寻址 Blob；`434–475` 校验 SHA-256 内容 hash 与声明 size。

`WorkspaceFileSyncStore.rs:279–299` 根据 operation 冲突顺序判断是否物化；`315–329` 写入本地 pending 意图；`390–415` 发布已验证 bytes 并提交 inventory。路径归属由 RuntimeStorageLayout 限制，未知、本机、越界路径不能因为远端输入就变成同步文件。

文件同步是完整内容替换和 owner 规则，不能描述为任意文件实时协同编辑或自动语义合并。终端改动探测依赖 scanner，mtime/size/inventory 等机制的可靠性仍需单独评估。

## 7. 成员控制与对账的证据

`core/crates/node/runtime/src/peer/space_reconcile.rs:189–210` 只接收对端自源的控制操作，不把未经验证的第三方转述当作对端签发事实；`296–378` 实际执行增量对账、重放和成员投影。

`core/crates/persistence/store/src/NetworkControlReadModel.rs:144–183` 在控制原文变化时重建排序后的控制状态；授权查询读取物化 read model。控制操作的到达顺序会影响暂时可见状态；重放合并日志得到一致策略是最终收敛机制，不等于一条全网瞬时原子授权序列。

`NetworkControlStore.rs:753–773` 把控制 projection 与 business clocks 分离。日志或缓存中的角色不能替代当前 replay 后的授权检查；多个成员尚未收到撤权时，传播前后的操作接纳边界需要在安全章节解释。

## 8. 已阅读的测试源文件及其可证明范围

| 源位置 | 表达的验收条件 | 不能据此声称 |
| --- | --- | --- |
| `node/runtime/tests/device_space/routing_contracts.rs:103–150` | 多跳、环、分区重连仍保留成员关系 | 真实公网任意拓扑已验证 |
| `routing_contracts.rs:151–213` | relay 能力撤销阻断 transit，TTL 用尽拒绝 | 完备 Byzantine 路由安全 |
| `routing_contracts.rs:254–285` | 已接收新 Binding 的本地 store 拒绝旧 expected node；重复/乱序操作不回退 | 分区时双端写入具有线性 CAS |
| `persistence_contracts.rs:61–175` | 三 store hop 文件更新/删除、缺失截断腐坏 Blob、两操作置换 | 任意文件语义 merge、所有崩溃点恢复 |
| `persistence_contracts.rs:177–238` | 本机/越界路径和未授权同步不能改文件/取业务原文 | 所有 Host 实现已审计 |
| `convergence_properties.rs:125–159` | 固定 16 个随机 seed 的双节点控制对账收敛与历史并集保留 | 普遍形式化收敛证明或大规模集群测试 |
| `sync_idle_gate.rs:265–557` | 空闲摘要门控、旧 consistency peer 不完成、失败退避、配置修改唤醒 | 当前所有移动端电量/流量成本已测量 |
| `sync_idle_gate.rs:652` | 部分插件失败不阻断健康复制路径 | 任意数据集之间绝无业务依赖 |
| `store/src/transaction/CompactionTests.rs:99–162` | 绝对赋值的整体事务压缩、保留部分有效/不明规则、指纹和 payload 删除回滚 | 所有事务代数都可任意压缩 |
| `store/src/sync/SqlChatSyncStoreTests/mod.rs:498–594` | 删除终态、同库原子性与旧写入不得复活会话 | 已从所有外部备份物理擦除 |
| 同上 `1544–1770` | 稀疏收据、压缩身份、内容摘要、同作者时钟回退、初始化后离线写重放 | 当前代码运行结果已经通过；本次未执行 |

## 9. 可直接采用的图解规格

1. **两条数据路径**：上方 Call/Watch/Push→Router→PeerLink→目标 Core；下方不可变事务→Receipt/owner→持久日志与业务物化→同步。标记实时流与持久数据不同生命周期。
2. **交接时序**：源 assistant 段持久提交→release 本地 lease→before 检查→先同步→本地 Binding CAS→即时安装→after/resume→目标取得本地 lease→下一模型请求。把“CAS 提交后安装/续跑失败窗口”用注释标出，不画成原子一步。
3. **持久同步管线**：immutable original durable receive→owner route/layout→prepare/validate/migrate→owner atomic commit or recoverable FileCommit→receipt/apply status→提供 snapshot 的 owner 才进入 content compare/correct。并排显示 pending/skip，而非消失或报告空成功。
4. **Space 路由图**：活跃直连作为第一跳，后续来自有期限的公告；relay capability 限制 transit，origin/previous/target 逐跳校验，TTL 减一。加权代价是算法支持；实时测量接入状态用独立标注。

## 10. 白皮书需删除或改写的典型承诺

| 不宜作为当前事实的表述 | 可由代码支撑的表达 |
| --- | --- |
| 全局状态永久强一致、任意设备瞬时一致 | 获授权副本经持久日志、精确收据、owner 合并和部分 owner 内容校正持续同步；网络/版本/owner 就绪是条件 |
| Binding 一次 CAS 就取得全球排他执行权 | 本地比较写入记录后续执行位置，记录经同步冲突规则传播；本地执行保护另行实施 |
| 迁移正在运行的 Agent/终端/浏览器 | 持久回合边界传递必要上下文，目标创建新的本地执行 |
| 请求编号保证所有工具恰好一次 | 原文去重适用于持久事务；远程实时调用和外部副作用的重复风险取决于业务协议 |
| 所有历史均永久保留、可完整审计 | 合规压缩可删除 payload，但保留覆盖身份、指纹/收据与初始化基线；内容历史与审计材料不是同一保留策略 |
| CRDT 自动解决一切冲突 | owner 声明的确定重放/冲突规则；普通文件为整文件状态，必要时按业务 revision 进行快照校正 |
| 任意版本自动互通、任意 schema 自动迁移 | 当前版本协商、明确迁移规则、未来格式 pending/拒绝完成；兼容性必须逐版本验证 |
| 已支持健康/负载/成本驱动全网最优调度 | 当前有可达性、角色/capability、加权路由算法和显式执行节点选择；质量采集与全局调度需分别交代 |
| 几千/几万节点轻松扩展 | 当前面向个人设备空间；本次没有规模实测、复杂度评估或资源上界证明 |

## 11. 补充审查：凭据归属、静态加密与传输信任

本节追加于 2026-11-07，仍固定于本文基线；采用只读源码审查，没有读取用户运行时凭据，也没有执行编译、构建或测试。结论是：**模型 Provider 的 API key、key pool 和自定义请求头进入可同步配置；本机静态加密不改变其 Space 归属。PeerLink 保护相邻配对节点之间的信道，多跳中继可以解密载荷，当前并非对中继不可见的端到端加密。**

### 11.1 Provider 配置包含可同步秘密

- `core/crates/foundation/model/src/ModelConfigData.rs:608–622`：`ProviderProfile` 直接包含 apiKey、useMultipleApiKeys、apiKeyPool、customHeaders、endpoint 和 models。
- `core/crates/runtime/application/src/data/preferences/ModelConfigManager.rs:1159–1166`：`writeProvider` 的注释是“Writes the complete provider as the synchronized preference value”；实际用 `serde_json::to_value(provider)` 整体写入 `provider_<id>`，未剥离上述字段。
- `ModelConfigManager.rs:87–97` 使用 `PreferencesDataStore::newEncryptedWithStorage`；`core/crates/persistence/store/src/PreferencesDataStore.rs:2940–2974` 明确该构造函数建立 encrypted **Space** preferences store，并装配 `SyncOperationStore` 与 `syncDescriptor`。
- `core/crates/runtime/application/src/data/preferences/PreferenceSpaceMerge.rs:27–44` 注册 model_configs 的 provider_ catalog；ignored_fields 只有 createdAt/updatedAt，不存在 secret 字段排除。
- `core/crates/foundation/util/src/RuntimeStorageLayout.rs:433–434` 定义路径 `runtime/config/preferences/model_configs.preferences.json`。Preference namespace 的同步归属由 Store 类型与 owner 注册决定，不能仅查询普通 runtime file layout 清单。
- `PreferenceSpaceMerge.rs:48–94` 同样注册 encrypted Space TTS/STT 配置；相应管理器采用 `newEncryptedWithStorage`（`TtsConfigManager.rs:32`、`SttConfigManager.rs:30`），这些配置中也有 apiKey。

准确的产品范围是：取得存储授权且实际提供 Core 存储服务的副本，可以接收并应用完整 Provider 配置。不能写成“所有 API key 默认只留原节点”“静态加密意味着获授权副本不能获得密钥”或“仅同步没有密钥的模型元数据”。

### 11.2 静态加密与同步链路分别保护什么

- `core/crates/persistence/store/src/PreferencesEncryption.rs:12–19`：XChaCha20-Poly1305、32-byte key、24-byte nonce。
- `PreferencesEncryption.rs:50–91`：主密钥通过 HostSecretStore 获取/创建，并有旧本地 key 文件迁移；没有配置 HostSecretStore 的显式路径仍可使用 `secure/preferences_encryption_key.json`。
- `core/crates/persistence/store/src/SyncOperationStore.rs:1208–1245`：保存 encrypted Preference 原文时用本机上下文加密 payload；`1248–1272` 在读取原文时解密。
- `SyncOperationStore.rs:1788–1791`：`original()` 返回解密后原文；`1999–2014` 的分页导出通过 original() 将解密后的逻辑操作放入传输页。接收节点使用自己的存储加密上下文保存。
- `hosts/windows/src/tools/storage/mod.rs:129–155`：Windows HostSecretStore 使用 Credential Manager；`hosts/apple/src/tools/storage/mod.rs:127–155` 使用 Keychain；`hosts/linux/src/tools/storage/mod.rs:61–142,251–265` 使用权限受限的文件目录，并非系统钥匙串。
- `hosts/android/src/runtime_storage.rs:96–132` 委托 Android 宿主 bridge；`hosts/web/src/tools/storage/mod.rs:186–205` 委托 JS hostSecretStore。仅凭 Rust trait 存在不能声称所有平台均有相同系统安全属性。
- `hosts/common/operit-host-native-storage/src/secrets.rs:1–7,20–63` 的显式 native profile secret store 是文件实现，Unix 设置私有权限，其它平台继承 profile ACL。

应分别评价本机静态密文、主密钥的 Host 保护、网络信道保护，以及获授权节点解密后的可读数据。四者不能合并成一句“端到端安全存储”。

### 11.3 真正 node-local 的 OAuth 与配对状态

- `core/crates/runtime/application/src/data/preferences/GitHubAuthPreferences.rs:31–32,49–60`：GitHub OAuth 使用 `CoreNodeSecretStore`。
- `core/crates/runtime/application/src/data/preferences/CodexAuthPreferences.rs:7–19,34–42`：Codex OAuth session 使用 `CoreNodeSecretStore`。
- `core/crates/persistence/store/src/PreferencesDataStore.rs:2349–2389`：该 Store 使用 `newNodeLocalWithStorage(..., true)`；`2995–3016` 的本机实现没有 `syncOperationStore` 和 `syncDescriptor`。这同时提供本机归属和 Preference 静态加密。
- `core/crates/node/runtime/src/PeerStateStore.rs:48–74`：inbound/outbound record 包含 sessionSecret；`89–108` 使用 `CoreNodeStateStore`。
- `PreferencesDataStore.rs:2173–2178`：`CoreNodeStateStore` 使用 `newNodeLocalWithStorage(..., false)`。因此配对 sessionSecret 当前是**本机且不进入 Space 同步，但没有走 CoreNodeSecretStore 的静态加密**；其文件保护取决于 Host/账户/部署边界。
- `RuntimeStorageLayout.rs:150–187`：identity、inbound/outbound sessions、pending pairing 与 host config 明确归属 CoreNode。

不能把“本机数据”直接改写成“全部凭据都在系统安全库”“全部凭据均静态加密”。运行时 provider API key 与本机 OAuth session 的实际归属也不同。

### 11.4 节点标识与私钥模型

- `core/crates/persistence/store/src/CoreNodeIdentityStore.rs:18–20` 的 CoreNodeIdentity 只含 nodeId；`91–100` 生成带时间与 UUID 的稳定标识。
- `core/crates/node/runtime/src/peer/crypto.rs:30–38` 生成每握手 ephemeral X25519 private key；`HostRuntimePeerService.rs:447–473` 每次握手派生新的 DH/session key。
- 本次在 node/runtime 与 persistence/store 的相关路径中未发现长期设备签名私钥、公钥证书或 PKI 身份体系。SPAKE2 的 Ed25519Group 是 PAKE 使用的群，不是设备 Ed25519 身份签名。

白皮书应写“稳定节点标识、持久配对共享凭据与每连接临时密钥”，不能凭旧文档概念引入长期设备签名私钥体系。

### 11.5 PeerLink 的实际密码学与逐跳边界

- `peer/crypto.rs:30–57`：X25519、HKDF-SHA256、HMAC-SHA256。
- `peer/crypto.rs:125–197`：SPAKE2 身份绑定当前 transcript；新配对的长期 session secret 绑定 PAKE 输出、start root 和上下文。
- `HostRuntimePeerService.rs:444–512`：握手校验 client/server nodeId、临时 public key、challenge、sessionId 与 proof，并建立 Channel。
- `peer/crypto.rs:253–288`：ChaCha20-Poly1305；双向独立派生 key；严格单调 nonce；transcript context 用作 AAD。
- `peer/crypto.rs:308–344`：编码后载荷封装在 `$peer.session/data`；接收端校验序号/tag 后获取明文并 decode。
- `core/crates/node/runtime/src/peer/dispatch.rs:53–80`：邻接节点解开 `RoutedCoreRequest`，把完整 payload 交给自己的 Router；`CoreNodeRouter.rs:2022` 对非本机目标继续转发；`HostRuntimePeerService.rs:660–668` 为下一 hop 独立获取对应 Channel 并重发。

所以 A→B→C 中，B 是 A–B 与 B–C 两条加密信道的端点，能看到路由与业务 payload 明文。当前代码没有源→最终目标的独立载荷加密或源签名验证。普通 originNodeId 是邻接节点递交的路由字段，完整性保护限于各 hop；不能宣称在恶意中继下仍具有端到端源身份不可伪造性或对中继保密。

### 11.6 Node policy 的检查与撤销范围

- `peer/dispatch.rs:101–111`：每次业务 entry 再检查连接政策和配对凭据；打开的 channel 不是永久授权。
- `peer/availability.rs:18–26`：连接使用受当前 `nodeIsDisconnected` 状态约束。
- `space_policy.rs:7–29`：配对不等于 Space 接纳；双方必须处于相同且已初始化的控制投影，且未断开。
- `CoreNodeRouter.rs:797–811`：逐跳检查 previous、origin、target 的成员/撤销状态；`517–571` 检查 generated route 的 capability 和 caller/target subject。
- `peer/sync_dispatch.rs:20–39`：同步要求认证配对、同 Space channel 与 Target route；`116–127` 要求复制两端均有 CoreVersion、未断开且有 storage.provide。
- `peer/sync_dispatch.rs:88–110`：Blob push 每个 chunk 和最终 close 重新检查授权。
- `NetworkControlStore.rs:1191–1209`：内置 user 和 relay 都含 storage.provide。Relay 角色不能解释成天然只转发密文、不接触或不保存业务副本。

这些检查使用当前节点已获知并重放的策略。异步撤销传播不等于全网瞬时原子撤权，也无法撤回先前已同步、导出或被外部系统保存的内容。

