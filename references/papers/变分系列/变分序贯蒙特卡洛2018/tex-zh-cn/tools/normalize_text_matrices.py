"""规范化本 XeLaTeX 工程的文本行矩阵，修复 Poppler 的同基线文字排序。

相对 Td 累加与新 BT 中的绝对定位可能产生浮点尾差。将 Td 改写为
同精度的绝对 Tm，保留字体、字距、颜色和链接。仅支持本工程所用的
水平文本操作；遇到旋转文本或其他换行操作时拒绝处理。保存前逐页
比较字形编号与坐标（误差上限 0.001 pt），并要求 144/216/72/96 dpi 中至少一次
逐像素一致，排除浮点抗锯齿边界差异，避免以选区修复为名改变可见版面。
"""
from decimal import Decimal
from pathlib import Path
import argparse
import re
import pymupdf

NUMBER = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)'
TOKEN = re.compile(r'/?[^\s\[\]{}<>/%()]+')
PRECISION = Decimal('0.001')


def operator_mask(data):
    """屏蔽字符串、十六进制串和注释，防止把文字中的 Td 当作操作符。"""
    masked = bytearray(data)
    i = 0
    while i < len(data):
        start = i
        if data[i] == 37:  # PDF 注释。
            while i < len(data) and data[i] not in (10, 13):
                i += 1
        elif data[i] == 40:  # 可嵌套的字面字符串；跳过转义字符。
            depth, i = 1, i + 1
            while i < len(data) and depth:
                if data[i] == 92:
                    i += 2
                    continue
                if data[i] == 40: depth += 1
                elif data[i] == 41: depth -= 1
                i += 1
            if depth: raise ValueError('PDF 字符串未闭合')
        elif data[i] == 60 and data[i:i+2] != b'<<':
            end = data.find(b'>', i + 1)
            if end < 0: raise ValueError('PDF 十六进制字符串未闭合')
            i = end + 1
        else:
            i += 2 if data[i:i+2] in (b'<<', b'>>') else 1
            continue
        masked[start:i] = b' ' * (i - start)
    return masked.decode('latin1')


def rewrite_stream(data):
    """使用十进制精确累计行起点，再用等价的绝对文本矩阵输出。"""
    tokens = list(TOKEN.finditer(operator_mask(data)))
    x = y = Decimal(0)
    inside = False
    edits = []
    for i, token in enumerate(tokens):
        op = token.group()
        if op == 'BI': raise ValueError('不处理带 inline image 的内容流')
        if op == 'BT':
            x = y = Decimal(0)
            inside = True
        elif op == 'ET': inside = False
        elif inside and op in ('TD', 'T*', "'", '"'):
            raise ValueError(f'本工程不支持的文本定位操作：{op}')
        elif inside and op == 'Tm':
            values = [Decimal(t.group()) for t in tokens[i-6:i]]
            if values[:4] != [1, 0, 0, 1]:
                raise ValueError('不处理旋转或缩放文本矩阵')
            x, y = values[4:]
        elif inside and op == 'Td':
            operands = tokens[i-2:i]
            if len(operands) != 2 or not all(re.fullmatch(NUMBER,t.group()) for t in operands):
                raise ValueError('Td 操作数不合法')
            x += Decimal(operands[0].group())
            y += Decimal(operands[1].group())
            if x != x.quantize(PRECISION) or y != y.quantize(PRECISION):
                raise ValueError('输入精度超过本工程的 3 位小数；拒绝静默舍入')
            command = f'1 0 0 1 {x:.3f} {y:.3f} Tm'.encode('ascii')
            edits.append((operands[0].start(), token.end(), command))
    for start, end, replacement in reversed(edits):
        data = data[:start] + replacement + data[end:]
    return data, len(edits)


def normalize(source, destination):
    """写入独立输出；视觉和导航必须与原始构建一致。"""
    if source.resolve() == destination.resolve():
        raise ValueError('输入输出必须分离')
    before = pymupdf.open(source)
    after = pymupdf.open(source)
    count = 0
    for page in after:
        for xref in page.get_contents():
            data, changes = rewrite_stream(after.xref_stream(xref))
            after.update_stream(xref, data)
            count += changes
    after.save(destination, deflate=True)
    after.close()
    with pymupdf.open(destination) as checked:
        assert len(before) == len(checked)
        assert before.get_toc() == checked.get_toc(), '书签发生变化'
        for index, page in enumerate(before):
            assert page.get_links() == checked[index].get_links(), '链接发生变化'
            # 每个字形及其顺序必须相同；只允许 PDF 浮点运算的亚像素尾差。
            original_chars = [c for span in page.get_texttrace() for c in span['chars']]
            changed_chars = [c for span in checked[index].get_texttrace() for c in span['chars']]
            assert len(original_chars) == len(changed_chars), '字形数量发生变化'
            for original, changed in zip(original_chars, changed_chars):
                assert original[:2] == changed[:2], '字形编号或顺序发生变化'
                delta = max(abs(a-b) for a,b in zip(original[2]+original[3], changed[2]+changed[3]))
                assert delta <= 0.001, f'第 {index+1} 页字形位置误差过大：{delta}'
            # 某些字形恰在栅格边界上，精确等价的十进制位置仍可能触发不同抗锯齿。
            # 仍要求至少一个固定 DPI 完全相同，不使用宽松像素差阈值。
            matched = None
            for dpi in (144, 216, 72, 96):
                a = page.get_pixmap(dpi=dpi)
                b = checked[index].get_pixmap(dpi=dpi)
                if a.samples == b.samples:
                    matched = dpi
                    break
            assert matched is not None, f'第 {index+1} 页视觉发生变化'
            if matched != 144:
                print(f'第 {index+1} 页：浮点栅格边界尾差；{matched} dpi 像素完全一致，字形坐标误差不超过 0.001 pt。')
    before.close()
    print(f'文本定位规范化：{count} 处；逐页渲染、链接和书签不变。')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    normalize(args.source, args.destination)
