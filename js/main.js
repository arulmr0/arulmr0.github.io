/* main.js — Dr. Arulmurugan Ramu academic website */

/* --- Year ------------------------------------------------- */
document.getElementById('year').textContent = new Date().getFullYear();

/* --- Mobile nav toggle ------------------------------------ */
const navToggle = document.getElementById('navToggle');
const navLinks  = document.getElementById('navLinks');

navToggle.addEventListener('click', () => {
  const open = navLinks.classList.toggle('open');
  navToggle.classList.toggle('open', open);
  navToggle.setAttribute('aria-expanded', open);
});

/* Close mobile nav on link click */
navLinks.querySelectorAll('a').forEach(link => {
  link.addEventListener('click', () => {
    navLinks.classList.remove('open');
    navToggle.classList.remove('open');
    navToggle.setAttribute('aria-expanded', 'false');
  });
});

/* --- Active nav link on scroll ---------------------------- */
const sections = document.querySelectorAll('section[id]');
const navItems = document.querySelectorAll('.nav-links a[href^="#"]');

const header = document.querySelector('.site-header');

const onScroll = () => {
  header.classList.toggle('scrolled', window.scrollY > 10);
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

contactForm.addEventListener('submit', async e => {
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

  const endpoint = contactForm.dataset.endpoint;
  if (endpoint) {
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { Accept: 'application/json' },
        body: new FormData(contactForm)
      });
      if (res.ok) {
        showFormMsg('Thank you! Your message has been sent. I will respond within 2 business days.', 'success');
        contactForm.reset();
      } else {
        showFormMsg('Something went wrong. Please email me directly at arulmr@gmail.com', 'error');
      }
    } catch {
      showFormMsg('Something went wrong. Please email me directly at arulmr@gmail.com', 'error');
    }
  } else {
    showFormMsg('Thank you! Your message has been received. I will respond within 2 business days.', 'success');
    contactForm.reset();
  }
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

/* --- #6 Dark mode ----------------------------------------- */
const darkToggle = document.getElementById('darkToggle');
const applyTheme = theme => {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);
};
applyTheme(localStorage.getItem('theme') || 'light');
darkToggle.addEventListener('click', () => {
  applyTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
});

/* --- #3 Back-to-top --------------------------------------- */
const backToTop = document.getElementById('backToTop');
window.addEventListener('scroll', () => {
  backToTop.classList.toggle('visible', window.scrollY > 400);
}, { passive: true });
backToTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));

/* --- #7 Publication search -------------------------------- */
const pubSearch = document.getElementById('pubSearch');
pubSearch.addEventListener('input', () => {
  const q = pubSearch.value.toLowerCase().trim();
  pubList.querySelectorAll('.pub-year-heading').forEach(h => h.style.display = '');
  pubList.querySelectorAll('.pub-item').forEach(item => {
    const text = item.textContent.toLowerCase();
    item.classList.toggle('hidden', q.length > 0 && !text.includes(q));
  });
  if (q.length > 0) {
    pubList.querySelectorAll('.pub-year-heading').forEach(heading => {
      let next = heading.nextElementSibling;
      let allHidden = true;
      while (next && !next.classList.contains('pub-year-heading')) {
        if (!next.classList.contains('hidden')) { allHidden = false; break; }
        next = next.nextElementSibling;
      }
      heading.style.display = allHidden ? 'none' : '';
    });
  }
});

/* --- #1 BibTeX copy buttons ------------------------------- */
function generateBibTeX(article) {
  const type  = article.dataset.type || 'journal';
  const year  = article.dataset.year || '';
  const titleEl  = article.querySelector('.pub-title a') || article.querySelector('.pub-title');
  const title    = titleEl ? titleEl.textContent.trim() : '';
  const authors  = article.querySelector('.pub-authors')?.textContent.trim() || '';
  const venueEl  = article.querySelector('.pub-venue em');
  const venue    = venueEl ? venueEl.textContent.trim() : '';
  const doiEl    = article.querySelector('a[href*="doi.org"]');
  const doi      = doiEl ? doiEl.href.replace('https://doi.org/', '') : '';
  const key      = (authors.split(',')[0].trim().split(' ').pop() || 'Ramu') + year;
  const bibType  = { journal: 'article', book: 'book', chapter: 'incollection', conference: 'inproceedings' }[type] || 'misc';
  const venueField = type === 'journal' ? `  journal   = {${venue}},\n` :
                     type === 'book'    ? '' :
                                          `  booktitle = {${venue}},\n`;
  return `@${bibType}{${key},\n  author    = {${authors}},\n  title     = {${title}},\n${venueField}  year      = {${year}}${doi ? `,\n  doi       = {${doi}}` : ''}\n}`;
}

document.querySelectorAll('.pub-item').forEach(article => {
  const links = article.querySelector('.pub-links');
  if (!links) return;
  const btn = document.createElement('button');
  btn.className = 'pub-link bib-btn';
  btn.textContent = 'BibTeX';
  btn.addEventListener('click', () => {
    navigator.clipboard.writeText(generateBibTeX(article)).then(() => {
      btn.textContent = 'Copied!';
      btn.classList.add('copied');
      setTimeout(() => { btn.textContent = 'BibTeX'; btn.classList.remove('copied'); }, 2000);
    });
  });
  links.appendChild(btn);
});

/* --- #9 Typewriter animation ------------------------------ */
const typewriterEl = document.getElementById('typewriter');
if (typewriterEl) {
  const roles = ['Associate Professor', 'AI & ML Researcher', 'Keynote Speaker', 'Book Author & Editor'];
  let ri = 0, ci = 0, deleting = false;
  const TYPE_SPEED = 80, DELETE_SPEED = 40, PAUSE = 1800;
  function tickTypewriter() {
    const role = roles[ri];
    if (!deleting) {
      typewriterEl.textContent = role.slice(0, ++ci);
      if (ci === role.length) { deleting = true; setTimeout(tickTypewriter, PAUSE); return; }
    } else {
      typewriterEl.textContent = role.slice(0, --ci);
      if (ci === 0) { deleting = false; ri = (ri + 1) % roles.length; }
    }
    setTimeout(tickTypewriter, deleting ? DELETE_SPEED : TYPE_SPEED);
  }
  tickTypewriter();
}

/* --- #8 Live citations from Semantic Scholar -------------- */
fetch('https://api.semanticscholar.org/graph/v1/author/search?query=Arulmurugan+Ramu+Heriot-Watt&fields=citationCount,paperCount&limit=1')
  .then(r => r.json())
  .then(data => {
    const author = data.data?.[0];
    if (!author) return;
    document.querySelectorAll('.stat-number').forEach(el => {
      const label = el.nextElementSibling?.textContent?.toLowerCase() || '';
      if (label.includes('citation') && author.citationCount > 0)
        el.textContent = author.citationCount.toLocaleString() + '+';
      if (label.includes('publication') && author.paperCount > 0)
        el.textContent = author.paperCount + '+';
    });
  }).catch(() => {});

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
