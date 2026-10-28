/* ИИ Пресс-секретарь — «жидкое стекло»: блик за курсором и смена темы кругом от кнопки.
   Подключается в base.html и landing.html. Уважает «Уменьшить движение». */
(function () {
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function isDark() {
        var t = document.documentElement.getAttribute('data-theme');
        if (t) return t === 'dark';
        return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    function syncLabels() {
        document.querySelectorAll('[data-theme-label]').forEach(function (el) {
            el.textContent = isDark() ? 'Светлая тема' : 'Тёмная тема';
        });
    }
    function applyTheme(next) {
        document.documentElement.setAttribute('data-theme', next);
        try { localStorage.setItem('theme', next); } catch (e) {}
        syncLabels();
    }

    /* Смена темы: новая тема раскрывается кругом из точки нажатия */
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('[data-theme-toggle]');
        if (!btn) return;
        var next = isDark() ? 'light' : 'dark';
        if (!document.startViewTransition || reduce) { applyTheme(next); return; }
        var r = btn.getBoundingClientRect();
        var x = r.left + r.width / 2, y = r.top + r.height / 2;
        var radius = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
        document.documentElement.classList.add('is-theme-switch');
        var t = document.startViewTransition(function () { applyTheme(next); });
        t.ready.then(function () {
            document.documentElement.animate(
                { clipPath: ['circle(0 at ' + x + 'px ' + y + 'px)', 'circle(' + radius + 'px at ' + x + 'px ' + y + 'px)'] },
                { duration: 520, easing: 'cubic-bezier(0.32, 0.72, 0, 1)', pseudoElement: '::view-transition-new(root)' }
            );
        }).catch(function () {});
        function done() { document.documentElement.classList.remove('is-theme-switch'); }
        t.finished.then(done, done);
    });
    document.addEventListener('DOMContentLoaded', syncLabels);

    /* Навигация: одна плашка на всё меню. При нажатии пункт становится активным в тот же кадр,
       плашка едет к нему пружиной, а раздел тем временем загружается — ничего не ждёт анимацию. */
    function placeIndicator(nav, item, animate) {
        var ind = nav.querySelector('.app-nav-indicator');
        if (!ind || !item) return;
        var n = nav.getBoundingClientRect(), r = item.getBoundingClientRect();
        ind.classList.toggle('no-anim', !animate);
        ind.style.setProperty('--nav-y', (r.top - n.top) + 'px');
        ind.style.height = r.height + 'px';
        ind.style.left = (r.left - n.left) + 'px';
        ind.style.width = r.width + 'px';
        ind.style.right = 'auto';
        ind.classList.add('is-ready');
        if (!animate) { void ind.offsetWidth; ind.classList.remove('no-anim'); }
    }
    function placeTab(bar, tab, animate) {
        var ind = bar.querySelector('.app-tab-indicator');
        if (!ind || !tab) return;
        var b = bar.getBoundingClientRect(), r = tab.getBoundingClientRect();
        ind.classList.toggle('no-anim', !animate);
        ind.style.setProperty('--tab-x', (r.left - b.left) + 'px');
        ind.style.setProperty('--tab-w', r.width + 'px');
        ind.classList.add('is-ready');
        if (!animate) { void ind.offsetWidth; ind.classList.remove('no-anim'); }
    }
    function setActive(list, el) {
        list.forEach(function (x) { x.classList.toggle('is-active', x === el); if (x === el) x.setAttribute('aria-current', 'page'); else x.removeAttribute('aria-current'); });
    }
    function initNav() {
        var nav = document.querySelector('[data-nav]');
        if (nav) {
            var items = Array.prototype.slice.call(nav.querySelectorAll('a.ps-sidenav-item'));
            placeIndicator(nav, nav.querySelector('.ps-sidenav-item.is-active'), false);
            nav.addEventListener('pointerdown', function (e) {
                var a = e.target.closest('a.ps-sidenav-item');
                if (!a || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey) return;
                setActive(items, a); placeIndicator(nav, a, !reduce);
            });
            nav.addEventListener('keydown', function (e) {
                var a = e.target.closest('a.ps-sidenav-item');
                if (a && e.key === 'Enter') { setActive(items, a); placeIndicator(nav, a, !reduce); }
            });
            window.addEventListener('resize', function () { placeIndicator(nav, nav.querySelector('.ps-sidenav-item.is-active'), false); });
        }
        var bar = document.querySelector('[data-tabs]');
        if (bar) {
            var tabs = Array.prototype.slice.call(bar.querySelectorAll('.ps-tab'));
            placeTab(bar, bar.querySelector('.ps-tab.is-active'), false);
            bar.addEventListener('pointerdown', function (e) {
                var t = e.target.closest('a.ps-tab');
                if (!t || e.button !== 0) return;
                setActive(tabs, t); placeTab(bar, t, !reduce);
            });
            window.addEventListener('resize', function () { placeTab(bar, bar.querySelector('.ps-tab.is-active'), false); });
        }
        /* Большой заголовок → компактная стеклянная панель, когда заголовок ушёл под край */
        var cb = document.querySelector('[data-compactbar]');
        var h1 = document.querySelector('.ps-main-head h1');
        if (cb && h1 && 'IntersectionObserver' in window) {
            new IntersectionObserver(function (en) {
                var stuck = !en[0].isIntersecting && en[0].boundingClientRect.top < 0;
                cb.classList.toggle('is-stuck', stuck);
                cb.setAttribute('aria-hidden', stuck ? 'false' : 'true');
            }, { rootMargin: '-52px 0px 0px 0px', threshold: 0 }).observe(h1);
        }
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initNav); else initNav();
    /* Возврат «Назад» из кэша страниц — плашку на место без анимации */
    window.addEventListener('pageshow', function (e) {
        if (!e.persisted) return;
        var nav = document.querySelector('[data-nav]'), bar = document.querySelector('[data-tabs]');
        var path = location.pathname;
        if (nav) {
            var cur = nav.querySelector('a.ps-sidenav-item[aria-current]');
            /* после «Назад» активен пункт текущего адреса, а не нажатый перед уходом */
            nav.querySelectorAll('a.ps-sidenav-item').forEach(function (a) {
                (a.getAttribute('data-prefixes') || a.getAttribute('href')).split(' ').forEach(function (p) {
                    if (path === p || path.indexOf(p + '/') === 0) cur = a;
                });
            });
            if (cur) { setActive(Array.prototype.slice.call(nav.querySelectorAll('a.ps-sidenav-item')), cur); placeIndicator(nav, cur, false); }
        }
        if (bar) {
            var tabs = Array.prototype.slice.call(bar.querySelectorAll('a.ps-tab')), hit = null;
            tabs.forEach(function (t) {
                (t.getAttribute('data-prefixes') || '').split(' ').forEach(function (p) { if (p && (path === p || path.indexOf(p + '/') === 0)) hit = t; });
            });
            var more = bar.querySelector('button.ps-tab');
            var target = hit || more;
            Array.prototype.slice.call(bar.querySelectorAll('.ps-tab')).forEach(function (t) {
                t.classList.toggle('is-active', t === target);
                if (t === target && t.tagName === 'A') t.setAttribute('aria-current', 'page'); else t.removeAttribute('aria-current');
            });
            placeTab(bar, target, false);
        }
    });

    /* Блик на стекле: светлое пятно следует за курсором */
    if (reduce) return;
    document.addEventListener('pointermove', function (e) {
        var g = e.target.closest && e.target.closest('.app-glass');
        if (!g) return;
        var r = g.getBoundingClientRect();
        g.style.setProperty('--glass-x', (e.clientX - r.left) + 'px');
        g.style.setProperty('--glass-y', (e.clientY - r.top) + 'px');
        g.classList.add('is-lit');
    }, { passive: true });
    document.addEventListener('pointerout', function (e) {
        var g = e.target.closest && e.target.closest('.app-glass');
        if (g && !g.contains(e.relatedTarget)) g.classList.remove('is-lit');
    });
})();
