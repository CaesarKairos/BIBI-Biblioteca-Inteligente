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
    if (localStorage.getItem('darkMode') === 'true') {
        document.body.classList.add('dark-mode');
    }
});
