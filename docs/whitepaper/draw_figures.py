"""Author the whitepaper's editable SVG figures using Python's standard library."""
from pathlib import Path
from html import escape
import math

OUT = Path(__file__).resolve().parent / "diagram"
BG = "#ffffff"
COL = {"cyan":"#007b8b", "green":"#16704a", "violet":"#6a4ca3", "amber":"#8c6000", "rose":"#ac3550", "slate":"#526575", "blue":"#2c5f9e"}
FILLS = {"cyan":"#f0f8fa", "green":"#f1f8f4", "violet":"#f5f2fa", "amber":"#fbf7ed", "rose":"#fcf2f4", "slate":"#f4f6f8", "blue":"#f0f5fb"}


class Figure:
    def __init__(self, title, subtitle, height):
        self.height = height
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1050 {height}" role="img" aria-label="{escape(title)}">',
                      '<style>text {font-family: SimHei, "Noto Sans SC", "Microsoft YaHei", sans-serif;}</style>',
                      f'<rect x="0" y="0" width="1050" height="{height}" rx="12" fill="{BG}"/>']
        self.text(32, 42, title, size=26, bold=True)
        self.text(32, 73, subtitle, size=18, color="slate")

    def text(self, x, y, text, size=20, color=None, bold=False, center=False):
        color = COL.get(color, color or "#172a3a")
        self.parts.append(f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{700 if bold else 400}" text-anchor="{"middle" if center else "start"}">{escape(text)}</text>')

    def rect(self, x, y, w, h, color="slate", dash=False, fill=BG, rx=9):
        dashed = ' stroke-dasharray="8,5"' if dash else ''
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{COL[color]}" stroke-width="1.6"{dashed}/>')

    def box(self, x, y, w, h, title, desc=(), color="cyan"):
        self.rect(x,y,w,h,color,fill=FILLS[color])
        self.text(x+w/2,y+30,title,22,color,True,True)
        for i, line in enumerate(desc):
            self.text(x+w/2,y+58+27*i,line,18,center=True)

    def arrow(self, pts, label=None, color="slate", dashed=False, label_xy=None):
        dashed = ' stroke-dasharray="7,5"' if dashed else ''
        self.parts.append(f'<polyline points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="none" stroke="{COL[color]}" stroke-width="2"{dashed}/>')
        x,y=pts[-1]; px,py=pts[-2]; theta=math.atan2(y-py,x-px)
        p1=(x-11*math.cos(theta)+5*math.sin(theta),y-11*math.sin(theta)-5*math.cos(theta))
        p2=(x-11*math.cos(theta)-5*math.sin(theta),y-11*math.sin(theta)+5*math.cos(theta))
        self.parts.append(f'<polygon points="{x},{y} {p1[0]},{p1[1]} {p2[0]},{p2[1]}" fill="{COL[color]}"/>')
        if label:
            lx,ly=label_xy or ((pts[0][0]+x)/2,(pts[0][1]+y)/2-10)
            self.text(lx,ly,label,18,color,center=True)

    def note(self, y, text, color="slate"):
        self.text(32,y,text,18,color)

    def save(self, name):
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT/name).write_text("\n".join(self.parts)+"\n</svg>\n", encoding="utf-8")


def main():
    f=Figure("01  个人设备空间与访问入口", "CoreNode 的地位对等；存储角色、执行权限与平台能力分别决定参与范围",640)
    f.rect(25,105,1000,340,"amber",True)
    f.text(45,135,"Space：成员、控制策略、可达性与获准的业务副本同步",20,"amber")
    f.arrow([(345,265),(385,265)],color="green")
    f.arrow([(680,265),(720,265)],color="green")
    f.box(50,165,295,210,"手机 CoreNode",["Rust Core + 本地 Host","交互、移动能力、任务发起","业务副本依授权参与"],"cyan")
    f.box(385,165,295,210,"桌面 CoreNode",["Rust Core + 本地 Host","文件、终端、浏览器","Binding 可指定其续跑"],"green")
    f.box(720,165,280,210,"长期在线 CoreNode",["Rust Core + 本地 Host","如 Linux 主机","仍是普通 Space 成员"],"violet")
    f.text(525,415,"PeerLink 可直连或逐跳转发；图中连线是示例拓扑",18,"slate",center=True)
    f.arrow([(195,485),(195,375)],color="cyan")
    f.arrow([(535,485),(535,445)],color="amber")
    f.arrow([(860,485),(860,445)],color="slate",dashed=True)
    f.box(50,485,295,94,"Web Access",["访问现有节点的界面"],"cyan")
    f.box(385,485,295,94,"受限 Edge",["设备服务；无完整业务副本"],"amber")
    f.box(720,485,280,94,"模型服务",["本地推理或外部 Provider"],"slate")
    f.note(615,"浏览器本地 WASM Core 是另一种部署路径；不能与 Web Access 等同。")
    f.save("01-device-space.svg")

    f=Figure("02  Core 的装配、依赖与 Host 边界", "箭头向下表示消费下层契约；节点网络并非业务运行时的子模块",710)
    for y in (185,325,465): f.arrow([(370,y),(370,y+40)],color="slate")
    f.box(40,105,660,80,"接入与投影",["Flutter / CLI / TUI · typed proxy / Link"],"cyan")
    f.box(40,225,660,100,"CoreApplication 装配根",["OperitApplication · LocalCoreProxy · NodeServices","CoreNodeRouter · RuntimeRemoteLinkService"],"green")
    f.box(40,365,660,100,"业务服务与可替换执行组件",["chat / Provider / tools / local-models","plugin-sdk / JavaScript bridge / runtime-support traits"],"green")
    f.box(40,505,660,80,"共享模型与持久化",["model / store / transaction owners"],"violet")
    f.box(745,105,265,480,"node / Link",["身份、配对与会话","Space 控制与授权","Binding 与路由","持久化同步","Call / Watch / Push","Host 传输适配"],"amber")
    f.arrow([(700,270),(745,270)],color="amber")
    f.arrow([(370,585),(370,625)],color="slate")
    f.arrow([(875,585),(875,625)],color="slate")
    f.box(40,625,970,60,"Host API traits  →  平台 Host 实现（文件 / 网络 / 终端 / 存储 / 推理 / 设备 I/O）",[],"blue")
    f.save("02-core-layers.svg")

    f=Figure("03  一次 Agent 交互中的状态与事实", "概念流程对应当前服务链；模型输出、工具执行、持久化和 UI 投影是不同阶段",570)
    f.arrow([(330,175),(380,175)],color="cyan")
    f.arrow([(670,175),(720,175)],color="cyan")
    f.arrow([(860,235),(860,325)],color="green",label="工具请求",label_xy=(910,285))
    f.arrow([(720,385),(670,385)],color="violet")
    f.arrow([(380,385),(330,385)],color="violet")
    f.arrow([(180,325),(180,275),(525,275),(525,235)],color="blue",label="继续下一次模型请求",label_xy=(390,266))
    f.box(40,115,290,120,"接收交互",["消息、附件、取消状态","运行参数与本地执行锁"],"cyan")
    f.box(380,115,290,120,"构造活动上下文",["历史 / 摘要 / 配置 / 工具","Provider 组装请求"],"cyan")
    f.box(720,115,290,120,"模型与流式输出",["远程 API 或本地推理","文本、工具请求、错误"],"green")
    f.box(720,325,290,120,"工具准入与执行",["AI 路径：模式 / hook / 批准","调用当前节点 Host 或扩展"],"rose")
    f.box(380,325,290,120,"持久化工具与消息事实",["参数、结果、错误和产物引用","同步传递持久状态"],"violet")
    f.box(40,325,290,120,"完成 / 取消 / 续跑",["可请求切换 Binding","进程与会话留在原节点"],"blue")
    f.note(498,"摘要是有损的上下文表示；持久消息、文件、外部副作用具有各自生命周期。")
    f.note(533,"当前普通摘要可异步启动；不能把这张概念图解释为每次请求前同步 checkpoint。")
    f.save("03-agent-cycle.svg")

    f=Figure("04  持久化同步的接收、物化与内容校验", "操作身份、稀疏收据、owner 规则与 blob 完整性共同决定结果",705)
    f.arrow([(335,180),(390,180)],color="violet")
    f.arrow([(675,180),(730,180)],color="violet")
    f.arrow([(870,240),(870,320)],color="green")
    f.arrow([(730,380),(675,380)],color="green")
    f.arrow([(390,380),(335,380)],color="green")
    f.box(40,120,295,120,"源节点业务写入",["事务 / preference / SQL / 文件","来源 ID 与序号、修订信息"],"violet")
    f.box(390,120,285,120,"增量交换",["授权检查与 endpoint 协商","按接收知识导出缺失操作"],"amber")
    f.box(730,120,280,120,"接收账本",["原文身份与去重","稀疏收据保留历史空洞"],"violet")
    f.box(730,320,280,120,"owner 选择与就绪检查",["格式 / 依赖 / blob / 迁移","未就绪记录保留待处理"],"green")
    f.box(390,320,285,120,"确定规则重放与提交",["Preference 文件提交协议","SQL owner 本库事务"],"green")
    f.box(40,320,295,120,"物化与通知",["持久业务视图更新","UI / watch 获得变化"],"cyan")
    f.arrow([(180,440),(180,510),(525,510),(525,550)],color="blue")
    f.box(40,550,970,102,"注册 snapshot owner 的附加闭环",["稳定导出范围下比较内容摘要 → 必要时选择完整快照校正 → 初始化事务与覆盖凭据","当前覆盖 Preference / 聊天 SQL / 插件 SQL；不是所有数据的统一修复"],"blue")
    f.note(684,"本图不表达跨设备分布式 ACID，也不保证一般业务操作可交换。")
    f.save("04-persistence-sync.svg")

    f=Figure("05  网络可达性与三类数据路径", "配对、Space 成员身份、调用授权与业务存储资格需要分别判断",610)
    f.arrow([(280,185),(405,185)],"PeerLink","amber")
    f.arrow([(650,185),(775,185)],"PeerLink","amber")
    f.box(40,130,240,110,"节点 A",["调用方 / 本地副本"],"cyan")
    f.box(405,130,245,110,"节点 B",["中间跳 / 可有业务副本"],"amber")
    f.box(775,130,235,110,"节点 C",["执行目标 / 本地 Host"],"green")
    f.box(40,300,970,70,"控制路径：成员、权限、审批与撤销；独立于业务同步知识进度",[],"rose")
    f.box(40,405,970,70,"实时路径：Call / Watch / Push；逐跳路由、TTL、流生命周期",[],"cyan")
    f.box(40,510,970,70,"业务同步：操作日志、对象与文件；双方须获 storage.provide 且提供 Core 存储",[],"violet")
    f.note(282,"A 与 C 可经 B 通信；这不会自动生成 A 与 C 的直接配对关系。")
    f.save("05-network-planes.svg")

    f=Figure("06  Binding 切换与目标节点续跑", "实现序列的抽象；请求失败、重提与节点崩溃可能使结果不确定",780)
    xs=[145,410,675,935]
    for x in xs:
        f.parts.append(f'<line x1="{x}" y1="180" x2="{x}" y2="715" stroke="#475569" stroke-dasharray="6,5"/>')
    for x,title,col in zip(xs,["Agent 工具回合","原执行节点","同步与 Binding","目标执行节点"],["cyan","green","violet","amber"]):
        f.box(x-107,110,214,70,title,[],col)
    f.arrow([(145,225),(410,225)],"1  switch_core 请求","cyan")
    f.text(438,268,"校验成员、能力、执行权限、可达性",18,"slate")
    f.arrow([(410,310),(675,310)],"2  完成段持久化，释放本地执行保护","green")
    f.arrow([(410,375),(935,375)],"3  BeforeChangeRoute 检查后同步目标","green")
    f.arrow([(410,440),(675,440)],"4  本地比较写入 Binding","violet")
    f.arrow([(675,505),(935,505)],"5  即时安装 Binding","violet")
    f.arrow([(410,570),(935,570)],"6  AfterChangeRoute + resumeContext","amber")
    f.text(740,625,"目标开始后续模型交互",20,"amber")
    f.text(40,678,"原节点不再推进该次正常续跑；PTY、浏览器会话、进行中的模型请求不搬迁。",18,"slate")
    f.note(748,"本地 CAS / generation / lease 不等于跨节点共识、外部副作用 fencing 或 exactly-once。","rose")
    f.save("06-binding-handoff.svg")

    f=Figure("07  扩展契约与实际执行位置", "包格式、工作流材料、远程协议与原生 SDK 是不同抽象层",630)
    for x in (165,520,880): f.arrow([(x,240),(x,330)],color="slate")
    f.box(40,125,250,115,"Skill",["说明、资源、可见性","提供工作流材料"],"cyan")
    f.box(360,125,320,115,"JS / TS Package、ToolPkg",["声明、脚本、资源、UI","Compose / 可选 WASM"],"green")
    f.box(755,125,255,115,"MCP",["外部 server 工具协议","本地进程或远端服务"],"amber")
    f.box(40,330,250,115,"工具系统",["发现、注册与上下文使用","无独立通用沙箱承诺"],"cyan")
    f.box(360,330,320,115,"Host JavaScript realm",["当前 native Host 使用 V8","WASM 实例可在 realm 内执行"],"green")
    f.box(755,330,255,115,"MCP 客户端与生命周期",["配置、工具描述与调用","外部程序拥有自身权限"],"amber")
    f.box(40,510,970,80,"共享契约与本地资源：plugin-sdk / SDK IPC / ToolRuntimeSupport / Host API",["跨节点可用性还取决于安装状态、运行时、依赖、权限与资源"],"violet")
    f.note(295,"工具被注册、接口可路由或数据已同步，都不单独证明插件可以在另一节点执行。")
    f.save("07-extension-runtime.svg")

    f=Figure("08  信任边界与工具调用准入", "网络信任、应用准入与操作系统隔离各有作用域，不能相互替代",675)
    f.rect(35,110,980,490,"slate",True)
    f.text(55,145,"外部隔离：设备 / 操作系统账号 / 应用沙盒 / 部署容器",22,"slate",True)
    f.rect(65,180,920,160,"blue")
    f.text(85,215,"Host：文件、终端、网络、推理与设备 I/O 的实际系统权限",21,"blue",True)
    f.arrow([(265,465),(265,340)],color="rose")
    f.arrow([(760,465),(760,340)],color="amber")
    f.box(90,465,350,100,"AI 工具路径",["能力模式 → policy / hook → 批准"],"rose")
    f.box(580,465,365,100,"Direct / 插件 / SDK 路径",["可跳过 AI preflight 与 hook"],"amber")
    f.text(525,300,"Host 不因 Full 模式或加入 Space 获得 root / 管理员权限",19,center=True)
    f.text(525,260,"执行范围受路径策略、工具实现、插件权限和外部隔离共同约束",18,"slate",center=True)
    f.note(638,"网络入口另需检查身份、配对、Space 策略与 endpoint 授权；撤权不能收回已复制数据。")
    f.save("08-security-boundaries.svg")

    f=Figure("09  凭据复制与链路加密的不同边界", "加密静态文件、保护相邻信道、限制复制对象和信任中继，是不同的问题",650)
    f.arrow([(340,205),(400,205)],color="amber")
    f.arrow([(650,205),(710,205)],color="amber")
    f.box(35,135,305,145,"源 CoreNode A",["完整 Provider 配置","含 apiKey / pool / headers","本机加密保存"],"violet")
    f.box(400,135,250,145,"中继 B",["逐跳信道端点","可读取转发明文","重新加密下一跳"],"amber")
    f.box(710,135,305,145,"存储副本 C",["获授权接收配置原文","用自身密钥静态保存","可使用收到的配置"],"violet")
    f.text(525,325,"PeerLink：A–B 与 B–C 分别认证加密；当前无对 B 保密的端到端封装",19,"amber",center=True)
    f.box(35,380,460,130,"OAuth 会话",["GitHub / Codex：node-local SecretStore","不进入 Space 业务复制；本机静态加密"],"green")
    f.box(550,380,465,130,"配对 sessionSecret",["node-local StateStore，不进入业务复制","当前未启用 Preference 静态加密"],"rose")
    f.note(565,"授权撤销阻止后续访问，不能收回其他设备已经获得的配置、密钥、明文或备份。")
    f.note(608,"Space 成员和路由中继必须属于用户接受的信任范围；不要假设中继天然只处理密文。")
    f.save("09-credential-scope.svg")
    print(f"Wrote 9 SVG figures to {OUT}")


if __name__ == "__main__":
    main()
