/* Настраиваемый баннер «Солнышко».
   MyorBanner.mount(host, opts) -> экземпляр. Разметку берёт из <template id="tpl">.
   opts:
     char    персонаж: sun | moon
     mood    во что перетекают глаза после появления числа:
             spark | stars | happy | half | closed | sad | none
     eyes    auto — поза идёт из реакции; остальные фиксируют позу и глушат её:
             open | half | closed | wide | squint | dash | gem | spark | happy |
             stars | sad
     mode    intro (со вступления) | loop (сразу цикл) | static (стоп-кадр)
     speed   множитель скорости
     press   реакция на нажатие
     number, label, fire, comet   показывать ли часть
     labelText   текст подписи (две строки)
     colors  {bg, blob-1, blob-2, inner-glow, ink, rays-1..3, face-1..3, radius}
*/
var MyorBanner = (function () {
  var LOOP = {LOOP};          // с этого момента идёт бесконечный цикл, с
  var REACT = {REACT_T0};       // с этого момента солнышко меняется в лице, с
  var uid = 0;

  function uniquify(frag) {
    // id в <defs> должны быть уникальны на странице, иначе второй баннер
    // возьмёт маску и градиенты первого
    var n = uid++;
    frag.querySelectorAll('defs [id]').forEach(function (el) {
      var was = el.id, now = was + '-' + n;
      el.id = now;
      frag.querySelectorAll('*').forEach(function (node) {
        for (var i = 0; i < node.attributes.length; i++)
          if (node.attributes[i].value === 'url(#' + was + ')')
            node.attributes[i].value = 'url(#' + now + ')';
      });
    });
  }

  function Banner(host, opts) {
    this.host = host;
    this.opts = {char: 'sun', mood: 'spark', eyes: 'auto', mode: 'intro', speed: 1, press: true,
                 number: true, label: true, fire: true, comet: true};
    this.build();
    this.set(opts || {});
  }

  Banner.prototype.build = function () {
    var frag = document.getElementById('tpl').content.cloneNode(true);
    uniquify(frag);
    this.host.innerHTML = '';
    this.host.appendChild(frag);
    this.el = this.host.querySelector('.stage');
    this._mode = null;

    var self = this, layer = this.el.querySelector('.sun-press');
    this.el.addEventListener('pointerdown', function () {
      if (!self.opts.press) return;
      layer.classList.remove('press');
      void layer.offsetWidth;                 // перезапуск анимации
      layer.classList.add('press');
      self.rate();                            // новая дорожка тоже должна идти в такт
    });
    layer.addEventListener('animationend', function (e) {
      if (e.animationName === 'sunPress') layer.classList.remove('press');
    });
  };

  Banner.prototype.anims = function () {
    // Смена data-mood или data-eyes создаёт новые дорожки, но только при
    // пересчёте стилей. Без него часть из них в список не попадёт — и
    // перемотка достанется не всем: одни окажутся на 5,7 с, другие на нуле.
    void this.el.offsetWidth;
    return this.el.getAnimations({subtree: true});
  };

  Banner.prototype.rate = function () {
    var r = this.opts.speed;
    this.anims().forEach(function (a) { try { a.playbackRate = r; } catch (e) {} });
  };

  /* Переключение режима без перестройки: вступление — это просто начало общей
     дорожки, поэтому «сразу цикл» = перемотка на LOOP, «стоп-кадр» = ещё пауза. */
  Banner.prototype.mode = function () {
    var m = this.opts.mode;
    if (m === this._mode) return;
    this._mode = m;
    this.anims().forEach(function (a) {
      try {
        a.play();
        a.currentTime = (m === 'intro' ? 0 : LOOP * 1000);
        if (m === 'static') a.pause();
      } catch (e) {}
    });
  };

  /* Перемотать все дорожки на t секунд. */
  Banner.prototype.seek = function (t, paused) {
    this.anims().forEach(function (a) {
      try {
        // play() сначала, перемотка потом: на уже отыгравшей дорожке play()
        // откатывает время в ноль, и перемотка ей не достаётся
        a.play();
        a.currentTime = t * 1000;
        if (paused) { a.pause(); }
      } catch (e) {}
    });
    this.rate();
    return this;
  };

  Banner.prototype.set = function (opts) {
    for (var k in opts) this.opts[k] = opts[k];
    var o = this.opts, st = this.el;
    // Смена настроения или позы меняет набор правил, а значит и набор дорожек:
    // новые стартуют с нуля, вместе с задержкой до реакции. Поэтому запоминаем,
    // где мы были, и возвращаем туда же.
    var cur = this.anims(), at = null, paused = false;
    if (cur.length) {
      at = cur[0].currentTime;
      paused = cur[0].playState === 'paused';
    }
    st.setAttribute('data-char', o.char);
    st.setAttribute('data-mood', o.mood);
    st.setAttribute('data-eyes', o.eyes);
    st.setAttribute('data-number', o.number ? 'on' : 'off');
    st.setAttribute('data-label', o.label ? 'on' : 'off');
    st.setAttribute('data-fire', o.fire ? 'on' : 'off');
    st.setAttribute('data-comet', o.comet ? 'on' : 'off');
    if (o.labelText != null) st.querySelector('.lbl i').textContent = o.labelText;
    if (o.colors) for (var c in o.colors) st.style.setProperty('--' + c, o.colors[c]);
    if (at != null) {
      this.seek(at / 1000, paused);
    }
    this.mode();
    this.rate();
    return this;
  };

  /* Проиграть заново: вступление стартует с нуля только на свежей разметке. */
  Banner.prototype.replay = function () {
    var o = this.opts;
    this.build();
    this._mode = null;
    return this.set(o);
  };

  return {
    mount: function (host, opts) { return new Banner(host, opts); },
    LOOP: LOOP,
    REACT: REACT
  };
})();
