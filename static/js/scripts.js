document.addEventListener('DOMContentLoaded', () => {
    const root = document.documentElement;
    const themeToggle = document.getElementById('themeToggle');
    const themeMeta = document.querySelector('meta[name="theme-color"]');
    const updateThemeButton = () => {
        if (!themeToggle) return;
        const dark = root.dataset.bsTheme === 'dark';
        themeToggle.setAttribute('aria-pressed', String(dark));
        themeToggle.setAttribute('aria-label', dark ? 'ライトモードに切り替える' : 'ダークモードに切り替える');
    };
    themeToggle?.addEventListener('click', () => {
        const theme = root.dataset.bsTheme === 'dark' ? 'light' : 'dark';
        root.dataset.bsTheme = theme;
        localStorage.setItem('trombonanza-theme', theme);
        if (themeMeta) themeMeta.content = theme === 'dark' ? '#101820' : '#f5f1e8';
        updateThemeButton();
    });
    updateThemeButton();

    const navbar = document.getElementById('mainNav');
    const updateNavbar = () => navbar?.classList.toggle('scrolled', window.scrollY > 40);
    window.addEventListener('scroll', updateNavbar, { passive: true });
    updateNavbar();

    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', event => {
            const targetId = anchor.getAttribute('href');
            if (!targetId || targetId === '#') return;
            const target = document.querySelector(targetId);
            if (!target) return;
            event.preventDefault();
            const navHeight = navbar?.offsetHeight || 0;
            window.scrollTo({ top: target.getBoundingClientRect().top + window.scrollY - navHeight, behavior: 'smooth' });
            if (document.querySelector('.navbar-collapse.show')) document.querySelector('.navbar-toggler')?.click();
        });
    });

    const modal = document.getElementById('composer-modal');
    if (modal) {
        const composerLinks = window.composerLinks || {};
        const modalTitle = document.getElementById('composer-modal-title');
        const modalBody = document.getElementById('composer-modal-body');
        document.querySelectorAll('.composer-link').forEach(link => {
            link.addEventListener('click', event => {
                event.preventDefault();
                const composer = link.dataset.composer;
                const entries = composerLinks[composer] || [];
                modalTitle.textContent = composer;
                modalBody.replaceChildren();
                if (entries.length) {
                    const table = document.createElement('table');
                    table.className = 'table table-sm mb-0';
                    const tbody = table.createTBody();
                    entries.forEach(entry => {
                        const row = tbody.insertRow();
                        const concert = row.insertCell();
                        const piece = row.insertCell();
                        const anchor = document.createElement('a');
                        anchor.href = `/concert/${encodeURIComponent(entry.page)}`;
                        anchor.textContent = entry.concert_name;
                        concert.append(anchor);
                        piece.textContent = entry.piece_name;
                    });
                    modalBody.append(table);
                } else {
                    const empty = document.createElement('div');
                    empty.className = 'text-muted small';
                    empty.textContent = '他の演奏会で演奏されていません。';
                    modalBody.append(empty);
                }
                modal.style.display = 'block';
            });
        });
        document.getElementById('composer-modal-close')?.addEventListener('click', () => { modal.style.display = 'none'; });
        modal.addEventListener('click', event => { if (event.target === modal) modal.style.display = 'none'; });
        document.addEventListener('keydown', event => { if (event.key === 'Escape') modal.style.display = 'none'; });
    }

    const contactForm = document.getElementById('contactForm');
    contactForm?.addEventListener('submit', async event => {
        event.preventDefault();
        const button = contactForm.querySelector('button[type="submit"]');
        const status = document.getElementById('contactStatus');
        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = '送信中...';
        status.className = 'form-status mt-3 mb-0';
        status.textContent = '';

        try {
            const formData = new FormData(contactForm);
            const payload = Object.fromEntries(formData.entries());
            const response = await fetch(contactForm.action, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(result.message || '送信できませんでした。時間をおいて再度お試しください。');

            status.classList.add('is-success');
            status.textContent = result.message || 'お問い合わせを送信しました。ありがとうございます。';
            contactForm.reset();
        } catch (error) {
            status.classList.add('is-error');
            status.textContent = error.message;
        } finally {
            button.disabled = false;
            button.textContent = originalText;
        }
    });

    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in-visible');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: .08 });
        document.querySelectorAll('main > section').forEach(section => {
            section.classList.add('fade-in-section');
            observer.observe(section);
        });
    }
});
