# 阶段二：文献调研

| 项目 | 内容 |
| --- | --- |
| 日期 | 2026-11-10 |
| 输入 | [阶段一](01-scope-and-problem.md) §10 的主题与种子文献；2.0 的 `research/related-work.md` |
| 书目核验 | Crossref REST API（按 DOI 或书目串查询）；arXiv API（版本、作者、日期、评注）；USENIX 论文以 PDF 首页的会议录信息为准 |
| 内容核验 | 从作者主页或会议的开放 PDF 下载全文，经 `pdftotext` 转为文本后定位引用句；HTML 页面经检索工具读取指定段落 |
| 检索 | arXiv API 10 条检索式；Semantic Scholar 7 条检索式因 HTTP 429 限流未取得结果，改用其批量接口取回已知文献的摘要 |
| 状态 | 完成。§5 修订了阶段一 §5 的新颖性判断 |

## 0. 阅读级别

| 级别 | 含义 | 可支持的用法 |
| --- | --- | --- |
| 全文 | 读到全文，引用句已在原文中定位 | 机制、定义与结论 |
| 正文（部分） | 读到 HTML 正文的相关部分 | 已定位的段落所陈述的内容 |
| 摘要 | 只读到摘要或作者评注 | 只用于说明“该工作研究什么”或作者报告的结论，正文中注明“作者报告” |
| 书目 | 只核验了书目信息 | 只用于标注工具或形式体系的出处，不支撑任何论断 |

## 1. 检索记录

检索日期为 2026-11-10，数据库为 arXiv（`export.arxiv.org/api/query`，按相关度排序，每式取前 15 条）。

| 检索式 | 命中数 | 纳入 |
| --- | ---: | --- |
| `abs:"LLM agent" AND abs:migration AND abs:device` | 1 | MVVM |
| `abs:"agent" AND abs:"handoff" AND abs:"language model"` | 45 | 《When "Must" Becomes "Maybe"》。其余为多 Agent 之间的任务交接或强化学习，与跨设备执行无关 |
| `abs:"cross-device" AND abs:"agent" AND abs:"language model"` | 7 | UFO³、TopoClaw、Unified Agent、Nexus |
| `abs:"durable execution" AND abs:agent` | 3 | 2606.17182（形式化并发异常）。另两篇研究工作流验证与预算上界，排除 |
| `abs:"exactly-once" AND abs:"language model"` | 9 | 无。命中项与执行语义无关 |
| `abs:"LLM agent" AND abs:checkpoint AND abs:recovery` | 14 | Atomix、ACRFence、AgentRewind。推理检查点与 RL 训练容错类工作排除 |
| `abs:"agent" AND abs:"fault tolerance" AND abs:"tool calls"` | 3 | Crab |
| `abs:"personal devices" AND abs:"LLM" AND abs:agent` | 6 | Personal LLM Agents 综述 |
| `abs:"agent state" AND abs:migration AND abs:LLM` | 0 | — |
| `abs:"session" AND abs:"continuity" AND abs:"LLM"` | 112 | 《Compaction as Epistemic Failure》。其余为对话记忆与咨询类应用，排除 |

纳入标准：研究对象是 LLM Agent 的执行、恢复、迁移、交接或其外部效果，或者为本文的形式模型提供定义、定理与机制。排除标准：只研究模型训练、推理内核性能或特定应用领域的对话质量。

局限：arXiv 以外的同行评审文献只通过已知文献的引文与种子清单覆盖；Semantic Scholar 的关键词检索未能执行，同行评审会议中可能存在未被发现的相关工作。

## 2. 文献矩阵

“定位”列给出引用句在原文中的位置。阅读级别为“全文”的条目，引用句均已在下载的全文中逐字核对。

### 2.1 分布式系统基础

| 键 | 书目 | 级别 | 本文引用的内容（定位） | 不能据此推出 |
| --- | --- | --- | --- | --- |
| Lam78 | L. Lamport. Time, Clocks, and the Ordering of Events in a Distributed System. *CACM* 21(7):558–565, 1978. DOI 10.1145/359545.359563 | 全文（2.0 已读） | happened-before 偏序；逻辑时钟可以构造与偏序一致的全序 | 逻辑时间较大等于物理时间较晚 |
| FLP85 | M. J. Fischer, N. A. Lynch, M. S. Paterson. Impossibility of Distributed Consensus with One Faulty Process. *JACM* 32(2):374–382, 1985. DOI 10.1145/3149.214121 | 全文 | “no completely asynchronous consensus protocol can tolerate even a single unannounced process death”（引言） | 部分同步或随机化系统中同样不可能 |
| GL02 | S. Gilbert, N. Lynch. Brewer's Conjecture and the Feasibility of Consistent, Available, Partition-Tolerant Web Services. *SIGACT News* 33(2):51–59, 2002. DOI 10.1145/564585.564601 | 全文 | 定理 1：异步网络模型中无法实现同时保证可用性与原子一致性的读写对象；证明要点是算法无法区分消息丢失与任意延迟 | 部分同步模型中的取舍与该定理相同 |
| Lam98 | L. Lamport. The Part-Time Parliament. *ACM TOCS* 16(2):133–169, 1998. DOI 10.1145/279227.279229 | 全文 | 每个 ballot 有唯一编号（B1）；任意两个 ballot 的 quorum 至少有一个公共成员（B2）；多数成员在场且足够久时提案可通过 | 两成员系统可以在一个成员失效时取得进展 |
| GC89 | C. G. Gray, D. R. Cheriton. Leases: An Efficient Fault-Tolerant Mechanism for Distributed File Cache Consistency. *SOSP* 1989, 202–210. DOI 10.1145/74850.74870 | 全文 | 租约是“在有限期限内授予持有者对某对象特定权利的契约”；短租约可减少故障后的等待；服务器无法联系持有者时必须等到租约到期；“Leases depend on well-behaved clocks”，需要为时钟偏差预留 ε（引言与容错讨论部分；pdftotext 未保留章节号） | 时钟故障下仍然正确 |
| Bur06 | M. Burrows. The Chubby Lock Service for Loosely-Coupled Distributed Systems. *OSDI* 2006. https://research.google/pubs/the-chubby-lock-service-for-loosely-coupled-distributed-systems/ | 全文 | §2.4：持锁进程发出请求 R 后失效，另一进程取得锁并行动，R 迟到后会在没有锁保护的情况下被执行；sequencer 包含锁名、模式与锁代次，接收服务器检验其仍然有效，否则拒绝；不支持 sequencer 的服务器用 lock-delay 降低风险 | 只靠锁本身就能防止迟到请求 |
| SRC84 | J. H. Saltzer, D. P. Reed, D. D. Clark. End-to-End Arguments in System Design. *ACM TOCS* 2(4):277–288, 1984. DOI 10.1145/357401.357402 | 全文 | “The function in question can completely and correctly be implemented only with the knowledge and help of the application standing at the end points of the communication system.” | 下层机制毫无价值（原文承认其可作为性能优化） |
| GS87 | H. Garcia-Molina, K. Salem. Sagas. *SIGMOD* 1987, 249–259. DOI 10.1145/38713.38742 | 全文 | 长事务可以写成可交错执行的事务序列；saga 的部分执行“must be compensated for”，即通过补偿事务处理 | 所有外部效果都存在补偿操作 |

### 2.2 弱连接复制与本地优先

| 键 | 书目 | 级别 | 本文引用的内容（定位） | 不能据此推出 |
| --- | --- | --- | --- | --- |
| Ter95 | D. B. Terry, M. M. Theimer, K. Petersen, A. J. Demers, M. J. Spreitzer, C. H. Hauser. Managing Update Conflicts in Bayou, a Weakly Connected Replicated Storage System. *SOSP* 1995, 172–182. DOI 10.1145/224056.224070 | 全文 | 每次更新附带应用定义的依赖检查与合并过程；更新分为 tentative 与 committed 两种状态；采用 primary 提交方案，由一台服务器决定提交顺序，这台 primary 也可以是一台断网的笔记本 | 去掉 primary 后仍有确定的提交顺序 |
| KS92 | J. J. Kistler, M. Satyanarayanan. Disconnected Operation in the Coda File System. *ACM TOCS* 10(1):3–25, 1992. DOI 10.1145/146941.146942 | 摘要 | 断连操作使客户端在共享存储暂时失效时仍可访问关键数据 | 只作为背景提及 |
| SPBZ11 | M. Shapiro, N. Preguiça, C. Baquero, M. Zawirski. Conflict-Free Replicated Data Types. *SSS* 2011, LNCS 6976, 386–400. DOI 10.1007/978-3-642-24550-3_29 | 全文（2.0 已读） | 强最终一致性：收到同一组更新的正确副本状态等价；模型假设非拜占庭进程 | 副本收敛蕴含执行唯一 |
| KWHM19 | M. Kleppmann, A. Wiggins, P. van Hardenberg, M. McGranaghan. Local-First Software: You Own Your Data, in Spite of the Cloud. *Onward!* 2019, 154–178. DOI 10.1145/3359591.3359737 | 全文（2.0 已读） | 本地优先的七项理想；设备上的副本是主要数据，而不是服务端权威副本的缓存 | 所有数据都应复制到每台设备 |

### 2.3 代码迁移与移动 Agent

| 键 | 书目 | 级别 | 本文引用的内容（定位） | 不能据此推出 |
| --- | --- | --- | --- | --- |
| FPV98 | A. Fuggetta, G. P. Picco, G. Vigna. Understanding Code Mobility. *IEEE TSE* 24(5):342–361, 1998. DOI 10.1109/32.685258 | 书目 | 强迁移与弱迁移分类的原始出处（定义原文见 CPV07） | 未读原文中关于资源绑定的论述，本文不引用该部分 |
| CPV07 | A. Carzaniga, G. P. Picco, G. Vigna. Is Code Still Moving Around? Looking Back at a Decade of Code Mobility. *ICSE Companion* 2007, 9–20. DOI 10.1109/ICSECOMPANION.2007.44 | 全文 | §2.1：强迁移允许执行单元把代码与执行状态（栈、指令指针）移到另一站点，挂起、传输、恢复；弱迁移不传输执行状态，“even though some data state could be transferred, the executing unit would need to be restarted upon arrival”；文中注明分类出自 FPV98 | —— |
| PS03 | S. Pleisch, A. Schiper. Fault-Tolerant Mobile Agent Execution. *IEEE Trans. Computers* 52(2):209–222, 2003. DOI 10.1109/TC.2003.1176987 | 全文 | 假设异步系统与崩溃故障（§2、§2.2）；非阻塞要求单个故障下执行仍能继续，靠复制实现，“However, replication may lead to multiple executions”（结论节）；不可靠的故障检测是违反 exactly-once 的另一来源（§3.4）；每阶段用一次共识决定执行结果，所依赖的共识算法需要 ◇S 故障检测器与多数正确进程（§5.1） | 少于三个参与者时可以同时得到非阻塞与 exactly-once |

### 2.4 持久执行与外部效果

| 键 | 书目 | 级别 | 本文引用的内容（定位） | 不能据此推出 |
| --- | --- | --- | --- | --- |
| BGJ21 | S. Burckhardt, C. Gillum, D. Justo, K. Kallas, C. McMahon, C. S. Meiklejohn. Durable Functions: Semantics for Stateful Serverless. *PACMPL* 5(OOPSLA):133, 2021. DOI 10.1145/3485510 | 全文 | 以事件历史保存编排状态，靠重放恢复；“the orchestration code must be deterministically replayable”，读取非确定数据或调用 I/O 必须包装为 activity 以便记录和重放（编排语义的非形式描述部分）；存储触发器“do not in fact guarantee exactly-once execution”（§1，挑战 C3） | LLM 调用可以直接放在编排代码中重放 |
| Bel20 | H. Zhang, A. Cardoza, P. B. Chen, S. Angel, V. Liu. Fault-tolerant and Transactional Stateful Serverless Workflows. *OSDI* 2020. https://www.usenix.org/conference/osdi20/presentation/zhang-haoran | 全文 | exactly-once 的定义：函数无论崩溃并重启多少次，结果状态都等价于恰好执行一次；做法是把操作日志写入数据库，并用 intent 表与收集器完成未结束的调用（设计目标部分、图 1） | 同样适用于不受控的第三方外部服务 |
| Tmp26 | Temporal Technologies. Activity Definition. 官方文档，访问于 2026-11-10。https://docs.temporal.io/activity-definition | 正文 | Activity 保证“observed as completed exactly once”，但可能被执行多次；Worker 在通知服务前崩溃时会重试；幂等键“enforced by the service you are calling from your Activity, not by the Activity itself” | 工程文档，不是独立实验 |
| Atx26 | B. Mohammadi, N. Potamitis, L. Klein, A. Arora, L. Bindschaedler. Atomix: Timely, Transactional Tool Use for Reliable Agentic Workflows. arXiv:2602.14849v2, 2026. DOI 10.48550/arXiv.2602.14849 | 正文（部分） | 以 epoch 与按资源的 frontier 决定提交；效果分为可逆（先执行，中止时补偿）、可缓冲（提交时才发出）与不可逆（在网关处等待提交）；作者声明“We do not claim semantic validation, distributed deployment, or full crash-safe exactly-once”，原型为单进程 Python 运行时 | 同样适用于多设备 |
| ACR26 | Y. Zheng, Y. Yang, W. Zhang, A. Quinn. ACRFence: Preventing Semantic Rollback Attacks in Agent Checkpoint-Restore. arXiv:2603.20625v1, 2026. DOI 10.48550/arXiv.2603.20625 | 正文（部分） | LLM Agent 在恢复后会重新合成略有不同的请求，服务器把它们视为新请求，导致重复付款等后果，使“重试安全”的建议失效；作者提出记录不可逆效果，恢复时执行“replay-or-fork”；概念验证中，检查点恢复的 10 次试验全部产生重复；ACRFence 本身尚未实现 | 该缓解机制已经验证 |

### 2.5 LLM Agent 运行时、迁移与恢复

| 键 | 书目 | 级别 | 本文引用的内容（定位） | 不能据此推出 |
| --- | --- | --- | --- | --- |
| Yao23 | S. Yao, J. Zhao, D. Yu, et al. ReAct: Synergizing Reasoning and Acting in Language Models. *ICLR* 2023. arXiv:2210.03629v3. DOI 10.48550/arXiv.2210.03629 | 全文（2.0 已读） | 推理、行动与观察交错的交互范式 | 复现其实验结果 |
| Pac23 | C. Packer, S. Wooders, K. Lin, et al. MemGPT: Towards LLMs as Operating Systems. arXiv:2310.08560v2, 2023. DOI 10.48550/arXiv.2310.08560 | 全文（2.0 已读） | 主上下文与外部上下文分层；接近容量时生成递归摘要，被逐出的消息仍保存在 recall storage 中 | 摘要无损 |
| Mei25 | K. Mei, X. Zhu, W. Xu, et al. AIOS: LLM Agent Operating System. *COLM* 2025. arXiv:2403.16971v5. DOI 10.48550/arXiv.2403.16971 | 正文（检索摘录） | 上下文管理器以基于文本与基于 logits 两种方式对生成过程做快照与恢复，用于单机调度中暂停 Agent 请求 | 可用于远程 Provider |
| Sun24 | B. Sun, Z. Huang, H. Zhao, W. Xiao, X. Zhang, Y. Li, W. Lin. Llumnix: Dynamic Scheduling for Large Language Model Serving. *OSDI* 2024. https://www.usenix.org/conference/osdi24/presentation/sun-biao | 全文 | 在模型实例之间实时迁移请求及其 GPU 内存状态（KV cache），停机时间近乎为零，且与序列长度无关 | 跨设备、跨 Provider 同样可行 |
| Wan25 | X. Wang, J. He, Z. Tang, et al. Adaptive AI Agent Placement and Migration in Edge Intelligence Systems. arXiv:2508.03345v1, 2025. DOI 10.48550/arXiv.2508.03345 | 摘要 | 在资源受限的边缘环境中放置与迁移 LLM Agent，以服务质量与时延为目标 | 讨论所有权安全 |
| Yan25 | Y. Yang, A. Hu, Y. Zheng, et al. MVVM: Deploy Your AI Agents—Securely, Efficiently, Everywhere. arXiv:2410.15894v2, 2025. DOI 10.48550/arXiv.2410.15894 | 正文（部分） | 在 Wasm 层的稳定点做检查点与恢复，实时迁移 Agent 工作区；副本间以向量时钟保证最终一致，“allowing temporary divergence during network partitions”；正文未讨论所有权、隔离或外部效果的 exactly-once | —— |
| Zha25 | C. Zhang, L. Li, H. Huang, et al. UFO³: Weaving the Digital Agent Galaxy. arXiv:2511.11332v2, 2025. DOI 10.48550/arXiv.2511.11332 | 正文（部分） | ConstellationAgent 是位于全局控制平面上的“central intelligence”；不变式 I1 要求每个子任务同一时刻至多分配给一台设备；设备断开后任务被标记为失败并修订 DAG | 讨论进行中任务的所有权转移 |
| Hua26 | H. Huang, Y. Guan, J. Wang, et al. TopoClaw: A Human-Centric and Topology-Aware Agent Operating System. arXiv:2605.15556v1, 2026. DOI 10.48550/arXiv.2605.15556 | 正文（部分） | 中心“认知枢纽”决定做什么，放置引擎决定动作在哪台设备执行；推理不在设备间迁移；未讨论断连、重试与执行唯一性 | —— |
| Cha26 | C. Chang, J. Zhou. Nexus: An Execution Fabric for AI Agents Across Cloud, Edge, and Devices. arXiv:2610.05709v1, 2026. DOI 10.48550/arXiv.2610.05709 | 正文（部分） | 云端保存持久调用记录；worker 分配使用有时限的执行租约，云端在接受结果前检查租约；效果不确定时要求显式的恢复决定；不保证 exactly-once；没有描述运行中 Agent 的跨设备迁移 | —— |
| Liu26 | X. Liu, R. B. Li, S. Wei, X. Lin, T. Nguyen. Unified Agent: Managing Interactions across Devices. arXiv:2608.05729v1, 2026. DOI 10.48550/arXiv.2608.05729 | 摘要 | 为跨设备、跨时间的请求设计紧凑的“carried state” | 执行位置的协议设计 |
| Zhu26 | Y. Zhuang, K. Chen, Y. Duan, et al. AgentRewind: Recoverable Execution for Long-Horizon LLM Agents. arXiv:2608.14380v1, 2026. DOI 10.48550/arXiv.2608.14380 | 摘要 | 对 Agent 上下文与受控环境做对齐的检查点，回退后继续执行 | —— |
| Wu26 | T. Wu, C. Chang, L. Cao, W. Gao, W. Wang. Crab: A Semantics-Aware Checkpoint/Restore Runtime for Agent Sandboxes. arXiv:2604.28138v1, 2026. DOI 10.48550/arXiv.2604.28138 | 摘要 | 指出 Agent 框架只看到工具调用、看不到其 OS 效果的“语义鸿沟”；检查点对齐到回合边界；作者报告超过 75% 的回合不产生与恢复相关的状态 | —— |
| Kha26 | S. Khan. Verified Detection and Prevention of Concurrency Anomalies in Multi-Agent Large Language Model Systems. arXiv:2606.17182v1, 2026. DOI 10.48550/arXiv.2606.17182 | 正文（部分） | 用 TLA+ 形式化 stale-generation 等四类并发异常，并给出 TLC 反例；模型是单一逻辑存储、无复制，假设生成确定；不涉及跨设备所有权或分区 | —— |
| Li24 | Y. Li, H. Wen, W. Wang, et al. Personal LLM Agents: Insights and Survey about the Capability, Efficiency and Security. arXiv:2401.05459v2, 2024. DOI 10.48550/arXiv.2401.05459 | 摘要 | 与个人数据、个人设备深度集成的 LLM Agent 综述 | —— |

### 2.6 上下文、交接与认知失效

| 键 | 书目 | 级别 | 本文引用的内容（定位） | 不能据此推出 |
| --- | --- | --- | --- | --- |
| Liu24 | N. F. Liu, K. Lin, J. Hewitt, et al. Lost in the Middle: How Language Models Use Long Contexts. *TACL* 12:157–173, 2024. DOI 10.1162/tacl_a_00638 | 摘要 | 作者报告：相关信息位于长上下文中部时，模型表现显著下降 | 对特定模型或任务的定量结论 |
| Sun26 | Y. Sun, H. Wang, Y. Zhu, et al. When "Must" Becomes "Maybe": Erosion of Workflow Constraints in LLM Agent Handoffs. arXiv:2608.24569v2, 2026. DOI 10.48550/arXiv.2608.24569 | 摘要 | 作者报告：直接传递状态的交接保留了全部安全阻断条件，而压缩、计划吸收等交接方式会反复削弱这些条件 | 跨设备交接的定量结果 |
| Tam26 | H. Tamba. Compaction as Epistemic Failure: How Agentic LLM Tools Fabricate Confirmed Results from Killed Processes. arXiv:2607.13071v2, 2026. DOI 10.48550/arXiv.2607.13071 | 正文 | 单一用户的案例报告：命令超时被杀（exit 143）后，终端里已出现的部分输出在压缩摘要中被记为“已完成”，后续会话不加核实地继承；作者归因为“conflation of observation and persistence” | 普遍发生率 |

### 2.7 安全、人机交互与形式化方法

| 键 | 书目 | 级别 | 本文引用的内容（定位） | 不能据此推出 |
| --- | --- | --- | --- | --- |
| SS75 | J. H. Saltzer, M. D. Schroeder. The Protection of Information in Computer Systems. *Proc. IEEE* 63(9):1278–1308, 1975. DOI 10.1109/PROC.1975.9939 | 正文（§I.A.3） | 失败安全默认、完全仲裁（“Every access to every object must be checked for authority”）、最小特权与心理可接受性 | —— |
| Gre23 | K. Greshake, S. Abdelnabi, S. Mishra, C. Endres, T. Holz, M. Fritz. Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection. *AISec* 2023, 79–90. DOI 10.1145/3605764.3623985 | 摘要 | 攻击者把提示注入到可能被检索的数据中，可以操纵应用功能，并控制“how and if other APIs are called” | —— |
| Bru19 | F. Brudy, C. Holz, R. Rädle, C.-J. Wu, S. Houben, C. N. Klokmose, N. Marquardt. Cross-Device Taxonomy: Survey, Opportunities and Challenges of Interactions Spanning Across Multiple Devices. *CHI* 2019, 1–28. DOI 10.1145/3290605.3300792 | 摘要 | 对 510 篇跨设备研究论文的分析与分类 | —— |
| DP08 | D. Dearman, J. S. Pierce. “It's on my other computer!”: Computing with Multiple Devices. *CHI* 2008, 767–776. DOI 10.1145/1357054.1357177 | 全文 | 访谈 27 人；“Participants assign different devices different roles within a task, but devices have no notion that their actions are part of a larger task” | —— |
| Cue10 | E. Cuervo, A. Balasubramanian, D. Cho, A. Wolman, S. Saroiu, R. Chandra, P. Bahl. MAUI: Making Smartphones Last Longer with Code Offload. *MobiSys* 2010, 49–62. DOI 10.1145/1814433.1814441 | 摘要 | 方法级细粒度卸载；作者指出以往方法或依赖程序员划分，或“coarse-grained requiring full process (or full VM) migration” | —— |
| New15 | C. Newcombe, T. Rath, F. Zhang, B. Munteanu, M. Brooker, M. Deardeuff. How Amazon Web Services Uses Formal Methods. *CACM* 58(4):66–73, 2015. DOI 10.1145/2699417 | 全文 | 一些危险的缺陷来自设计本身：代码忠实实现了设计，而设计没有处理罕见场景；AWS 使用 TLA+ 描述并检查设计 | 模型检查等于证明实现正确 |
| Lam94 | L. Lamport. The Temporal Logic of Actions. *ACM TOPLAS* 16(3):872–923, 1994. DOI 10.1145/177492.177726 | 书目 | 本文所用规约逻辑的出处 | —— |
| YML99 | Y. Yu, P. Manolios, L. Lamport. Model Checking TLA+ Specifications. *CHARME* 1999, LNCS 1703, 54–66. DOI 10.1007/3-540-48153-2_6 | 书目 | 本文所用模型检查器 TLC 的出处 | —— |

## 3. 弃用与未核验条目

下列条目在阶段一曾列为种子文献，因无法取得一手内容或书目不符，不进入参考文献表。

| 条目 | 原因 |
| --- | --- |
| Rothermel & Straßer, SRDS 1998 | DOI 已核验（10.1109/RELDIS.1998.740480），但没有取得摘要或全文；其观察者节点协议改由 PS03 的相关论述间接说明，正文不单独引用 |
| Pleisch & Schiper, SRDS 2000 | 书目已核验（10.1109/RELDI.2000.885388）；内容以期刊版 PS03 为准，避免重复引用 |
| Malkhi & Terry, WinFS 简洁版本向量 | 出版方页面需要登录，没有取得摘要或全文 |
| Parker 等, 版本向量 (1983) | 书目已核验，未取得内容 |
| Dwork, Lynch & Stockmeyer (1988) | 可获得的 PDF 是扫描图像，无法转为文本；多数派要求改由 Lam98 的 quorum 条件说明 |
| Oki & Liskov, Viewstamped Replication | Crossref 的题名与常用题名不符，未进一步核验 |
| Milojičić 等, 进程迁移综述 | 未取得全文；“整进程迁移代价高”的论点改由 CPV07 与 Cue10 支撑 |
| Hardy, The Confused Deputy | 原文页面证书校验失败 |
| Chun 等, CloneCloud；Satyanarayanan (2001) | 没有摘要或全文 |
| PRACTI、IsolateGPT、AgentDojo | 与收窄后的论证无直接关系 |

## 4. 最近邻工作的比较

| 系统或研究 | 协调方式 | 连续性单位 | 执行唯一性与所有权 | 外部效果 | 状态 |
| --- | --- | --- | --- | --- | --- |
| UFO³ [Zha25] | 全局控制平面上的中心编排 Agent | DAG 子任务分配到设备 | 不变式：子任务同一时刻至多一个活动分配；由中心维护 | 设备断开时任务失败并修订 DAG | 预印本 |
| TopoClaw [Hua26] | 中心认知枢纽 + 放置引擎 | 跨设备的单个动作 | 未讨论 | 未讨论失败处理 | 预印本（技术报告） |
| Nexus [Cha26] | 云端持久记录 + 路由器对等路由 | 每次调用对应一个持久任务 | 云端检查有时限的执行租约 | 操作日志复用；效果不确定时显式恢复；不保证 exactly-once | 预印本（技术报告） |
| MVVM [Yan25] | 未明确 | Wasm 稳定点的执行状态（接近强迁移） | 未讨论；副本在分区期间允许分歧 | 未讨论 | 预印本 |
| AgentRewind [Zhu26]、Crab [Wu26] | 单机 | 对齐的上下文与环境检查点，对齐到回合边界 | 不涉及 | 回退与恢复 | 预印本 |
| ACRFence [ACR26]、Atomix [Atx26] | 单机运行时 | 工具调用 | 不涉及 | 效果日志与 replay-or-fork；按效果类别提交 | 预印本 |
| Kha26 | 单一逻辑存储，无复制 | 读—生成—写操作 | stale-generation 等异常的 TLA+ 形式化 | 工具效果重排 | 预印本 |
| **本文（Operit2）** | 对等节点，无常驻协调者；副本最终一致 | 回合边界上的持久事实 + 续跑上下文 | 本文的研究对象 | 本文 RQ4 | —— |

这张表显示两点。第一，现有跨设备 Agent 系统把执行唯一性交给一个中心组件：UFO³ 的编排者、TopoClaw 的认知枢纽、Nexus 的云端租约检查。第二，检查点与效果相关的工作都在单个运行时内部讨论，没有处理执行位置在副本之间转移的情形。

## 5. 新颖性结论（修订阶段一 §5）

阶段一说“没有找到同时处理这些约束的已发表研究”。系统检索之后，这一判断需要修正：跨设备 LLM Agent 已经出现了多个 2025–2026 年的系统（UFO³、TopoClaw、Nexus、MVVM、Unified Agent），单机 Agent 的检查点、回退与效果安全也有专门研究（AgentRewind、Crab、ACRFence、Atomix），用 TLA+ 形式化 Agent 运行时并发异常的工作同样存在（Kha26）。

在本次检索范围内，尚未发现以下组合被研究过：**没有中心协调者时，副本最终一致的对等设备之间，一个 LLM Agent 会话的执行所有权如何在回合边界转移；转移的安全性质（单一推进、交接互斥、续跑至多一次）如何定义并经模型检查；所有权协议如何与外部效果语义及用户仲裁配合。**本文的新颖性主张限于这一组合及其形式化分析、协议与验证方法，并注明检索日期与范围；不主张“首个跨设备 Agent”。

另有两点修订：

1. Kha26 已经使用“stale-generation”一词描述多 Agent 共享存储中的异常。本文的“过期代次推进”专指执行位置记录的代次，与之不同，正文须明确区分。
2. ACR26 指出 LLM 会在恢复后重新合成不同的请求，这使服务端幂等键无法识别重复。它直接影响 RQ4：续跑一旦重复（阶段一 X3），重复的不只是同一请求，还可能是内容不同的新请求。

## 6. 对后续阶段的影响

- **RQ1：** Tam26 与 Sun26 为“信念—环境一致性”提供了独立的旁证，分别涉及压缩把观察当作持久事实，以及压缩式交接削弱约束。核心结构不变：模型检查不覆盖语义层面，这一部分以定义、机制设计与评价方案处理。
- **RQ2、RQ3：** 方法上参照 New15 与 Kha26。协议的接管策略以 PS03（多数派见证）、GC89（租约）与 Ter95（primary 提交）为三类先例。
- **RQ4：** 效果分类参照 Atx26 的三类效果；效果身份必须由运行时在调用前分配，不能依赖模型重新生成的请求内容（ACR26）。
- **相关工作章节：** 按“中心协调的跨设备 Agent / 单机检查点与效果 / 经典所有权与复制”三组组织，突出 §4 表中的差异。
