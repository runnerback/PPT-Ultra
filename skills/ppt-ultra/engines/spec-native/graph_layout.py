# -*- coding: utf-8 -*-
"""
Spec Native engine · 按内容画的图示布局（模型只给节点 / 边 / 泳道 / 参与者，坐标在这里算）

- flow      ：Graphviz dot（splines=ortho）算节点坐标与正交折线；direction LR / TB（层级分解就是 TB 的 flow）
- swimlane  ：dot 只做排序（LR 布局的 x 决定列），y 由泳道行决定；边按正交折线自己走
- sequence  ：公式布局，直接在 ppt_build._draw_sequence 里画；这里只做校验

输出 dg 规格交 ppt_build._draw_diagram 渲染（与 diagram 版式同一份规格）：
  { bounds:{x,y,w,h}, nodes:[{kind:'shape'|'group', shape, x,y,w,h, text, emph, laneLabelW}], edges:[{points:[{x,y}], startArrow, endArrow, label, style}] }
单位英寸、y 向下。校验不通过直接抛 ValueError（有问题及时暴露，不兜底）。
依赖：系统包 graphviz（dot）。macOS `brew install graphviz`，Ubuntu `apt install graphviz`，Windows 官方安装包并加入 PATH。
"""
import shlex
import shutil
import subprocess

# 文字限制按字形宽度（英寸）而不是字数：英文单词占位小（按字数会误拒「消息+session_key」这类混排）
LIMITS = dict(nodes=14, edges=20, text_w=2.6, label_w=2.0, lanes=5, participants=6, participant_w=1.6, messages=12, msg_w=2.4)
SHAPES = {'rect': 'rect', 'round': 'round_rect', 'diamond': 'diamond', 'pill': 'round_rect', 'circle': 'ellipse'}
DOT_SHAPES = {'rect': 'box', 'round': 'box', 'diamond': 'diamond', 'pill': 'box', 'circle': 'ellipse'}
DIRECTIONS = ('LR', 'TB')
LANE_LABEL_W = 0.95
SWIM_NODE_W_MAX = 1.9    # 泳道图节点最宽（超过就折两行）
SWIM_COL_GAP = 0.45     # 列间距（连线标签放这里）
SWIM_ROW_H = 1.2


def _tw(text):
    """文本宽度估算（英寸，10.5pt）：中日韩字 0.17，其它 0.09"""
    return sum(0.17 if ord(ch) > 0x2E7F else 0.09 for ch in text)


def _node_size(text, shape):
    tw = _tw(text) + 0.4
    w = min(2.3, max(1.0, tw))
    h = 0.8 if tw > 2.3 else 0.6
    if shape == 'diamond':
        w += 0.5; h += 0.25
    elif shape == 'circle':
        w = h = max(0.85, h)
    return w, h


def validate_graph(g, kind):
    if not isinstance(g, dict):
        raise ValueError(f'{kind} 页缺少 graph 对象')
    nodes = g.get('nodes'); edges = g.get('edges') or []
    if not isinstance(nodes, list) or not nodes:
        raise ValueError(f'{kind} 页 graph.nodes 为空')
    if len(nodes) > LIMITS['nodes']:
        raise ValueError(f'{kind} 页节点 {len(nodes)} 个超过上限 {LIMITS["nodes"]}')
    ids = set()
    for n in nodes:
        nid = str(n.get('id') or '').strip(); text = str(n.get('text') or '').strip()
        if not nid or nid in ids:
            raise ValueError(f'{kind} 页节点 id 缺失或重复：{nid!r}')
        if not text:
            raise ValueError(f'{kind} 页节点 {nid} 没有 text')
        if _tw(text) > LIMITS['text_w']:
            raise ValueError(f'{kind} 页节点「{text}」太宽（上限约 {round(LIMITS["text_w"] / 0.17)} 个汉字宽）')
        if n.get('shape') and n['shape'] not in SHAPES:
            raise ValueError(f'{kind} 页节点「{text}」形状 {n["shape"]!r} 不在 {sorted(SHAPES)} 内')
        ids.add(nid)
    if not isinstance(edges, list):
        raise ValueError(f'{kind} 页 graph.edges 须为数组')
    if len(edges) > LIMITS['edges']:
        raise ValueError(f'{kind} 页连线 {len(edges)} 条超过上限 {LIMITS["edges"]}')
    for e in edges:
        a, b = str(e.get('from') or ''), str(e.get('to') or '')
        if a not in ids or b not in ids:
            raise ValueError(f'{kind} 页连线引用了不存在的节点：{a!r} → {b!r}')
        if a == b:
            raise ValueError(f'{kind} 页连线不能自指：{a!r}')
        if _tw(str(e.get('label') or '')) > LIMITS['label_w']:
            raise ValueError(f'{kind} 页连线标签「{e.get("label")}」太宽（上限约 {round(LIMITS["label_w"] / 0.17)} 个汉字宽）')
    if g.get('direction') and g['direction'] not in DIRECTIONS:
        raise ValueError(f'{kind} 页 direction 只能是 LR / TB，收到 {g["direction"]!r}')
    if kind == 'swimlane':
        lanes = g.get('lanes')
        if not isinstance(lanes, list) or not lanes or len(lanes) > LIMITS['lanes']:
            raise ValueError('泳道图 lanes 须为 1~5 条')
        lanes = [str(x).strip() for x in lanes]
        if len(set(lanes)) != len(lanes) or not all(lanes):
            raise ValueError('泳道图 lanes 有重复或空名')
        for n in nodes:
            if str(n.get('lane') or '') not in lanes:
                raise ValueError(f'泳道图节点「{n["text"]}」的 lane {n.get("lane")!r} 不在 lanes 内')
    elif not edges:
        raise ValueError('流程图没有 edges')


def validate_sequence(seq):
    if not isinstance(seq, dict):
        raise ValueError('sequence 页缺少 sequence 对象')
    parts = seq.get('participants'); msgs = seq.get('messages')
    if not isinstance(parts, list) or not (2 <= len(parts) <= LIMITS['participants']):
        raise ValueError(f'时序图 participants 须为 2~{LIMITS["participants"]} 个')
    parts = [str(p).strip() for p in parts]
    if len(set(parts)) != len(parts) or not all(parts):
        raise ValueError('时序图 participants 有重复或空名')
    for p in parts:
        if _tw(p) > LIMITS['participant_w']:
            raise ValueError(f'时序图参与者「{p}」太宽（上限约 {round(LIMITS["participant_w"] / 0.17)} 个汉字宽）')
    if not isinstance(msgs, list) or not (1 <= len(msgs) <= LIMITS['messages']):
        raise ValueError(f'时序图 messages 须为 1~{LIMITS["messages"]} 条')
    for m in msgs:
        a, b, text = str(m.get('from') or ''), str(m.get('to') or ''), str(m.get('text') or '').strip()
        if a not in parts or b not in parts:
            raise ValueError(f'时序图消息引用了不存在的参与者：{a!r} → {b!r}')
        if a == b:
            raise ValueError(f'时序图消息不能自指：{a!r}')
        if not text or _tw(text) > LIMITS['msg_w']:
            raise ValueError(f'时序图消息「{text}」为空或太宽（上限约 {round(LIMITS["msg_w"] / 0.17)} 个汉字宽）')
        if m.get('kind') and m['kind'] not in ('sync', 'async', 'return'):
            raise ValueError(f'时序图消息 kind {m["kind"]!r} 只能是 sync / async / return')


def _run_dot(src):
    if not shutil.which('dot'):
        raise RuntimeError('未安装 Graphviz（dot），flow / swimlane / hierarchy 版式需要它')
    r = subprocess.run(['dot', '-Tplain'], input=src.encode('utf-8'), capture_output=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError('dot 布局失败：' + r.stderr.decode('utf-8', 'replace')[:300])
    return r.stdout.decode('utf-8')


def _dot_source(g, direction, keys, ortho):
    has_label = any(e.get('label') for e in g.get('edges') or [])
    L = [f'digraph G {{ rankdir={direction}; splines={"ortho" if ortho else "line"}; nodesep={0.55 if has_label else 0.4}; ranksep=0.6; node [fixedsize=true label=""]; edge [arrowsize=0.6];']
    for n in g['nodes']:
        w, h = _node_size(str(n['text']).strip(), n.get('shape'))
        L.append(f'{keys[n["id"]]} [shape={DOT_SHAPES.get(n.get("shape"), "box")} width={w:.2f} height={h:.2f}];')
    for e in g.get('edges') or []:
        L.append(f'{keys[e["from"]]} -> {keys[e["to"]]};')
    L.append('}')
    return '\n'.join(L)


def _parse_plain(text):
    """dot -Tplain → { h, nodes:{key:(cx,cy,w,h)}, edges:[(tail, head, [(x,y)...])] }（坐标单位英寸，y 向上）"""
    out = {'h': 0.0, 'nodes': {}, 'edges': []}
    for line in text.splitlines():
        t = shlex.split(line)
        if not t:
            continue
        if t[0] == 'graph':
            out['h'] = float(t[3])
        elif t[0] == 'node':
            out['nodes'][t[1]] = (float(t[2]), float(t[3]), float(t[4]), float(t[5]))
        elif t[0] == 'edge':
            n = int(t[3])
            pts = [(float(t[4 + 2 * k]), float(t[5 + 2 * k])) for k in range(n)]
            out['edges'].append((t[1], t[2], pts))
    return out


def _dedupe(points):
    res = []
    for p in points:
        if not res or abs(p['x'] - res[-1]['x']) > 0.01 or abs(p['y'] - res[-1]['y']) > 0.01:
            res.append(p)
    return res


def _edge_out(e, points):
    arrow = e.get('arrow') or 'end'
    return {
        'points': points, 'label': str(e.get('label') or '').strip(),
        'style': 'dashed' if e.get('style') == 'dashed' else 'solid',
        'startArrow': arrow == 'both', 'endArrow': arrow in ('end', 'both'),
    }


def layout_flow(g):
    validate_graph(g, 'flow')
    keys = {n['id']: f'n{i + 1}' for i, n in enumerate(g['nodes'])}
    plain = _parse_plain(_run_dot(_dot_source(g, g.get('direction') or 'LR', keys, ortho=True)))
    H = plain['h']
    nodes = []
    for n in g['nodes']:
        cx, cy, w, h = plain['nodes'][keys[n['id']]]
        nodes.append({'id': n['id'], 'kind': 'shape', 'shape': SHAPES.get(n.get('shape'), 'round_rect'), 'x': cx - w / 2, 'y': (H - cy) - h / 2,
                      'w': w, 'h': h, 'text': str(n['text']).strip(), 'emph': bool(n.get('emph'))})
    edges = []
    for e in g.get('edges') or []:
        match = next((pe for pe in plain['edges'] if pe[0] == keys[e['from']] and pe[1] == keys[e['to']]), None)
        if not match:
            raise RuntimeError(f'dot 没有返回连线 {e["from"]} → {e["to"]} 的坐标')
        points = _dedupe([{'x': x, 'y': H - y} for x, y in match[2]])
        if len(points) < 2:
            raise RuntimeError(f'连线 {e["from"]} → {e["to"]} 坐标点不足')
        edges.append(_edge_out(e, points))
        plain['edges'].remove(match)   # 平行边各取各的
    return {'bounds': _bounds(nodes, edges), 'nodes': nodes, 'edges': edges}


def _route_swim(s, t):
    sx, sy = s['x'] + s['w'] / 2, s['y'] + s['h'] / 2
    tx, ty = t['x'] + t['w'] / 2, t['y'] + t['h'] / 2
    if t['x'] >= s['x'] + s['w']:                      # 向前：右侧出、左侧进
        x1, x2 = s['x'] + s['w'], t['x']
        if s['lane'] == t['lane']:
            return [{'x': x1, 'y': sy}, {'x': x2, 'y': ty}]
        xm = (x1 + x2) / 2
        return [{'x': x1, 'y': sy}, {'x': xm, 'y': sy}, {'x': xm, 'y': ty}, {'x': x2, 'y': ty}]
    if s['lane'] == t['lane']:                          # 同泳道回边：走节点上方
        yg = s['y'] - 0.14
        return [{'x': sx, 'y': s['y']}, {'x': sx, 'y': yg}, {'x': tx, 'y': yg}, {'x': tx, 'y': t['y']}]
    if t['y'] > s['y']:                                 # 目标在下：走行间空隙
        yg = (s['y'] + s['h'] + t['y']) / 2
        return [{'x': sx, 'y': s['y'] + s['h']}, {'x': sx, 'y': yg}, {'x': tx, 'y': yg}, {'x': tx, 'y': t['y']}]
    yg = (t['y'] + t['h'] + s['y']) / 2
    return [{'x': sx, 'y': s['y']}, {'x': sx, 'y': yg}, {'x': tx, 'y': yg}, {'x': tx, 'y': t['y'] + t['h']}]


def layout_swimlane(g):
    validate_graph(g, 'swimlane')
    lanes = [str(x).strip() for x in g['lanes']]
    keys = {n['id']: f'n{i + 1}' for i, n in enumerate(g['nodes'])}
    plain = _parse_plain(_run_dot(_dot_source(g, 'LR', keys, ortho=False)))
    # 列号：按 dot 的 x 归并（同 rank 的 x 相同）
    xs = sorted({round(plain['nodes'][keys[n['id']]][0], 2) for n in g['nodes']})
    col_of = {x: i for i, x in enumerate(xs)}
    # 每列宽 = 该列最宽节点 + 列间距（短文字的列窄，整图不至于被拉得很宽再缩小）；长文字折两行而不是缩字号
    sized = []
    for n in g['nodes']:
        col = col_of[round(plain['nodes'][keys[n['id']]][0], 2)]
        w, h = _node_size(str(n['text']).strip(), n.get('shape'))
        if w > SWIM_NODE_W_MAX:
            w, h = SWIM_NODE_W_MAX, 0.8
        sized.append((n, col, w, h))
    col_w = [0.0] * len(xs)
    for _, col, w, _h in sized:
        col_w[col] = max(col_w[col], w + SWIM_COL_GAP)
    col_x = []
    acc = LANE_LABEL_W + 0.3
    for cw in col_w:
        col_x.append(acc); acc += cw
    nodes = []
    for n, col, w, h in sized:
        lane = lanes.index(str(n['lane']).strip())
        nodes.append({'id': n['id'], 'kind': 'shape', 'shape': SHAPES.get(n.get('shape'), 'round_rect'), 'lane': lane,
                      'x': col_x[col] + (col_w[col] - w) / 2, 'y': lane * SWIM_ROW_H + (SWIM_ROW_H - h) / 2,
                      'w': w, 'h': h, 'text': str(n['text']).strip(), 'emph': bool(n.get('emph'))})
    by_id = {n['id']: n for n in nodes}
    total_w = acc + 0.2
    groups = [{'id': f'lane{i}', 'kind': 'group', 'x': 0, 'y': i * SWIM_ROW_H, 'w': total_w, 'h': SWIM_ROW_H - 0.08, 'text': name, 'laneLabelW': LANE_LABEL_W}
              for i, name in enumerate(lanes)]
    edges = [_edge_out(e, _route_swim(by_id[e['from']], by_id[e['to']])) for e in g.get('edges') or []]
    all_nodes = groups + nodes
    return {'bounds': {'x': 0, 'y': 0, 'w': total_w, 'h': len(lanes) * SWIM_ROW_H - 0.08}, 'nodes': all_nodes, 'edges': edges}


def _bounds(nodes, edges):
    xs = [n['x'] for n in nodes] + [n['x'] + n['w'] for n in nodes] + [p['x'] for e in edges for p in e['points']]
    ys = [n['y'] for n in nodes] + [n['y'] + n['h'] for n in nodes] + [p['y'] for e in edges for p in e['points']]
    x0, y0 = min(xs), min(ys)
    return {'x': x0, 'y': y0, 'w': max(1.0, max(xs) - x0), 'h': max(1.0, max(ys) - y0)}


def layout(g, kind):
    if kind == 'flow':
        return layout_flow(g)
    if kind == 'swimlane':
        return layout_swimlane(g)
    raise ValueError(f'未知图示类型 {kind!r}')
