/**
 * Слой хранения настроек пользователя (тема оформления и т.п.).
 * Сейчас данные хранятся в localStorage, но интерфейс асинхронный —
 * при появлении бэкенда достаточно подставить сюда fetch-запросы
 * к своему API (например window.ICS_API_BASE = "https://api.example.com"),
 * не меняя код, который вызывает Settings.get/set.
 */
const Settings = (() => {
  const LOCAL_PREFIX = "ics:";

  async function get(key, fallback = null) {
    if (window.ICS_API_BASE) {
      try {
        const res = await fetch(`${window.ICS_API_BASE}/settings/${key}`, {
          credentials: "include",
        });
        if (res.ok) {
          const data = await res.json();
          if (data && typeof data.value !== "undefined") return data.value;
        }
      } catch (err) {
        /* бэкенд недоступен — используем локальное хранилище как фолбэк */
      }
    }
    const local = localStorage.getItem(LOCAL_PREFIX + key);
    return local !== null ? local : fallback;
  }

  async function set(key, value) {
    localStorage.setItem(LOCAL_PREFIX + key, value);
    if (window.ICS_API_BASE) {
      try {
        await fetch(`${window.ICS_API_BASE}/settings/${key}`, {
          method: "PUT",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ value }),
        });
      } catch (err) {
        /* тихо игнорируем — значение уже сохранено локально */
      }
    }
  }

  return { get, set };
})();

/* ============ Theme switch (blue / light / dark) ============ */
(async function initTheme() {
  const root = document.documentElement;
  const buttons = Array.from(document.querySelectorAll("[data-theme-choice]"));

  function applyActiveState(theme) {
    buttons.forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.themeChoice === theme);
    });
  }

  function setTheme(theme) {
    root.setAttribute("data-theme", theme);
    applyActiveState(theme);
    Settings.set("theme", theme);
  }

  const saved = await Settings.get("theme", "blue");
  setTheme(saved);

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => setTheme(btn.dataset.themeChoice));
  });
})();

/* ============ Mobile nav ============ */
(function initMobileNav() {
  const burger = document.getElementById("burger");
  const nav = document.getElementById("nav");
  const header = document.querySelector(".header");
  const headerInner = header?.querySelector(".header__inner");
  if (!burger || !nav) return;

  const MOBILE_NAV_BP = 1100;

  function updateNavOrigin() {
    if (window.innerWidth >= MOBILE_NAV_BP || !headerInner) return;
    const burgerRect = burger.getBoundingClientRect();
    const innerRect = headerInner.getBoundingClientRect();
    const originX = burgerRect.left + burgerRect.width / 2 - innerRect.left;
    const originY = burgerRect.bottom - innerRect.top + 8;
    nav.style.transformOrigin = `${originX}px ${originY}px`;
  }

  function setNavOpen(open) {
    if (open) updateNavOrigin();
    nav.classList.toggle("open", open);
    header?.classList.toggle("is-nav-open", open);
    burger.setAttribute("aria-expanded", open ? "true" : "false");
    burger.setAttribute("aria-controls", "nav");
    document.body.classList.toggle("nav-open", open);
  }

  burger.addEventListener("click", (e) => {
    e.stopPropagation();
    setNavOpen(!nav.classList.contains("open"));
  });

  nav.addEventListener("click", (e) => {
    if (e.target.closest("a, .nav__cabinet")) setNavOpen(false);
  });

  document.addEventListener("click", (e) => {
    if (!nav.classList.contains("open")) return;
    if (e.target.closest(".header")) return;
    setNavOpen(false);
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && nav.classList.contains("open")) setNavOpen(false);
  });

  window.addEventListener("resize", () => {
    if (nav.classList.contains("open")) updateNavOrigin();
    if (window.innerWidth >= MOBILE_NAV_BP && nav.classList.contains("open")) setNavOpen(false);
  });
})();

/* ============ Scroll progress bar ============ */
const progressBar = document.getElementById("scrollProgress");
function updateProgress() {
  const scrollTop = window.scrollY;
  const docHeight = document.documentElement.scrollHeight - window.innerHeight;
  const pct = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
  progressBar.style.width = pct + "%";
}
document.addEventListener("scroll", updateProgress, { passive: true });
updateProgress();

/* ============ Reveal on scroll (staggered via CSS --i) ============ */
const revealItems = document.querySelectorAll(
  ".card, .channel, .why, .steps li, .about__points li, .stat"
);
revealItems.forEach((el) => el.classList.add("reveal"));

const io = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        io.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.15 }
);
revealItems.forEach((el) => io.observe(el));

/* ============ Animated stat counters ============ */
function animateCount(el) {
  const target = parseFloat(el.dataset.countTo);
  const prefix = el.dataset.prefix || "";
  const suffix = el.dataset.suffix || "";
  const duration = 1100;
  const start = performance.now();

  function tick(now) {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const value = Math.round(target * eased);
    el.innerHTML = `${prefix}${value}${suffix}`;
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

const counters = document.querySelectorAll("[data-count-to]");
const staticStats = document.querySelectorAll("[data-static]");
staticStats.forEach((el) => { el.textContent = el.dataset.static; });

const counterIO = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        animateCount(entry.target);
        counterIO.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.4 }
);
counters.forEach((el) => counterIO.observe(el));
