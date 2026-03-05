// FOUC prevention — runs immediately
(function() {
    const saved = localStorage.getItem('lumina-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = saved || (prefersDark ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
})();

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('lumina-theme', next);

    // Update toggle button icon if present
    const icon = document.querySelector('.theme-toggle-icon');
    if (icon) {
        icon.textContent = next === 'dark' ? '\u2600\uFE0F' : '\uD83C\uDF19';
    }
}
