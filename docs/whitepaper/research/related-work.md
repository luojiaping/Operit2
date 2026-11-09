# 中文技术白皮书：外部文献与开源实现调研记录

资料核查日期：2026-11-07。适用代码基线：`1ef788456713e0502688dc0b7928511d98b813ec`。

本记录服务于白皮书的相关工作、术语定义、设计取舍和局限性论证。所有下列来源均通过 TinyFish 实际读取；论文使用正文，项目使用官方文档或官方仓库 README。官方仓库的声明只代表项目自身的设计与功能说明，不构成本次独立性能验证。未执行外部或本地项目的编译、构建、测试或部署。

Operit2 的对照背景来自 `docs/core-node-space-binding-architecture.md`、`docs/sync-architecture.md` 和 `docs/a2a-extension-architecture.md`。本文中的 Operit2 对照是写作建议，仍应由实际代码审查确认；外部文献不能证明 Operit2 的实现正确性。

## 1. 可采用的相关工作结构

| 研究方向 | 核心来源 | 可以解释的问题 | 应避免的错误结论 |
| --- | --- | --- | --- |
| 模型推理与工具使用 | ReAct、Toolformer [R01–R02] | 模型输出、环境操作和反馈构成循环；模型能力与运行时职责不同 | 不能因存在工具循环而声称实现了 ReAct 的实验结果，或具备 Toolformer 的训练方法 |
| 上下文与持久记忆 | MemGPT、Letta Code [R03, R18] | 有限上下文、可检索历史、可写记忆和跨会话状态的区别 | 摘要不是完整历史；保存历史不等于模型随时准确召回；长期使用不自动产生学习效果 |
| 用户数据与多设备 | Local-first [R04] | 设备上的持久副本、离线可用、用户控制、服务依赖 | 本地保存数据不等于模型离线推理；开放源代码不自动满足全部 local-first 理想 |
| 复制与事件顺序 | CRDT、Lamport、Automerge [R05–R07] | 事件因果、确定性合并、收敛条件和业务不变量 | 逻辑时钟不是物理时间；同一日志的确定性重放不是共识；副本收敛不等于执行唯一 |
| Agent 编排和可恢复执行 | LangGraph [R08–R10] | 图状态、检查点、完成的步骤、重放边界、人类介入 | 恢复不等于迁移 CPU 栈或精确跳回原源代码行；持久化步骤结果不自动消除重试副作用 |
| 工作流和外部副作用 | Temporal [R11–R12] | 事件历史、工作流/Activity 分离、重试与幂等 | 完成被观察一次不等于外部操作只执行一次；幂等性不能仅由编排器声明 |
| 工具互操作与安全 | MCP [R13–R14] | Host/Client/Server、工具发现、能力协商、用户授权 | MCP 兼容不等于所有特性/版本实现完整；协议不能替应用保证安全 |
| 异构 Agent 互操作 | A2A [R15] | Agent Card、任务、消息、交付物、异步生命周期 | A2A Agent 不必共享内部状态；接入 A2A 不等于加入 Operit2 Space |
| 文件与网络基础设施 | Syncthing、iroh [R16–R17] | 文件块复制与端点连接分别解决什么问题 | 文件同步不复制业务事务语义；连通性/加密不授予业务权限或迁移活动会话 |

## 2. 逐项来源和可引用发现

### [R01] ReAct

**书目信息**：Yao, S.; Zhao, J.; Yu, D.; Du, N.; Shafran, I.; Narasimhan, K.; Cao, Y. *ReAct: Synergizing Reasoning and Acting in Language Models*. ICLR 2023；预印本首发 2022，核查版本 v3（2023-03-10）。

- 原始记录：<https://arxiv.org/abs/2210.03629>。
- 已读正文：<https://arxiv.org/html/2210.03629v3>。
- 项目：<https://react-lm.github.io/>。
- DOI：`10.48550/arXiv.2210.03629`。
- 核查日期：2026-11-07。

**可引用发现**：ReAct 将语言推理轨迹、任务动作与环境观测交错组织，使模型利用外部反馈调整后续动作。论文分别在问答、事实核验和交互决策基准上评估该提示方法；这是一种模型交互范式，不是跨设备运行时或分布式事务协议。

**Operit2 对照**：可在 Agent 闭环章节解释“模型请求—工具执行—结果入上下文—下一次模型请求”的通用背景。应把 Operit2 的增量放在持久化、Host 适配、授权、节点路由和跨设备继续执行的工程机制上。

**不能据此推导**：Operit2 的 Agent 必然生成可见思维链；使用某 Provider 的工具调用就完整复现 ReAct；Operit2 获得了论文中的成功率提升。论文中的特定模型、提示、工具与任务基准不能直接移植为本项目成绩。

### [R02] Toolformer

**书目信息**：Schick, T., et al. *Toolformer: Language Models Can Teach Themselves to Use Tools*. NeurIPS 2023；arXiv:2302.04761，2023。

- 原始记录：<https://arxiv.org/abs/2302.04761>。
- 已读正文：<https://arxiv.org/html/2302.04761v1>。
- DOI：`10.48550/arXiv.2302.04761`。
- 核查日期：2026-11-07。

**可引用发现**：Toolformer 采样候选 API 调用、执行调用、以 API 结果是否改善后续 token 预测损失为标准筛选训练样本，再用增广语料微调模型。推理时，生成流遇到 API 结果分隔符后调用外部 API，把结果插入再继续生成。本文解决的是工具使用能力的训练，不是工具权限、系统隔离或多设备协作。

**Operit2 对照**：适合用于区分“模型学习何时调用工具”与“运行时提供、批准、执行和记录工具调用”。若 Operit2 不训练模型，应明确其 Provider 无关的执行基础设施定位。

**不能据此推导**：插件系统会自动提升模型本体推理能力；Operit2 实现了自监督工具学习；更多工具意味着更高成功率。

### [R03] MemGPT

**书目信息**：Packer, C., et al. *MemGPT: Towards LLMs as Operating Systems*. arXiv:2310.08560，2023；已读修订版 v2（2024-02-12）。

- 原始记录：<https://arxiv.org/abs/2310.08560>。
- 已读正文：<https://arxiv.org/html/2310.08560v2>。
- DOI：`10.48550/arXiv.2310.08560`。
- 核查日期：2026-11-07。

**可引用发现**：MemGPT 区分 main context 与 external context。主上下文包括系统指令、可写工作上下文和 FIFO 消息队列；外部历史与 archival storage 必须经过显式检索进入当前提示后才能影响该轮推理。队列管理器在上下文压力上升时发出警告，并在达到容量边界时生成递归摘要；被逐出当前窗口的消息仍保存在 recall storage。论文还利用函数调用与控制标志安排模型连续处理或让出控制。

**Operit2 对照**：应分别讨论原始消息持久化、当前模型输入、压缩摘要、记忆实体和检索工具。跨设备同步这些记录，可提供继续执行所需的数据，但不保证模型完全重建先前推理。

**不能据此推导**：模型拥有无限上下文；摘要无损；持久历史中的每条信息都可被准确召回；应用的“记忆”意味着模型权重持续学习。论文的 OS 比喻也不是操作系统级的内存或权限隔离。

### [R04] Local-first software

**书目信息**：Kleppmann, M.; Wiggins, A.; van Hardenberg, P.; McGranaghan, M. *Local-first software: You own your data, in spite of the cloud*. Onward! 2019。

- 已读作者机构公开全文：<https://www.inkandswitch.com/essay/local-first/>。
- 论文 DOI：`10.1145/3359591.3359737`。
- 核查日期：2026-11-07。

**可引用发现**：论文/作者文章提出七项理想：交互及时、多设备可访问、支持离线、无缝协作、长期可访问、默认安全隐私、用户最终控制。其关键转变是把设备本地副本当作用户可操作的主要数据，而非服务端权威副本的可丢弃缓存。文章同时说明多设备并发修改和协作合并本身是困难问题，并将 CRDT 视为可用基础技术之一。

**Operit2 对照**：适合解释个人设备空间为何需要节点本地持久化、可导出数据和可选的常在线设备。云上 CoreNode 可参与设备协作，而“云”并非天然等于唯一控制点。

**不能据此推导**：所有数据都应复制给每台设备；本地持久化意味着 API Provider 不会收到数据；软件开源或可自托管足以保证隐私；网络断开时仍能调用远程模型和远程工具。

### [R05] Conflict-free Replicated Data Types

**书目信息**：Shapiro, M.; Preguiça, N.; Baquero, C.; Zawirski, M. *Conflict-Free Replicated Data Types*. SSS 2011，LNCS 6976，386–400。

- 已读作者公开原文：<https://asc.di.fct.unl.pt/~nmp/pubs/sss-2011.pdf>。
- DOI：`10.1007/978-3-642-24550-3_29`。
- HAL 地址 <https://inria.hal.science/inria-00609399v2/document> 返回反机器人页面，未作为内容证据。
- 核查日期：2026-11-07。

**可引用发现**：正文第 2 节给出 eventual delivery、termination 与 strong convergence 等条件；已接收同一组更新的正确副本具有等价状态，是 strong eventual consistency 的核心。状态式 CRDT 可通过 join-semilattice、合并的交换性/结合性/幂等性以及单调更新满足收敛条件。操作式方法有其交付和操作交换条件。模型明确假设非拜占庭进程，不能把理论结论任意扩大到恶意节点。

**Operit2 对照**：可以用作审查同步保证的严格参照：必须说明操作身份、来源、顺序、重复投递、业务验证、删除、依赖缺失以及传播假设。若采用的是“保存操作后按确定顺序重放、摘要核查与矫正”，应如实命名这一实际机制。

**不能据此推导**：所有追加日志系统都是 CRDT；确定性排序足以满足论文中全部 SEC 条件；副本状态收敛意味着任意跨实体业务不变量成立；副本收敛阻止两个隔离节点分别执行同一个外部操作。

### [R06] Lamport 逻辑时钟

**书目信息**：Lamport, L. *Time, Clocks, and the Ordering of Events in a Distributed System*. Communications of the ACM, 21(7):558–565，1978。

- 已读作者原文：<https://lamport.azurewebsites.net/pubs/time-clocks.pdf>。
- DOI：`10.1145/359545.359563`。
- 核查日期：2026-11-07。

**可引用发现**：happened-before 定义事件的偏序，同进程的先后、消息发送到接收以及传递性构成因果关系。逻辑时钟可配合额外确定性规则构造与该偏序一致的全序；论文明确讨论了这类顺序可能不同于用户感知的物理先后。

**Operit2 对照**：可解释同步操作中的逻辑时间与来源序号为什么分别存在，以及确定性重放为何需要明确的排序规则。

**不能据此推导**：逻辑时间戳较大一定意味着物理时间较晚；全序意味着全体节点在同一瞬间知道该顺序；有时钟就获得线性一致或外部副作用唯一性。

### [R07] Automerge 官方仓库

**来源**：Automerge contributors. *automerge/automerge*，官方开源实现；持续更新项目，本文不赋予固定出版年。

- 已读官方仓库：<https://github.com/automerge/automerge>。
- 核查日期：2026-11-07。

**可引用发现**：仓库将 Automerge 定义为 CRDT 实现、压缩格式与同步协议的库。核心为 Rust，并通过 JavaScript/Wasm 和 C FFI 暴露。它提供 JSON-like 可并发修改的数据结构及变更合并机制，定位于支持 local-first 应用的持久化基础。

**Operit2 对照**：两者都面向多副本持久数据，但比较应着重语义层级：Automerge 是通用数据结构/同步库；Operit2 的领域 owner 还需要处理聊天、偏好、插件与文件的特定事务和授权边界。除非依赖清单和实现证明，不应称 Operit2 采用 Automerge。

**不能据此推导**：CRDT 能理解任意业务引用；引入 Automerge 会自动解决外部操作重试、成员授权或跨设备运行时继续执行。仓库提及的内存改进也不能作为本项目性能。

### [R08] LangGraph 官方仓库

**来源**：LangChain contributors. *langchain-ai/langgraph*，官方开源实现。

- 已读：<https://github.com/langchain-ai/langgraph>。
- 核查日期：2026-11-07。

**可引用发现**：仓库将 LangGraph 定位于长期、有状态工作流与 Agent 的低层编排基础，包含 durable execution、人类介入和状态记忆；明确说明可不依赖 LangChain 独立使用。其公共接口受 NetworkX 启发，设计背景提及 Pregel 与 Apache Beam。

**Operit2 对照**：LangGraph 解决应用定义的图执行和状态管理；Operit2 的个人设备空间、Host 平台能力和业务副本是另一个设计维度。这些维度可以组合，不能用“框架只适合云端、Operit2 才能本地运行”进行未经依据的优劣对比。

**不能据此推导**：仓库宣传语已经独立证明无丢失恢复；任何 checkpointer 均可跨重启；图编排自动包含设备成员关系和授权。

### [R09] LangGraph Checkpointers

**来源**：LangChain. *Checkpointers*，官方文档。

- 已读：<https://docs.langchain.com/oss/python/langgraph/checkpointers>。
- 背景已读：<https://docs.langchain.com/oss/python/langgraph/persistence>。
- 核查日期：2026-11-07。

**可引用发现**：checkpointer 以 thread 保存每个 super-step 的图状态快照，同时记录步骤内已完成节点的 pending writes，避免同一 super-step 其它节点失败时重算这些成功节点。`thread_id` 标识已保存状态；新输入、错误后恢复、interrupt 恢复、历史重放具有不同调用方式。单独复用 thread ID 不意味着继续未完成执行。一般持久化文档还明确区分线程内 checkpointer 与跨线程 store，指出内存 saver 无法跨进程重启保留状态。

**Operit2 对照**：应给出自己的“可继续边界”，而不是泛称支持 checkpoint。工具结果持久化之后、下一次模型请求之前是一种应用层恢复/交接边界，与 LangGraph 的 super-step 边界不是同一抽象。

**不能据此推导**：已保存聊天消息等同于完整工作流检查点；任何进程本地句柄都可序列化；一个节点迁往另一节点后能继续使用原终端进程、网络连接或浏览器会话。

**链接变更记录**：此次读取 `https://docs.langchain.com/oss/python/langgraph/durable-execution` 返回的是标题为 *Persistence* 的通用页，因此白皮书应使用上述实际已读页面，不应据旧 URL 标题引用旧版内容。

### [R10] LangGraph Functional API：恢复、确定性与幂等性

**来源**：LangChain. *Functional API*，官方文档。

- 已读：<https://docs.langchain.com/oss/python/langgraph/functional-api>。
- 核查日期：2026-11-07。

**可引用发现**：恢复不会跳回中断的精确源代码行。Functional API 从 entrypoint 开始重放，从 checkpointer 恢复已完成 task 和 subgraph 的结果；非确定性操作和副作用应封装为 task。已开始但尚未完成记录的 task 可能再次运行，因此仍需设计幂等操作或使用幂等键。序列化也是显式前提：配置 checkpointer 时 entrypoint 输入/输出及 task 输出需要 JSON 可序列化。

**Operit2 对照**：适合给“状态继续执行”下精确定义，说明持久化结果、可重放决策与活动执行资源之间的区别；也能指导白皮书的实验矩阵覆盖“操作已成功、完成记录未落盘”这一故障窗口。

**不能据此推导**：持久化框架能回滚外部副作用；同一个业务请求在故障后绝不重复；磁盘保存结果与远端服务执行构成原子事务。

### [R11] Temporal 官方实现

**来源**：Temporal contributors. *temporalio/temporal*，官方服务器仓库。

- 已读：<https://github.com/temporalio/temporal>。
- 核查日期：2026-11-07。

**可引用发现**：Temporal 将自身定位为 durable execution 平台，服务端持久地编排 Workflow，应用通过语言 SDK 定义 Workflow、Activity 和 Worker。官方仓库明确区分服务器和应用 SDK/Worker。

**Operit2 对照**：可讨论集中式持久工作流基础设施与个人设备自治运行时在部署、状态权威和平台能力上的不同。只比较设计目标和机制，不凭项目规模推测可靠性或吞吐。

**不能据此推导**：Operit2 不需要中央服务器就具有与 Temporal 相同的故障恢复和调度保证；“去中心”必然更可靠；两个项目存在性能排名。

### [R12] Temporal Activity 定义与幂等性

**来源**：Temporal. *Activity Definition*，官方文档。

- 已读：<https://docs.temporal.io/activity-definition>。
- 核查日期：2026-11-07。

**可引用发现**：官方文档给出明确故障窗口：Worker 完成外部操作后、向服务端报告完成前崩溃，可能导致 Activity 被再次执行。文档区分“observed as completed exactly once”和 Activity 可能执行多次、部分完成多次。业务副作用应幂等，幂等键通常需要由被调用的外部服务实施，而不是 Activity 函数单方面声明。

**Operit2 对照**：白皮书可明确把“同步操作重复应用的幂等性”和“工具对外产生副作用的幂等性”分开。Binding 的代次或本地执行互斥即使约束了某层调度，也不能直接推出付款、发信、删除文件等外部操作的 exactly-once。

**不能据此推导**：请求 ID、持久日志、取消、超时、租约或路由切换单独就能实现外部副作用唯一。若本项目尚无外部幂等协议，应明确留下这一限制。

### [R13] Model Context Protocol 规范

**来源**：Model Context Protocol maintainers. *Model Context Protocol Specification*, revision 2025-11-25。

- 已读固定版规范：<https://modelcontextprotocol.io/specification/2025-11-25>。
- 已读官方仓库：<https://github.com/modelcontextprotocol/modelcontextprotocol>。
- 核查日期：2026-11-07。

**可引用发现**：该版本通过 JSON-RPC 2.0 组织 Host、Client、Server，定义能力协商及资源、提示、工具等功能，并包含 sampling、roots、elicitation 等可选客户端能力。规范强调用户同意、数据隐私、工具安全，明确协议本身不能强制落实全部安全原则，具体应用应负责授权与保护。

**Operit2 对照**：将 MCP 作为工具系统的互操作接入，与 ToolPkg、Skill、自身 Host API 的职责分别说明。`MCP Host` 是协议角色，不要与 Operit2 的 OS Host 适配 trait 混为一谈。必须按代码写出传输和功能支持范围；引用规范不意味着项目实现了全部规范。

**不能据此推导**：接入工具即可信；工具描述或 annotations 是安全证明；MCP 客户端具备 OS 隔离；MCP 与 Operit2 Space/Binding 同义。

### [R14] MCP 安全最佳实践

**来源**：Model Context Protocol maintainers. *Security Best Practices*, revision 2025-11-25。

- 已读：<https://modelcontextprotocol.io/specification/2025-11-25/basic/security_best_practices>。
- 核查日期：2026-11-07。

**可引用发现**：文档分析 confused deputy、token passthrough、OAuth 发现过程的 SSRF 和 session hijacking。尤其强调 MCP 服务不能接收不是明确签发给自己的 token，应用不能把 session ID 当作身份认证的替代，动态发现端点和重定向目标需要按部署环境限制。

**Operit2 对照**：威胁模型应包括恶意插件/服务器、提示注入、凭据作用域、远端 URL 与本地网络访问。批准一次工具调用不等于验证其全部传递依赖。白皮书应区分“代码已有约束”“操作者部署条件”“尚需审计的攻击面”。

**不能据此推导**：使用 TLS 就解决授权；任意远端服务与节点共享请求头都安全；插件的运行容器天然隔离被调用 Host 能力。

### [R15] Agent2Agent (A2A)

**来源**：A2A Project. *Agent2Agent (A2A) Protocol Specification*，官方规范；同时核查官方仓库。规范随项目演进，本文引用访问时内容，不以 `latest` 链接声称永久固定版本。

- 已读规范：<https://a2a-protocol.org/latest/specification/>。
- 已读官方仓库：<https://github.com/a2aproject/A2A>。
- 核查日期：2026-11-07。

**可引用发现**：A2A 面向独立且可能不透明的 Agent 系统，允许发现能力、交换消息、管理任务、获取交付物，不要求共享内部思维、记忆或工具。当前规范把 canonical data model、abstract operations 与 concrete protocol bindings 分开；Agent Card、Task、Message、Part 和 Artifact 是关键概念，异步状态与取消是协议交互的一部分。

**Operit2 对照**：已有本地 A2A 扩展文档声明 JSON-RPC 1.0/0.3 客户端范围，并列出未实现 SSE、推送、服务端和其它绑定；需由代码审查确认。A2A 对接的是外部 Agent，Space 对接的是同一应用体系中的成员节点与授权业务复制。前者可以在保留内部状态的前提下协作，后者可能复制继续执行所需的业务状态，两者的信任与同步边界不同。

**不能据此推导**：支持 `send_message/get_task/cancel_task` 就完整支持所有协议绑定；远端接受取消请求就必然终止活动工作；A2A Agent 自动获得 CoreNode 的设备成员身份；外部状态的 `completed` 能证明工具副作用未重复。

### [R16] Syncthing：文件复制

**来源**：Syncthing contributors. *Block Exchange Protocol v1*，官方规范及实现仓库。

- 已读协议：<https://docs.syncthing.net/specs/bep-v1.html>。
- 已读官方仓库：<https://github.com/syncthing/syncthing>。
- 核查日期：2026-11-07。

**可引用发现**：BEP 的本地模型包含文件元数据和块哈希，设备交换模型并请求缺失或过期块以趋向全局模型。当前规范明确可靠传输之上使用 TLS 1.3 或更高版本进行加密与认证，参考实现使用证书指纹作为 Device ID。仓库定位是个人设备之间持续文件同步。

**Operit2 对照**：可以说明“同步整个文件”与“按领域操作复制数据库和偏好”的语义区别，以及内容哈希为何适合 Blob 完整性校验/去重。工作区文件复制仍必须定义目录范围、冲突、删除和本地排除规则。

**不能据此推导**：把 SQLite 文件交给一般文件同步就等同于事务复制；文件块一致意味着业务记录引用一致；加密传输解决节点是否应读取该数据的授权问题。

### [R17] iroh：端点连通性与协议分层

**来源**：n0 contributors. *n0-computer/iroh*，官方开源实现。

- 已读官方仓库：<https://github.com/n0-computer/iroh>。
- 核查日期：2026-11-07。

**可引用发现**：iroh 提供按公钥寻址的端点连接，使用 QUIC 提供认证加密与并发流，并有 NAT 穿透与 relay 机制。仓库把 blob 传输、gossip 与文档键值复制作为可组合的上层协议列出；连接层和数据语义层由此分开。

**Operit2 对照**：适合解释 Link transport、成员路由、业务授权、同步与执行调度各自承担的职责。本项目实际 transport 仍以依赖和代码为准；此处是架构层级的参照，不表示采用了 iroh。

**不能据此推导**：任何 LAN 发现实现均具有公网 NAT 穿透；知道端点公钥就具备文件/终端使用权限；QUIC 的并发流提供业务事务原子性或 Agent 任务继续执行。

### [R18] Letta 当前实现方向

**来源**：Letta contributors. *letta-ai/letta-code*，官方活跃实现仓库。

- 已读活跃仓库：<https://github.com/letta-ai/letta-code>。
- 已读迁移声明：<https://github.com/letta-ai/letta>。
- 核查日期：2026-11-07。

**可引用发现**：旧 `letta` 仓库声明当前活跃代码已转向 `letta-code`。当前 README 描述有状态 Agent harness、记忆块、消息检索、skills、权限、计划任务和 remote computers，明确提供 cloud/local backend 选择。其云模式描述为由 Letta Cloud 保存 Agent 记忆、身份和会话，并可路由到不同计算机执行。这里只核查 README 功能声明，没有审计其实现或性能。

**Operit2 对照**：可把 MemGPT 的历史研究和 Letta 的当前产品架构分别引用。Operit2 应说明自身节点本地身份、授权副本和 Space 的具体权威边界；不能把跨设备、长期记忆或可本地运行当作独有特征。若讨论云/本地差别，必须指明所比较的部署模式。

**不能据此推导**：Letta 只能中心服务器部署；其所有模式都使用相同同步/信任模型；README 所述“learn/self-improve”已证明普遍的在线模型学习；两项目存在可量化优越性。

## 3. 建议在白皮书中写出的边界

1. **问题陈述**：个人多设备 Agent 的困难是能力异构、状态持久化、授权和不稳定连接同时出现。可借 local-first 说明数据控制目标，用 ReAct/Toolformer 解释工具使用背景。不要把这些既有概念包装为本项目原创算法。
2. **贡献表述**：可采用“统一 Host 能力边界、按持久事实继续执行、领域操作复制、个人设备协作范围”这样的工程贡献；每一项须对应本地代码证据。避免首创、领先、无限扩展或固有可靠等没有对照实验的表述。
3. **一致性**：明确单数据集原子提交、操作接收、已应用标志、收据和跨数据集引用的范围。逻辑顺序、内容收敛和执行互斥分开论证。若没有证明，不使用 CRDT/SEC/线性一致作为产品保证。
4. **执行语义**：区分工具操作、结果持久化、下一次模型请求、Binding 切换和远端继续。专门说明操作已经产生副作用而结果尚未持久化的故障窗口，引用 Temporal 和 LangGraph 的幂等性限制。
5. **记忆**：原始记录、摘要、检索索引、可写长期事实、当前提示分层。保存历史和恢复任务不意味着恢复模型内部未公开的状态，也不意味着模型能无损还原所有历史。
6. **安全**：威胁模型应列出网络对手、被攻陷成员、恶意插件/模型输出、错误审批与凭据泄露。Host API 是能力抽象；OS sandbox、应用能力限制与用户审批是不同层。凡是依赖操作者部署条件的安全性，应直接列出这些条件。
7. **互操作**：MCP、A2A 与 Space 各自有不同接口和信任对象；引用协议时固定版本或写访问日期，并给出实际支持子集。不同协议拥有相近的 task/session/thread 术语，不能据名称合并语义。
8. **评估**：将设计分析与实测结果分开。未运行的故障注入实验写作待验证方法；不能把外部论文成绩、仓库星数、静态测试文件数或架构图当成本系统性能证据。

## 4. 推荐实验问题（本次未运行）

| 研究问题 | 可操作实验 | 需要报告的指标 | 关键否证条件 |
| --- | --- | --- | --- |
| 交接是否保留已确认事实 | 在工具开始、成功、结果提交、Binding 更新、远端接收等边界注入故障 | 可继续比例、重复模型请求数、重复工具副作用、丢失结果、恢复时间 | “结果已提交”与“目标可读”之间仍有依赖未满足 |
| 复制是否在所定义范围内收敛 | 多节点离线并发、乱序/重复操作、重连、缺 Blob、业务 owner 验证失败 | 内容摘要、操作覆盖、待应用队列、流量、重放时间与峰值内存 | 收据推进而业务事实丢失，或不同重放顺序得到不同最终可见值 |
| 授权是否控制传播与执行 | 撤销 storage 授权、退出 Space、移除成员、插件停用后再发送请求 | 被拒绝调用、泄漏字节、仍保留的数据范围、撤销生效延迟 | 仅有连接/成员身份就允许读业务 Blob 或调用 Host |
| 异构设备是否正确表达能力 | 相同任务在桌面、移动端、浏览器和 Edge 上请求不支持能力 | 明确拒绝率、错误定位、无权限误执行、平台能力声明准确度 | 不支持的操作被标记为成功，或审批绕过本机权限 |
| 长期运行成本是否可接受 | 随历史记录数、Blob 量和节点数增长，测空闲与增量同步 | CPU、内存、数据库/日志增长、每轮传输、p50/p95 延迟 | 空闲周期重复全量、历史大小导致不可控工作集、活动资源泄漏 |

这些是可重复评估设计，不是已取得的结果。白皮书如不包含本项目实测，应采用“设计与实现白皮书/系统设计论文”定位，明确性能、故障恢复和攻击面验证的证据缺口。
