"""Draw the whitepaper's A4 cover as editable, self-contained vector geometry."""
from html import escape
from pathlib import Path

BASE = Path(__file__).resolve().parent
INK = "#132f43"
TEAL = "#007d8b"
BLUE = "#3779b6"
MUTED = "#657d8d"
PARTS = []


def polygon(points, fill="none", stroke="none", width=1):
    pts = " ".join(f"{x:.2f},{y:.2f}" for x,y in points)
    PARTS.append(f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')


def line(points, color, width=1, dash=None):
    pts = " ".join(f"{x:.2f},{y:.2f}" for x,y in points)
    dashed = f' stroke-dasharray="{dash}"' if dash else ""
    PARTS.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{width}"{dashed}/>')


def circle(x, y, r, fill, stroke="none", width=1):
    PARTS.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')


def text(x,y,value,size=14,color=INK,family="CoverSans",bold=False,align="start"):
    font = {"CoverSans":"Segoe UI", "CoverCN":"Microsoft YaHei", "CoverMono":"Consolas"}[family]
    PARTS.append(f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-family="{font}" data-pdf-font="{family}" font-weight="{700 if bold else 400}" text-anchor="{align}">{escape(value)}</text>')


def iso(u,v,z=0):
    return 426 + 52*(u-v), 520 + 30*(u+v) - z


def plane(z, fill, stroke):
    polygon([iso(0,0,z),iso(6,0,z),iso(6,6,z),iso(0,6,z)],fill,stroke,1.2)
    for i in range(1,6):
        line([iso(i,0,z),iso(i,6,z)],stroke,0.7)
        line([iso(0,i,z),iso(6,i,z)],stroke,0.7)


def slab(cx, cy, width, color, top_fill, side_fill, height=13):
    a=(cx,cy-width*.25)
    b=(cx+width*.5,cy)
    c=(cx,cy+width*.25)
    d=(cx-width*.5,cy)
    polygon([d,c,(c[0],c[1]+height),(d[0],d[1]+height)],side_fill,color,1.25)
    polygon([c,b,(b[0],b[1]+height),(c[0],c[1]+height)],"#e0ecf3",color,1.25)
    polygon([a,b,c,d],top_fill,color,1.4)


def node(u,v,color):
    cx,cy=iso(u,v)
    # All three nodes have the same geometry and scale.
    for dz,fill in [(10,"#f8fbfd"),(37,"#f5fafc"),(64,"#ffffff")]:
        slab(cx,cy-dz,152,color,fill,"#edf5f8")
    chip_y=cy-64
    slab(cx,chip_y-8,72,color,"#e8f4f7","#d5e9ef",7)
    polygon([(cx,chip_y-23),(cx+24,chip_y-11),(cx,chip_y+1),(cx-24,chip_y-11)],color)
    for dx in (-45,-30,-15,0,15,30,45):
        line([(cx+dx,cy-64+38-abs(dx)*.5+14),(cx+dx,cy-64+38-abs(dx)*.5+19)],color,1)


def main():
    PARTS.clear()
    PARTS.extend([
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 1188" role="img" aria-label="Operit2 中文技术白皮书封面">',
        '<title>Operit2 技术白皮书</title>',
        '<desc>白底出版网格、深墨标题、蓝绿等量节点与层叠状态平面，表达个人设备空间中的连接与连续性。</desc>',
        '<rect x="0" y="0" width="840" height="1188" fill="#ffffff"/>',
    ])
    # Publication masthead.
    line([(64,63),(88,63)],TEAL,4)
    text(101,69,"OPERIT",16,INK,bold=True)
    text(776,68,"RESEARCH & ENGINEERING",11,MUTED,"CoverMono",align="end")
    line([(64,91),(776,91)],"#d7e4ea",1)
    text(61,202,"OPERIT2",100,INK,bold=True)
    text(66,236,"TECHNICAL WHITE PAPER",15,TEAL,"CoverMono")
    text(62,310,"技术白皮书",49,INK,"CoverCN",True)
    text(65,365,"面向个人设备空间的",26,INK,"CoverCN")
    text(65,405,"可持续 Agent 运行时",30,INK,"CoverCN")
    line([(66,437),(129,437)],TEAL,3)
    text(150,442,"ARCHITECTURE  /  STATE  /  CONTINUITY",11.2,MUTED,"CoverMono")

    # Layered persistent state. Explicit coordinates match the PDF renderer.
    plane(-73,"#f4f8fb","#e3edf3")
    plane(-35,"#f9fcfd","#dce8ef")
    for u,v in [(0,0),(0,6),(6,0),(6,6)]:
        line([iso(u,v,-73),iso(u,v)],"#cfdee7",1.1,dash="4,5")
    plane(0,"#fcfefe","#d7e6ed")
    # Precision ticks and sparse plotted vertices provide scale without clutter.
    for u in range(7):
        for v in range(7):
            x,y=iso(u,v)
            circle(x,y,1.25,"#c2d6df")
    for u,v in [(0,0),(0,6),(6,0),(6,6)]:
        x,y=iso(u,v)
        line([(x-6,y),(x+6,y)],"#9dbcc9",1)
        line([(x,y-5),(x,y+5)],"#9dbcc9",1)

    # Peer links follow the plane. There is no central hub or directional arrow.
    line([iso(1,4.3),iso(1,1),iso(3.7,1)],TEAL,2.8)
    line([iso(3.7,1),iso(5.1,1),iso(5.1,4.3)],BLUE,2.4)
    line([iso(5.1,4.3),iso(1,4.3)],"#4c95b4",2.3)
    for u,v in [(1,1),(5.1,1),(1,4.3),(5.1,4.3)]:
        x,y=iso(u,v)
        circle(x,y,4,"#ffffff",TEAL,1.6)
    # Short offset traces add depth while preserving the three equal nodes.
    line([iso(1,4.3,-35),iso(5.1,4.3,-35),iso(5.1,2.4,-35)],"#a5c7d6",1.4)
    for u,v in [(2.2,4.3),(4.2,4.3)]:
        x,y=iso(u,v)
        circle(x,y,4,TEAL)
    # Far-to-near painter order.
    node(3.7,1,BLUE)
    node(1,4.3,TEAL)
    node(5.1,4.3,TEAL)

    # Marginal labels are drawn after the solids, outside their silhouettes.
    text(64,656,"CORENODE / 01",11.5,TEAL,"CoverMono")
    line([(64,668),(135,668),(175,690)],"#7fb1bd",1)
    text(776,597,"CORENODE / 02",11.5,BLUE,"CoverMono",align="end")
    line([(776,609),(705,609),(646,643)],"#8cadca",1)
    text(776,855,"CORENODE / 03",11.5,TEAL,"CoverMono",align="end")
    line([(776,867),(692,867),(547,779)],"#7fb1bd",1)

    # Engineering marginalia: conceptual art, not a product guarantee diagram.
    text(66,548,"01 / DEVICE SPACE",10.5,MUTED,"CoverMono")
    line([(66,559),(157,559),(195,580)],"#b3cbd6",1)
    text(772,953,"STATE / CONTINUITY",10.5,MUTED,"CoverMono",align="end")
    line([(64,1017),(776,1017)],"#d7e4ea",1)
    text(65,1056,"Operit 项目",18,INK,"CoverCN")
    text(65,1093,"技术架构与实现研究",12.5,MUTED,"CoverCN")
    text(65,1118,"源码基线 1ef7884 · 预览阶段",10.5,MUTED,"CoverCN")
    text(776,1058,"2.0",31,TEAL,bold=True,align="end")
    text(776,1093,"中文版 / CHINESE EDITION",10.8,MUTED,"CoverCN",align="end")
    text(776,1118,"2026.11.07",11.5,MUTED,"CoverMono",align="end")
    PARTS.append("</svg>")
    output=BASE/"cover.svg"
    output.write_text("\n".join(PARTS)+"\n",encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
