# 中文技术白皮书 3.0

本目录保存 2026-11-10 完成的中文版 3.0 白皮书：正文源文、TLA+ 模型、配图、生成脚本，以及八个研究阶段的记录。3.0 研究个人设备空间中 LLM Agent 的回合边界续跑与执行所有权；系统架构与各子系统的描述仍以 [2.0](../README.md) 为准。代码基线为 upstream/main `0c53fae1811b1731e43a0386bd4f42106fe422e7`。

- [阅读版 PDF](../../Operit2技术白皮书-3.0.pdf)
- [正文（生成的 Markdown）](Operit2-Whitepaper-zh-v3.md)；编辑请改 [源文](Operit2-Whitepaper-zh-v3.src.md)

## 研究阶段记录

| 阶段 | 记录 | 内容 |
| --- | --- | --- |
| 一 | [研究范围与问题定义](01-scope-and-problem.md) | 范围方案、问题陈述、证据等级、候选反例 |
| 二 | [文献调研](02-literature.md) | 检索记录、核验后的文献矩阵、最近邻比较、新颖性结论 |
| 三 | [研究框架与技术模型](03-model.md) | 形式模型、源码映射、X1–X7、FCP 与验证结果 |
| 四 | [章节大纲与论证结构](04-outline.md) | 章节、论证链、图与一致性规则 |
| 五 | 正文 | `Operit2-Whitepaper-zh-v3.src.md` |
| 六 | [交叉引用与一致性检查](06-consistency.md) | 自动检查项与人工发现的问题 |
| 七 | [同行评审式审查](07-review.md) | 审查意见与处理 |
| 八 | [修订、引用核验与定稿](08-final.md) | 核验结果、交付物、未完成的工作 |

## 文件

| 文件 | 作用 |
| --- | --- |
| `Operit2-Whitepaper-zh-v3.src.md` | 正文源文。引用写作 `[@Key]`，源码证据写作 `[Cn]`，在附录 A 中定义 |
| `references.json` | 参考文献条目，键与 `02-literature.md` 一致 |
| `build_v3.py` | 生成 `Operit2-Whitepaper-zh-v3.md`：编号引用、生成参考文献表与附录 B 的实验表，并做一致性检查 |
| `draw_figures_v3.py`、`diagram/` | 四张图的生成脚本与 SVG |
| `draw_cover_v3.py`、`cover.svg` | 封面 |
| `render_v3.py` | 渲染 PDF（由 2.0 的渲染器改编） |
| `model/` | TLA+ 模型、实验参数、TLC 配置与日志、运行脚本、轨迹摘要脚本 |

## 重新生成

以下命令只生成文档或运行模型检查器，不构建、不测试项目。Python 使用仓库虚拟环境。

```powershell
.\.venv\Scripts\python.exe -X utf8 docs/whitepaper/v3/draw_figures_v3.py
.\.venv\Scripts\python.exe -X utf8 docs/whitepaper/v3/draw_cover_v3.py
.\.venv\Scripts\python.exe -X utf8 docs/whitepaper/v3/build_v3.py
.\.venv\Scripts\python.exe -X utf8 docs/whitepaper/v3/render_v3.py
```

渲染需要 ReportLab，项目虚拟环境中没有安装。可以把 ReportLab 安装到一个单独的目录，再让 `CODEX_PDF_PACKAGES` 指向该目录（与 2.0 的做法相同）。字体与 2.0 相同，默认从 `C:/Windows/Fonts` 读取。PDF 默认输出到 `docs/Operit2技术白皮书-3.0.pdf`。

模型检查需要 Java 与 `tla2tools.jar`。本文的结果由 v1.7.4 得到，SHA-256 为 `936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88`。

```bash
cd docs/whitepaper/v3/model
TLA2TOOLS=/path/to/tla2tools.jar ./run_tlc.sh          # 全部实验；fen_takeover_safe 约 21 分钟
python -X utf8 trace_summary.py results/cur_x1_window.log
```

违规实验在找到第一个反例时停止。8 个 worker 并行时，停止前探索的状态数会变化；最短反例的长度保持不变。
