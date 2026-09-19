# -*- coding: utf-8 -*-
"""Генерирует src/keyframes.css.

Траектория полёта берётся из макета (Figma 1386:17442) через traj.py:
вход слева -> дуга через кадр -> выход за правый край -> петля под баннером
вне кадра -> возврат снизу по центру -> остановка в точке покоя.

Комета и солнышко едут по одному и тому же пути с общим профилем скорости,
а подмена одного другим происходит вне кадра, поэтому стыка не видно.
Скорость задана явно: ровная на видимом участке, чуть быстрее на петле
(этого не видно) и плавно гаснущая к точке покоя. Желейное растяжение
выводится из мгновенной скорости по тому же пути.
"""
import math
from pathlib import Path

import traj

OUT = Path(__file__).parent / 'keyframes.css'
L = []
def w(s=''):
    L.append(s)

# ---------------------------------------------------------------- геометрия
BASE_CX, BASE_CY = 283.46, 95.53         # центр .sun-pos при left:177.99 top:-10
BASE_SIZE = 210.939                       # размер солнышка в финальном кадре (1386:17452)
FIGMA_DY = -1.0                           # поправка к координатам Figma по вертикали
REST_SIZE = 111.64                        # рабочий размер на паузе

# ---------------------------------------------------------------- путь
P = traj.build()
ACC = traj.arclen(P)
TOTAL = ACC[-1]
pos_at_u = lambda u: traj.at_length(P, ACC, TOTAL * min(max(u, 0.0), 1.0))

def _u_exit():
    """Доля пути, на которой объект уходит за правый край."""
    ins = [0 <= x <= traj.FRAME_W and 0 <= y <= traj.FRAME_H for x, y in P]
    for i in range(len(P) - 1, 0, -1):
        if ins[i - 1] and not ins[i]:
            return ACC[i] / TOTAL
    return 0.5

U_EXIT = _u_exit()
U_DEC = 0.78          # с этой доли пути начинаем гасить скорость (объект вне кадра)
U_HAND = 0.70         # здесь комета сменяется солнышком — тоже вне кадра
V1 = 852.0            # скорость на видимом участке, px/с
BOOST = 1.24          # разгон на петле: её не видно, а пустая пауза короче

# На вершине дуги комета слегка «зависает», как брошенный предмет. Провал
# мягкий и симметричный, скорость на стыках не меняется, зато растяжение —
# оно считается из скорости — на глазах отпускает и снова набирается.
U_TOP, HANG, HANG_W = 0.30, 0.80, 0.135

def _hang(u):
    r = (u - U_TOP) / HANG_W
    return 1 - (1 - HANG) * math.exp(-r * r)

def _speed(u):
    if u <= U_EXIT:
        return V1 * _hang(u)
    r = min(1.0, (u - U_EXIT) / 0.06)
    return V1 * _hang(u) * (1 + (BOOST - 1) * (r * r * (3 - 2 * r)))

# --- фаза A: от старта до U_DEC, время интегрируем по пути
NA = 900
_ta, _ua = [0.0], [0.0]
for i in range(1, NA + 1):
    u0, u1 = (i - 1) / NA * U_DEC, i / NA * U_DEC
    ds = (u1 - u0) * TOTAL
    _ta.append(_ta[-1] + ds / _speed((u0 + u1) / 2))
    _ua.append(u1)
T_DEC = _ta[-1]

# --- фаза B: от U_DEC до точки покоя, easeOutCubic со стыковкой по скорости
L3 = (1 - U_DEC) * TOTAL
T3 = 3 * L3 / _speed(U_DEC)
T_REST = T_DEC + T3

def u_at_time(t):
    if t >= T_REST:
        return 1.0
    if t > T_DEC:
        x = (t - T_DEC) / T3
        return U_DEC + (1 - (1 - x) ** 3) * (1 - U_DEC)
    lo, hi = 0, len(_ta) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if _ta[mid] < t:
            lo = mid + 1
        else:
            hi = mid
    if lo == 0:
        return 0.0
    f = (t - _ta[lo - 1]) / max(_ta[lo] - _ta[lo - 1], 1e-9)
    return _ua[lo - 1] + (_ua[lo] - _ua[lo - 1]) * f

def _t_at_u(u):
    lo, hi = 0.0, T_REST
    for _ in range(60):
        mid = (lo + hi) / 2
        if u_at_time(mid) < u:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2

def _u_enter():
    ins = [0 <= x <= traj.FRAME_W and 0 <= y <= traj.FRAME_H for x, y in P]
    for i in range(len(P) - 1, 0, -1):
        if ins[i] and not ins[i - 1]:
            return ACC[i] / TOTAL
    return 0.9

T_HAND = _t_at_u(U_HAND)          # момент подмены кометы солнышком
U_ENTER = _u_enter()
T_ENTER = _t_at_u(U_ENTER)        # момент возврата в кадр снизу

# ---------------------------------------------------------------- тайминг
HOLD_T1 = T_REST + 2.20                   # пауза: взгляд и моргание
MOVE_T1 = HOLD_T1 + 1.60                  # уход вправо и рост
SUN_DUR = MOVE_T1
GAZE_T0 = T_REST + 0.45
REACT_T0 = MOVE_T1 + 0.80                 # солнышко заметило число
REACT_DUR = 0.55                          # и меняется в лице
LOOP_T0 = MOVE_T1 + 1.70                  # старт зацикленной части

MOVE_PTS = [(traj.REST[0], traj.REST[1], REST_SIZE),
            (228.0, 70.0, 140.0), (262.0, 70.0, 178.0),
            (289.0, 86.0, 218.0), (BASE_CX, BASE_CY + 1, BASE_SIZE)]

# ---------------------------------------------------------------- помощники
r2 = lambda v: round(v, 3)

def kf(name, rows, dur, fmt):
    w('@keyframes %s{' % name)
    seen = set()
    for r in rows:
        p = round(max(0.0, min(dur, r[0])) / dur * 100, 3)
        if p in seen:
            continue
        seen.add(p)
        w('  %s%%{%s}' % (p, fmt(*r[1:])))
    w('}')
    w()

def lerp(a, b, t):
    return a + (b - a) * t

def ease_in_out(p):
    return 4 * p ** 3 if p < .5 else 1 - (-2 * p + 2) ** 3 / 2

def catmull(pts, u):
    n = len(pts) - 1
    s = min(int(u * n), n - 1)
    t = u * n - s
    p0, p1, p2, p3 = pts[max(s - 1, 0)], pts[s], pts[s + 1], pts[min(s + 2, n)]
    t2, t3 = t * t, t * t * t
    return [0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2
                   + (-a + 3 * b - 3 * c + d) * t3)
            for a, b, c, d in zip(p0, p1, p2, p3)]

# перепараметризация сплайна ухода вправо по длине дуги
_LUT, _prev, _acc = [], catmull(MOVE_PTS, 0.0), 0.0
for _i in range(1, 601):
    _p = catmull(MOVE_PTS, _i / 600)
    _acc += math.hypot(_p[0] - _prev[0], _p[1] - _prev[1])
    _LUT.append((_acc, _i / 600))
    _prev = _p
_MT = _LUT[-1][0]

def move_at(p):
    target = p * _MT
    lo, hi = 0, len(_LUT) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if _LUT[mid][0] < target:
            lo = mid + 1
        else:
            hi = mid
    return catmull(MOVE_PTS, _LUT[lo][1])

def simplify(ts, vals, tol):
    """Оставляет только ключи, без которых линейная интерполяция ушла бы
    дальше tol: густо на быстрых участках, почти пусто на паузе."""
    keep, i = [0], 0
    while i < len(ts) - 1:
        j = i + 2
        while j < len(ts):
            ok = True
            for m in range(i + 1, j):
                f = (ts[m] - ts[i]) / (ts[j] - ts[i])
                for a, b, c in zip(vals[i], vals[j], vals[m]):
                    if abs(lerp(a, b, f) - c) > tol:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
            j += 1
        keep.append(j - 1)
        i = j - 1
    if keep[-1] != len(ts) - 1:
        keep.append(len(ts) - 1)
    return keep

# ---------------------------------------------------------------- солнышко
GROW_U0 = 0.86          # с этой доли пути солнышко начинает расти
START_SIZE = 26.0

def sun_at(t):
    """(cx, cy, size, opacity) в момент t."""
    if t < T_HAND:
        x, y = pos_at_u(U_HAND)
        return (x, y, START_SIZE, 0.0)
    if t <= T_REST:
        u = u_at_time(t)
        x, y = pos_at_u(u)
        f = ease_in_out(min(1.0, max(0.0, (u - GROW_U0) / (1 - GROW_U0))))
        return (x, y, lerp(START_SIZE, REST_SIZE, f), 1.0)
    if t <= HOLD_T1:
        return (traj.REST[0], traj.REST[1], REST_SIZE, 1.0)
    p = ease_in_out(min(1.0, (t - HOLD_T1) / (MOVE_T1 - HOLD_T1)))
    return tuple(move_at(p)) + (1.0,)

STEPS = 240
TS_ALL = [SUN_DUR * i / STEPS for i in range(STEPS + 1)]
PATH_ALL = [sun_at(t) for t in TS_ALL]
_keep = simplify(TS_ALL, [(c[0], c[1], c[2] * .6, c[3] * 40) for c in PATH_ALL], 0.45)
TS = [TS_ALL[i] for i in _keep]
PATH = [PATH_ALL[i] for i in _keep]

w('/* ---- солнышко: возврат снизу по траектории из макета, пауза, уход вправо ---- */')
kf('sunPath', [(t, c[0] - BASE_CX, c[1] + FIGMA_DY - BASE_CY, c[3]) for t, c in zip(TS, PATH)],
   SUN_DUR, lambda dx, dy, o: 'transform:translate(%.2fpx,%.2fpx);opacity:%.2f' % (dx, dy, o))
kf('sunSize', [(t, c[2] / BASE_SIZE) for t, c in zip(TS, PATH)],
   SUN_DUR, lambda k: 'transform:scale(%.4f)' % k)

# ---------------------------------------------------------------- желе
MAX_V = 300.0      # скорость, при которой растяжение максимально
MAX_A = 0.17       # предельное растяжение вдоль направления движения

def wobble_at(t, t0, amp, cycles=2.0, dur=0.85, decay=3.4):
    """Затухающее колебание с t0. amp > 0 — сначала сплющивание."""
    if not (t0 <= t <= t0 + dur):
        return 0.0
    f = (t - t0) / dur
    return amp * math.exp(-decay * f) * math.cos(2 * math.pi * cycles * f)

JELLY_DUR = LOOP_T0
_last_ang = [0.0]

def jelly_at(t):
    h = 0.02
    t0, t1 = max(0.0, t - h), min(SUN_DUR, t + h)
    if t1 <= t0:
        vx = vy = 0.0
    else:
        a, b = sun_at(t0), sun_at(t1)
        vx, vy = (b[0] - a[0]) / (t1 - t0), (b[1] - a[1]) / (t1 - t0)
    sp = math.hypot(vx, vy)
    amp = min(MAX_A, sp / MAX_V * MAX_A)
    if sp > 5:
        _last_ang[0] = math.degrees(math.atan2(vy, vx))
    b = wobble_at(t, T_REST, 0.16) + wobble_at(t, MOVE_T1, 0.115)
    return _last_ang[0], 1 + amp, 1 - amp, 1 + b, 1 - b

JSTEPS = 320
JTS = [JELLY_DUR * i / JSTEPS for i in range(JSTEPS + 1)]
JV = [jelly_at(t) for t in JTS]
JV[-1] = (JV[-1][0], 1.0, 1.0, 1.0, 1.0)
_jk = simplify(JTS, [(v[0] * .4, v[1] * 60, v[2] * 60, v[3] * 60, v[4] * 60) for v in JV], 0.4)
w('/* ---- желе: растяжение выведено из мгновенной скорости по траектории ---- */')
kf('sunJelly', [(JTS[i],) + JV[i] for i in _jk], JELLY_DUR,
   lambda ang, sx, sy, wx, wy:
   'transform:rotate(%.1fdeg) scale(%.4f,%.4f) rotate(%.1fdeg) scale(%.4f,%.4f)'
   % (ang, sx, sy, -ang, wx, wy))

# ---------------------------------------------------------------- комета
# Комета — то же желе, что солнышко, просто летит вчетверо быстрее, поэтому
# форма считается из движения по тому же принципу, а не рисуется позой:
#   цель  = растяжение по скорости (тот же закон) минус сплющивание на
#           повороте (центростремительное ускорение прижимает тело),
#   форма = цель, до которой тело догоняется пружиной.
# Пружина почти критическая: она сглаживает, а не раскачивает — тело ведёт себя
# как плотная капля, а не как студень на пружинке.
# Голова смотрит точно вдоль пути, а вот хвост догоняет её мягче и на дуге
# заметно отстаёт — это и читается как взмах.
C_VREF = 880.0        # скорость, при которой комета растянута полностью
C_AMAX = 0.22         # предельное растяжение вдоль оси тела
C_TURN = 0.12         # вклад поворота: прижимает тело поперёк движения
LAT_REF = 9000.0      # поперечное ускорение, при котором вклад максимален
BODY_F, BODY_Z = 3.2, 0.80    # пружина формы: догоняет без раскачки
TAIL_F, TAIL_Z = 2.6, 0.70    # хвост мягче — отстаёт, но тоже не дрожит
TAIL_STRETCH = 0.35           # хвост тянется сильнее головы
DIR_W = 0.011         # окно, по которому снимается скорость, с
ANG_W = 0.024         # окно, по которому снимается направление, с
ANG_SMOOTH = 0.012    # и сглаживание направления, с
TURN_W = 0.026        # окно для скорости поворота, с
SMOOTH_W = 0.022      # сглаживание цели перед пружиной, с
# Ломаная траектории состоит из отрезков по 0,6 px, поэтому «мгновенные»
# направление и кривизна по ней — ступеньки и шум. Плюс у самой линии из макета
# есть излом на 75-й px пути: заход по касательной стыкуется с кривой, которая
# сразу за стыком уходит на 30° за 6 px. По времени это 7 мс — в движении
# не видно, но голова на таком успевает дёрнуться. Поэтому направление снимаем
# хордой в ~20 px и сглаживаем: угол идёт ровно, путь остаётся как в макете.


def _unwrap(seq):
    """Убирает скачки угла через ±180°, иначе пружина дёрнется на петле."""
    out = [seq[0]]
    for v in seq[1:]:
        while v - out[-1] > 180:
            v -= 360
        while v - out[-1] < -180:
            v += 360
        out.append(v)
    return out


def _box(vals, half):
    """Скользящее среднее — снимает шум сетки, не сдвигая фазу."""
    if half < 1:
        return list(vals)
    n = len(vals)
    return [sum(vals[max(i - half, 0):min(i + half + 1, n)])
            / len(vals[max(i - half, 0):min(i + half + 1, n)]) for i in range(n)]


def _spring(grid, tgt, f, zeta, x0):
    """Значение, догоняющее tgt пружиной с заданным затуханием."""
    w0 = 2 * math.pi * f
    x, v, out = x0, 0.0, [x0]
    for i in range(1, len(grid)):
        dt = grid[i] - grid[i - 1]
        v += (w0 * w0 * (tgt[i - 1] - x) - 2 * zeta * w0 * v) * dt
        x += v * dt
        out.append(x)
    return out


def soft_body(dur, sample, calm=False, bias=None):
    """Желейная дорожка кометы: (ts, ang, amp, dtail) на отрезке [0, dur].

    bias(t) — добавка к цели поверх движения (ей тело растягивают на краях,
    пока оно рассеивается).
    """
    n = max(int(dur * 1200), 80)
    grid = [dur * i / n for i in range(n + 1)]
    pos = [sample(t) for t in grid]
    step = dur / n
    dw = max(1, int(DIR_W / step))
    tw = max(1, int(TURN_W / step))

    aw = max(1, int(ANG_W / step))
    sp, ang = [], []
    for i in range(len(grid)):
        lo, hi = max(i - dw, 0), min(i + dw, n)
        dt = grid[hi] - grid[lo]
        sp.append(math.hypot(pos[hi][0] - pos[lo][0], pos[hi][1] - pos[lo][1]) / dt)
        lo, hi = max(i - aw, 0), min(i + aw, n)
        ang.append(math.degrees(math.atan2(pos[hi][1] - pos[lo][1], pos[hi][0] - pos[lo][0])))
    sp = _box(sp, dw)
    ang = _box(_unwrap(ang), max(1, int(ANG_SMOOTH / step)))

    tgt = []
    for i in range(len(grid)):
        lo, hi = max(i - tw, 0), min(i + tw, n)
        om = abs(ang[hi] - ang[lo]) * math.pi / 180 / (grid[hi] - grid[lo])
        tgt.append(C_AMAX * min(1.0, sp[i] / C_VREF)
                   - C_TURN * min(1.0, sp[i] * om / LAT_REF))
    if bias:
        tgt = [v + bias(t) for v, t in zip(tgt, grid)]
    tgt = _box(tgt, max(1, int(SMOOTH_W / step)))

    amp = _spring(grid, tgt, BODY_F, BODY_Z, tgt[0] if calm else 0.0)
    tang = _spring(grid, ang, TAIL_F, TAIL_Z, ang[0])
    return grid, ang, amp, [t - a for t, a in zip(tang, ang)]


def dash_keys(name, dur, sample, tol=0.4, bias=None):
    """Пишет пару keyframes: тело (поворот + желе) и взмах хвоста."""
    grid, ang, amp, dtail = soft_body(dur, sample, False, bias)
    keep = simplify(grid, [(a * .35, m * 90, d * 1.4) for a, m, d in zip(ang, amp, dtail)], tol)
    kf(name, [(grid[i], ang[i], amp[i]) for i in keep], dur,
       lambda a, m: 'transform:rotate(%.2fdeg) scale(%.4f,%.4f)' % (a, 1 + m, 1 - m))
    kf(name + 'Tail', [(grid[i], dtail[i], amp[i]) for i in keep], dur,
       lambda d, m: 'transform:rotate(%.2fdeg) scale(%.4f,%.4f)'
       % (d, 1 + m * TAIL_STRETCH, 1 - m * TAIL_STRETCH * .5))


def smoothstep(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


# Комета не включается и не выключается на краю кадра, а собирается из ничего
# на входе и слегка рассеивается на выходе — у обоих краёв она полупрозрачная.
FADE_IN0, FADE_IN_W = 0.012, 0.095
FADE_OUT0, FADE_OUT_W, FADE_OUT_TO = 0.470, 0.085, 0.16
DISPERSE = 0.11       # пока тело тает, оно ещё и вытягивается — истончается

def _fade(u):
    return (smoothstep((u - FADE_IN0) / FADE_IN_W)
            * (1 - (1 - FADE_OUT_TO) * smoothstep((u - FADE_OUT0) / FADE_OUT_W)))


DASH_DUR = T_HAND
w('/* ---- комета: тот же путь до подмены солнышком (подмена вне кадра) ---- */')
rows = []
ND = 150
for i in range(ND + 1):
    t = DASH_DUR * i / ND
    u = u_at_time(t)
    x, y = pos_at_u(u)
    rows.append((t, x, y, round(_fade(u), 3)))
_dk = simplify([r[0] for r in rows], [(r[1], r[2], r[3] * 45) for r in rows], 0.4)
kf('dashFly', [rows[i] for i in _dk], DASH_DUR,
   lambda x, y, o: 'transform:translate(%.1fpx,%.1fpx);opacity:%s' % (x, y, o))

w('/* ---- желе кометы: форма догоняет движение пружиной, хвост — тело ---- */')
dash_keys('dashJelly', DASH_DUR, lambda t: pos_at_u(u_at_time(t)),
          bias=lambda t: DISPERSE * (1 - _fade(u_at_time(t))))

# ---------------------------------------------------------------- цикл
LOOP = 4.4
w('/* ---- цикл: пульсация и медленное «дыхание» желе ---- */')
kf('jellyIdle', [(0, 1.0, 1.0), (LOOP * .28, 1.022, .978), (LOOP * .55, .984, 1.016),
                 (LOOP * .80, 1.010, .990), (LOOP, 1.0, 1.0)],
   LOOP, lambda sx, sy: 'transform:scale(%.4f,%.4f)' % (sx, sy))
kf('sunPulse', [(0, 1.0, 0, 0), (LOOP * .45, .952, 6, -3), (LOOP, 1.0, 0, 0)],
   LOOP, lambda k, dx, dy: 'transform:translate(%spx,%spx) scale(%s)' % (dx, dy, k))

PRESS = 0.74
prows = [(0.0, 1.0, 1.0), (0.085, 1.17, .855)]
for i in range(1, 19):
    t = 0.085 + (PRESS - 0.085) * i / 18
    b = wobble_at(t, 0.085, 0.115, cycles=2.4, dur=PRESS - 0.085, decay=3.6)
    prows.append((t, 1 + b, 1 - b))
prows[-1] = (PRESS, 1.0, 1.0)
w('/* ---- отклик на нажатие ---- */')
kf('sunPress', prows, PRESS, lambda sx, sy: 'transform:scale(%.4f,%.4f)' % (sx, sy))

# ---------------------------------------------------------------- глаза
EASE_BK = 'cubic-bezier(.34,1.24,.44,1)'
GD = LOOP_T0 - GAZE_T0
w('/* ---- взгляд и моргание ---- */')
kf('gazeIntro', [(0.00, 0), (0.35, 0), (0.65, -9), (1.05, -9), (1.35, -9),
                 (1.65, 9), (2.05, 9), (2.35, 9), (2.65, 0), (GD, 0)], GD,
   lambda dx: 'transform:translateX(%spx);animation-timing-function:%s' % (dx, EASE_BK))
kf('gazeLoop', [(0.00, 0), (0.45, 0), (0.85, 9), (1.75, 9), (2.15, 0), (2.55, 0),
                (2.95, -9), (3.70, -9), (4.10, 0), (4.40, 0)], LOOP,
   lambda dx: 'transform:translateX(%spx);animation-timing-function:%s' % (dx, EASE_BK))

OPEN, SHUT = 'height:36px;y:-18px', 'height:13px;y:-6.5px'
def blink(name, dur, centres, half=0.075):
    rows = [(0.0, OPEN)]
    for c in centres:
        if c + half < dur:
            rows += [(c - half, OPEN), (c, SHUT), (c + half, OPEN)]
    rows.append((dur, OPEN))
    kf(name, rows, dur, lambda v: '%s;animation-timing-function:cubic-bezier(.4,0,.5,1)' % v)
blink('blinkIntro', GD, [1.05, 2.05, 2.62, 3.25, 3.95, 4.55, 5.15])
blink('blinkLoop', LOOP, [0.40, 1.80, 2.55, 3.72])

# ---------------------------------------------------------------- свечение, лучи
SOFT = 'drop-shadow(0 0 8.4px rgba(var(--glow-a),.55)) drop-shadow(0 0 22px rgba(var(--glow-b),.25))'
FULL = 'drop-shadow(0 0 8.4px rgba(var(--glow-a),1)) drop-shadow(0 0 22px rgba(var(--glow-b),1))'
BIG = 'drop-shadow(0 0 11px rgba(var(--glow-a),1)) drop-shadow(0 0 30px rgba(var(--glow-b),1))'
# ---------------------------------------------------------------- реакция
# До появления числа баннер у всех одинаковый — оранжевый, обычные глаза.
# Дальше персонаж «видит» число и меняется в лице, а фон уходит в свою палитру:
# на светлую эмоцию ярче, на тёмную темнее и тусклее.
# Раскадровка восторга — Figma 1380:17010, позы — 1310:16477 (луна — 1310:16478).
#
# Каждая эмоция приходит через одни и те же первые кадры (обычные -> округлились)
# и дальше расходится к своей позе.
#
# Персонаж замечает число и сразу моргает: глаза сжимаются по вертикали в
# чёрточку, ровно в этот момент подменяются на новую позу, и та из чёрточки
# раскрывается. Промежуточных кадров нет — одно моргание, и уже другая эмоция.
#
# Двух фигур одновременно на экране не бывает: если показать обе целиком, их
# наложение читается как третья фигура, то есть как рывок. Полупрозрачности
# тоже нет — глаза вырезаны маской, и подтаявший вырез выглядел бы как моргание
# не там, где надо. Сжатие только по вертикали: горизонтальное двигало бы
# каждый глаз к центру пары, то есть вбок.
FADE = 0.17                               # половина моргания, с
FLAT = 0.14                               # до чего сплющивается поза в момент подмены
EPS = 0.008                               # подмена мгновенная, но ключи нужны разные
BLINK = 0.50                              # доля реакции, на которой происходит подмена
TEAR = 0.78                               # слеза набегает уже после

SEQS = {}
for _m in ('spark', 'stars', 'happy', 'half', 'closed', 'sad'):
    SEQS[_m] = [('bar', 0, BLINK), (_m, BLINK, None)]
SEQS['sad'].append(('tear', TEAR, None))

BRIGHT = ('spark', 'stars', 'happy')      # от них фон светлеет
DIM = ('half', 'closed', 'sad')           # от них темнеет


def pose_keys(name, a, b):
    """Дорожка одной позы: (время, прозрачность, сжатие по вертикали)."""
    if a <= 0:
        rows = [(0.0, 1, 1.0)]
    else:
        t = REACT_DUR * a
        rows = [(0.0, 0, FLAT), (max(0.0, t - EPS), 0, FLAT),
                (t, 1, FLAT), (min(REACT_DUR, t + FADE), 1, 1.0)]
    if b is None:
        rows.append((REACT_DUR, 1, 1.0))
    else:
        t = REACT_DUR * b
        rows += [(max(rows[-1][0], t - FADE), 1, 1.0), (t, 1, FLAT),
                 (min(REACT_DUR, t + EPS), 0, FLAT), (REACT_DUR, 0, FLAT)]
    kf(name, rows, REACT_DUR,
       lambda o, s: 'opacity:%s;transform:scaleY(%.3f)' % (o, s))


w('/* ---- реакция: позы глаз сменяются через моргание ---- */')
MOOD_CSS = []
for mood, seq in SEQS.items():
    for cls, a, b in seq:
        name = mood + cls[:1].upper() + cls[1:]
        pose_keys(name, a, b)
        MOOD_CSS.append('.stage[data-mood="%s"] .eyes-%s{display:block;'
                        'animation:%s %ss %ss cubic-bezier(.45,0,.55,1) both}'
                        % (mood, cls, name, r2(REACT_DUR), r2(REACT_T0)))

w('/* ---- реакция: фон уходит в палитру настроения ---- */')
w('@keyframes bgTo{to{background:var(--to-bg)}}')
w()
w('@keyframes blob1To{to{background:var(--to-blob-1)}}')
w()
w('@keyframes blob2To{to{background:var(--to-blob-2)}}')
w()
w('@keyframes innerTo{to{box-shadow:inset 0 0 6px 4px rgba(255,255,255,.9),'
  ' inset 0 0 46px 0 var(--to-inner)}}')
w()

w('/* ---- свечение и вращение лучей ---- */')
w('@keyframes glowIn{from{filter:%s}to{filter:%s}}' % (SOFT, FULL))
w()
w('@keyframes glowBreath{0%%{filter:%s}45%%{filter:%s}100%%{filter:%s}}' % (FULL, BIG, FULL))
w()
w('@keyframes rayspin{from{transform:rotate(0)}to{transform:rotate(360deg)}}')
w()

# ---------------------------------------------------------------- текст
# Цифры не влетают сбоку, а вырастают каждая из центра своей формы: при малом
# масштабе цифра стягивается в точку у себя же в середине. Масштаб догоняет
# единицу той же пружиной, что и форма кометы, только распущенной — отсюда
# перелёт.
# Пока цифра больше своего размера, она шире и ниже, на возврате — уже и выше:
# то же «сохранение объёма», что у солнышка.
DIG_DUR, DIG_START = 0.52, 0.07
LBL_DUR, LBL_START = 0.40, 0.86
FIRE_DUR, FIRE_START = 0.34, 0.10


def pop_keys(name, dur, start, f, zeta, squash, fade):
    """Рост на месте с желейным перелётом: (масштаб, прозрачность)."""
    n = 60
    grid = [dur * i / n for i in range(n + 1)]
    k = _spring(grid, [1.0] * (n + 1), f, zeta, start)
    rows = []
    for t, v in zip(grid, k):
        # сплющивание — только про перелёт: на самом росте оно дало бы вместо
        # точки вертикальную щепку
        a = max(-0.09, min(0.09, squash * (v - 1)))
        rows.append((t, v * (1 + a), v * (1 - a), round(smoothstep(t / (dur * fade)), 3)))
    rows[-1] = (dur, 1.0, 1.0, 1.0)
    kf(name, rows, dur,
       lambda sx, sy, o: 'transform:scale(%.4f,%.4f);opacity:%s' % (sx, sy, o))


w('/* ---- текст: цифра вырастает на месте с желейным перелётом ---- */')
pop_keys('digitIn', DIG_DUR, DIG_START, 3.1, 0.58, 0.60, 0.24)

# Звёздочка луны: падает на ниточке и дальше едва заметно качается.
w('/* ---- звёздочка луны: падает на ниточке и качается ---- */')
w('@keyframes starIn{')
w('  0%{opacity:0;transform:translateY(-9px) rotate(-7deg)}')
w('  45%{opacity:1}')
w('  62%{transform:translateY(0) rotate(4.5deg)}')
w('  82%{transform:translateY(0) rotate(-2deg)}')
w('  100%{opacity:1;transform:translateY(0) rotate(0)}')
w('}')
w()
kf('starSwing', [(0, 0.0), (LOOP * .30, 2.4), (LOOP * .62, -2.0),
                 (LOOP * .84, 0.8), (LOOP, 0.0)],
   LOOP, lambda a: 'transform:rotate(%.2fdeg)' % a)

w('/* ---- подпись: появляется на месте, дальше чуть дышит, как желе ---- */')
pop_keys('lblIn', LBL_DUR, LBL_START, 3.6, 0.62, 0.50, 0.45)

# Огонёк — не часть подписи, а свой акцент: он распускается из точки у себя в
# середине, как цифры, а не проявляется вместе с текстом. Подпись стартует с
# 0.86 — на ней это выглядит как мягкое проявление, а на иконке 17 px было бы
# просто «включили».
w('/* ---- огонёк: распускается из своего центра, как цифры ---- */')
pop_keys('fireIn', FIRE_DUR, FIRE_START, 3.6, 0.62, 0.55, 0.28)
kf('lblPulse', [(0, 1.0, 1.0), (LOOP * .30, 1.016, .986), (LOOP * .58, .990, 1.010),
                (LOOP * .82, 1.006, .995), (LOOP, 1.0, 1.0)],
   LOOP, lambda sx, sy: 'transform:scale(%.4f,%.4f)' % (sx, sy))

# Цифры в цикле тоже дышат: размер гуляет, плюс лёгкий наклон вокруг центра.
# У двойки и нуля фазы разведены — в унисон это выглядело бы как дрожь всего
# блока, а не как две живые цифры.
def idle_keys(name, pts, amp=0.018, tilt=0.8):
    """pts — опорные точки (доля цикла, размер, наклон) в долях амплитуды.
    На концах цикла дорожка строго единичная, иначе вход в цикл заметен."""
    rows = [(0.0, 1.0, 1.0, 0.0)]
    for f, k, r in pts:
        rows.append((LOOP * f, 1 + amp * k, 1 - amp * k, tilt * r))
    rows.append((LOOP, 1.0, 1.0, 0.0))
    kf(name, rows, LOOP,
       lambda sx, sy, r: 'transform:rotate(%.3fdeg) scale(%.4f,%.4f)' % (r, sx, sy))

idle_keys('digitIdle2', [(.24, 1.0, .55), (.52, -.62, -1.0), (.78, .34, .45)])
idle_keys('digitIdle0', [(.34, 1.0, .60), (.62, -.58, -1.0), (.86, .30, .40)])

OUT.write_text('\n'.join(L) + '\n', encoding='utf-8')


# ---------------------------------------------------------------- moods.css
# Какие позы участвуют в каком настроении и куда уходит фон. Правил много и все
# они механические, поэтому файл пишет генератор, а не рука.
ML = ['/* создаётся gen_keyframes.py — руками не править */']

def _pal(moods, pre):
    sel = ',\n'.join('.stage[data-mood="%s"]' % m for m in moods)
    ML.append('%s{--to-bg:var(--%s-bg); --to-blob-1:var(--%s-blob-1);\n'
              '   --to-blob-2:var(--%s-blob-2); --to-inner:var(--%s-inner)}'
              % (sel, pre, pre, pre, pre))

_pal(BRIGHT, 'up')
_pal(DIM, 'down')
_all = ',\n'.join('.stage[data-mood="%s"]' % m for m in SEQS)
ML.append('%s{animation:bgTo .7s %ss ease-out both}' % (_all, r2(REACT_T0)))
for _cls, _name in (('b41', 'blob1To'), ('b40', 'blob2To'), ('inner', 'innerTo')):
    _sel = ',\n'.join('.stage[data-mood="%s"] .%s' % (m, _cls) for m in SEQS)
    ML.append('%s{animation:%s .7s %ss ease-out both}' % (_sel, _name, r2(REACT_T0)))
ML.append('/* после реакции взгляд по сторонам выключен: он возил бы позу вбок */')
_gz = ',\n'.join('.stage[data-mood="%s"] .gaze' % m for m in SEQS)
ML.append('%s{animation:gazeIntro %ss %ss both}'
          % (_gz, r2(LOOP_T0 - GAZE_T0), r2(GAZE_T0)))
ML.append('/* позы: выкладываем нужные и отдаём порядок дорожкам */')
ML += MOOD_CSS
(Path(__file__).parent / 'moods.css').write_text('\n'.join(ML) + '\n', encoding='utf-8')
# ---------------------------------------------------------------- тайминг в bindings
TIMES = dict(
    DASH_DUR=r2(DASH_DUR),          # комета летит до подмены вне кадра
    SUN_DUR=r2(SUN_DUR),            # путь солнышка: возврат, пауза, уход вправо
    JELLY_DUR=r2(JELLY_DUR),        # желейная дорожка вступления
    GAZE_T0=r2(GAZE_T0), GD=r2(GD), # мимика: старт и длительность
    LOOP=r2(LOOP_T0),               # с этого момента идёт бесконечный цикл
    SPIN_T0=r2(T_REST + 1.20),      # лучи начинают вращаться
    GLOW_T0=r2(T_REST + 1.10),      # свечение разгорается
    GLOW_T1=r2(T_REST + 2.30),      # и дальше «дышит»
    NUM_T0=r2(MOVE_T1 + 0.25),
    NUM0_T0=r2(MOVE_T1 + 0.37),   # ноль выскакивает сразу следом за двойкой
    REACT_T0=r2(REACT_T0), REACT_DUR=r2(REACT_DUR),
    STAR_T0=r2(MOVE_T1 + 0.05),  # звёздочка падает, как только луна встала
    LBL_T0=r2(MOVE_T1 + 0.85),   # после того, как цифры встали на место
    FIRE_T0=r2(MOVE_T1 + 0.91),  # огонёк — следом за подписью, свой акцент
    T_ENTER=r2(T_ENTER), T_REST=r2(T_REST), HOLD_T1=r2(HOLD_T1), MOVE_T1=r2(MOVE_T1))
(Path(__file__).parent / 'times.py').write_text(
    '# создаётся gen_keyframes.py\nTIMES = %r\n' % TIMES, encoding='utf-8')

print('keyframes.css: %d строк' % len(L))
print('  путь %.0f px, выход за кадр %.1f%%, возврат %.1f%%' % (TOTAL, U_EXIT * 100, U_ENTER * 100))
print('  комета 0..%.2f с | вне кадра %.2f..%.2f с | покой %.2f с' % (T_HAND, _t_at_u(U_EXIT), T_ENTER, T_REST))
print('  пауза до %.2f с | уход вправо до %.2f с | цикл с %.2f с' % (HOLD_T1, MOVE_T1, LOOP_T0))
print('  реакция %.2f..%.2f с' % (REACT_T0, REACT_T0 + REACT_DUR))
