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
const header = document.querySelector(".header");
const bgGlows = document.querySelectorAll(".bg-glow");

function updateProgress() {
  const scrollTop = window.scrollY;
  const docHeight = document.documentElement.scrollHeight - window.innerHeight;
  const pct = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
  if (progressBar) progressBar.style.width = `${pct}%`;
  if (header) header.classList.toggle("is-scrolled", scrollTop > 24);
  bgGlows.forEach((glow, index) => {
    const shift = scrollTop * (index === 0 ? 0.04 : -0.03);
    glow.style.transform = `translate3d(0, ${shift}px, 0)`;
  });
}
document.addEventListener("scroll", updateProgress, { passive: true });
updateProgress();

/* ============ Reveal on scroll (staggered via CSS --i) ============ */
const revealItems = document.querySelectorAll(
  ".card, .channel, .why, .steps li, .about__points li, .stat, .plan-card, .hero__badge, .hero__title, .hero__desc, .hero__cta, .hero__frame, .cta__box, .footer__col, .section__head"
);
revealItems.forEach((el) => el.classList.add("reveal"));

const sectionBlocks = document.querySelectorAll(".section, .cta, .footer__grid");
sectionBlocks.forEach((el) => el.classList.add("reveal-section"));

const io = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        io.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.12, rootMargin: "0px 0px -6% 0px" }
);
revealItems.forEach((el) => io.observe(el));
sectionBlocks.forEach((el) => io.observe(el));

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

/* ============ Billing period toggle + animated prices ============ */
(function initBillingPeriodToggles() {
  const PRICE_ANIM_MS = 500;

  function parseRub(text) {
    return parseInt(String(text || "").replace(/\D/g, ""), 10) || 0;
  }

  function formatRub(value) {
    return `${value.toLocaleString("ru-RU")} ₽`;
  }

  function animatePriceStrong(el, target) {
    const from = parseRub(el.textContent);
    const to = parseRub(typeof target === "string" ? target : target.textContent);
    if (from === to) return;

    const targetText = typeof target === "string" ? target : target.textContent;
    const start = performance.now();
    const duration = 600;

    function tick(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(from + (to - from) * eased);
      el.textContent = formatRub(current);
      if (progress < 1) {
        requestAnimationFrame(tick);
      } else {
        el.textContent = targetText;
      }
    }

    requestAnimationFrame(tick);
  }

  function preparePriceBoxes(panel) {
    const period = panel?.querySelector("[data-billing-toggle]")?.dataset.period || "monthly";
    panel?.querySelectorAll(".plan-card__price").forEach((box) => {
      if (box.dataset.priceReady) return;
      box.dataset.priceReady = "1";
      box.classList.add("plan-card__price--switchable");
      box.querySelectorAll("[data-price-period]").forEach((layer) => {
        const active = layer.dataset.pricePeriod === period;
        layer.hidden = false;
        layer.removeAttribute("hidden");
        layer.classList.remove("is-leaving", "is-entering");
        layer.classList.toggle("is-visible", active);
        layer.toggleAttribute("aria-hidden", !active);
      });
    });
  }

  function switchPanelPeriod(panel, period) {
    if (!panel) return;
    const toggle = panel.querySelector("[data-billing-toggle]");
    if (!toggle || toggle.dataset.period === period) return;

    toggle.dataset.period = period;
    toggle.querySelectorAll("button[data-period-btn]").forEach((btn) => {
      btn.classList.toggle("is-active", btn.dataset.periodBtn === period);
    });

    preparePriceBoxes(panel);

    // Добавляем анимацию "пульсации" на карточки
    panel.querySelectorAll(".plan-card").forEach((card) => {
      card.style.transform = "scale(0.98)";
      card.style.opacity = "0.7";
      setTimeout(() => {
        card.style.transform = "";
        card.style.opacity = "";
      }, 50);
    });

    panel.querySelectorAll(".plan-card__price--switchable").forEach((box) => {
      const animId = String(Number(box.dataset.priceAnimId || 0) + 1);
      box.dataset.priceAnimId = animId;

      const outgoing = box.querySelector("[data-price-period].is-visible");
      const incoming = box.querySelector(`[data-price-period="${period}"]`);
      if (!incoming || outgoing === incoming) return;

      incoming.hidden = false;
      incoming.removeAttribute("hidden");
      incoming.removeAttribute("aria-hidden");
      incoming.classList.remove("is-leaving");
      incoming.classList.add("is-entering");

      if (outgoing) {
        outgoing.classList.remove("is-entering");
        outgoing.classList.add("is-leaving");
      }

      requestAnimationFrame(() => {
        if (box.dataset.priceAnimId !== animId) return;
        incoming.classList.add("is-visible");
        incoming.classList.remove("is-entering");
        const outStrong = outgoing?.querySelector("strong");
        const inStrong = incoming.querySelector("strong");
        if (outStrong && inStrong) {
          const fromVal = parseRub(outStrong.textContent);
          const toVal = parseRub(inStrong.textContent);
          inStrong.textContent = formatRub(fromVal);
          animatePriceStrong(inStrong, formatRub(toVal));
        }
      });

      window.setTimeout(() => {
        if (box.dataset.priceAnimId !== animId) return;
        if (outgoing) {
          outgoing.classList.remove("is-visible", "is-leaving");
          outgoing.setAttribute("aria-hidden", "true");
        }
        incoming.classList.add("is-visible");
        incoming.classList.remove("is-entering");
        incoming.removeAttribute("aria-hidden");
      }, PRICE_ANIM_MS);
    });
  }

  document.querySelectorAll("[data-plans-panel]").forEach(preparePriceBoxes);

  document.querySelectorAll("[data-billing-toggle]").forEach((toggle) => {
    if (toggle.dataset.toggleBound) return;
    toggle.dataset.toggleBound = "1";

    toggle.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-period-btn]");
      if (!btn) return;
      const panel = toggle.closest("[data-plans-panel]");
      switchPanelPeriod(panel, btn.dataset.periodBtn);
    });
  });

  window.ICS = window.ICS || {};
  window.ICS.switchBillingPeriod = switchPanelPeriod;
})();
