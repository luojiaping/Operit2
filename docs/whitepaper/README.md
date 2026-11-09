# 中文技术白皮书

本目录保存 2026-11-07 重写的中文版 2.0 白皮书源文、技术配图及研究证据。代码基线为 `1ef788456713e0502688dc0b7928511d98b813ec`。

中文版 3.0（2026-11-10，回合边界续跑与执行所有权）的源文、模型与研究记录在 [v3](v3/README.md)，阅读版为 `docs/Operit2技术白皮书-3.0.pdf`。

- [正文（Markdown）](Operit2-Whitepaper-zh.md)
- [阅读版 PDF](../Operit2技术白皮书.pdf)
- [封面 SVG 源文件](cover.svg) / [实际 PDF 封面截图](cover-preview.png)
- [封面截图与评分记录](cover-review.md)
- [分布式与事务同步源码审查](research/distributed-code-audit.md)
- [运行时、平台、工具与记忆源码审查](research/runtime-code-audit.md)
- [外部论文、协议与仓库调研](research/related-work.md)

正文按系统设计论文组织，包括摘要、问题与目标、相关工作、系统模型、架构、执行与上下文、持久复制、路由与交接、扩展、平台、安全、评价方法、未来工作、源码附录和参考文献。当前证据是静态代码与测试源阅读，未将其描述为本轮行为或性能实验结果。

## 技术配图

`diagram/` 中的 9 张 SVG 是可编辑源文件；对应 `@2x.png` 用于预览。PDF 直接绘制 SVG 图元为矢量，正文与图中文字可搜索，字体在 PDF 中嵌入。

| 图 | 内容 |
| --- | --- |
| [01](diagram/01-device-space.svg) | 个人设备空间、CoreNode、Edge 与访问入口 |
| [02](diagram/02-core-layers.svg) | Core 装配、依赖与 Host 边界 |
| [03](diagram/03-agent-cycle.svg) | Agent 交互、工具与持久事实 |
| [04](diagram/04-persistence-sync.svg) | 原文、收据、owner、物化与内容校正 |
| [05](diagram/05-network-planes.svg) | 控制、实时协议与业务复制 |
| [06](diagram/06-binding-handoff.svg) | Binding 切换时序与故障边界 |
| [07](diagram/07-extension-runtime.svg) | Skill、ToolPkg、JavaScript/WASM 与 MCP |
| [08](diagram/08-security-boundaries.svg) | Host、AI 准入、Direct 与外部隔离 |
| [09](diagram/09-credential-scope.svg) | 凭据复制、本机秘密、逐跳加密与中继信任 |

## 文档生成

这些命令只生成文档，不运行 Cargo、Flutter 或项目行为测试。Python 使用仓库虚拟环境；依赖为 ReportLab，图的 PNG 转换使用 Sharp 或可用的 SVG 渲染器。正文使用宋体和黑体；封面使用微软雅黑、Segoe UI 和 Consolas。默认字体目录为 `C:/Windows/Fonts`；可通过 `--font-dir` 指定包含 `simsun.ttc`、`simhei.ttf`、`msyh.ttc`、`msyhbd.ttc`、`segoeui.ttf`、`segoeuib.ttf`、`consola.ttf` 的合法字体目录。

```powershell
.\.venv\Scripts\python.exe -X utf8 docs/whitepaper/draw_figures.py
.\.venv\Scripts\python.exe -X utf8 docs/whitepaper/draw_cover.py
.\.venv\Scripts\python.exe -X utf8 docs/whitepaper/render_whitepaper.py
```

如使用 Codex 已提供的依赖目录，可将 `CODEX_PDF_PACKAGES` 设为该运行时的 Python `site-packages` 路径，避免修改项目虚拟环境。该变量仅用于文档工具，不参与产品运行或依赖选择。

默认 PDF 输出到既有中文白皮书路径，便于保持 README 链接有效。`--source`、`--output` 可指定文稿及输出路径。生成后应使用 Poppler 渲染页面，检查目录、标题、跨页表格、中文字符、配图标注和超链接，再交付。

封面通过 `draw_cover.py` 生成 A4 比例 SVG，再在 PDF 首页面中直接绘制矢量图元。封面的等量节点、连接与层叠平面是主题视觉，不作为系统架构或共享存储保证。实际封面截图可从导出的 PDF 获取：

```powershell
pdftoppm -f 1 -singlefile -scale-to 1800 -png docs/Operit2技术白皮书.pdf docs/whitepaper/cover-preview
```

英文 PDF 是 2026-09 旧版，本轮未翻译；文档入口已明确标注旧版状态。旧中文版本可通过 Git 历史取得。
