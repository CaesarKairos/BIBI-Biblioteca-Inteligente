function showSection(section) {
    document.getElementById('home-section').classList.remove('active');
    document.getElementById('about-section').classList.remove('active');

    if(section === 'home') {
        document.getElementById('home-section').classList.add('active');
    } else {
        document.getElementById('about-section').classList.add('active');
    }
}

async function carregarHeroImage() {
    const heroImg = document.getElementById('hero-image');
    try {
        const resp = await fetch('/api/hero-image');
        const data = await resp.json();
        heroImg.src = data.url;
    } catch (error) {
        console.error('Erro ao carregar hero image:', error);
        heroImg.src = 'static/images/hero/hero.jpg';
    }
    heroImg.onerror = function() {
        this.src = 'static/images/hero/hero.jpg';
    };
}

document.addEventListener('DOMContentLoaded', () => {
    carregarHeroImage();
    let darkMode = localStorage.getItem('darkMode') === 'true';
    try {
        const config = JSON.parse(localStorage.getItem('bibiConfig'));
        if (typeof config?.darkMode === 'boolean') darkMode = config.darkMode;
    } catch { /* Preserva o fallback de instalações anteriores. */ }
    if (darkMode) {
        document.body.classList.add('dark-mode');
    }
});
