/* ИИ Пресс-секретарь — фон первого экрана лендинга.
   Направление — сдержанность: один крупный целый знак справа, как одноцветная версия логотипа
   (листы одного тона, тени приглушают лист, а не вырезают его). Знак покачивается ±2,5°, дышит масштабом ±2,5%, раз в цикл по нему проходит блик.
   Фактура — сетка 12 колонок по контейнеру. Время суток (data-daypart у .lp-hero) меняет свет градиента
   и раскрытие веера; ночью — редкие звёзды. Левая половина под текстом остаётся чистой.
   Всё движение — синусы одной фазы цикла (24 с), поэтому цикл бесшовный.
   ?t=N замораживает кадр (для проверки), «Уменьшить движение» — один статичный кадр, пауза вне экрана и на скрытой вкладке. */
(function () {
    var hero = document.querySelector('.lp-hero');
    var canvas = hero && hero.querySelector('.lp-bg');
    if (!canvas || !canvas.getContext) return;
    var ctx = canvas.getContext('2d');
    var off = document.createElement('canvas');   // слой знака: собираем без нахлёста, кладём с одной прозрачностью
    var PERIOD = 24;                 // секунд в цикле
    var TAU = Math.PI * 2;
    var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
    var freeze = new URLSearchParams(location.search).get('t');

    /* Параметры суток: градиент (3 точки), раскрытие веера, свет, плотность постов */
    var DAY = {
        morning: { g: ['#56c6f2', '#1d71b8', '#1b5fa6'], open: 0.62, breathe: 0.22, sun: 1, horizon: 0, posts: 3, laps: 1, stars: 0, windows: 0 },
        day:     { g: ['#009fe3', '#1d71b8', '#1a63aa'], open: 0.92, breathe: 0.08, sun: 0, horizon: 0, posts: 6, laps: 2, stars: 0, windows: 0 },
        evening: { g: ['#1590d8', '#1d71b8', '#2b3f97'], open: 0.6,  breathe: 0.12, sun: 2, horizon: 1, posts: 3, laps: 1, stars: 0, windows: 6 },
        night:   { g: ['#1d71b8', '#22337e', '#312783'], open: 0.32, breathe: 0.06, sun: 0, horizon: 0, posts: 1, laps: 1, stars: 1, windows: 14 }
    };
    var part = hero.getAttribute('data-daypart') || 'day';
    var P = DAY[part] || DAY.day;

    /* Знак — настоящие контуры логотипа (координаты исходника 5669×5669).
       Три группы по порядку наложения: правый лист (задний), средний с тенью на правом, левый (передний) с тенью на среднем. */
    var GLYPH = [
        { side: 1,  sheets: ["M3720.19,2839.18l-572.18,1154.71-60.86,122.81-329.71-882.38c-1.19-3.17-2.33-6.37-3.44-9.59l71.95-505.75c42.35-78.96,97.59-152.06,163.21-211.45l541.2-489.89,66.89,74.35,87.56,97.32c124.93,138.85,141.13,436.45,35.38,649.87Z", "M4723.87,3339.65l-1093.38,989.71c-87.45,79.16-182.61,115.97-254.55,98.46-48.02-11.69-83.39-47.1-105.12-105.25l-26.86-71.89c.21-.42.41-.83.62-1.25l654.81-1321.45c67.88-136.98,99.36-301.15,88.64-462.25-11.04-166.03-65.93-311.7-154.54-410.19l-87.97-97.77,404.13-365.81c87.45-79.16,182.61-115.97,254.55-98.46,48.02,11.69,83.39,47.1,105.11,105.25l419.71,1123.26c65.38,174.96-28.57,457.81-205.15,617.64Z"], shades: [] },
        { side: 0,  sheets: ["M1926.21,3394.65c-124.93-138.85-141.13-436.46-35.38-649.87l353.54-713.47-86.91-49.82-356.23,718.89c-124.39,251.03-101.72,591.81,50.64,761.15l574.59,638.64,18.48-128.96-518.73-576.56ZM3684.81,2189.31l-87.56-97.32-66.89-74.35-66.89-74.34-580.67-645.4c-36.29-40.34-75.92-60.7-118.03-60.7-6.06,0-12.17.42-18.34,1.27-73.35,10.06-148.41,79.17-200.79,184.86l-212.3,428.44,153.87,88.2c114.94,65.89,212.58,187.13,274.93,341.4,33.16,82.06,54.57,168.96,63.58,255.66,6.36,61.34,6.52,122.59.23,181.95l-71.95,505.75-29.64,206.77-105.14,733.41,109,121.15c36.29,40.34,75.92,60.7,118.03,60.7,6.06,0,12.17-.42,18.34-1.27,55.4-7.6,111.78-48.89,158.62-114.18,15.18-21.15,29.35-44.82,42.17-70.68l21.77-43.93,60.86-122.81,572.18-1154.71c105.75-213.42,89.55-511.02-35.38-649.87Z"], shades: ["M3056.27,2581.67l540.98-489.68-66.89-74.35-66.89-74.34-541.42,490.09c-34.48,31.22-66.75,66.01-96.33,103.64,6.36,61.34,6.52,122.59.23,181.95l-71.95,505.75-29.64,206.77,298.85,799.81c15.18-21.15,29.35-44.82,42.17-70.68l21.77-43.93,60.86-122.81-296.9-794.57c-65.37-174.97,28.58-457.81,205.16-617.65Z"] },
        { side: -1, sheets: ["M2624.35,2719.79l-179.41,1251.42-18.48,128.96-11.4,79.49c-2.35,16.38-5.34,32.21-8.94,47.42-22.07,93.22-66.84,162.99-124.06,190.91-18.29,8.93-37.5,13.39-57.54,13.38-28.6,0-58.89-9.09-90.56-27.24l-1040.33-596.3c-162.04-92.88-270.39-370.53-236.59-606.3l209.28-1459.87c16.74-116.76,66.46-205.86,133-238.33,18.3-8.92,37.51-13.38,57.55-13.38,28.6,0,58.88,9.09,90.56,27.24l723.11,414.48,86.92,49.82,86.91,49.82,143.38,82.18c162.05,92.88,270.39,370.53,236.6,606.3Z"], shades: ["M1926.21,3394.65c-124.93-138.85-141.13-436.46-35.38-649.87l353.54-713.47-86.91-49.82-86.92-49.82-358.91,724.31c-67.88,136.98-99.36,301.15-88.64,462.25,11.04,166.02,65.93,311.7,154.54,410.19l628.59,698.66c3.6-15.21,6.59-31.04,8.94-47.42l11.4-79.49,18.48-128.96-518.73-576.56Z", "M2754,3224.73l68.32-476.56c1.39-9.67,2.6-19.4,3.63-29.19l-71.95,505.75Z"] }
    ];
    var GLYPH_PIVOT = { x: 2900, y: 4450 }, GLYPH_TOP = 1237, GLYPH_H = 4431 - 1237;
    var GPATH = (typeof Path2D === 'function') ? GLYPH.map(function (g) {
        return { side: g.side, sheets: g.sheets.map(function (p) { return new Path2D(p); }), shades: g.shades.map(function (p) { return new Path2D(p); }) };
    }) : null;

    /* Детерминированный генератор — звёзды и окна одинаковы между кадрами и заморозками */
    function rng(seed) { return function () { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; }; }

    var W = 0, H = 0, dpr = 1, stars = [], wins = [], cols = [], cardX = 0, cardW = 0;

    function layout() {
        var r = hero.getBoundingClientRect();
        dpr = Math.min(window.devicePixelRatio || 1, 2);
        W = Math.max(1, Math.round(r.width)); H = Math.max(1, Math.round(r.height));
        canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
        off.width = canvas.width; off.height = canvas.height;
        canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        /* Колонки сетки — ровно по контейнеру страницы (1200, поля 32/16) */
        var container = hero.querySelector('.lp-container');
        var cr = container.getBoundingClientRect();
        var pad = parseFloat(getComputedStyle(container).paddingLeft) || 0;
        var left = cr.left - r.left + pad, width = cr.width - pad * 2;
        cols = [];
        for (var i = 0; i <= 12; i++) cols.push(left + width * i / 12);
        /* Центр карточки примера — ось веера: карточка «вырастает» из знака */
        var card = hero.querySelector('.lp-demo .ps-post') || hero.querySelector('.lp-demo');
        if (card) { var k = card.getBoundingClientRect(); cardX = k.left - r.left + k.width / 2; cardW = k.width; }
        else { cardX = W * 0.72; cardW = W * 0.3; }
        var R = rng(part.length * 97 + 13);
        stars = [];
        for (var s = 0; s < 46; s++) stars.push({ x: R() * W, y: R() * H * 0.8, r: 0.6 + R() * 1.4, k: 1 + Math.floor(R() * 3), o: R() });
        wins = [];
        var row = H / 6;
        for (var w = 0; w < P.windows; w++) wins.push({ c: 6 + Math.floor(R() * 6), y: Math.round(1 + R() * 4) * row, o: R(), k: 1 + Math.floor(R() * 2) });
    }

    function roundRect(x, y, w, h, rad) {
        ctx.beginPath();
        ctx.moveTo(x + rad, y); ctx.lineTo(x + w - rad, y); ctx.quadraticCurveTo(x + w, y, x + w, y + rad);
        ctx.lineTo(x + w, y + h - rad); ctx.quadraticCurveTo(x + w, y + h, x + w - rad, y + h);
        ctx.lineTo(x + rad, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - rad);
        ctx.lineTo(x, y + rad); ctx.quadraticCurveTo(x, y, x + rad, y); ctx.closePath();
    }

    function draw(t) {
        var ph = (t % PERIOD) / PERIOD * TAU;      // фаза цикла 0..2π
        ctx.clearRect(0, 0, W, H);

        /* 1. Свет: градиент 200° — светлая сторона справа сверху, глубокая слева снизу (под текстом) */
        var a = 245 * Math.PI / 180, cx = W / 2, cy = H / 2, len = Math.abs(W * Math.sin(a)) + Math.abs(H * Math.cos(a));
        var gx = Math.sin(a) * len / 2, gy = -Math.cos(a) * len / 2;
        var g = ctx.createLinearGradient(cx - gx, cy - gy, cx + gx, cy + gy);
        g.addColorStop(0, P.g[0]); g.addColorStop(0.62, P.g[1]); g.addColorStop(1, P.g[2]);
        ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);

        /* 2. Фактура: колонки сетки по контейнеру, едва заметно */
        ctx.strokeStyle = 'rgba(255,255,255,0.05)'; ctx.lineWidth = 1;
        for (var i = 0; i < cols.length; i++) { var x = Math.round(cols[i]) + 0.5; ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }

        /* Ночь: редкие звёзды в правой половине, мерцание на кратных частотах фазы */
        if (P.stars) {
            for (var s = 0; s < stars.length; s++) {
                var st = stars[s];
                if (st.x < W * 0.5) continue;
                var tw = 0.4 + 0.6 * (0.5 + 0.5 * Math.sin(ph * st.k + st.o * TAU));
                ctx.fillStyle = 'rgba(255,255,255,' + (0.5 * tw).toFixed(3) + ')';
                ctx.beginPath(); ctx.arc(st.x, st.y, st.r * 0.8, 0, TAU); ctx.fill();
            }
        }

        /* 3. Знак — одноцветная версия логотипа целиком: белые листы, тени вырезаны (зазоры между листами).
           Знак не разбирается на части — в исходнике листы хранятся видимыми кусками, и при раздельном повороте
           вылезают рваные края. Движение — у знака целиком: покачивание вокруг оси ±2,5°, дыхание масштаба ±2,5%,
           раз в цикл по знаку проходит мягкий блик. Слой собирается отдельно и кладётся с одной прозрачностью. */
        if (!GPATH) return;
        var narrow = W < 960;
        var base = (narrow ? Math.min(H * 0.5, W * 0.8) : H * 1.15) / GLYPH_H;
        var breathe = 1 + 0.025 * Math.sin(ph);
        var gScale = base * breathe;
        var gw = 4100 * base;                                      // ширина знака в исходнике ≈ 4100
        var px = narrow ? W - gw * 0.34 : Math.min(W - gw * 0.24, cardX + cardW * 0.34);
        var py = H + GLYPH_H * base * 0.04;
        var sway = Math.sin(ph + Math.PI / 3) * 2.5 * Math.PI / 180;
        var oc = off.getContext('2d');
        oc.setTransform(1, 0, 0, 1, 0, 0); oc.clearRect(0, 0, off.width, off.height);
        oc.setTransform(dpr, 0, 0, dpr, 0, 0);
        oc.save();
        oc.translate(px, py); oc.rotate(sway); oc.scale(gScale, gScale);
        oc.translate(-GLYPH_PIVOT.x, -GLYPH_PIVOT.y);
        oc.fillStyle = '#ffffff';
        for (var gi = 0; gi < GPATH.length; gi++) for (var si = 0; si < GPATH[gi].sheets.length; si++) oc.fill(GPATH[gi].sheets[si]);
        /* Тени не вырезают лист, а приглушают его на 45% — как в цветном логотипе: листы целые, глубина видна */
        oc.globalCompositeOperation = 'destination-out';
        oc.globalAlpha = 0.45;
        for (var gj = 0; gj < GPATH.length; gj++) for (var sk = 0; sk < GPATH[gj].shades.length; sk++) oc.fill(GPATH[gj].shades[sk]);
        oc.globalAlpha = 1;
        oc.restore();
        /* Блик: полоса идёт слева направо один раз за цикл, начинается и заканчивается за пределами знака */
        var u = (ph / TAU);
        var left = px - gw * 0.9, right = px + gw * 0.9;
        var bx = left + (right - left) * u;
        var band = gw * 0.35;
        var sg = oc.createLinearGradient(bx - band, py - band * 0.6, bx + band, py + band * 0.6);   // наклон от ширины полосы, не от высоты экрана
        sg.addColorStop(0, 'rgba(255,255,255,0)'); sg.addColorStop(0.5, 'rgba(255,255,255,1)'); sg.addColorStop(1, 'rgba(255,255,255,0)');
        oc.save();
        oc.globalCompositeOperation = 'source-atop';
        oc.globalAlpha = 0.9;
        oc.fillStyle = sg; oc.fillRect(0, 0, W, H);
        oc.restore();
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        /* основной тон знака; блик внутри слоя добавляет до +60% к яркости на своей полосе */
        ctx.globalAlpha = P.stars ? 0.1 : 0.12;
        ctx.drawImage(off, 0, 0);
        ctx.restore();
    }

    var running = !reduce && freeze === null, visible = true, start = performance.now();
    function loop(now) {
        if (running && visible && !document.hidden) draw((now - start) / 1000);
        requestAnimationFrame(loop);
    }
    function init() {
        layout();
        if (freeze !== null) { draw(parseFloat(freeze) || 0); window.__ready = true; return; }
        if (reduce) { draw(PERIOD * 0.25); return; }          // статичный кадр
        requestAnimationFrame(loop);
    }
    function relayout() { layout(); if (!running) draw(freeze !== null ? parseFloat(freeze) || 0 : PERIOD * 0.25); }
    window.addEventListener('resize', relayout);
    /* Высота первого экрана меняется вместе с примером поста — холст следует за ней */
    if ('ResizeObserver' in window) {
        var lastH = 0;
        new ResizeObserver(function (en) { var h = Math.round(en[0].contentRect.height); if (h !== lastH) { lastH = h; relayout(); } }).observe(hero);
    }
    if ('IntersectionObserver' in window) new IntersectionObserver(function (e) { visible = e[0].isIntersecting; }).observe(hero);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(init); else init();
})();
