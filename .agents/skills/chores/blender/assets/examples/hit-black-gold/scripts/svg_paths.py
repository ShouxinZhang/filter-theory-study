"""解析当前校徽 SVG 的 m/l/h/v/c/s/z 路径，保留多轮廓和曲线控制点。"""
import re
import xml.etree.ElementTree as ET


def parse_path(data):
    tokens=re.findall(r'[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?',data)
    i=0;cur=(0.,0.);start=cur;cmd=None;lastcmd=None;lastcontrol=None;contours=[];points=[]
    def num():
        nonlocal i
        v=float(tokens[i]);i+=1;return v
    def xy(rel):
        x,y=num(),num();return (x+cur[0],y+cur[1]) if rel else (x,y)
    def add(end,c1=None,c2=None):
        nonlocal cur
        if c1 is not None:points[-1]['right']=c1
        points.append({'co':end,'left':c2 or end,'right':end});cur=end
    while i<len(tokens):
        if tokens[i].isalpha():cmd=tokens[i];i+=1
        kind=cmd.lower();rel=cmd.islower()
        if kind=='m':
            if points:contours.append(points)
            points=[];end=xy(rel);start=end;add(end);cmd='l' if rel else 'L'
        elif kind=='l':add(xy(rel))
        elif kind=='h':v=num();add((cur[0]+v if rel else v,cur[1]))
        elif kind=='v':v=num();add((cur[0],cur[1]+v if rel else v))
        elif kind=='c':
            a,b,end=xy(rel),xy(rel),xy(rel);add(end,a,b);lastcontrol=b
        elif kind=='s':
            a=(2*cur[0]-lastcontrol[0],2*cur[1]-lastcontrol[1]) if lastcmd in ('c','s') else cur
            b,end=xy(rel),xy(rel);add(end,a,b);lastcontrol=b
        elif kind=='z':
            if points[-1]['co']==points[0]['co']:points[0]['left']=points[-1]['left'];points.pop()
            contours.append(points);points=[];cur=start;cmd=None
        else:raise ValueError(cmd)
        lastcmd=kind
    if points:contours.append(points)
    return contours


def read_emblem(path):
    root=ET.parse(path).getroot();ns='{http://www.w3.org/2000/svg}';group=root.find(ns+'g');result=[]
    # 素材 group 将原始坐标的 Y 向上转成 SVG 向下；这里直接使用原始 Y 向上坐标。
    assert group.get('transform')=='matrix(1.3333333 0 0 -1.3333333 0 320)'
    for el in group.findall(ns+'path'):
        tr=el.get('transform','');off=(0,0)
        if tr:
            assert tr.startswith('translate(');off=tuple(map(float,re.findall(r'[-+]?\d*\.?\d+',tr)))
        contours=parse_path(el.attrib['d'])
        for c in contours:
            for p in c:
                for k in p:p[k]=((p[k][0]+off[0]-132)/55,(p[k][1]+off[1]-120)/55)
        result.append(contours)
    return result
