# -*- coding: utf-8 -*-
"""Снимает анимацию покадрово из banner.html и собирает GIF.
   python export_gif.py            -> preview-full.gif и preview-loop.gif, 25 fps
"""
import ast
import asyncio, sys
from pathlib import Path
from playwright.async_api import async_playwright
from PIL import Image

R = Path(__file__).parent
TMP = R / '.frames'
URL = (R / 'banner.html').as_uri()

async def grab(t0, t1, fps, tag):
    TMP.mkdir(exist_ok=True)
    n = int(round((t1 - t0) * fps))
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 500, 'height': 300}, device_scale_factor=1)
        await pg.goto(URL)
        await pg.evaluate('()=>document.fonts.ready')
        await pg.wait_for_timeout(600)
        el = pg.locator('.stage')
        await pg.evaluate("()=>document.fonts.ready")
        for i in range(n):
            t = t0 + i / fps
            await pg.evaluate(
                "(t)=>{document.getAnimations().forEach(a=>{try{a.pause();a.currentTime=t*1000}catch(e){}})}", t)
            await pg.wait_for_timeout(25)
            await el.screenshot(path=str(TMP / f'{tag}{i:04d}.png'))
        await b.close()
    return n

def build(tag, n, fps, out):
    frames = [Image.open(TMP / f'{tag}{i:04d}.png').convert('RGB')
              .convert('P', palette=Image.ADAPTIVE, colors=256) for i in range(n)]
    frames[0].save(R / out, save_all=True, append_images=frames[1:],
                   duration=int(round(1000 / fps)), loop=0, optimize=True, disposal=2)
    print(out, f'{n} кадров', f'{(R/out).stat().st_size/1024:.0f} КБ')

async def main():
    _t = (R / 'src' / 'times.py').read_text(encoding='utf-8')
    loop0 = ast.literal_eval(_t[_t.index('{'):])['LOOP']      # старт зацикленной части
    n = await grab(0.0, loop0 + 4.4, 25, 'f'); build('f', n, 25, 'preview-full.gif')
    n = await grab(loop0, loop0 + 4.4, 25, 'l'); build('l', n, 25, 'preview-loop.gif')
    for p in TMP.glob('*.png'): p.unlink()
    TMP.rmdir()

asyncio.run(main())
