/**
 * Личный кабинет: email OTP, онбординг предприятия, sidebar-dashboard (UI).
 */
(function initCabinet() {
  const TOKEN_KEY = "ics:auth_token";
  const REFRESH_KEY = "ics:auth_refresh";
  const USER_KEY = "ics:auth_user";
  const COMPANY_KEY = "ics:company_profile";

  const VIEW_META = {
    overview: { eyebrow: "Обзор", title: "Главная" },
    bookings: { eyebrow: "Записи", title: "Записи клиентов" },
    settings: { eyebrow: "Настройки", title: "Настройки предприятия" },
    telegram: { eyebrow: "Интеграции", title: "Telegram" },
    templates: { eyebrow: "Контент", title: "Шаблоны уведомлений" },
  };

  const cabinet = document.getElementById("cabinet");
  const cabinetPanel = document.getElementById("cabinetPanel");
  const backdrop = document.getElementById("cabinetBackdrop");
  const openBtn = document.getElementById("openCabinet");
  const closeBtn = document.getElementById("closeCabinet");
  const stepRegister = document.getElementById("cabinetStepRegister");
  const stepVerify = document.getElementById("cabinetStepVerify");
  const stepOnboarding = document.getElementById("cabinetStepOnboarding");
  const stepApp = document.getElementById("cabinetStepApp");
  const registerForm = document.getElementById("registerForm");
  const verifyForm = document.getElementById("verifyForm");
  const onboardingForm = document.getElementById("onboardingForm");
  const settingsForm = document.getElementById("settingsForm");
  const registerError = document.getElementById("registerError");
  const verifyError = document.getElementById("verifyError");
  const onboardingError = document.getElementById("onboardingError");
  const settingsError = document.getElementById("settingsError");
  const settingsSaved = document.getElementById("settingsSaved");
  const verifyEmailDisplay = document.getElementById("verifyEmailDisplay");
  const verifyDevHint = document.getElementById("verifyDevHint");
  const backToRegister = document.getElementById("backToRegister");
  const logoutBtn = document.getElementById("cabinetLogout");
  const logoutBtnAlt = document.getElementById("cabinetLogoutAlt");
  const bookingsList = document.getElementById("bookingsList");
  const bookingsLoading = document.getElementById("bookingsLoading");
  const dashboardUserName = document.getElementById("dashboardUserName");
  const sidebarUserName = document.getElementById("sidebarUserName");
  const sidebarUserEmail = document.getElementById("sidebarUserEmail");
  const sidebarCompanyName = document.getElementById("sidebarCompanyName");
  const appViewEyebrow = document.getElementById("appViewEyebrow");
  const appViewTitle = document.getElementById("appViewTitle");
  const onboardingCompanyName = document.getElementById("onboardingCompanyName");
  const onboardingOwnerEmail = document.getElementById("onboardingOwnerEmail");
  const settingsCompanyName = document.getElementById("settingsCompanyName");
  const settingsOwnerEmail = document.getElementById("settingsOwnerEmail");
  const settingsPhone = document.getElementById("settingsPhone");
  const overviewApiKey = document.getElementById("overviewApiKey");
  const settingsApiKey = document.getElementById("settingsApiKey");
  const telegramApiKey = document.getElementById("telegramApiKey");
  const nav = document.getElementById("nav");
  const cabinetNav = document.getElementById("cabinetNav");

  let pendingEmail = "";
  let pendingName = "";
  let pendingPhone = "";
  let activeView = "overview";

  function apiBase() {
    return (window.ICS_API_BASE || "").replace(/\/$/, "");
  }

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function setSession(token, refreshToken, user) {
    localStorage.setItem(TOKEN_KEY, token);
    if (refreshToken) {
      localStorage.setItem(REFRESH_KEY, refreshToken);
    }
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  function clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
  }

  function getStoredUser() {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY) || "null");
    } catch {
      return null;
    }
  }

  function getCompanyProfile() {
    try {
      return JSON.parse(localStorage.getItem(COMPANY_KEY) || "null");
    } catch {
      return null;
    }
  }

  function saveCompanyProfile(profile) {
    localStorage.setItem(COMPANY_KEY, JSON.stringify(profile));
  }

  function generateApiKey() {
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  }

  function showError(el, msg) {
    if (!el) return;
    el.textContent = msg;
    el.hidden = !msg;
  }

  function setButtonLoading(btn, loading, loadingText) {
    if (!btn) return;
    if (loading) {
      if (!btn.dataset.defaultHtml) {
        btn.dataset.defaultHtml = btn.innerHTML;
      }
      btn.disabled = true;
      btn.setAttribute("aria-busy", "true");
      btn.innerHTML = loadingText;
      return;
    }
    btn.disabled = false;
    btn.removeAttribute("aria-busy");
    if (btn.dataset.defaultHtml) {
      btn.innerHTML = btn.dataset.defaultHtml;
    }
  }

  function formatApiError(message) {
    const map = {
      "Failed to store verification code.":
        "Не удалось сохранить код. Проверьте, что в Supabase выполнены миграции 004 и 005.",
      "Failed to send verification email.":
        "Не удалось отправить письмо. Проверьте SMTP на Amvera.",
      "Email delivery is not configured.":
        "Почта не настроена на сервере (SMTP).",
      "Invalid code.": "Неверный код.",
      "Code expired. Request a new one.": "Код истёк. Запросите новый.",
      "Company is already configured for this account.":
        "Компания уже настроена для этого аккаунта.",
      "Company is not configured yet.": "Сначала укажите данные предприятия.",
      "Failed to create company. Please try again.":
        "Не удалось создать компанию. Попробуйте ещё раз.",
    };
    return map[message] || message;
  }

  function needsOnboarding(user) {
    return !user?.company_id;
  }

  function profileFromCompany(company) {
    return {
      companyName: company.name,
      ownerEmail: company.owner_email,
      apiKey: company.api_key,
      createdAt: company.created_at,
    };
  }

  function mapSessionUser(user) {
    return {
      name: user.name,
      email: user.email,
      phone: user.phone || null,
      role: user.role || "client",
      company_id: user.company_id || null,
    };
  }

  async function loadCompanyProfile() {
    try {
      const company = await apiFetch("/api/v1/company/me");
      const profile = profileFromCompany(company);
      saveCompanyProfile(profile);
      return profile;
    } catch {
      return null;
    }
  }

  function setPanelWide(wide) {
    cabinetPanel.classList.toggle("cabinet__panel--wide", wide);
  }

  function showStep(step) {
    const steps = [stepRegister, stepVerify, stepOnboarding, stepApp];
    steps.forEach((s) => {
      s.hidden = s !== step;
    });
    setPanelWide(step === stepApp);
  }

  function syncUserUi(user) {
    const name = user?.name || user?.email || "Пользователь";
    const email = user?.email || "—";
    dashboardUserName.textContent = name;
    sidebarUserName.textContent = name;
    sidebarUserEmail.textContent = email;
    if (settingsPhone && user?.phone) {
      settingsPhone.value = user.phone;
    }
  }

  function syncCompanyUi(profile) {
    if (!profile) return;
    sidebarCompanyName.textContent = profile.companyName || "ICS";
    const key = profile.apiKey || "—";
    overviewApiKey.textContent = key;
    settingsApiKey.textContent = key;
    telegramApiKey.textContent = key;
    settingsCompanyName.value = profile.companyName || "";
    settingsOwnerEmail.value = profile.ownerEmail || "";
    document
      .querySelector('#setupChecklist li[data-check="company"]')
      ?.classList.add("is-done");
  }

  function switchView(viewId) {
    activeView = viewId;
    cabinetNav.querySelectorAll(".cabinet-app__nav-btn").forEach((btn) => {
      btn.classList.toggle("is-active", btn.dataset.view === viewId);
    });
    document.querySelectorAll("[data-view-panel]").forEach((panel) => {
      panel.hidden = panel.dataset.viewPanel !== viewId;
    });
    const meta = VIEW_META[viewId] || VIEW_META.overview;
    appViewEyebrow.textContent = meta.eyebrow;
    appViewTitle.textContent = meta.title;
    if (viewId === "bookings") {
      loadBookings();
    }
  }

  function enterApp(user, profile) {
    syncUserUi(user);
    if (profile) {
      syncCompanyUi(profile);
    }
    showStep(stepApp);
    switchView(activeView);
  }

  async function openCabinet() {
    document.body.classList.add("cabinet-open");
    cabinet.classList.add("is-open");
    cabinet.setAttribute("aria-hidden", "false");
    nav.classList.remove("open");

    const token = getToken();
    if (!token) {
      showStep(stepRegister);
      registerForm.reset();
      showError(registerError, "");
      return;
    }

    const user = getStoredUser();
    syncUserUi(user);

    if (needsOnboarding(user)) {
      onboardingOwnerEmail.value = user?.email || "";
      showStep(stepOnboarding);
      return;
    }

    const profile = getCompanyProfile() || (await loadCompanyProfile());
    enterApp(user, profile);
  }

  function closeCabinet() {
    document.body.classList.remove("cabinet-open");
    cabinet.classList.remove("is-open");
    cabinet.setAttribute("aria-hidden", "true");
  }

  async function apiFetch(path, options = {}) {
    const base = apiBase();
    if (!base) {
      throw new Error(
        "API не настроен. Локально: js/config.js. На Vercel: переменная ICS_API_BASE (URL Amvera)."
      );
    }
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    const token = getToken();
    if (token && !headers.Authorization) {
      headers.Authorization = `Bearer ${token}`;
    }

    let res;
    try {
      res = await fetch(`${base}${path}`, { ...options, headers });
    } catch {
      throw new Error(
        "Не удалось подключиться к серверу. Проверьте ICS_API_BASE и CORS_ORIGINS на бэкенде."
      );
    }

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = data.detail;
      const msg = Array.isArray(detail)
        ? detail.map((d) => d.msg || d).join(", ")
        : detail || data.message || "Ошибка сервера";
      throw new Error(msg);
    }
    return data;
  }

  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    showError(registerError, "");
    const fd = new FormData(registerForm);
    pendingName = (fd.get("name") || "").toString().trim();
    pendingEmail = (fd.get("email") || "").toString().trim().toLowerCase();
    pendingPhone = (fd.get("phone") || "").toString().trim();
    const btn = registerForm.querySelector("button[type=submit]");
    setButtonLoading(btn, true, "Отправка…");

    try {
      const payload = { email: pendingEmail, name: pendingName };
      if (pendingPhone) payload.phone = pendingPhone;

      const data = await apiFetch("/api/v1/auth/send-code", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      verifyEmailDisplay.textContent = pendingEmail;
      if (data.dev_code && verifyDevHint) {
        verifyDevHint.textContent = `Режим разработки: код ${data.dev_code} (SMTP не настроен)`;
        verifyDevHint.hidden = false;
      } else if (verifyDevHint) {
        verifyDevHint.hidden = true;
        verifyDevHint.textContent = "";
      }
      verifyForm.reset();
      showError(verifyError, "");
      showStep(stepVerify);
    } catch (err) {
      showError(registerError, formatApiError(err.message));
    } finally {
      setButtonLoading(btn, false);
    }
  });

  verifyForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    showError(verifyError, "");
    const code = new FormData(verifyForm).get("code").toString().trim();
    const btn = verifyForm.querySelector("button[type=submit]");
    setButtonLoading(btn, true, "Проверка…");

    try {
      const data = await apiFetch("/api/v1/auth/verify-code", {
        method: "POST",
        body: JSON.stringify({ email: pendingEmail, code }),
      });

      const user = data.user || {};
      const sessionUser = mapSessionUser({
        name: user.name || pendingName,
        email: user.email || pendingEmail,
        phone: user.phone || pendingPhone || null,
        role: user.role || "client",
        company_id: user.company_id || null,
      });
      setSession(data.access_token, data.refresh_token, sessionUser);

      if (needsOnboarding(sessionUser)) {
        onboardingOwnerEmail.value = sessionUser.email || "";
        onboardingCompanyName.value = "";
        showStep(stepOnboarding);
      } else {
        const profile = getCompanyProfile() || (await loadCompanyProfile());
        enterApp(sessionUser, profile);
      }
    } catch (err) {
      showError(verifyError, formatApiError(err.message));
    } finally {
      setButtonLoading(btn, false);
    }
  });

  onboardingForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    showError(onboardingError, "");
    const fd = new FormData(onboardingForm);
    const companyName = (fd.get("company_name") || "").toString().trim();
    const ownerEmail = (fd.get("owner_email") || "").toString().trim().toLowerCase();
    if (!companyName) {
      showError(onboardingError, "Укажите название предприятия.");
      return;
    }

    const btn = onboardingForm.querySelector("button[type=submit]");
    setButtonLoading(btn, true, "Создание…");

    try {
      const data = await apiFetch("/api/v1/company/setup", {
        method: "POST",
        body: JSON.stringify({
          company_name: companyName,
          owner_email: ownerEmail || undefined,
        }),
      });

      const sessionUser = mapSessionUser(data.user);
      setSession(data.access_token, data.refresh_token, sessionUser);
      const profile = profileFromCompany(data.company);
      saveCompanyProfile(profile);
      enterApp(sessionUser, profile);
    } catch (err) {
      showError(onboardingError, formatApiError(err.message));
    } finally {
      setButtonLoading(btn, false);
    }
  });

  settingsForm.addEventListener("submit", (e) => {
    e.preventDefault();
    showError(settingsError, "");
    settingsSaved.hidden = true;
    const fd = new FormData(settingsForm);
    const existing = getCompanyProfile() || {};
    const profile = {
      ...existing,
      companyName: (fd.get("company_name") || "").toString().trim(),
      ownerEmail: (fd.get("owner_email") || "").toString().trim().toLowerCase(),
      apiKey: existing.apiKey || generateApiKey(),
    };
    if (!profile.companyName || !profile.ownerEmail) {
      showError(settingsError, "Заполните обязательные поля.");
      return;
    }
    saveCompanyProfile(profile);
    syncCompanyUi(profile);

    const user = getStoredUser() || {};
    user.phone = (fd.get("phone") || "").toString().trim() || user.phone;
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    syncUserUi(user);
    settingsSaved.hidden = false;
    setTimeout(() => {
      settingsSaved.hidden = true;
    }, 2500);
  });

  backToRegister.addEventListener("click", () => {
    showStep(stepRegister);
    showError(verifyError, "");
    if (verifyDevHint) {
      verifyDevHint.hidden = true;
      verifyDevHint.textContent = "";
    }
  });

  function handleLogout() {
    clearSession();
    localStorage.removeItem(COMPANY_KEY);
    activeView = "overview";
    showStep(stepRegister);
    registerForm.reset();
    setPanelWide(false);
  }

  logoutBtn.addEventListener("click", handleLogout);
  logoutBtnAlt.addEventListener("click", handleLogout);

  cabinetNav.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-view]");
    if (!btn) return;
    switchView(btn.dataset.view);
  });

  document.querySelectorAll("[data-copy-target]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const el = document.getElementById(btn.dataset.copyTarget);
      if (!el) return;
      const text = el.textContent.trim();
      try {
        await navigator.clipboard.writeText(text);
        const prev = btn.textContent;
        btn.textContent = "Скопировано";
        setTimeout(() => {
          btn.textContent = prev;
        }, 1500);
      } catch {
        alert("Не удалось скопировать");
      }
    });
  });

  function statusLabel(status) {
    const map = {
      pending: "Ожидает",
      confirmed: "Подтверждена",
      scheduled: "Запланирована",
      cancelled: "Отменена",
      completed: "Завершена",
    };
    return map[status] || status;
  }

  function formatDate(dateStr, timeStr) {
    const [y, m, d] = dateStr.split("-");
    const time = timeStr ? timeStr.slice(0, 5) : "";
    return `${d}.${m}.${y}${time ? " в " + time : ""}`;
  }

  async function loadBookings() {
    if (!bookingsList || !bookingsLoading) return;
    bookingsList.innerHTML = "";
    bookingsLoading.hidden = false;
    bookingsList.appendChild(bookingsLoading);

    try {
      const bookings = await apiFetch("/api/v1/bookings/my");
      bookingsLoading.remove();

      if (!bookings.length) {
        bookingsList.innerHTML =
          '<p class="cabinet__empty">Активных записей пока нет.</p>';
        return;
      }

      bookings.forEach((b) => {
        const card = document.createElement("article");
        card.className = "cabinet__booking";
        card.innerHTML = `
          <div class="cabinet__booking-main">
            <span class="cabinet__booking-service">${b.service_name}</span>
            <span class="cabinet__booking-company">${b.company_name}</span>
            <span class="cabinet__booking-date">${formatDate(b.appointment_date, b.appointment_time)}</span>
          </div>
          <div class="cabinet__booking-meta">
            <span class="cabinet__status cabinet__status--${b.status}">${statusLabel(b.status)}</span>
            ${
              b.status !== "cancelled" && b.status !== "completed"
                ? `<button type="button" class="cabinet__cancel" data-id="${b.id}">Отменить</button>`
                : ""
            }
          </div>`;
        bookingsList.appendChild(card);
      });

      bookingsList.querySelectorAll(".cabinet__cancel").forEach((btn) => {
        btn.addEventListener("click", () => cancelBooking(btn.dataset.id, btn));
      });
    } catch (err) {
      bookingsLoading.remove();
      bookingsList.innerHTML = `<p class="cabinet__error">${err.message}</p>`;
    }
  }

  async function cancelBooking(id, btn) {
    if (!confirm("Отменить эту запись?")) return;
    btn.disabled = true;
    try {
      await apiFetch(`/api/v1/bookings/${id}/cancel`, { method: "POST" });
      loadBookings();
    } catch (err) {
      alert(err.message);
      btn.disabled = false;
    }
  }

  openBtn.addEventListener("click", openCabinet);
  closeBtn.addEventListener("click", closeCabinet);
  backdrop.addEventListener("click", closeCabinet);

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && cabinet.classList.contains("is-open")) closeCabinet();
  });

  nav.addEventListener("click", (e) => {
    if (e.target.closest("#openCabinet")) {
      e.preventDefault();
      openCabinet();
    }
  });
})();
