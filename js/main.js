/* main.js — Dr. Arulmurugan Ramu academic website */

/* --- Year ------------------------------------------------- */
document.getElementById('year').textContent = new Date().getFullYear();

/* --- Mobile nav toggle ------------------------------------ */
const navToggle = document.getElementById('navToggle');
const navLinks  = document.getElementById('navLinks');

navToggle.addEventListener('click', () => {
  const open = navLinks.classList.toggle('open');
  navToggle.setAttribute('aria-expanded', open);
});

/* Close mobile nav on link click */
navLinks.querySelectorAll('a').forEach(link => {
  link.addEventListener('click', () => {
    navLinks.classList.remove('open');
    navToggle.setAttribute('aria-expanded', 'false');
  });
});

/* --- Active nav link on scroll ---------------------------- */
const sections = document.querySelectorAll('section[id]');
const navItems = document.querySelectorAll('.nav-links a[href^="#"]');

const onScroll = () => {
  const scrollY = window.scrollY + 80;
  sections.forEach(sec => {
    if (scrollY >= sec.offsetTop && scrollY < sec.offsetTop + sec.offsetHeight) {
      navItems.forEach(a => {
        a.classList.remove('active');
        if (a.getAttribute('href') === '#' + sec.id) a.classList.add('active');
      });
    }
  });
};
window.addEventListener('scroll', onScroll, { passive: true });

/* --- Publication filter + sort (descending year) ---------- */
const filterBtns = document.querySelectorAll('.pub-filter');
const pubList    = document.getElementById('pubList');

function removeYearHeadings() {
  pubList.querySelectorAll('.pub-year-heading').forEach(h => h.remove());
}

function applyFilter(filter) {
  const items = Array.from(pubList.querySelectorAll('.pub-item'));
  removeYearHeadings();

  if (filter === 'all') {
    /* Show all, sort by year desc, then insert year group headings */
    items.forEach(item => item.classList.remove('hidden'));
    const sorted = items.sort((a, b) => Number(b.dataset.year) - Number(a.dataset.year));
    sorted.forEach(item => pubList.appendChild(item));

    /* Insert a heading before the first item of each year */
    let currentYear = null;
    sorted.forEach(item => {
      const yr = item.dataset.year;
      if (yr !== currentYear) {
        currentYear = yr;
        const heading = document.createElement('div');
        heading.className = 'pub-year-heading';
        heading.textContent = yr;
        pubList.insertBefore(heading, item);
      }
    });
  } else {
    /* Type filter: flat list, no year headings */
    items.forEach(item => {
      item.classList.toggle('hidden', item.dataset.type !== filter);
    });
    const sorted = items.sort((a, b) => {
      const aH = a.classList.contains('hidden');
      const bH = b.classList.contains('hidden');
      if (aH !== bH) return aH ? 1 : -1;
      return Number(b.dataset.year) - Number(a.dataset.year);
    });
    sorted.forEach(item => pubList.appendChild(item));
  }
}

filterBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    filterBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    applyFilter(btn.dataset.filter);
  });
});

/* Apply on initial load */
applyFilter('all');

/* --- Contact form (front-end only) ----------------------- */
const contactForm = document.getElementById('contactForm');

contactForm.addEventListener('submit', e => {
  e.preventDefault();

  const name    = contactForm.name.value.trim();
  const email   = contactForm.email.value.trim();
  const message = contactForm.message.value.trim();

  if (!name || !email || !message) {
    showFormMsg('Please fill in all required fields.', 'error');
    return;
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    showFormMsg('Please enter a valid email address.', 'error');
    return;
  }

  /* Replace with a real backend / Formspree / EmailJS call */
  showFormMsg('Thank you! Your message has been received. I will respond within 2 business days.', 'success');
  contactForm.reset();
});

function showFormMsg(text, type) {
  let el = document.getElementById('formMsg');
  if (!el) {
    el = document.createElement('p');
    el.id = 'formMsg';
    el.style.cssText = 'margin-top:12px; padding:12px 16px; border-radius:6px; font-size:.9rem; font-weight:500;';
    contactForm.appendChild(el);
  }
  el.textContent = text;
  el.style.background = type === 'success' ? 'rgba(16,120,90,.1)' : 'rgba(200,50,50,.1)';
  el.style.color       = type === 'success' ? '#0a6b50'             : '#a02020';
  el.style.border      = type === 'success' ? '1px solid rgba(16,120,90,.25)' : '1px solid rgba(200,50,50,.25)';

  setTimeout(() => el && el.remove(), 6000);
}

/* --- Smooth reveal on scroll (Intersection Observer) ------ */
if ('IntersectionObserver' in window) {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.research-card, .course-card, .team-card, .news-item').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 400ms ease, transform 400ms ease';
    observer.observe(el);
  });
}
