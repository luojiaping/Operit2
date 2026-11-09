"""Author the v3 whitepaper figures as editable SVG (standard library only).

The Figure helper is adapted from docs/whitepaper/draw_figures.py (2.0) so that both
editions share one visual language.  Only rect, line, polyline, polygon, circle and
text elements are emitted, which is the subset the PDF renderer draws as vectors.
Usage: python -X utf8 draw_figures_v3.py
"""
import math
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parent / "diagram"
BG = "#ffffff"
INK = "#172a3a"
COL = {"cyan": "#007b8b", "green": "#16704a", "violet": "#6a4ca3", "amber": "#8c6000",
       "rose": "#ac3550", "slate": "#526575", "blue": "#2c5f9e", "gray": "#8a99a6"}
FILLS = {"cyan": "#f0f8fa", "green": "#f1f8f4", "violet": "#f5f2fa", "amber": "#fbf7ed",
         "rose": "#fcf2f4", "slate": "#f4f6f8", "blue": "#f0f5fb", "gray": "#e9edf0"}


class Figure:
    def __init__(self, title, subtitle, height, width=1050):
        self.width, self.height = width, height
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">',
                      '<style>text {font-family: SimHei, "Noto Sans SC", "Microsoft YaHei", sans-serif;}</style>',
                      f'<rect x="0" y="0" width="{width}" height="{height}" rx="12" fill="{BG}"/>']
        self.text(32, 42, title, size=26, bold=True)
        self.text(32, 73, subtitle, size=18, color="slate")

    def text(self, x, y, text, size=19, color=None, bold=False, anchor="start"):
        color = COL.get(color, color or INK)
        self.parts.append(f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
                          f'font-weight="{700 if bold else 400}" text-anchor="{anchor}">{escape(text)}</text>')

    def rect(self, x, y, w, h, color="slate", dash=False, fill=None, rx=9, width=1.6):
        dashed = ' stroke-dasharray="8,5"' if dash else ""
        fill = FILLS.get(fill, fill) if fill else BG
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
                          f'stroke="{COL[color]}" stroke-width="{width}"{dashed}/>')

    def block(self, x, y, w, h, color="gray"):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="{FILLS[color]}" '
                          f'stroke="{COL[color]}" stroke-width="1.4"/>')

    def line(self, x1, y1, x2, y2, color="slate", dash=False, width=1.6):
        dashed = ' stroke-dasharray="7,5"' if dash else ""
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{COL[color]}" '
                          f'stroke-width="{width}"{dashed}/>')

    def arrow(self, pts, label=None, color="slate", dashed=False, label_xy=None, size=17, both=False):
        dash = ' stroke-dasharray="7,5"' if dashed else ""
        self.parts.append(f'<polyline points="{" ".join(f"{x},{y}" for x, y in pts)}" fill="none" '
                          f'stroke="{COL[color]}" stroke-width="2"{dash}/>')
        self._head(pts[-2], pts[-1], color)
        if both:
            self._head(pts[1], pts[0], color)
        if label:
            lx, ly = label_xy or ((pts[0][0] + pts[-1][0]) / 2, (pts[0][1] + pts[-1][1]) / 2 - 9)
            self.text(lx, ly, label, size, color, anchor="middle")

    def _head(self, previous, point, color):
        (px, py), (x, y) = previous, point
        theta = math.atan2(y - py, x - px)
        p1 = (x - 12 * math.cos(theta) + 5 * math.sin(theta), y - 12 * math.sin(theta) - 5 * math.cos(theta))
        p2 = (x - 12 * math.cos(theta) - 5 * math.sin(theta), y - 12 * math.sin(theta) + 5 * math.cos(theta))
        self.parts.append(f'<polygon points="{x:.1f},{y:.1f} {p1[0]:.1f},{p1[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}" '
                          f'fill="{COL[color]}"/>')

    def dot(self, x, y, color="slate", r=6):
        self.parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{COL[color]}" stroke="{COL[color]}"/>')

    def save(self, name):
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / name).write_text("\n".join(self.parts) + "\n</svg>\n", encoding="utf-8")


def node_box(f, x, y, title, view, view_color, rows):
    f.rect(x, y, 300, 250, "cyan", fill="cyan")
    f.text(x + 150, y + 32, title, 21, "cyan", True, "middle")
    f.rect(x + 16, y + 48, 268, 44, view_color, fill=view_color, rx=6)
    f.text(x + 150, y + 76, view, 16, view_color, True, "middle")
    for index, row in enumerate(rows):
        f.text(x + 22, y + 124 + 30 * index, row, 17)


def figure_views():
    f = Figure("01  设备空间中的 Binding 视图",
               "每个节点按本机视图路由；同步使视图趋同，在此之前可能不一致", 600)
    node_box(f, 30, 105, "手机 CoreNode A", "视图：owner=A，gen=1（过期）", "amber",
             ["持久日志与事实：可复制", "本地执行保护：进程内", "暂态：在途请求、界面会话", "资源：本机权限与模型"])
    node_box(f, 375, 105, "桌面 CoreNode B", "视图：owner=B，gen=2", "green",
             ["持久日志与事实：可复制", "本地执行保护：进程内", "暂态：PTY、WebView、MCP", "资源：工作区挂载与凭据"])
    node_box(f, 720, 105, "Linux CoreNode C", "视图：owner=B，gen=2", "green",
             ["持久日志与事实：可复制", "本地执行保护：进程内", "暂态：PTY、长任务进程", "资源：常在线、本机权限"])
    f.arrow([(330, 230), (375, 230)], color="slate", dashed=True, both=True)
    f.arrow([(675, 230), (720, 230)], color="slate", dashed=True, both=True)
    f.arrow([(870, 355), (870, 420), (525, 420), (525, 358)], label="C 上的请求：本机视图 → 转发到 B 执行", color="green",
            label_xy=(698, 444))
    f.arrow([(120, 355), (120, 410), (230, 410), (230, 358)], color="rose")
    f.text(30, 500, "A 上的请求：本机视图仍指向 A，于是在 A 本地执行，与 B 并发（第 5 节 X1、X2 的结构）", 17, "rose")
    f.text(30, 530, "虚线：持久同步（日志取并集，冲突按 createdAt、originDeviceId、sequence 裁决，代次不参与）", 17, "slate")
    f.text(30, 560, "暂态资源始终留在所在节点；交接只传递持久事实与有界配置（弱迁移）", 17, "slate")
    f.save("fig1-views.svg")


def lane(f, x, y0, y1, label, color="slate"):
    f.text(x, y0 - 12, label, 20, color, True, "middle")
    f.line(x, y0, x, y1, color, dash=True, width=1.3)


def step(f, x, y, text, color="slate", w=330):
    f.rect(x - w / 2, y - 20, w, 34, color, fill=color, rx=6)
    f.text(x, y + 3, text, 16, color, anchor="middle")


def figure_current():
    f = Figure("02  现有的回合边界交接（upstream/main 0c53fae18）",
               "各步骤在发起节点上依次执行，没有分布式事务包围；括注为第 5 节反例所在的窗口", 730)
    ax, bx = 250, 790
    lane(f, ax, 120, 660, "源端 A（owner，发起者）")
    lane(f, bx, 120, 660, "目标 B")
    step(f, ax, 150, "assistant 段持久提交", "slate")
    step(f, ax, 205, "释放本地执行保护", "rose")
    step(f, ax, 260, "BeforeChangeRoute：取得后立即释放", "slate")
    f.arrow([(ax, 318), (bx, 318)], label="提交前同步（每页 ≤512 条操作）", color="slate", both=True)
    step(f, ax, 375, "本地比较写入 (B, g+1)，只比较 nodeId", "slate")
    f.arrow([(ax, 430), (bx, 430)], label="即时安装 Binding（经冲突裁决）", color="slate")
    f.arrow([(ax, 490), (bx, 490)], label="AfterChangeRoute（传入历史）", color="amber")
    step(f, bx, 580, "取得执行保护，以传入历史续跑", "green")
    step(f, bx, 635, "调用保持到续跑回合发送结束", "slate")
    f.rect(40, 188, 40, 202, "rose", fill="rose", rx=6)
    f.text(60, 300, "X1", 18, "rose", True, "middle")
    f.text(440, 222, "X1 窗口：本机视图仍指向 A，", 15, "rose")
    f.text(440, 242, "执行保护已空闲", 15, "rose")
    f.text(300, 518, "X3：响应丢失后可能被转发层重提", 15, "amber")
    f.text(300, 538, "X7：可能在后续交接之后才到达", 15, "amber")
    f.text(40, 700, "其他节点发起的切换在发起节点上执行同一过程（X2、X4、X5）；冲突次序不含代次（X6）", 16, "slate")
    f.save("fig2-current.svg")


def timeline(f, y, label, lanes, x0=150, x1=1010):
    f.text(32, y, label, 19, None, True)
    rows = {}
    for index, name in enumerate(lanes):
        ly = y + 36 + index * 40
        f.text(x0 - 12, ly + 6, name, 17, "slate", anchor="end")
        f.line(x0, ly, x1, ly, "gray", width=1.2)
        rows[name] = ly
    return rows


def figure_anomalies():
    f = Figure("03  三类异常的交错（TLC 反例的示意）",
               "灰色方块：正在执行的回合；红色方块：违反性质的执行；箭头：Binding 操作的传播", 760)
    r = timeline(f, 120, "X1 交接窗口（违反执行互斥）", ["A", "B"])
    f.block(160, r["A"] - 12, 170, 24, "gray")
    f.text(245, r["A"] - 18, "回合 g1", 14, "slate", anchor="middle")
    f.dot(340, r["A"], "rose")
    f.text(340, r["A"] + 30, "释放保护", 14, "rose", anchor="middle")
    f.block(400, r["A"] - 12, 420, 24, "rose")
    f.text(610, r["A"] - 18, "新用户消息：A 仍按本机视图执行 g1", 14, "rose", anchor="middle")
    f.arrow([(520, r["A"] + 8), (520, r["B"] - 12)], color="slate")
    f.text(538, r["B"] - 22, "CAS (B,g2) + 安装", 14, "slate")
    f.block(640, r["B"] - 12, 330, 24, "rose")
    f.text(805, r["B"] + 30, "B 以传入历史续跑 g2（不含 A 的新回合）", 14, "rose", anchor="middle")

    r = timeline(f, 290, "X4 并发切换（同一代次两个 owner，违反 S1）", ["A", "B", "C"])
    f.text(170, r["A"] - 8, "A 空闲，两次探测都通过", 14, "slate")
    f.arrow([(400, r["A"] + 6), (400, r["B"] - 12)], color="slate")
    f.text(410, r["B"] - 20, "B：CAS (A,g1)→(B,g2)", 14, "slate")
    f.arrow([(470, r["A"] + 6), (470, r["C"] - 12)], color="slate")
    f.text(480, r["C"] - 20, "C：CAS (A,g1)→(C,g2)", 14, "slate")
    f.block(660, r["B"] - 12, 300, 24, "rose")
    f.block(700, r["C"] - 12, 260, 24, "rose")
    f.text(830, r["B"] - 18, "B 在 g2 执行", 14, "rose", anchor="middle")
    f.text(830, r["C"] + 30, "C 也在 g2 执行", 14, "rose", anchor="middle")

    r = timeline(f, 500, "X6 时钟偏差（代次回退与路由循环，违反收敛后可路由）", ["A 时钟=3", "B 时钟=2", "C 时钟=2"])
    f.arrow([(220, r["A 时钟=3"] + 6), (220, r["B 时钟=2"] - 10)], color="slate")
    f.text(230, r["B 时钟=2"] - 20, "(B,g2)@3", 14, "slate")
    f.arrow([(420, r["B 时钟=2"] - 6), (420, r["A 时钟=3"] + 10)], color="amber")
    f.text(430, r["A 时钟=3"] + 26, "(A,g3)@2：安装时 A 已崩溃", 14, "amber")
    f.text(640, r["C 时钟=2"] - 10, "C 同步后选中 @3 的 g2；A 重启后同样选中 g2", 14, "slate")
    f.arrow([(820, r["A 时钟=3"] + 4), (820, r["B 时钟=2"] - 4)], color="rose")
    f.arrow([(860, r["B 时钟=2"] - 4), (860, r["A 时钟=3"] + 4)], color="rose")
    f.text(880, r["A 时钟=3"] + 26, "A→B→A", 14, "rose")
    f.text(32, 700, "各轨迹的完整步骤见第 5.2 节；参数见附录 B。图为示意，横轴不表示真实时间比例", 16, "slate")
    f.text(32, 730, "最小补丁 HoldLease 消除 X1，但 X4、X6 与 X7 在打补丁后依然出现", 16, "slate")
    f.save("fig3-anomalies.svg")


def figure_fcp():
    f = Figure("04  代次隔离续跑协议 FCP 的交接时序",
               "让出发生在接受之前；目标按代次至多接受一次续跑；旧 owner 在提交时自隔离", 720)
    ax, bx, cx = 210, 640, 930
    lane(f, ax, 120, 615, "owner A（代次 g）")
    lane(f, bx, 120, 615, "目标 B")
    lane(f, cx, 120, 615, "其他节点 C")
    step(f, ax, 150, "回合结束：仍是 (A,g) 才提交（M6）", "slate", 340)
    step(f, ax, 205, "持有保护写入 (B,g+1)（M2、M3）", "green", 340)
    step(f, ax, 260, "释放保护；本机请求转发给 B", "slate", 340)
    f.arrow([(ax, 318), (bx, 318)], label="交接消息：代次 g+1 + 事实（M4）", color="green")
    step(f, bx, 375, "持久化事实；代次优先合并（M1）", "slate", 340)
    step(f, bx, 430, "accepted < g+1 ? 接受并续跑（M5）", "green", 340)
    f.arrow([(ax, 488), (bx, 488)], label="重复或迟到的交接消息", color="amber", dashed=True)
    step(f, bx, 543, "accepted = g+1：丢弃，不再续跑", "amber", 340)
    f.arrow([(cx, 595), (ax, 595)], label="C 上的切换：转移请求只发给 owner（M2）", color="slate", dashed=True,
            label_xy=(575, 585))
    f.text(32, 650, "owner 不可达：默认等待（T0）；用户确认后接管（T1），写入 takeover 代次，原 owner 重连后自隔离", 16, "slate")
    f.text(32, 678, "代次即隔离令牌：外部服务不检查代次，检查只发生在提交与合并两处（第 6.2 节）", 16, "slate")
    f.save("fig4-fcp.svg")


def main():
    figure_views()
    figure_current()
    figure_anomalies()
    figure_fcp()
    print(f"wrote 4 SVG figures to {OUT}")


if __name__ == "__main__":
    main()
