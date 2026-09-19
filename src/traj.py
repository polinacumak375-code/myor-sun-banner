# -*- coding: utf-8 -*-
"""Траектория полёта из макета (Figma 1386:17442, «Arrow 2»).

В экспорте Figma стрелка — это залитый контур обводки. Центральная линия
собрана из «прямых» участков этого контура и лежит в traj.path в координатах
svg-ассета. Здесь она разбирается, переводится в координаты кадра 382 x 144,
достраивается заходом из-за левого края и подводкой к точке покоя солнышка,
после чего параметризуется по длине дуги.

Путь: вход слева -> дуга через кадр -> выход за правый край -> петля под
баннером вне кадра -> возврат снизу по центру -> остановка в точке покоя.
"""
import math
import re
from pathlib import Path

# смещение из системы координат svg-ассета в координаты кадра
OFF_X, OFF_Y = 18.23, 47.01
REST = (190.8, 75.86)          # точка покоя солнышка (Figma 1380:17347)
FRAME_W, FRAME_H = 382, 144


def _parse(d):
    """Разбирает путь из M и абсолютных C в список кубических сегментов."""
    nums = re.findall(r'-?\d*\.?\d+(?:e-?\d+)?', d)
    nums = [float(n) for n in nums]
    segs = []
    cur = (nums[0], nums[1])
    i = 2
    while i + 5 < len(nums) + 1 and i + 5 <= len(nums):
        p1 = (nums[i], nums[i + 1])
        p2 = (nums[i + 2], nums[i + 3])
        p3 = (nums[i + 4], nums[i + 5])
        segs.append((cur, p1, p2, p3))
        cur = p3
        i += 6
    return segs


def _bez(p0, p1, p2, p3, t):
    m = 1 - t
    return (m ** 3 * p0[0] + 3 * m * m * t * p1[0] + 3 * m * t * t * p2[0] + t ** 3 * p3[0],
            m ** 3 * p0[1] + 3 * m * m * t * p1[1] + 3 * m * t * t * p2[1] + t ** 3 * p3[1])


def _sample(segs, per_seg=140):
    pts = []
    for s in segs:
        for i in range(per_seg + (1 if s is segs[-1] else 0)):
            pts.append(_bez(*s, i / per_seg))
    return pts


def _cut_at_frame_return(pts):
    """Индекс, на котором путь возвращается в кадр снизу (последний вход)."""
    inside = [0 <= x <= FRAME_W and 0 <= y <= FRAME_H for x, y in pts]
    for i in range(len(pts) - 1, 0, -1):
        if inside[i] and not inside[i - 1]:
            return i
    return len(pts) - 1


def build():
    """Возвращает список точек пути в координатах кадра."""
    raw = _sample(_parse(Path(__file__).parent.joinpath('traj.path').read_text(encoding='utf-8')))
    pts = [(x + OFF_X, y + OFF_Y) for x, y in raw]

    # --- заход из-за левого края: продолжаем по касательной в начале кривой,
    #     направление на стыке совпадает, так что излома не видно
    p0, p1 = pts[0], pts[8]
    d = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) or 1
    t0 = ((p1[0] - p0[0]) / d, (p1[1] - p0[1]) / d)
    LEAD = 74.0
    lead = [(p0[0] - t0[0] * LEAD * (1 - i / 26), p0[1] - t0[1] * LEAD * (1 - i / 26))
            for i in range(26)]

    # --- обрезаем «хвост» стрелки и подводим к точке покоя
    cut = _cut_at_frame_return(pts) + 22      # немного выше нижнего края
    body = lead + pts[:cut]
    p = body[-1]
    q = body[-6]
    d = math.hypot(p[0] - q[0], p[1] - q[1]) or 1
    tan = ((p[0] - q[0]) / d, (p[1] - q[1]) / d)
    dist = math.hypot(REST[0] - p[0], REST[1] - p[1])
    c1 = (p[0] + tan[0] * dist * .55, p[1] + tan[1] * dist * .55)
    c2 = (REST[0], REST[1] + dist * .45)      # приходим снизу, гасим скорость
    tail = [_bez(p, c1, c2, REST, i / 40) for i in range(1, 41)]
    return body + tail


def arclen(pts):
    acc = [0.0]
    for a, b in zip(pts, pts[1:]):
        acc.append(acc[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    return acc


def at_length(pts, acc, s):
    """Точка на пути по пройденной длине."""
    if s <= 0:
        return pts[0]
    if s >= acc[-1]:
        return pts[-1]
    lo, hi = 0, len(acc) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if acc[mid] < s:
            lo = mid + 1
        else:
            hi = mid
    a, b = pts[lo - 1], pts[lo]
    f = (s - acc[lo - 1]) / max(acc[lo] - acc[lo - 1], 1e-9)
    return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)


if __name__ == '__main__':
    P = build()
    A = arclen(P)
    print('точек %d, длина %.1f px' % (len(P), A[-1]))
    for f in [i / 20 for i in range(21)]:
        x, y = at_length(P, A, A[-1] * f)
        tag = '' if (0 <= x <= FRAME_W and 0 <= y <= FRAME_H) else '   [вне кадра]'
        print('  %5.1f%%  x=%7.1f  y=%7.1f%s' % (f * 100, x, y, tag))
