// Preferências visuais locais. As larguras efetivas sempre respeitam a janela atual.
function iniciarRedimensionamentoPaineis() {
    const shell = document.querySelector('.app-container');
    const handles = {left: document.getElementById('resize-sidebar'), right: document.getElementById('resize-details')};
    const properties = {left: '--sidebar-width', right: '--details-width'};
    let preferred = {};
    try { preferred = JSON.parse(localStorage.getItem('bibiPanelWidths')) || {}; } catch { /* padrões CSS */ }
    if (typeof preferred !== 'object' || Array.isArray(preferred)) preferred = {};
    let current = {}, drag = null, frame = null;
    const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
    const defaults = () => {
        const css = getComputedStyle(shell);
        return {left: parseFloat(css.getPropertyValue('--sidebar-default')), right: parseFloat(css.getPropertyValue('--details-default'))};
    };
    function limits() {
        const width = shell.clientWidth;
        const min = {left: width <= 900 ? 148 : 180, right: 220};
        const center = Math.min(320, width - 16 - min.left - min.right);
        return {min, max: {left: 320, right: 420}, available: width - 16 - center};
    }
    function apply() {
        if (window.innerWidth <= 700) return;
        const base = defaults(), limit = limits();
        current = {};
        for (const side of ['left', 'right']) {
            const requested = Number.isFinite(preferred[side]) ? preferred[side] : base[side];
            current[side] = clamp(requested, limit.min[side], limit.max[side]);
        }
        // Reduz primeiro os detalhes, depois a navegação, sem reduzir o centro além do limite.
        current.right = Math.max(limit.min.right, Math.min(current.right, limit.available - current.left));
        current.left = Math.min(current.left, limit.available - current.right);
        for (const side of ['left', 'right']) {
            const other = side === 'left' ? 'right' : 'left';
            shell.style.setProperty(properties[side], `${current[side]}px`);
            handles[side].setAttribute('aria-valuenow', Math.round(current[side]));
            handles[side].setAttribute('aria-valuemin', limit.min[side]);
            handles[side].setAttribute('aria-valuemax', Math.floor(Math.min(limit.max[side], limit.available - current[other])));
        }
    }
    function setWidth(side, value) {
        const limit = limits(), other = side === 'left' ? 'right' : 'left';
        // A outra lateral não se desloca durante o arraste.
        preferred[other] = current[other];
        preferred[side] = clamp(value, limit.min[side], Math.min(limit.max[side], limit.available - current[other]));
        apply();
    }
    function save() {
        try { localStorage.setItem('bibiPanelWidths', JSON.stringify(preferred)); } catch { /* armazenamento indisponível */ }
    }
    function stop(event) {
        if (!drag || (event && event.pointerId !== drag.pointerId)) return;
        drag = null;
        shell.classList.remove('resizing-panels');
        save();
    }
    for (const [side, handle] of Object.entries(handles)) {
        handle.addEventListener('pointerdown', event => {
            if (event.button !== 0 || window.innerWidth <= 700) return;
            event.preventDefault();
            handle.focus();
            drag = {side, pointerId: event.pointerId, x: event.clientX, width: current[side]};
            handle.setPointerCapture(event.pointerId);
            shell.classList.add('resizing-panels');
        });
        handle.addEventListener('pointermove', event => {
            if (!drag || drag.pointerId !== event.pointerId) return;
            setWidth(side, drag.width + (event.clientX - drag.x) * (side === 'left' ? 1 : -1));
        });
        handle.addEventListener('pointerup', stop);
        handle.addEventListener('pointercancel', stop);
        handle.addEventListener('lostpointercapture', stop);
        handle.addEventListener('dblclick', () => { delete preferred[side]; apply(); save(); });
        handle.addEventListener('keydown', event => {
            if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
            event.preventDefault(); event.stopPropagation();
            const delta = (event.key === 'ArrowRight' ? 16 : -16) * (side === 'left' ? 1 : -1);
            setWidth(side, event.key === 'Home' ? 0 : event.key === 'End' ? Infinity : current[side] + delta);
            save();
        });
    }
    window.addEventListener('resize', () => {
        stop();
        if (frame) cancelAnimationFrame(frame);
        frame = requestAnimationFrame(() => { frame = null; apply(); });
    });
    apply();
}
