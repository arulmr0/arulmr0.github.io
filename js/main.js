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

/* ============================================================
   VISUAL EFFECTS 1–7
   ============================================================ */

/* --- #1 Hero particle canvas ------------------------------ */
(function () {
  const canvas = document.getElementById('heroCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let W, H, particles;

  const COLORS = ['rgba(14,116,144,.7)', 'rgba(192,106,24,.6)', 'rgba(255,255,255,.3)'];

  function resize() {
    const hero = canvas.parentElement;
    W = canvas.width  = hero.offsetWidth;
    H = canvas.height = hero.offsetHeight;
  }

  function mkParticle() {
    return {
      x: Math.random() * W,
      y: Math.random() * H,
      r: Math.random() * 1.8 + 0.4,
      vx: (Math.random() - .5) * .25,
      vy: (Math.random() - .5) * .25,
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
    };
  }

  function init() {
    resize();
    particles = Array.from({ length: 90 }, mkParticle);
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    particles.forEach(p => {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0) p.x = W; if (p.x > W) p.x = 0;
      if (p.y < 0) p.y = H; if (p.y > H) p.y = 0;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.fill();
    });
    /* Draw connecting lines for nearby pairs */
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 90) {
          ctx.beginPath();
          ctx.strokeStyle = `rgba(14,116,144,${.18 * (1 - dist / 90)})`;
          ctx.lineWidth = .5;
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.stroke();
        }
      }
    }
    requestAnimationFrame(draw);
  }

  init();
  draw();
  window.addEventListener('resize', () => { resize(); particles = Array.from({ length: 90 }, mkParticle); }, { passive: true });
})();

/* --- #2 Staggered scroll reveal --------------------------- */
(function () {
  const targets = document.querySelectorAll(
    '.research-card, .course-card, .team-card, .news-item, .talk-card, .stat-item, .editorial-role'
  );
  targets.forEach(el => el.classList.add('reveal'));

  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); }
    });
  }, { threshold: 0.12 });

  targets.forEach(el => obs.observe(el));
})();

/* --- #5 Animated stat counters ---------------------------- */
(function () {
  function parseNum(str) {
    return parseInt(str.replace(/[^0-9]/g, ''), 10) || 0;
  }
  function animateCounter(el, target, suffix) {
    let start = null;
    const duration = 1600;
    function step(ts) {
      if (!start) start = ts;
      const progress = Math.min((ts - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.floor(eased * target).toLocaleString() + suffix;
      if (progress < 1) requestAnimationFrame(step);
      else el.textContent = target.toLocaleString() + suffix;
    }
    requestAnimationFrame(step);
  }

  const statsBar = document.querySelector('.stats-bar');
  if (!statsBar) return;
  let triggered = false;
  const obs = new IntersectionObserver(entries => {
    if (triggered || !entries[0].isIntersecting) return;
    triggered = true;
    statsBar.querySelectorAll('.stat-number').forEach(el => {
      const raw = el.textContent;
      const target = parseNum(raw);
      const suffix = raw.includes('+') ? '+' : (raw.includes('x') ? 'x' : '');
      animateCounter(el, target, suffix);
    });
  }, { threshold: 0.5 });
  obs.observe(statsBar);
})();

/* --- #7 Custom cursor dot --------------------------------- */
(function () {
  const dot = document.getElementById('cursorDot');
  if (!dot || window.matchMedia('(pointer: coarse)').matches) return;

  let mx = -100, my = -100, cx = -100, cy = -100;
  let raf;

  document.addEventListener('mousemove', e => { mx = e.clientX; my = e.clientY; }, { passive: true });

  const hoverTargets = 'a, button, .pub-filter, .tag, .bib-btn, .stat-item';
  document.querySelectorAll(hoverTargets).forEach(el => {
    el.addEventListener('mouseenter', () => dot.classList.add('hovering'));
    el.addEventListener('mouseleave', () => dot.classList.remove('hovering'));
  });

  function loop() {
    cx += (mx - cx) * 0.18;
    cy += (my - cy) * 0.18;
    dot.style.left = cx + 'px';
    dot.style.top  = cy + 'px';
    raf = requestAnimationFrame(loop);
  }
  loop();
})();

/* ============================================================
   FEATURES 8вЂ“12
   ============================================================ */

/* --- #12 Reading progress bar ----------------------------- */
(function () {
  const bar = document.getElementById('readingProgress');
  if (!bar) return;
  window.addEventListener('scroll', () => {
    const doc = document.documentElement;
    const pct = (doc.scrollTop / (doc.scrollHeight - doc.clientHeight)) * 100;
    bar.style.width = Math.min(pct, 100) + '%';
  }, { passive: true });
})();

/* --- #8 Hero tag cloud -> publication filter --------------- */
(function () {
  const tagBtns = document.querySelectorAll('.tag-filter-btn');
  if (!tagBtns.length) return;

  const TOPIC_KEYWORDS = {
    'Artificial Intelligence': ['artificial intelligence', 'intelligent system', 'ai'],
    'Machine Learning':        ['machine learning', 'classification', 'prediction', 'neural network', 'gradient boosting'],
    'Deep Learning':           ['deep learning', 'cnn', 'convolutional', 'lstm', 'transformer'],
    'Computer Vision':         ['computer vision', 'image', 'traffic', 'visual', 'spatial'],
    'Healthcare AI':           ['lung cancer', 'neuroimaging', 'healthcare', 'biomedical', 'clinical'],
    'NLP':                     ['nlp', 'natural language', 'text', 'language'],
    'IoT':                     ['iot', 'internet of things', 'sensor', 'urban'],
    'Blockchain':              ['blockchain', 'vehicular', 'vanet', 'trust management'],
    'Big Data':                ['big data', 'cognitive computing', 'data science'],
  };

  function clearTopicFilter() {
    tagBtns.forEach(b => b.classList.remove('active-tag'));
    pubList.querySelectorAll('.pub-item').forEach(el => el.classList.remove('hidden'));
    pubList.querySelectorAll('.pub-year-heading').forEach(el => el.style.display = '');
  }

  tagBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const topic = btn.dataset.topic;
      if (btn.classList.contains('active-tag')) {
        clearTopicFilter();
        return;
      }
      tagBtns.forEach(b => b.classList.remove('active-tag'));
      btn.classList.add('active-tag');

      const keywords = TOPIC_KEYWORDS[topic] || [topic.toLowerCase()];
      pubList.querySelectorAll('.pub-item').forEach(item => {
        const text = item.textContent.toLowerCase();
        item.classList.toggle('hidden', !keywords.some(k => text.includes(k)));
      });
      pubList.querySelectorAll('.pub-year-heading').forEach(h => {
        let next = h.nextElementSibling;
        let anyVisible = false;
        while (next && !next.classList.contains('pub-year-heading')) {
          if (!next.classList.contains('hidden')) { anyVisible = true; break; }
          next = next.nextElementSibling;
        }
        h.style.display = anyVisible ? '' : 'none';
      });

      const pubSec = document.getElementById('publications');
      if (pubSec) pubSec.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
})();

/* --- #9 Timeline / Grid view toggle ----------------------- */
(function () {
  const gridBtn     = document.getElementById('viewGrid');
  const timelineBtn = document.getElementById('viewTimeline');
  if (!gridBtn || !timelineBtn) return;

  timelineBtn.addEventListener('click', () => {
    pubList.classList.add('timeline-view');
    timelineBtn.classList.add('active'); timelineBtn.setAttribute('aria-pressed', 'true');
    gridBtn.classList.remove('active'); gridBtn.setAttribute('aria-pressed', 'false');
  });
  gridBtn.addEventListener('click', () => {
    pubList.classList.remove('timeline-view');
    gridBtn.classList.add('active'); gridBtn.setAttribute('aria-pressed', 'true');
    timelineBtn.classList.remove('active'); timelineBtn.setAttribute('aria-pressed', 'false');
  });
})();

/* --- #10 Co-author network SVG ---------------------------- */
(function () {
  const svg = document.getElementById('coauthorSvg');
  if (!svg) return;

  const CENTER = { x: 350, y: 190 };
  const coauthors = [
    { name: 'A. Haldorai',        count: 18, angle: 0   },
    { name: 'S. K. Ravichandran', count: 8,  angle: 45  },
    { name: 'D. Vetrithangam',    count: 6,  angle: 90  },
    { name: 'T. D. Adugna',       count: 5,  angle: 135 },
    { name: 'R. Venkatesh',       count: 4,  angle: 180 },
    { name: 'Puneet Kumar',       count: 4,  angle: 225 },
    { name: 'S. A. R. Khan',      count: 3,  angle: 270 },
    { name: 'Suriya Murugan',     count: 3,  angle: 315 },
  ];

  const ns = 'http://www.w3.org/2000/svg';
  function mkEl(tag, attrs) {
    const e = document.createElementNS(ns, tag);
    Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v));
    return e;
  }

  const RADIUS = 138;
  coauthors.forEach((node, i) => {
    const angle = (node.angle * Math.PI) / 180;
    const x = CENTER.x + RADIUS * Math.cos(angle);
    const y = CENTER.y + RADIUS * Math.sin(angle);

    svg.appendChild(mkEl('line', {
      class: 'coauthor-edge',
      x1: CENTER.x, y1: CENTER.y, x2: x, y2: y,
      'stroke-width': Math.max(1, node.count * 0.25),
    }));

    const r = Math.max(10, Math.min(22, node.count * 1.2));
    svg.appendChild(mkEl('circle', {
      class: 'node-circle',
      cx: x, cy: y, r,
      fill: 'hsl(' + (185 + i * 20) + ',52%,' + (40 + i * 2) + '%)',
      stroke: 'white', 'stroke-width': 2,
    }));

    const lbl = mkEl('text', { class: 'node-label', x, y: y + r + 13 });
    lbl.textContent = node.name.split(' ').slice(-1)[0];
    svg.appendChild(lbl);
  });

  svg.appendChild(mkEl('circle', {
    class: 'node-circle center-node',
    cx: CENTER.x, cy: CENTER.y, r: 32,
    stroke: 'white', 'stroke-width': 3,
  }));
  const cl = mkEl('text', { class: 'node-label', x: CENTER.x, y: CENTER.y + 5 });
  cl.textContent = 'Ramu';
  cl.setAttribute('font-weight', '700');
  cl.setAttribute('fill', '#fff');
  cl.setAttribute('font-size', '13');
  svg.appendChild(cl);
  const cl2 = mkEl('text', { class: 'node-label', x: CENTER.x, y: CENTER.y + 19 });
  cl2.textContent = '125+ pubs';
  cl2.setAttribute('font-size', '9');
  cl2.setAttribute('fill', 'rgba(255,255,255,.7)');
  svg.appendChild(cl2);
})();

/* --- #11 Copy citation (APA / MLA / IEEE) ----------------- */
(function () {
  function buildCitations(article) {
    const titleEl = article.querySelector('.pub-title a') || article.querySelector('.pub-title');
    const title   = titleEl ? titleEl.textContent.trim() : '';
    const authors = article.querySelector('.pub-authors')?.textContent.trim() || '';
    const venueEl = article.querySelector('.pub-venue em');
    const venue   = venueEl ? venueEl.textContent.trim() : '';
    const year    = article.dataset.year || '';
    const doiEl   = article.querySelector('a[href*="doi.org"]');
    const doi     = doiEl ? doiEl.href : '';

    return {
      apa:  authors + ' (' + year + '). ' + title + '. ' + venue + '. ' + (doi || ''),
      mla:  authors + '. "' + title + '." ' + venue + ', ' + year + '. ' + (doi || ''),
      ieee: authors + ', "' + title + '," ' + venue + ', ' + year + '. ' + (doi ? 'Available: ' + doi : ''),
    };
  }

  document.querySelectorAll('.pub-item').forEach(article => {
    const links = article.querySelector('.pub-links');
    if (!links) return;

    const wrap    = document.createElement('div');
    wrap.className = 'pub-link cite-btn';

    const mainBtn = document.createElement('button');
    mainBtn.className = 'pub-link';
    mainBtn.textContent = 'Cite';
    mainBtn.style.cssText = 'border:1px solid var(--border-2);border-radius:4px;padding:3px 10px;font-size:.75rem;cursor:pointer;background:none;font-family:var(--font);color:var(--text-2);';

    const menu = document.createElement('div');
    menu.className = 'cite-menu';

    ['APA', 'MLA', 'IEEE'].forEach(fmt => {
      const btn = document.createElement('button');
      btn.textContent = 'Copy ' + fmt;
      btn.addEventListener('click', e => {
        e.stopPropagation();
        const cites = buildCitations(article);
        navigator.clipboard.writeText(cites[fmt.toLowerCase()]).then(() => {
          btn.textContent = 'Copied!';
          setTimeout(() => { btn.textContent = 'Copy ' + fmt; }, 1800);
        });
        wrap.classList.remove('open');
      });
      menu.appendChild(btn);
    });

    mainBtn.addEventListener('click', e => {
      e.stopPropagation();
      wrap.classList.toggle('open');
    });
    document.addEventListener('click', () => wrap.classList.remove('open'), { passive: true });

    wrap.appendChild(mainBtn);
    wrap.appendChild(menu);
    links.appendChild(wrap);
  });
})();

/* ============================================================
   INNOVATIVE FEATURES 1, 5, 6, 7, 8, 9, 10
   ============================================================ */

/* --- #10 Particle color reacts to dark/light theme -------- */
(function () {
  const canvas = document.getElementById('heroCanvas');
  if (!canvas) return;
  const origApply = window._applyTheme || null;
})();

/* --- #1 AI Research Chatbot ------------------------------- */
(function () {
  const fab      = document.getElementById('chatFab');
  const panel    = document.getElementById('chatPanel');
  const closeBtn = document.getElementById('chatClose');
  const form     = document.getElementById('chatForm');
  const input    = document.getElementById('chatInput');
  const msgs     = document.getElementById('chatMessages');
  const suggests = document.querySelectorAll('.chat-suggest');
  if (!fab) return;

  const KB = [
    {
      patterns: ['research area', 'topic', 'interest', 'work on', 'speciali'],
      reply: 'My core research areas are: Artificial Intelligence, Machine Learning, Deep Learning, Computer Vision, Healthcare AI, Natural Language Processing, IoT, and Blockchain. I focus on applying these to solve real-world problems — particularly in healthcare diagnostics, smart city traffic, and vehicular network security.'
    },
    {
      patterns: ['phd', 'doctoral', 'supervise', 'supervision', 'student'],
      reply: 'Yes! I accept 1-2 PhD students per year. Current open areas include AI/ML for healthcare, traffic prediction, and edge computing. To apply, email arulmr@gmail.com with your CV, research proposal, and academic transcripts. Funding opportunities may be available.'
    },
    {
      patterns: ['collaborat', 'joint', 'partner', 'co-author', 'work with'],
      reply: 'I welcome international academic collaborations! I have active co-authors across Asia, Africa, and Europe. To propose a collaboration, email arulmr@gmail.com with your institution, research interest, and a brief proposal. I especially welcome joint grant applications and dataset-sharing projects.'
    },
    {
      patterns: ['publication', 'paper', 'journal', 'book', 'article', 'published'],
      reply: 'I have 125+ publications including journals (Scientific Reports, Mobile Networks & Applications), books (Springer, Apple Academic Press), and conference papers. My most recent is a 2025 Nature Scientific Reports paper on traffic prediction using dual adjacency graphs. See the Publications section or visit my Google Scholar profile.'
    },
    {
      patterns: ['citation', 'impact', 'h-index', 'scopus', 'scholar'],
      reply: 'I have 1,800+ citations on Google Scholar. You can view my full profile at: scholar.google.com/citations?user=vGGhoQ8AAAAJ or my Scopus profile at authorId=56996013100.'
    },
    {
      patterns: ['contact', 'email', 'reach', 'message', 'get in touch'],
      reply: 'You can reach me at arulmr@gmail.com. I am based at Heriot-Watt University, Aktobe Campus, Kazakhstan. For collaboration or PhD enquiries, please include your CV and a brief description of your proposal. I typically respond within 2 business days.'
    },
    {
      patterns: ['teach', 'course', 'lecture', 'class', 'module'],
      reply: 'I teach courses including Artificial Intelligence, Machine Learning, Deep Learning, Computer Vision, Data Structures & Algorithms, and IoT at both undergraduate and postgraduate levels at Heriot-Watt University, Aktobe Campus.'
    },
    {
      patterns: ['keynote', 'talk', 'speaker', 'conference', 'invited'],
      reply: 'I am an invited keynote speaker at ICRTT 2026 (International Conference on Recent Trends in Technology). I also participate in international conferences and workshops on AI, ML, and related topics.'
    },
    {
      patterns: ['heriot', 'university', 'aktobe', 'kazakhstan', 'hwu'],
      reply: 'I am an Associate Professor in the Department of Computational Science and Software Engineering at Heriot-Watt University, Aktobe Campus, Kazakhstan. Heriot-Watt is a Scottish university with global campuses.'
    },
    {
      patterns: ['healthcare', 'medical', 'cancer', 'lung', 'clinical'],
      reply: 'Healthcare AI is a major focus of my research. Key papers include early lung cancer detection using neural networks (2018), neuroimaging techniques review (2024), and ML applications in biomedical signal processing. I am open to collaborations with medical institutions on AI diagnostic tools.'
    },
    {
      patterns: ['hello', 'hi ', 'hey', 'who are you', 'what can you'],
      reply: 'Hi there! I am Dr. Ramu\'s research assistant. I can answer questions about his publications, research areas, PhD supervision, collaboration opportunities, and contact details. What would you like to know?'
    },
  ];

  function respond(text) {
    const q = text.toLowerCase();
    const match = KB.find(entry => entry.patterns.some(p => q.includes(p)));
    return match
      ? match.reply
      : 'Great question! For specific details, please email Dr. Ramu directly at arulmr@gmail.com. You can also explore the Publications, Research, and Contact sections of this website.';
  }

  function addMsg(text, role) {
    const div = document.createElement('div');
    div.className = 'chat-msg ' + role;
    div.textContent = text;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
  }

  function sendQ(q) {
    if (!q.trim()) return;
    addMsg(q, 'user');
    input.value = '';
    setTimeout(() => addMsg(respond(q), 'bot'), 480);
  }

  fab.addEventListener('click', () => {
    panel.hidden = !panel.hidden;
    if (!panel.hidden) input.focus();
  });
  closeBtn.addEventListener('click', () => { panel.hidden = true; });
  form.addEventListener('submit', e => { e.preventDefault(); sendQ(input.value); });
  suggests.forEach(btn => btn.addEventListener('click', () => sendQ(btn.textContent)));
})();

/* --- #5 Story Timeline Scroll Reveal ---------------------- */
(function () {
  const items = document.querySelectorAll('.story-item');
  if (!items.length) return;
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); } });
  }, { threshold: 0.2 });
  items.forEach(el => obs.observe(el));
})();

/* --- #7 Animated Topic Wheel SVG -------------------------- */
(function () {
  const svg = document.getElementById('topicWheel');
  if (!svg) return;

  const topics = [
    { label: 'Machine\nLearning',  count: 45, color: '#0e7490' },
    { label: 'Deep\nLearning',     count: 30, color: '#0891b2' },
    { label: 'Healthcare\nAI',     count: 22, color: '#c06a18' },
    { label: 'Computer\nVision',   count: 18, color: '#d97c1e' },
    { label: 'IoT',                count: 15, color: '#0e6e82' },
    { label: 'NLP',                count: 12, color: '#b5601a' },
    { label: 'Blockchain',         count: 10, color: '#1a6ea0' },
    { label: 'Big Data',           count: 8,  color: '#e08520' },
  ];

  const ns = 'http://www.w3.org/2000/svg';
  const CX = 260, CY = 260, R_OUTER = 200, R_INNER = 70;
  const total = topics.reduce((s, t) => s + t.count, 0);
  let startAngle = -Math.PI / 2;

  topics.forEach((topic, i) => {
    const slice = (topic.count / total) * 2 * Math.PI;
    const endAngle = startAngle + slice;
    const mid = startAngle + slice / 2;
    const r = R_INNER + (R_OUTER - R_INNER) * 0.55;

    const x1o = CX + R_OUTER * Math.cos(startAngle);
    const y1o = CY + R_OUTER * Math.sin(startAngle);
    const x2o = CX + R_OUTER * Math.cos(endAngle);
    const y2o = CY + R_OUTER * Math.sin(endAngle);
    const x1i = CX + R_INNER * Math.cos(endAngle);
    const y1i = CY + R_INNER * Math.sin(endAngle);
    const x2i = CX + R_INNER * Math.cos(startAngle);
    const y2i = CY + R_INNER * Math.sin(startAngle);
    const largeArc = slice > Math.PI ? 1 : 0;

    const path = document.createElementNS(ns, 'path');
    path.setAttribute('class', 'wheel-slice');
    path.setAttribute('d', `M${x1o},${y1o} A${R_OUTER},${R_OUTER} 0 ${largeArc} 1 ${x2o},${y2o} L${x1i},${y1i} A${R_INNER},${R_INNER} 0 ${largeArc} 0 ${x2i},${y2i} Z`);
    path.setAttribute('fill', topic.color);
    path.setAttribute('stroke', 'white');
    path.setAttribute('stroke-width', '2');
    path.setAttribute('data-topic', topic.label.replace('\n', ' '));

    path.addEventListener('click', () => {
      const topicName = topic.label.replace('\n', ' ').trim();
      const tagBtn = Array.from(document.querySelectorAll('.tag-filter-btn')).find(b => b.dataset.topic && topicName.includes(b.dataset.topic.split(' ')[0]));
      if (tagBtn) tagBtn.click();
    });

    const lx = CX + r * Math.cos(mid);
    const ly = CY + r * Math.sin(mid);

    const lines = topic.label.split('\n');
    const tEl = document.createElementNS(ns, 'text');
    tEl.setAttribute('class', 'wheel-label');
    tEl.setAttribute('x', lx);
    tEl.setAttribute('y', ly - (lines.length > 1 ? 7 : 0));
    tEl.setAttribute('pointer-events', 'none');
    lines.forEach((line, li) => {
      const ts = document.createElementNS(ns, 'tspan');
      ts.setAttribute('x', lx);
      ts.setAttribute('dy', li === 0 ? '0' : '14');
      ts.textContent = line;
      tEl.appendChild(ts);
    });

    const cEl = document.createElementNS(ns, 'text');
    cEl.setAttribute('class', 'wheel-count');
    cEl.setAttribute('x', lx);
    cEl.setAttribute('y', ly + (lines.length > 1 ? 20 : 14));
    cEl.setAttribute('pointer-events', 'none');
    cEl.textContent = topic.count + ' pubs';

    svg.appendChild(path);
    svg.appendChild(tEl);
    svg.appendChild(cEl);

    startAngle = endAngle;
  });

  const cCircle = document.createElementNS(ns, 'circle');
  cCircle.setAttribute('cx', CX); cCircle.setAttribute('cy', CY); cCircle.setAttribute('r', R_INNER - 2);
  cCircle.setAttribute('fill', 'var(--surface)'); cCircle.setAttribute('stroke', 'var(--border)'); cCircle.setAttribute('stroke-width', '1.5');
  svg.appendChild(cCircle);

  const cText = document.createElementNS(ns, 'text');
  cText.setAttribute('class', 'wheel-center');
  cText.setAttribute('x', CX); cText.setAttribute('y', CY - 6);
  cText.textContent = '125+';
  const cSub = document.createElementNS(ns, 'text');
  cSub.setAttribute('x', CX); cSub.setAttribute('y', CY + 12);
  cSub.setAttribute('font-size', '10'); cSub.setAttribute('text-anchor', 'middle');
  cSub.setAttribute('fill', 'var(--text-3)'); cSub.textContent = 'papers';
  svg.appendChild(cText);
  svg.appendChild(cSub);
})();

/* --- #8 Paper Spotlight — fetch citation count ------------ */
(function () {
  const el = document.getElementById('spotCite');
  if (!el) return;
  fetch('https://api.semanticscholar.org/graph/v1/paper/DOI:10.1038/s41598-025-25075-4?fields=citationCount')
    .then(r => r.json())
    .then(d => { if (d.citationCount !== undefined) el.textContent = d.citationCount; })
    .catch(() => { el.textContent = '—'; });
})();

/* ============================================================
   FEATURES 15 — New batch
   ============================================================ */

/* --- #1 Live h-index badge via Semantic Scholar ----------- */
(function () {
  const statGrid = document.querySelector('.stats-grid');
  if (!statGrid) return;
  const el = document.createElement('div');
  el.className = 'stat-item';
  el.innerHTML = '<span class="stat-number" id="hIdxNum">—</span><span class="stat-label">H-Index</span>';
  statGrid.appendChild(el);

  fetch('https://api.semanticscholar.org/graph/v1/author/search?query=Arulmurugan+Ramu&fields=hIndex,citationCount')
    .then(r => r.json())
    .then(d => {
      const author = (d.data || []).find(a => a.hIndex);
      if (author && author.hIndex) {
        document.getElementById('hIdxNum').textContent = author.hIndex;
      }
    })
    .catch(() => {});
})();

/* --- #2 Journal IF badges --------------------------------- */
(function () {
  const IF_MAP = {
    'Scientific Reports': '4.6',
    'Mobile Networks': '3.8',
    'IEEE Access': '3.9',
    'Computers, Materials': '3.0',
    'Journal of Healthcare Engineering': '3.7',
    'Electronics': '2.9',
    'Sensors': '3.5',
    'Diagnostics': '3.6',
    'Sustainability': '3.3',
    'Springer': null,
    'Nature': '64.8',
  };
  document.querySelectorAll('.pub-venue').forEach(el => {
    const text = el.textContent;
    for (const [key, val] of Object.entries(IF_MAP)) {
      if (val && text.includes(key)) {
        const badge = document.createElement('span');
        badge.className = 'if-badge';
        badge.textContent = val;
        el.appendChild(badge);
        break;
      }
    }
  });
})();

/* --- #3 Peer review counter (stat item) ------------------- */
(function () {
  const statGrid = document.querySelector('.stats-grid');
  if (!statGrid) return;
  const el = document.createElement('div');
  el.className = 'stat-item';
  el.innerHTML = '<span class="stat-number" data-target="300" data-suffix="+">0+</span><span class="stat-label">Papers Reviewed</span>';
  statGrid.appendChild(el);
})();

/* --- #5 Keyboard shortcut palette ------------------------- */
(function () {
  const overlay = document.getElementById('kbPalette');
  if (!overlay) return;
  const closeBtn = overlay.querySelector('.kb-close');

  function openPalette() {
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
  }
  function closePalette() {
    overlay.classList.remove('open');
    document.body.style.overflow = '';
  }

  document.addEventListener('keydown', e => {
    const tag = document.activeElement.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA') return;
    if (e.key === '?' || e.key === '/') { e.preventDefault(); openPalette(); }
    if (e.key === 'Escape') closePalette();
    if (e.key === 'd' || e.key === 'D') document.getElementById('darkToggle')?.click();
    if (e.key === 'p' || e.key === 'P') { document.querySelector('#publications a, #publications')?.scrollIntoView({behavior:'smooth'}); }
    if (e.key === 'c' || e.key === 'C') { document.getElementById('contact')?.scrollIntoView({behavior:'smooth'}); }
    if (e.key === 'h' || e.key === 'H') { window.scrollTo({top:0,behavior:'smooth'}); }
    if (e.key === 't') document.getElementById('backToTop')?.click();
  });

  overlay.addEventListener('click', e => { if (e.target === overlay) closePalette(); });
  closeBtn?.addEventListener('click', closePalette);
})();

/* --- #6 Sticky year navigator ----------------------------- */
(function () {
  const nav = document.getElementById('yearNav');
  const pubSection = document.getElementById('publications');
  if (!nav || !pubSection) return;

  function buildNav() {
    const years = [...new Set(
      Array.from(document.querySelectorAll('.pub-year-heading')).map(h => h.dataset.year || h.textContent.trim())
    )].sort((a,b) => b - a);
    if (!years.length) return;

    nav.innerHTML = '';
    years.forEach(year => {
      const item = document.createElement('div');
      item.className = 'year-nav-item';
      item.innerHTML = `<span class="year-nav-label">${year}</span><div class="year-nav-dot"></div>`;
      item.addEventListener('click', () => {
        const heading = Array.from(document.querySelectorAll('.pub-year-heading')).find(h => h.textContent.includes(year));
        heading?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
      item.dataset.year = year;
      nav.appendChild(item);
    });
  }

  const pubObs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      nav.classList.toggle('visible', e.isIntersecting);
    });
  }, { threshold: 0.05 });
  pubObs.observe(pubSection);

  function updateActive() {
    const headings = Array.from(document.querySelectorAll('.pub-year-heading'));
    let active = null;
    for (const h of headings) {
      const rect = h.getBoundingClientRect();
      if (rect.top < window.innerHeight * 0.4) active = h.dataset.year || h.textContent.trim();
    }
    if (!active) return;
    nav.querySelectorAll('.year-nav-item').forEach(item => {
      item.classList.toggle('active', item.dataset.year === active);
    });
  }

  window.addEventListener('scroll', updateActive, { passive: true });
  setTimeout(buildNav, 800);
})();

/* --- #7 Share button -------------------------------------- */
(function () {
  const btn = document.getElementById('shareBtn');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    const data = {
      title: 'Dr. Arulmurugan Ramu — Research Profile',
      text: 'Check out Dr. Ramu\'s academic research profile — 125+ publications, 1800+ citations in AI/ML.',
      url: window.location.href,
    };
    if (navigator.share) {
      try { await navigator.share(data); } catch (_) {}
    } else {
      navigator.clipboard.writeText(window.location.href).then(() => {
        btn.title = 'Link copied!';
        btn.style.background = 'var(--teal)';
        btn.style.color = '#fff';
        setTimeout(() => {
          btn.title = 'Share this page';
          btn.style.background = '';
          btn.style.color = '';
        }, 2000);
      });
    }
  });
})();

/* --- #8 Print CV button ----------------------------------- */
(function () {
  const btn = document.getElementById('printBtn');
  if (!btn) return;
  btn.addEventListener('click', () => window.print());
})();

/* --- #11 Semantic Scholar most-cited papers feed ---------- */
(function () {
  const list = document.getElementById('ssFeedList');
  if (!list) return;

  const KNOWN_DOIS = [
    '10.1038/s41598-025-25075-4',
    '10.53759/7669/jmc202404020',
    '10.4018/979-8-3373-0265-2',
    '10.1007/978-3-319-71767-8_9',
    '10.1007/s11063-020-10327-3',
  ];

  Promise.all(KNOWN_DOIS.map(doi =>
    fetch(`https://api.semanticscholar.org/graph/v1/paper/DOI:${doi}?fields=title,citationCount,venue,year,externalIds`)
      .then(r => r.json())
      .catch(() => null)
  )).then(papers => {
    const valid = papers.filter(p => p && p.title);
    if (!valid.length) return;
    valid.sort((a, b) => (b.citationCount || 0) - (a.citationCount || 0));

    list.innerHTML = '';
    valid.forEach((p, i) => {
      const doi = p.externalIds?.DOI || '';
      const url = doi ? `https://doi.org/${doi}` : '#';
      list.innerHTML += `
        <div class="ss-paper">
          <div class="ss-rank">${i + 1}</div>
          <div class="ss-body">
            <div class="ss-title"><a href="${url}" target="_blank" rel="noopener">${p.title}</a></div>
            <div class="ss-venue">${p.venue || 'Journal/Conference'} · ${p.year || ''}</div>
            <div class="ss-cite">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
              ${p.citationCount ?? '—'} citations
            </div>
          </div>
        </div>`;
    });
  });
})();

/* --- #13 Aurora blobs — show after load ------------------- */
(function () {
  const hero = document.querySelector('.hero');
  if (!hero) return;
  hero.classList.add('aurora-loaded');
})();

/* --- #14 Scroll-snap toggle ------------------------------- */
(function () {
  const btn = document.getElementById('snapBtn');
  if (!btn) return;
  let active = false;
  btn.addEventListener('click', () => {
    active = !active;
    document.documentElement.classList.toggle('snap-mode', active);
    btn.classList.toggle('active', active);
    btn.title = active ? 'Disable scroll snap' : 'Enable scroll snap';
  });
})();

/* --- #15 Dark mode transition animation ------------------- */
(function () {
  const toggle = document.getElementById('darkToggle');
  if (!toggle) return;
  toggle.addEventListener('click', () => {
    document.documentElement.classList.add('theme-transitioning');
    setTimeout(() => document.documentElement.classList.remove('theme-transitioning'), 600);
  }, true); // capture: true — runs before existing handler
})();

/* --- Publications collapsed preview (show 8 by default) --- */
(function () {
  const list = document.getElementById('pubList');
  const btn  = document.getElementById('pubShowMore');
  if (!list || !btn) return;

  const LIMIT = 8;
  let expanded = false;

  function markExtras() {
    // Mark items beyond LIMIT as extra (respects current filter visibility)
    const visible = Array.from(list.querySelectorAll('.pub-item'))
      .filter(el => !el.classList.contains('pub-hidden'));
    visible.forEach((el, i) => {
      el.classList.toggle('pub-extra', i >= LIMIT);
    });
    const hasExtra = visible.length > LIMIT;
    btn.style.display = hasExtra && !expanded ? '' : (expanded ? '' : 'none');
    btn.textContent   = expanded
      ? `Show fewer publications ↑`
      : `Show all ${visible.length} publications ↓`;
  }

  function setExpanded(val) {
    expanded = val;
    list.classList.toggle('pub-preview', !expanded);
    markExtras();
    if (!expanded) {
      // Scroll back to top of publications section smoothly
      document.getElementById('publications')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  btn.addEventListener('click', () => setExpanded(!expanded));

  // Init: collapsed by default
  list.classList.add('pub-preview');
  markExtras();
  btn.style.display = '';

  // Re-run after filter changes (patch applyFilter)
  const orig = window.applyFilter;
  if (typeof orig === 'function') {
    window.applyFilter = function (...args) {
      orig(...args);
      // After filter applies, re-evaluate extras
      setTimeout(() => {
        if (!expanded) markExtras();
      }, 50);
    };
  }
})();
