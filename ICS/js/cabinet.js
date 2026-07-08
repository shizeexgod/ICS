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
    calendar: { eyebrow: "Расписание", title: "Календарь" },
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
  const telegramStatus = document.getElementById("telegramStatus");
  const telegramManagersList = document.getElementById("telegramManagersList");
  const statAppointmentsToday = document.getElementById("statAppointmentsToday");
  const statActiveClients = document.getElementById("statActiveClients");
  const statRemindersWeek = document.getElementById("statRemindersWeek");
  const sidebarPlanBadge = document.getElementById("sidebarPlanBadge");
  const planBanner = document.getElementById("planBanner");
  const nav = document.getElementById("nav");
  const cabinetNav = document.getElementById("cabinetNav");
  const calendarGrid = document.getElementById("calendarGrid");
  const calendarMonthLabel = document.getElementById("calendarMonthLabel");
  const calendarDayTitle = document.getElementById("calendarDayTitle");
  const calendarDayList = document.getElementById("calendarDayList");
  const calendarPrevMonth = document.getElementById("calendarPrevMonth");
  const calendarNextMonth = document.getElementById("calendarNextMonth");
  const calendarCreateForm = document.getElementById("calendarCreateForm");
  const calendarCreateError = document.getElementById("calendarCreateError");
  const calendarCreateSuccess = document.getElementById("calendarCreateSuccess");
  const calendarDate = document.getElementById("calendarDate");
  const calendarTime = document.getElementById("calendarTime");

  let pendingEmail = "";
  let pendingName = "";
  let pendingPhone = "";
  let activeView = "overview";
  let calendarMonth = new Date();
  let calendarSelectedDate = toDateKey(new Date());
  let calendarAppointments = [];
  let calendarLoaded = false;

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
      plan: company.plan || null,
    };
  }

  function syncPlanUi(plan) {
    if (!plan || !sidebarPlanBadge) return;
    const isPro = plan.plan === "pro";
    sidebarPlanBadge.textContent = isPro ? "Pro" : "Trial";
    sidebarPlanBadge.classList.toggle("cabinet-app__plan-badge--pro", isPro);

    if (!planBanner) return;
    if (isPro) {
      planBanner.hidden = true;
      planBanner.textContent = "";
      return;
    }

    const days = plan.trial_days_left ?? 0;
    const remaining = plan.reminders_remaining ?? 0;
    let text = `Trial: осталось <strong>${days} дн.</strong> и <strong>${remaining}</strong> напоминаний из 100.`;
    if (!plan.is_trial_active) {
      text = `Trial завершён. Перейдите на <strong>Pro (${plan.pro_price_rub} ₽/мес)</strong> — оплата через ЮKassa скоро.`;
    } else if (!plan.can_send_reminders) {
      text = `Лимит trial исчерпан. Pro — <strong>${plan.pro_price_rub} ₽/мес</strong> (ЮKassa скоро).`;
    }
    planBanner.innerHTML = text;
    planBanner.hidden = false;
  }

  async function loadDashboardStats() {
    if (!statAppointmentsToday) return;
    try {
      const stats = await apiFetch("/api/v1/company/stats");
      statAppointmentsToday.textContent = String(stats.appointments_today ?? 0);
      statActiveClients.textContent = String(stats.active_clients ?? 0);
      statRemindersWeek.textContent = String(stats.reminders_week ?? 0);
    } catch {
      statAppointmentsToday.textContent = "0";
      statActiveClients.textContent = "0";
      statRemindersWeek.textContent = "0";
    }
  }

  async function loadTelegramStatus() {
    if (!telegramStatus) return;
    try {
      const data = await apiFetch("/api/v1/company/telegram");
      telegramStatus.textContent = data.connected ? "Подключено" : "Не подключено";
      telegramStatus.classList.toggle("cabinet-app__badge--ok", data.connected);

      const checklistItem = document.querySelector('#setupChecklist li[data-check="telegram"]');
      if (checklistItem) {
        checklistItem.classList.toggle("is-done", data.connected);
      }

      if (!telegramManagersList) return;
      if (!data.managers?.length) {
        telegramManagersList.innerHTML =
          '<p class="cabinet-app__empty-inline">Пока нет привязанных Telegram-админов.</p>';
        return;
      }
      telegramManagersList.innerHTML = data.managers
        .map(
          (m) =>
            `<p class="cabinet-app__manager-item">Chat ID: <code>${m.tg_chat_id}</code></p>`
        )
        .join("");
    } catch {
      telegramStatus.textContent = "Не подключено";
    }
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
    if (profile.plan) syncPlanUi(profile.plan);
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
    } else if (viewId === "calendar") {
      if (!calendarLoaded) {
        loadCalendar();
      } else {
        renderCalendarGrid();
        renderCalendarDayList();
      }
    } else if (viewId === "overview") {
      loadDashboardStats();
      loadTelegramStatus();
    } else if (viewId === "telegram") {
      loadTelegramStatus();
    }
  }

  function enterApp(user, profile) {
    syncUserUi(user);
    if (profile) {
      syncCompanyUi(profile);
    }
    showStep(stepApp);
    switchView(activeView);
    loadDashboardStats();
    loadTelegramStatus();
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

  settingsForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    showError(settingsError, "");
    settingsSaved.hidden = true;
    const fd = new FormData(settingsForm);
    const companyName = (fd.get("company_name") || "").toString().trim();
    const ownerEmail = (fd.get("owner_email") || "").toString().trim().toLowerCase();
    const phone = (fd.get("phone") || "").toString().trim();
    if (!companyName || !ownerEmail) {
      showError(settingsError, "Заполните обязательные поля.");
      return;
    }

    const btn = settingsForm.querySelector('button[type="submit"]');
    setButtonLoading(btn, true, "Сохранение…");

    try {
      const company = await apiFetch("/api/v1/company/me", {
        method: "PATCH",
        body: JSON.stringify({ name: companyName, owner_email: ownerEmail }),
      });
      if (phone) {
        await apiFetch("/api/v1/company/profile", {
          method: "PATCH",
          body: JSON.stringify({ phone }),
        });
      }
      const profile = profileFromCompany(company);
      saveCompanyProfile(profile);
      syncCompanyUi(profile);

      const user = getStoredUser() || {};
      user.phone = phone || user.phone;
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      syncUserUi(user);
      settingsSaved.hidden = false;
      setTimeout(() => {
        settingsSaved.hidden = true;
      }, 2500);
    } catch (err) {
      showError(settingsError, formatApiError(err.message));
    } finally {
      setButtonLoading(btn, false);
    }
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
    calendarLoaded = false;
    calendarAppointments = [];
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

  const MONTH_NAMES = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
  ];

  function toDateKey(date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  }

  function parseDateKey(key) {
    const [y, m, d] = key.split("-").map(Number);
    return new Date(y, m - 1, d);
  }

  function formatDayTitle(key) {
    const date = parseDateKey(key);
    const weekday = date.toLocaleDateString("ru-RU", { weekday: "long" });
    const day = date.getDate();
    const month = MONTH_NAMES[date.getMonth()];
    const year = date.getFullYear();
    return `${weekday.charAt(0).toUpperCase() + weekday.slice(1)}, ${day} ${month} ${year}`;
  }

  function appointmentsByDate(appointments) {
    const map = new Map();
    appointments.forEach((item) => {
      const key = item.appointment_date;
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(item);
    });
    map.forEach((items) => {
      items.sort((a, b) => String(a.appointment_time).localeCompare(String(b.appointment_time)));
    });
    return map;
  }

  function renderCalendarGrid() {
    if (!calendarGrid || !calendarMonthLabel) return;

    const year = calendarMonth.getFullYear();
    const month = calendarMonth.getMonth();
    calendarMonthLabel.textContent = `${MONTH_NAMES[month]} ${year}`;

    const firstDay = new Date(year, month, 1);
    const startOffset = (firstDay.getDay() + 6) % 7;
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const todayKey = toDateKey(new Date());
    const byDate = appointmentsByDate(calendarAppointments);

    calendarGrid.innerHTML = "";

    for (let i = 0; i < startOffset; i += 1) {
      const empty = document.createElement("div");
      empty.className = "cabinet-calendar__cell cabinet-calendar__cell--empty";
      empty.setAttribute("aria-hidden", "true");
      calendarGrid.appendChild(empty);
    }

    for (let day = 1; day <= daysInMonth; day += 1) {
      const date = new Date(year, month, day);
      const key = toDateKey(date);
      const count = byDate.get(key)?.length || 0;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "cabinet-calendar__cell";
      btn.dataset.date = key;
      btn.setAttribute("role", "gridcell");
      btn.setAttribute("aria-label", `${day} ${MONTH_NAMES[month]}, записей: ${count}`);
      if (key === todayKey) btn.classList.add("is-today");
      if (key === calendarSelectedDate) btn.classList.add("is-selected");
      if (count > 0) btn.classList.add("has-events");

      btn.innerHTML = `<span class="cabinet-calendar__day-num">${day}</span>${
        count > 0 ? `<span class="cabinet-calendar__dot" aria-hidden="true"></span>` : ""
      }`;
      btn.addEventListener("click", () => selectCalendarDay(key));
      calendarGrid.appendChild(btn);
    }
  }

  function renderCalendarDayList() {
    if (!calendarDayTitle || !calendarDayList) return;

    calendarDayTitle.textContent = formatDayTitle(calendarSelectedDate);
    const byDate = appointmentsByDate(calendarAppointments);
    const items = byDate.get(calendarSelectedDate) || [];

    if (!items.length) {
      calendarDayList.innerHTML =
        '<p class="cabinet-app__empty-inline">На этот день записей нет.</p>';
      return;
    }

    calendarDayList.innerHTML = items
      .map((item) => {
        const time = String(item.appointment_time).slice(0, 5);
        return `
          <article class="cabinet-calendar__event">
            <div class="cabinet-calendar__event-time">${time}</div>
            <div class="cabinet-calendar__event-body">
              <strong>${item.service_name}</strong>
              <span>${item.client_name} · ${item.client_phone}</span>
              <span class="cabinet__status cabinet__status--${item.status}">${statusLabel(item.status)}</span>
            </div>
          </article>`;
      })
      .join("");
  }

  function selectCalendarDay(key) {
    calendarSelectedDate = key;
    if (calendarDate) calendarDate.value = key;
    renderCalendarGrid();
    renderCalendarDayList();
  }

  async function loadCalendar() {
    if (!calendarGrid) return;
    calendarGrid.innerHTML = '<p class="cabinet__loading">Загрузка календаря…</p>';

    try {
      calendarAppointments = await apiFetch("/api/v1/company/appointments");
      calendarLoaded = true;
      renderCalendarGrid();
      renderCalendarDayList();
      if (calendarDate && !calendarDate.value) {
        calendarDate.value = calendarSelectedDate;
      }
    } catch (err) {
      calendarGrid.innerHTML = `<p class="cabinet__error">${err.message}</p>`;
    }
  }

  function shiftCalendarMonth(delta) {
    calendarMonth = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() + delta, 1);
    renderCalendarGrid();
  }

  async function loadBookings() {
    if (!bookingsList || !bookingsLoading) return;
    bookingsList.innerHTML = "";
    bookingsLoading.hidden = false;
    bookingsList.appendChild(bookingsLoading);

    try {
      const bookings = await apiFetch("/api/v1/company/appointments");
      bookingsLoading.remove();

      if (!bookings.length) {
        bookingsList.innerHTML =
          '<p class="cabinet__empty">Записей пока нет. Создайте через webhook или календарь.</p>';
        return;
      }

      bookings.forEach((b) => {
        const card = document.createElement("article");
        card.className = "cabinet__booking";
        const canAct = b.status !== "cancelled" && b.status !== "completed";
        card.innerHTML = `
          <div class="cabinet__booking-main">
            <span class="cabinet__booking-service">${b.service_name}</span>
            <span class="cabinet__booking-company">${b.client_name} · ${b.client_phone}</span>
            <span class="cabinet__booking-date">${formatDate(b.appointment_date, b.appointment_time)}</span>
          </div>
          <div class="cabinet__booking-meta">
            <span class="cabinet__status cabinet__status--${b.status}">${statusLabel(b.status)}</span>
            ${
              canAct
                ? `<button type="button" class="cabinet__confirm" data-id="${b.id}">Подтвердить</button>
                   <button type="button" class="cabinet__cancel" data-id="${b.id}">Отменить</button>`
                : ""
            }
          </div>`;
        bookingsList.appendChild(card);
      });

      bookingsList.querySelectorAll(".cabinet__cancel").forEach((btn) => {
        btn.addEventListener("click", () => updateBookingStatus(btn.dataset.id, "cancelled", btn));
      });
      bookingsList.querySelectorAll(".cabinet__confirm").forEach((btn) => {
        btn.addEventListener("click", () => updateBookingStatus(btn.dataset.id, "confirmed", btn));
      });
    } catch (err) {
      bookingsLoading.remove();
      bookingsList.innerHTML = `<p class="cabinet__error">${err.message}</p>`;
    }
  }

  async function updateBookingStatus(id, status, btn) {
    const label = status === "cancelled" ? "отменить" : "подтвердить";
    if (!confirm(`Вы уверены, что хотите ${label} эту запись?`)) return;
    btn.disabled = true;
    try {
      await apiFetch(`/api/v1/company/appointments/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      loadBookings();
      loadDashboardStats();
    } catch (err) {
      alert(err.message);
      btn.disabled = false;
    }
  }

  calendarPrevMonth?.addEventListener("click", () => shiftCalendarMonth(-1));
  calendarNextMonth?.addEventListener("click", () => shiftCalendarMonth(1));

  calendarCreateForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    showError(calendarCreateError, "");
    if (calendarCreateSuccess) calendarCreateSuccess.hidden = true;

    const submitBtn = calendarCreateForm.querySelector('button[type="submit"]');
    setButtonLoading(submitBtn, true, "Создание…");

    const formData = new FormData(calendarCreateForm);
    const payload = {
      full_name: String(formData.get("full_name") || "").trim(),
      phone: String(formData.get("phone") || "").trim(),
      service_name: String(formData.get("service_name") || "").trim(),
      appointment_date: String(formData.get("appointment_date") || ""),
      appointment_time: String(formData.get("appointment_time") || ""),
    };

    try {
      await apiFetch("/api/v1/company/appointments", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      calendarSelectedDate = payload.appointment_date;
      calendarMonth = parseDateKey(payload.appointment_date);
      calendarLoaded = false;
      await loadCalendar();
      loadDashboardStats();

      if (calendarCreateSuccess) calendarCreateSuccess.hidden = false;
      calendarCreateForm.querySelector("#calendarClientName")?.focus();
      calendarCreateForm.reset();
      if (calendarDate) calendarDate.value = calendarSelectedDate;
      if (calendarTime) calendarTime.value = payload.appointment_time;
    } catch (err) {
      showError(calendarCreateError, err.message);
    } finally {
      setButtonLoading(submitBtn, false);
    }
  });

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
