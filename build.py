# -*- coding: utf-8 -*-
"""Собирает из src/ три файла: banner.html (голый баннер, это продакшн),
index.html (превью) и playground.html (конструктор: глаза, цвета, части, анимация).

Перед сборкой прогоняет src/gen_keyframes.py — он пересчитывает keyframes.css
из траекторий макета.
"""
import ast
import subprocess
import sys
from pathlib import Path

R = Path(__file__).parent
def rd(p):
    return (R / p).read_text(encoding='utf-8')

subprocess.run([sys.executable, str(R / 'src' / 'gen_keyframes.py')], check=True)

# времена анимаций считает генератор — подставляем их в bindings.css
_times = rd('src/times.py')
TIMES = ast.literal_eval(_times[_times.index('{'):])
BINDINGS = rd('src/bindings.css')
for _k, _v in TIMES.items():
    BINDINGS = BINDINGS.replace('{%s}' % _k, str(_v))
import re as _re
_left = _re.findall(r'\{[A-Z][A-Z_0-9]*\}', BINDINGS)
assert not _left, 'в bindings.css остались неподставленные времена: %s' % _left

# компонент: {LOOP} ему нужен, чтобы уметь перематывать на зацикленную часть
BANNER_JS = (rd('src/banner.js').replace('{LOOP}', str(TIMES['LOOP']))
             .replace('{REACT_T0}', str(TIMES['REACT_T0'])))

FONTS = rd('src/fonts.css')
PREVIEW = rd('src/preview.css')
CSS = (rd('src/base.css') + '\n' + rd('src/keyframes.css') + '\n'
       + rd('src/moods.css') + '\n' + BINDINGS)
STAGE = rd('src/banner.html')
MOON = rd('src/moon.html').strip()
for _ph, _f in (('MOON_CLOSED', 'moon/eye-closed.path'), ('MOON_HAPPY', 'moon/eye-happy.path'),
                ('MOON_SPARK', 'moon/eye-spark.path'), ('MOON_SAD', 'moon/eye-sad.path'),
                ('MOON_TEAR', 'moon/eye-tear.path'), ('GEM_PATH', 'eyes/gem.path'),
                ('STAR_EYE', 'eyes/star.path'), ('MOON_PATH', 'moon/moon.path')):
    MOON = MOON.replace(_ph, rd('src/' + _f).strip())
STAGE = STAGE.replace('<!--<<MOON>>-->', MOON)
STAGE = STAGE.replace('STAR_PATH', rd('src/moon/star.path').strip())

EYES = rd('src/eyes.html').strip()
for _ph, _f in (('HAPPY_PATH', 'eyes/happy.path'), ('STAR_PATH', 'eyes/star.path'),
                ('SAD_PATH', 'eyes/sad.path'), ('TEAR_PATH', 'eyes/tear.path'),
                ('WINK_PATH', 'eyes/wink.path'), ('GEM_PATH', 'eyes/gem.path'),
                ('SPARK_PATH', 'eyes/spark.path')):
    EYES = EYES.replace(_ph, rd('src/' + _f).strip())
STAGE = STAGE.replace('EYES', EYES)
for _ph, _f in (('RAYS_PATH', 'rays.path'), ('DIGIT2', 'digit2.path'),
                ('DIGIT0', 'digit0.path'), ('FIRE', 'fire.path')):
    STAGE = STAGE.replace(_ph, rd('src/' + _f).strip())

# Скрипт нужен только для отклика на нажатие — сама анимация работает без JS.
PRESS_JS = """
function bindPress(st) {
  var layer = st.querySelector('.sun-press');
  st.addEventListener('pointerdown', function () {
    layer.classList.remove('press');
    void layer.offsetWidth;                 // перезапуск анимации
    layer.classList.add('press');
  });
  layer.addEventListener('animationend', function (e) {
    if (e.animationName === 'sunPress') layer.classList.remove('press');
  });
}
""".strip()

BANNER = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MYOR — баннер «Солнышко»</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;display:grid;place-items:center;background:transparent}
/*<<FONTS>>*/
/*<<CSS>>*/</style>
</head>
<body>
<!--<<STAGE>>-->
<script>
/*<<PRESS>>*/
document.querySelectorAll('.stage').forEach(bindPress);
</script>
</body>
</html>
"""

INDEX = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MYOR — анимация «Солнышко»</title>
<style>
/*<<FONTS>>*/

/* ---------- страница-превью (в продакшн не нужна) ---------- */
/*<<PREVIEW>>*/
/*<<CSS>>*/</style>
</head>
<body>

<div class="row">
  <div><p class="cap">1 : 1 — 382 × 144</p><div class="banner-host"></div></div>
  <div><p class="cap">× 2</p><div class="zoom-box"><div class="banner-host"></div></div></div>
</div>

<div class="ui">
  <button id="replay">↻ Проиграть заново</button>
  <button id="slow">Замедлить ×0.35</button>
</div>
<p class="hint">Вступление проигрывается один раз (≈6,5 с), дальше — бесконечный цикл.
Нажмите на баннер: солнышко сплющивается и отыгрывает желейный отскок.<br>
Цвета, части, состояния глаз и режим анимации — в <a href="playground.html">конструкторе</a>.</p>

<template id="tpl">
<!--<<STAGE>>-->
</template>

<script>
/*<<BANNER_JS>>*/

var banners = [];
document.querySelectorAll('.banner-host').forEach(function (h) {
  banners.push(MyorBanner.mount(h));
});

document.getElementById('replay').onclick = function () {
  banners.forEach(function (b) { b.replay(); });
};
var slow = false;
document.getElementById('slow').onclick = function (e) {
  slow = !slow;
  banners.forEach(function (b) { b.set({speed: slow ? 0.35 : 1}); });
  e.target.textContent = slow ? 'Обычная скорость' : 'Замедлить ×0.35';
};
</script>
</body>
</html>
"""

def fill(tpl, **parts):
    for k, v in parts.items():
        for marker in ('/*<<%s>>*/' % k, '<!--<<%s>>-->' % k):
            tpl = tpl.replace(marker, v)
    return tpl

(R / 'banner.html').write_text(
    fill(BANNER, FONTS=FONTS, CSS=CSS, STAGE=STAGE, PRESS=PRESS_JS), encoding='utf-8')
(R / 'index.html').write_text(
    fill(INDEX, FONTS=FONTS, PREVIEW=PREVIEW, CSS=CSS, STAGE=STAGE, BANNER_JS=BANNER_JS),
    encoding='utf-8')
(R / 'playground.html').write_text(
    fill(rd('src/playground.html'), FONTS=FONTS, CSS=CSS, STAGE=STAGE, BANNER_JS=BANNER_JS),
    encoding='utf-8')

print('собрано: banner.html, index.html, playground.html')
