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
    settings: { eyebrow: "Настройки", title: "Настройки и подписка" },
    telegram: { eyebrow: "Интеграции", title: "Telegram" },
    templates: { eyebrow: "Контент", title: "Шаблоны уведомлений" },
  };

  const STAFF_BACKEND_HINT =
    "Раздел сотрудников недоступен на сервере. Выполните миграцию 010_company_staff.sql в Supabase, затем задеплойте бэкенд: git push amvera main:master";

  const cabinet = document.getElementById("cabinet");
  const cabinetPanel = document.getElementById("cabinetPanel");
  const backdrop = document.getElementById("cabinetBackdrop");
  const openBtn = document.getElementById("openCabinet");
  const closeBtn = document.getElementById("closeCabinet");
  const stepChoice = document.getElementById("cabinetStepChoice");
  const stepLogin = document.getElementById("cabinetStepLogin");
  const stepRegister = document.getElementById("cabinetStepRegister");
  const stepVerify = document.getElementById("cabinetStepVerify");
  const stepOnboarding = document.getElementById("cabinetStepOnboarding");
  const stepApp = document.getElementById("cabinetStepApp");
  const choiceLoginBtn = document.getElementById("choiceLoginBtn");
  const choiceRegisterBtn = document.getElementById("choiceRegisterBtn");
  const backToChoiceFromLogin = document.getElementById("backToChoiceFromLogin");
  const backToChoiceFromRegister = document.getElementById("backToChoiceFromRegister");
  const loginForm = document.getElementById("loginForm");
  const loginError = document.getElementById("loginError");
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
  const staffCreateForm = document.getElementById("staffCreateForm");
  const staffCreateError = document.getElementById("staffCreateError");
  const staffList = document.getElementById("staffList");
  const staffCountBadge = document.getElementById("staffCountBadge");
  const statAppointmentsToday = document.getElementById("statAppointmentsToday");
  const statActiveClients = document.getElementById("statActiveClients");
  const statRemindersWeek = document.getElementById("statRemindersWeek");
  const sidebarPlanBadge = document.getElementById("sidebarPlanBadge");
  const trialPlanNote = document.getElementById("trialPlanNote");
  const upgradeProBtnOverview = document.getElementById("upgradeProBtnOverview");
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
  const calendarDateField = document.getElementById("calendarDateField");
  const calendarTimeField = document.getElementById("calendarTimeField");
  const calendarDateTrigger = document.getElementById("calendarDateTrigger");
  const calendarDateTriggerText = document.getElementById("calendarDateTriggerText");
  const calendarDatePanel = document.getElementById("calendarDatePanel");
  const pickerMonthLabel = document.getElementById("pickerMonthLabel");
  const pickerPrevMonth = document.getElementById("pickerPrevMonth");
  const pickerNextMonth = document.getElementById("pickerNextMonth");
  const pickerDaysGrid = document.getElementById("pickerDaysGrid");
  const calendarTimeTrigger = document.getElementById("calendarTimeTrigger");
  const calendarTimeTriggerText = document.getElementById("calendarTimeTriggerText");
  const calendarTimePanel = document.getElementById("calendarTimePanel");
  const pickerHourList = document.getElementById("pickerHourList");
  const pickerMinuteList = document.getElementById("pickerMinuteList");
  const templatesList = document.getElementById("templatesList");
  const templatesLoading = document.getElementById("templatesLoading");
  const referralCode = document.getElementById("referralCode");
  const referralBalance = document.getElementById("referralBalance");
  const referralCountBadge = document.getElementById("referralCountBadge");

  let referralProgram = null;

  let pendingEmail = "";
  let pendingName = "";
  let pendingPhone = "";
  let pendingAuthStep = null; // stepLogin or stepRegister — куда вернуться из шага OTP
  let activeView = "overview";
  let calendarMonth = new Date();
  let calendarSelectedDate = toDateKey(new Date());
  let calendarAppointments = [];
  let calendarLoaded = false;
  let templatesLoaded = false;
  let pickerMonth = new Date();
  let pickerHour = null;
  let pickerMinute = null;

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
      "Payment provider is not configured. Contact support.":
        "Оплата не настроена на сервере. Добавьте YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY на Amvera.",
      "Company already has an active Pro subscription.":
        "У вас уже активна подписка Pro.",
      "Failed to create payment. Please try again later.":
        "Не удалось создать платёж. Попробуйте позже.",
      "Email already registered.":
        "Этот email уже зарегистрирован. Войдите с кодом из письма.",
      "Referral code not found.": "Промокод не найден.",
      "You cannot use your own referral code.": "Нельзя использовать свой промокод.",
      "Referral discount is only available on the first paid subscription.":
        "Скидка по промокоду доступна только при первой оплате подписки.",
      "Invalid referral code.": "Некорректный промокод.",
      "Failed to update template.": "Не удалось сохранить шаблон. Проверьте подключение к серверу.",
      "Failed to save template.": "Не удалось сохранить шаблон. Проверьте подключение к серверу.",
      "Not Found": STAFF_BACKEND_HINT,
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

  const PLAN_LABEL = { trial: "Trial", pro: "Pro", max: "Max" };
  const PERIOD_LABEL = { monthly: "1 месяц", semiannual: "6 месяцев", annual: "1 год" };
  const PLAN_PRICING = {
    pro: { monthly: 1290, semiannual: 6570, annual: 10900 },
    max: { monthly: 2490, semiannual: 12690, annual: 20900 },
  };

  let pendingPaymentPlan = null;
  let pendingPaymentPeriod = null;

  function formatPlanDate(iso) {
    if (!iso) return "";
    try {
      return new Date(iso).toLocaleDateString("ru-RU", {
        day: "numeric",
        month: "long",
        year: "numeric",
      });
    } catch {
      return "";
    }
  }

  function syncPlanUi(plan) {
    if (!plan) return;

    const isPaidActive =
      (plan.plan === "pro" || plan.plan === "max") && plan.subscription_status === "active";
    const activePlan = isPaidActive ? plan.plan : "trial";
    const days = plan.trial_days_left ?? 0;
    const remaining = plan.reminders_remaining ?? 0;

    if (sidebarPlanBadge) {
      sidebarPlanBadge.textContent = PLAN_LABEL[activePlan];
      sidebarPlanBadge.classList.toggle("cabinet-app__plan-badge--pro", activePlan !== "trial");
    }

    document.querySelectorAll("#cabinetStepApp .plan-card, #settingsPlans .plan-card").forEach((card) => {
      const planType = card.dataset.plan;
      const isActive = planType === activePlan;
      card.classList.toggle("is-active", isActive);

      const status = card.querySelector(".plan-card__status");
      if (status) {
        status.textContent = isActive ? "Активна" : "Неактивна";
        status.classList.toggle("plan-card__status--active", isActive);
        status.classList.toggle("plan-card__status--inactive", !isActive);
        status.hidden = false;
      }

      const expiryEl = card.querySelector(`[data-plan-expiry="${planType}"]`);
      if (expiryEl) {
        if (isActive && plan.subscription_ends_at) {
          expiryEl.textContent = `Активен до ${formatPlanDate(plan.subscription_ends_at)}`;
          expiryEl.hidden = false;
        } else {
          expiryEl.hidden = true;
        }
      }

      const cta = card.querySelector("[data-plan-cta]");
      if (cta && (planType === "pro" || planType === "max")) {
        cta.hidden = isActive;
        cta.textContent = "Оплатить";
        cta.onclick = (ev) => startPlanPayment(planType, ev);
      }
    });

    document.querySelectorAll(".plans-panel__frame").forEach((frame) => {
      if (typeof frame._syncPlanHighlight === "function") {
        frame._syncPlanHighlight();
      }
    });

    if (trialPlanNote) {
      if (activePlan !== "trial") {
        trialPlanNote.textContent = "";
        trialPlanNote.hidden = true;
      } else if (!plan.is_trial_active) {
        trialPlanNote.textContent = "Trial завершён.";
        trialPlanNote.hidden = false;
      } else if (!plan.can_send_reminders) {
        trialPlanNote.textContent = "Лимит напоминаний исчерпан.";
        trialPlanNote.hidden = false;
      } else {
        trialPlanNote.textContent = `Осталось ${days} дн. и ${remaining} напоминаний.`;
        trialPlanNote.hidden = false;
      }
    }
  }

  async function startPlanPayment(plan, ev) {
    const btn = ev?.currentTarget || document.querySelector(`[data-plan-cta="${plan}"]:not([hidden])`);
    const panel = btn?.closest("[data-plans-panel]");
    const billingPeriod = panel?.querySelector("[data-billing-toggle]")?.dataset.period || "monthly";

    pendingPaymentPlan = plan;
    pendingPaymentPeriod = billingPeriod;

    const prefillCode =
      referralProgram?.discount_available && referralProgram?.prefill_code
        ? referralProgram.prefill_code
        : "";

    showPaymentModal(plan, billingPeriod, prefillCode);
  }

  function showPaymentModal(plan, period, promoCode) {
    const modal = document.getElementById("paymentModal");
    const planEl = document.getElementById("paymentPlan");
    const periodEl = document.getElementById("paymentPeriod");
    const emailEl = document.getElementById("paymentEmail");
    const amountEl = document.getElementById("paymentAmount");
    const promoInputEl = document.getElementById("paymentPromoInput");
    const promoHintEl = document.getElementById("paymentPromoHint");
    const promoSection = document.getElementById("paymentPromoSection");

    if (!modal) return;

    const user = getStoredUser();
    const profile = getCompanyProfile();
    planEl.textContent = PLAN_LABEL[plan] || plan;
    periodEl.textContent = PERIOD_LABEL[period] || period;
    emailEl.textContent = profile?.ownerEmail || user?.email || "—";

    const baseAmount = PLAN_PRICING[plan]?.[period] || 0;
    amountEl.textContent = `${baseAmount.toLocaleString("ru-RU")} ₽`;
    amountEl.dataset.baseAmount = baseAmount;

    const showPromo = Boolean(referralProgram?.discount_available);
    if (promoSection) promoSection.hidden = !showPromo;

    if (promoInputEl) {
      promoInputEl.value = showPromo ? promoCode : "";
      promoHintEl.hidden = true;
      promoHintEl.textContent = "";
      promoHintEl.style.color = "";
      promoInputEl.oninput = () => {
        const code = promoInputEl.value.trim().toUpperCase();
        if (code) {
          previewModalPromo(code, plan, period, amountEl, promoHintEl);
        } else {
          amountEl.textContent = `${baseAmount.toLocaleString("ru-RU")} ₽`;
          promoHintEl.hidden = true;
        }
      };
    }

    modal.hidden = false;
    document.body.style.overflow = "hidden";

    if (showPromo && promoCode) {
      previewModalPromo(promoCode, plan, period, amountEl, promoHintEl);
    }
  }

  async function previewModalPromo(code, plan, period, amountEl, hintEl) {
    if (!code) {
      hintEl.hidden = true;
      return;
    }
    
    try {
      const data = await apiFetch("/api/v1/billing/validate-referral", {
        method: "POST",
        body: JSON.stringify({ referral_code: code, plan, billing_period: period }),
      });
      
      if (data.discount_rub > 0) {
        amountEl.textContent = `${data.final_amount_rub.toLocaleString("ru-RU")} ₽`;
        hintEl.textContent = `Промокод применён! Скидка: ${data.discount_rub.toLocaleString("ru-RU")} ₽`;
        hintEl.hidden = false;
        hintEl.style.color = "";
      } else {
        hintEl.hidden = true;
      }
    } catch (err) {
      hintEl.textContent = formatApiError(err.message);
      hintEl.hidden = false;
      hintEl.style.color = "var(--error, #ff6b6b)";
    }
  }

  function closePaymentModal() {
    const modal = document.getElementById("paymentModal");
    if (modal) {
      modal.hidden = true;
      document.body.style.overflow = "";
    }
  }

  async function confirmPaymentModal() {
    const confirmBtn = document.getElementById("paymentModalConfirm");
    const promoInput = document.getElementById("paymentPromoInput");
    
    if (!pendingPaymentPlan || !pendingPaymentPeriod) return;
    
    setButtonLoading(confirmBtn, true, "Переход к оплате…");
    const returnUrl = `${window.location.origin}${window.location.pathname}?billing=success`;
    const referralCodeValue = promoInput?.value.trim().toUpperCase() || null;
    
    try {
      const body = { 
        return_url: returnUrl, 
        plan: pendingPaymentPlan, 
        billing_period: pendingPaymentPeriod 
      };
      if (referralCodeValue) body.referral_code = referralCodeValue;
      
      const data = await apiFetch("/api/v1/billing/create-payment", {
        method: "POST",
        body: JSON.stringify(body),
      });
      
      window.location.href = data.confirmation_url;
    } catch (err) {
      alert(err.message);
      setButtonLoading(confirmBtn, false);
    }
  }

  // Payment modal event listeners
  const paymentModalClose = document.getElementById("paymentModalClose");
  const paymentModalCancel = document.getElementById("paymentModalCancel");
  const paymentModalConfirm = document.getElementById("paymentModalConfirm");
  
  if (paymentModalClose) paymentModalClose.addEventListener("click", closePaymentModal);
  if (paymentModalCancel) paymentModalCancel.addEventListener("click", closePaymentModal);
  if (paymentModalConfirm) paymentModalConfirm.addEventListener("click", confirmPaymentModal);
  
  const paymentModal = document.getElementById("paymentModal");
  if (paymentModal) {
    const overlay = paymentModal.querySelector(".payment-modal__overlay");
    if (overlay) overlay.addEventListener("click", closePaymentModal);
  }

  function syncPromoRows() {
    /* Промокод вводится только в модальном окне оплаты */
  }

  function syncReferralCard(program) {
    if (!program) return;
    if (referralCode) referralCode.textContent = program.code || "—";
    if (referralBalance) {
      referralBalance.textContent = `${(program.balance_rub ?? 0).toLocaleString("ru-RU")} ₽`;
    }
    if (referralCountBadge) {
      const count = program.referrals_count ?? 0;
      const n = Math.abs(count) % 100;
      const n1 = n % 10;
      let word = "приглашений";
      if (n < 10 || n > 20) {
        if (n1 === 1) word = "приглашение";
        else if (n1 >= 2 && n1 <= 4) word = "приглашения";
      }
      referralCountBadge.textContent = `${count} ${word}`;
    }
    syncPromoRows();
    loadReferralPurchases();
  }

  async function loadReferralPurchases() {
    const purchasesContainer = document.getElementById("referralPurchases");
    const purchasesList = document.getElementById("referralPurchasesList");
    if (!purchasesContainer || !purchasesList) return;

    try {
      const data = await apiFetch("/api/v1/billing/referral-purchases");
      if (!data || !data.purchases || data.purchases.length === 0) {
        purchasesContainer.hidden = true;
        return;
      }

      purchasesContainer.hidden = false;
      purchasesList.innerHTML = "";

      data.purchases.forEach((purchase) => {
        const item = document.createElement("div");
        item.className = "cabinet-referral__purchase";
        const date = new Date(purchase.created_at).toLocaleDateString("ru-RU");
        item.innerHTML = `
          <div class="cabinet-referral__purchase-info">
            <span class="cabinet-referral__purchase-name">${purchase.company_name || "Компания"}</span>
            <span class="cabinet-referral__purchase-meta">ID: ${purchase.company_id} · ${date}</span>
          </div>
          <span class="cabinet-referral__purchase-amount">+${purchase.reward_rub.toLocaleString("ru-RU")} ₽</span>
        `;
        purchasesList.appendChild(item);
      });
    } catch (err) {
      console.error("Failed to load referral purchases:", err);
      purchasesContainer.hidden = true;
    }
  }

  async function loadReferralProgram() {
    if (!getToken()) return;
    const urlRef = new URLSearchParams(window.location.search).get("ref");
    try {
      const data = await apiFetch("/api/v1/billing/referral");
      referralProgram = { ...data, prefill_code: urlRef ? urlRef.trim().toUpperCase() : null };
      syncReferralCard(referralProgram);
    } catch {
      referralProgram = urlRef ? { discount_available: true, prefill_code: urlRef.trim().toUpperCase() } : null;
      syncPromoRows();
    }
  }

  async function previewPromoCode(inputEl, hintEl, plan = "pro") {
    const code = inputEl?.value.trim().toUpperCase();
    if (!hintEl) return;
    if (!code) {
      hintEl.hidden = true;
      hintEl.textContent = "";
      return;
    }
    const panel = inputEl.closest("[data-plans-panel]");
    const billingPeriod = panel?.querySelector("[data-billing-toggle]")?.dataset.period || "monthly";
    try {
      const data = await apiFetch("/api/v1/billing/validate-referral", {
        method: "POST",
        body: JSON.stringify({ referral_code: code, plan, billing_period: billingPeriod }),
      });
      hintEl.textContent = `Скидка ${data.discount_percent}%: −${data.discount_rub.toLocaleString("ru-RU")} ₽, к оплате ${data.final_amount_rub.toLocaleString("ru-RU")} ₽`;
      hintEl.hidden = false;
      hintEl.classList.remove("cabinet-promo__hint--error");
    } catch (err) {
      hintEl.textContent = formatApiError(err.message);
      hintEl.hidden = false;
      hintEl.classList.add("cabinet-promo__hint--error");
    }
  }

  async function handleBillingReturn() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("billing") !== "success") return;

    const token = getToken();
    if (!token) return;

    try {
      await apiFetch("/api/v1/billing/status");
      const company = await loadCompanyProfile();
      if (company) syncCompanyUi(company);
      openCabinet();
      switchView("overview");
    } catch {
      /* webhook may still be processing */
    } finally {
      params.delete("billing");
      const clean = params.toString();
      const newUrl = `${window.location.pathname}${clean ? `?${clean}` : ""}${window.location.hash}`;
      window.history.replaceState({}, "", newUrl);
    }
  }

  async function loadDashboardStats() {
    if (!statAppointmentsToday) return;
    const statEls = [statAppointmentsToday, statActiveClients, statRemindersWeek];
    statEls.forEach((el) => el.classList.add("is-loading"));
    try {
      const stats = await apiFetch("/api/v1/company/stats");
      statAppointmentsToday.textContent = String(stats.appointments_today ?? 0);
      statActiveClients.textContent = String(stats.active_clients ?? 0);
      statRemindersWeek.textContent = String(stats.reminders_week ?? 0);
    } catch {
      statAppointmentsToday.textContent = "0";
      statActiveClients.textContent = "0";
      statRemindersWeek.textContent = "0";
    } finally {
      statEls.forEach((el) => el.classList.remove("is-loading"));
    }
  }

  const staffRolePicker = document.getElementById("staffRolePicker");
  const staffRoleInput = document.getElementById("staffRole");

  const ROLE_LABELS = {
    owner: "Владелец",
    director: "Директор",
    administrator: "Администратор",
    employee: "Сотрудник",
    manager: "Сотрудник",
    admin: "Администратор",
    receptionist: "Ресепшен",
  };

  function getRoleLabel(role) {
    return ROLE_LABELS[role] || role || "Сотрудник";
  }

  function getStaffInitials(name) {
    const parts = String(name || "")
      .trim()
      .split(/\s+/)
      .filter(Boolean);
    if (!parts.length) return "?";
    if (parts.length === 1) return parts[0].slice(0, 2);
    return `${parts[0][0] || ""}${parts[1][0] || ""}`;
  }

  function setStaffRole(role) {
    const value = role || "employee";
    if (staffRoleInput) staffRoleInput.value = value;
    staffRolePicker?.querySelectorAll(".cabinet-staff__role-btn").forEach((btn) => {
      const active = btn.dataset.role === value;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function initStaffRolePicker() {
    if (!staffRolePicker) return;
    staffRolePicker.querySelectorAll(".cabinet-staff__role-btn").forEach((btn) => {
      btn.addEventListener("click", () => setStaffRole(btn.dataset.role));
    });
    setStaffRole(staffRoleInput?.value || "employee");
  }

  function formatStaffMeta(staff) {
    const parts = [];
    if (staff.telegram_username) {
      parts.push(`@${staff.telegram_username}`);
    }
    if (staff.phone) {
      parts.push(staff.phone);
    }
    return parts.join(" · ") || "Telegram @username не указан";
  }

  function renderStaffList(staffItems) {
    if (!staffList) return;
    const active = staffItems.filter((s) => s.is_active);
    if (staffCountBadge) {
      staffCountBadge.textContent = String(active.length);
    }

    if (!active.length) {
      staffList.innerHTML = `
        <div class="cabinet-staff__empty">
          <p>Пока нет сотрудников. Добавьте первого — иначе бот примет любого с API-ключом.</p>
        </div>
      `;
      return;
    }

    staffList.innerHTML = active
      .map((staff) => {
        const connected = staff.is_connected;
        const statusClass = connected ? "is-connected" : "";
        const statusText = connected ? "Подключён" : "Ожидает";
        const role = staff.role || "employee";
        const roleClass = ["owner", "director", "administrator"].includes(role)
          ? ` cabinet-staff__role-badge--${role}`
          : "";
        return `
          <article class="cabinet-staff__item" data-staff-id="${staff.id}">
            <div class="cabinet-staff__avatar" aria-hidden="true">${getStaffInitials(staff.full_name)}</div>
            <div class="cabinet-staff__info">
              <div class="cabinet-staff__name-row">
                <span class="cabinet-staff__name">${staff.full_name}</span>
                <span class="cabinet-staff__role-badge${roleClass}">${getRoleLabel(role)}</span>
              </div>
              <span class="cabinet-staff__meta">${formatStaffMeta(staff)}</span>
            </div>
            <div class="cabinet-staff__aside">
              <span class="cabinet-staff__status ${statusClass}">${statusText}</span>
              <button type="button" class="btn btn--ghost" data-staff-delete="${staff.id}">Удалить</button>
            </div>
          </article>
        `;
      })
      .join("");

    staffList.querySelectorAll("[data-staff-delete]").forEach((btn) => {
      btn.addEventListener("click", () => deleteStaff(btn.dataset.staffDelete, btn));
    });
  }

  async function loadStaffList() {
    if (!staffList) return;
    try {
      const staffItems = await apiFetch("/api/v1/company/staff");
      renderStaffList(staffItems || []);
    } catch {
      if (staffCountBadge) staffCountBadge.textContent = "0";
      staffList.innerHTML = `
        <div class="cabinet-staff__empty">
          <p>${STAFF_BACKEND_HINT}</p>
        </div>
      `;
    }
  }

  async function deleteStaff(staffId, btn) {
    if (!staffId) return;
    if (!confirm("Удалить сотрудника из списка?")) return;
    setButtonLoading(btn, true, "Удаление…");
    try {
      await apiFetch(`/api/v1/company/staff/${staffId}`, { method: "DELETE" });
      await loadStaffList();
      await loadTelegramStatus();
    } catch (err) {
      alert(err.message);
      setButtonLoading(btn, false);
    }
  }

  function setTelegramStatusBadge(connected) {
    if (!telegramStatus) return;
    telegramStatus.textContent = connected ? "Подключено" : "Не подключено";
    telegramStatus.classList.remove("cabinet-app__badge--muted");
    telegramStatus.classList.toggle("cabinet-app__badge--ok", connected);
  }

  async function loadTelegramStatus() {
    if (!telegramStatus) return;
    try {
      const data = await apiFetch("/api/v1/company/telegram");
      setTelegramStatusBadge(Boolean(data.connected));

      const checklistItem = document.querySelector('#setupChecklist li[data-check="telegram"]');
      if (checklistItem) {
        checklistItem.classList.toggle("is-done", data.connected);
      }

      if (!telegramManagersList) return;
      if (!data.managers?.length) {
        telegramManagersList.innerHTML =
          '<p class="cabinet-app__empty-inline">Пока нет привязанных Telegram-чатов.</p>';
        return;
      }
      telegramManagersList.innerHTML = data.managers
        .map((m) => {
          const name = m.full_name || "Сотрудник";
          const username = m.telegram_username ? `@${m.telegram_username}` : "";
          const role = m.role ? getRoleLabel(m.role) : "";
          const meta = [username, role].filter(Boolean).join(" · ");
          return `<p class="cabinet-app__manager-item"><strong>${name}</strong>${meta ? ` — ${meta}` : ""}<br>Chat ID: <code>${m.tg_chat_id}</code></p>`;
        })
        .join("");
    } catch {
      setTelegramStatusBadge(false);
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
    const steps = [stepChoice, stepLogin, stepRegister, stepVerify, stepOnboarding, stepApp];
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
      loadReferralProgram();
    } else if (viewId === "telegram") {
      loadStaffList();
      loadTelegramStatus();
    } else if (viewId === "templates") {
      warmUpBackend();
      loadTemplates();
    } else if (viewId === "settings") {
      loadReferralProgram();
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
    loadReferralProgram();
    requestAnimationFrame(() => {
      document.querySelectorAll("[data-billing-toggle]").forEach((toggle) => {
        window.ICS?.syncBillingToggle?.(toggle);
      });
    });
  }

  function warmUpBackend() {
    const base = apiBase();
    if (!base) return;
    fetch(`${base}/health`, { method: "GET" }).catch(() => {});
  }

  async function openCabinet() {
    warmUpBackend();
    document.body.classList.add("cabinet-open");
    cabinet.classList.add("is-open");
    cabinet.setAttribute("aria-hidden", "false");
    nav.classList.remove("open");

    const token = getToken();
    if (!token) {
      showStep(stepChoice);
      registerForm.reset();
      loginForm.reset();
      showError(registerError, "");
      showError(loginError, "");
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

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async function fetchWithTimeout(url, options, timeoutMs) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      return await fetch(url, { ...options, signal: controller.signal });
    } finally {
      clearTimeout(timer);
    }
  }

  function clearAuthErrors() {
    [registerError, loginError, verifyError].forEach((el) => showError(el, ""));
  }

  let sendCodeInFlight = false;

  function connectionErrorMessage() {
    const base = apiBase() || "API";
    const origin = window.location.origin;
    return `Не удалось подключиться к ${base}. Проверьте, что бэкенд на Amvera запущен, и в CORS_ORIGINS указан ${origin}.`;
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

    const url = `${base}${path}`;
    let res;
    let lastErr;
    const delays = [0, 2200];
    for (let attempt = 0; attempt < delays.length; attempt++) {
      if (delays[attempt]) await sleep(delays[attempt]);
      try {
        if (attempt > 0) {
          await fetchWithTimeout(`${base}/health`, { method: "GET" }, 10000).catch(() => {});
        }
        res = await fetchWithTimeout(url, { ...options, headers }, 20000);
        lastErr = null;
        break;
      } catch (err) {
        lastErr = err;
      }
    }
    if (lastErr) {
      throw new Error(connectionErrorMessage());
    }

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = data.detail;
      const msg = Array.isArray(detail)
        ? detail.map((d) => d.msg || d).join(", ")
        : detail || data.message || "Ошибка сервера";
      throw new Error(formatApiError(msg));
    }
    return data;
  }

  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (sendCodeInFlight) return;
    clearAuthErrors();
    const fd = new FormData(registerForm);
    pendingName = (fd.get("name") || "").toString().trim();
    pendingEmail = (fd.get("email") || "").toString().trim().toLowerCase();
    pendingPhone = (fd.get("phone") || "").toString().trim();
    const btn = registerForm.querySelector("button[type=submit]");
    setButtonLoading(btn, true, "Отправка…");
    sendCodeInFlight = true;

    try {
      const payload = { email: pendingEmail, name: pendingName };
      if (pendingPhone) payload.phone = pendingPhone;

      const data = await apiFetch("/api/v1/auth/send-code", {
        method: "POST",
        body: JSON.stringify({ ...payload, intent: "register" }),
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
      pendingAuthStep = stepRegister;
      showStep(stepVerify);
    } catch (err) {
      const msg = formatApiError(err.message);
      if (msg.includes("уже зарегистрирован")) {
        loginForm.querySelector('input[name="email"]').value = pendingEmail;
        clearAuthErrors();
        showError(loginError, msg);
        showStep(stepLogin);
        return;
      }
      showError(registerError, msg);
    } finally {
      sendCodeInFlight = false;
      setButtonLoading(btn, false);
    }
  });

  choiceLoginBtn.addEventListener("click", () => {
    warmUpBackend();
    showError(loginError, "");
    loginForm.reset();
    showStep(stepLogin);
  });

  choiceRegisterBtn.addEventListener("click", () => {
    showError(registerError, "");
    registerForm.reset();
    showStep(stepRegister);
  });

  backToChoiceFromLogin.addEventListener("click", () => showStep(stepChoice));
  backToChoiceFromRegister.addEventListener("click", () => showStep(stepChoice));

  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (sendCodeInFlight) return;
    clearAuthErrors();
    const fd = new FormData(loginForm);
    pendingName = "";
    pendingEmail = (fd.get("email") || "").toString().trim().toLowerCase();
    pendingPhone = "";
    const btn = loginForm.querySelector("button[type=submit]");
    setButtonLoading(btn, true, "Отправка…");
    sendCodeInFlight = true;

    try {
      const data = await apiFetch("/api/v1/auth/send-code", {
        method: "POST",
        body: JSON.stringify({ email: pendingEmail, intent: "login" }),
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
      pendingAuthStep = stepLogin;
      showStep(stepVerify);
    } catch (err) {
      showError(loginError, formatApiError(err.message));
    } finally {
      sendCodeInFlight = false;
      setButtonLoading(btn, false);
    }
  });

  const verifyCodeInput = verifyForm.querySelector('input[name="code"]');
  if (verifyCodeInput) {
    verifyCodeInput.addEventListener("input", () => {
      const value = verifyCodeInput.value.trim();
      if (/^\d{4}$/.test(value) && !verifyForm.dataset.submitting) {
        verifyForm.requestSubmit();
      }
    });
  }

  verifyForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    showError(verifyError, "");
    const code = new FormData(verifyForm).get("code").toString().trim();
    if (!/^\d{4}$/.test(code)) return;
    const btn = verifyForm.querySelector("button[type=submit]");
    verifyForm.dataset.submitting = "1";
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
      delete verifyForm.dataset.submitting;
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
    showStep(pendingAuthStep || stepChoice);
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
    templatesLoaded = false;
    showStep(stepChoice);
    registerForm.reset();
    loginForm.reset();
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
    if (calendarDateTriggerText) calendarDateTriggerText.textContent = formatDateTriggerText(key);
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
        if (calendarDateTriggerText) {
          calendarDateTriggerText.textContent = formatDateTriggerText(calendarSelectedDate);
        }
      }
    } catch (err) {
      calendarGrid.innerHTML = `<p class="cabinet__error">${err.message}</p>`;
    }
  }

  function shiftCalendarMonth(delta) {
    calendarMonth = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() + delta, 1);
    renderCalendarGrid();
  }

  /* ============ Custom date/time field pickers ============ */
  function formatDateTriggerText(key) {
    if (!key) return "Выберите дату";
    const date = parseDateKey(key);
    return `${date.getDate()} ${MONTH_NAMES[date.getMonth()].toLowerCase()} ${date.getFullYear()}`;
  }

  function isInsideFieldPicker(el) {
    return Boolean(
      el?.closest?.(".field-picker__panel, .field-picker__time-list")
    );
  }

  function isFieldPickerControl(el) {
    return Boolean(el?.closest?.(".field-picker"));
  }

  function bindFieldPickerGuards() {
    [calendarDatePanel, calendarTimePanel, pickerHourList, pickerMinuteList].forEach((el) => {
      if (!el) return;
      el.addEventListener("mousedown", (e) => e.stopPropagation());
      el.addEventListener("wheel", (e) => e.stopPropagation(), { passive: true });
      el.addEventListener("scroll", (e) => e.stopPropagation(), true);
    });
  }

  function closeAllFieldPickers(except) {
    [calendarDateField, calendarTimeField].forEach((field) => {
      if (field && field !== except) field.classList.remove("is-open");
    });
    if (calendarDatePanel && calendarDateField !== except) calendarDatePanel.hidden = true;
    if (calendarTimePanel && calendarTimeField !== except) calendarTimePanel.hidden = true;
  }

  function positionFieldPanel(field, panel) {
    // The panel is position:fixed, but an ancestor (.cabinet__panel) has a
    // CSS transform, which makes it the containing block for fixed
    // descendants. Compute coordinates relative to that ancestor instead of
    // the raw viewport so the panel lands next to its trigger regardless.
    const anchor = field.closest(".cabinet__panel") || document.body;
    const anchorRect = anchor.getBoundingClientRect();
    const fieldRect = field.getBoundingClientRect();
    let top = fieldRect.bottom - anchorRect.top + 8;
    let left = fieldRect.left - anchorRect.left;
    panel.style.top = `${top}px`;
    panel.style.left = `${left}px`;
    panel.hidden = false;
    // Clamp horizontally so the panel doesn't run off the right edge.
    const panelRect = panel.getBoundingClientRect();
    const overflowRight = panelRect.right - anchorRect.right;
    if (overflowRight > 0) {
      left = Math.max(8, left - overflowRight - 8);
      panel.style.left = `${left}px`;
    }
    const overflowBottom = panelRect.bottom - anchorRect.bottom;
    if (overflowBottom > 0) {
      top = fieldRect.top - anchorRect.top - panelRect.height - 8;
      panel.style.top = `${Math.max(8, top)}px`;
    }
  }

  function toggleFieldPicker(field, panel) {
    const isOpen = field.classList.contains("is-open");
    closeAllFieldPickers();
    if (isOpen) return;
    field.classList.add("is-open");
    positionFieldPanel(field, panel);
  }

  function renderPickerDays() {
    if (!pickerDaysGrid || !pickerMonthLabel) return;
    const year = pickerMonth.getFullYear();
    const month = pickerMonth.getMonth();
    pickerMonthLabel.textContent = `${MONTH_NAMES[month]} ${year}`;

    const firstDay = new Date(year, month, 1);
    const startOffset = (firstDay.getDay() + 6) % 7;
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const todayKey = toDateKey(new Date());
    const selectedKey = calendarDate?.value || "";

    pickerDaysGrid.innerHTML = "";
    for (let i = 0; i < startOffset; i += 1) {
      const empty = document.createElement("span");
      empty.className = "field-picker__day-empty";
      pickerDaysGrid.appendChild(empty);
    }
    for (let day = 1; day <= daysInMonth; day += 1) {
      const key = toDateKey(new Date(year, month, day));
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = String(day);
      if (key === todayKey) btn.classList.add("is-today");
      if (key === selectedKey) btn.classList.add("is-selected");
      btn.addEventListener("click", () => {
        if (calendarDate) calendarDate.value = key;
        if (calendarDateTriggerText) calendarDateTriggerText.textContent = formatDateTriggerText(key);
        closeAllFieldPickers();
        calendarDateField?.classList.remove("is-open");
        if (calendarDatePanel) calendarDatePanel.hidden = true;
      });
      pickerDaysGrid.appendChild(btn);
    }
  }

  function shiftPickerMonth(delta) {
    pickerMonth = new Date(pickerMonth.getFullYear(), pickerMonth.getMonth() + delta, 1);
    renderPickerDays();
  }

  function syncTimeTriggerText() {
    if (!calendarTimeTriggerText) return;
    if (pickerHour == null) {
      calendarTimeTriggerText.textContent = "—:—";
      return;
    }
    const h = String(pickerHour).padStart(2, "0");
    const m = String(pickerMinute ?? 0).padStart(2, "0");
    calendarTimeTriggerText.textContent = `${h}:${m}`;
  }

  function commitTimeIfComplete() {
    if (pickerHour == null) return;
    const minute = pickerMinute ?? 0;
    const value = `${String(pickerHour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
    if (calendarTime) calendarTime.value = value;
    syncTimeTriggerText();
  }

  function initPickerTimeFromValue() {
    const current = calendarTime?.value || "";
    const [curH, curM] = current ? current.split(":").map(Number) : [null, null];
    pickerHour = Number.isFinite(curH) ? curH : null;
    pickerMinute = Number.isFinite(curM) ? curM : null;
  }

  function renderPickerTime() {
    if (!pickerHourList || !pickerMinuteList) return;

    pickerHourList.innerHTML = "";
    for (let h = 0; h < 24; h += 1) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = String(h).padStart(2, "0");
      if (h === pickerHour) btn.classList.add("is-selected");
      btn.addEventListener("click", () => {
        pickerHour = h;
        if (pickerMinute == null) pickerMinute = 0;
        renderPickerTime();
        commitTimeIfComplete();
      });
      pickerHourList.appendChild(btn);
    }

    pickerMinuteList.innerHTML = "";
    [0, 15, 30, 45].forEach((m) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = String(m).padStart(2, "0");
      if (m === pickerMinute) btn.classList.add("is-selected");
      btn.addEventListener("click", () => {
        pickerMinute = m;
        renderPickerTime();
        commitTimeIfComplete();
        closeAllFieldPickers();
        calendarTimeField?.classList.remove("is-open");
        if (calendarTimePanel) calendarTimePanel.hidden = true;
      });
      pickerMinuteList.appendChild(btn);
    });

    syncTimeTriggerText();
  }

  calendarDateTrigger?.addEventListener("click", (e) => {
    e.stopPropagation();
    if (calendarDate?.value) pickerMonth = parseDateKey(calendarDate.value);
    renderPickerDays();
    toggleFieldPicker(calendarDateField, calendarDatePanel);
  });
  calendarTimeTrigger?.addEventListener("click", (e) => {
    e.stopPropagation();
    initPickerTimeFromValue();
    renderPickerTime();
    toggleFieldPicker(calendarTimeField, calendarTimePanel);
  });
  pickerPrevMonth?.addEventListener("click", (e) => { e.stopPropagation(); shiftPickerMonth(-1); });
  pickerNextMonth?.addEventListener("click", (e) => { e.stopPropagation(); shiftPickerMonth(1); });
  calendarDatePanel?.addEventListener("click", (e) => e.stopPropagation());
  calendarTimePanel?.addEventListener("click", (e) => e.stopPropagation());
  bindFieldPickerGuards();
  document.addEventListener("click", (e) => {
    if (isFieldPickerControl(e.target)) return;
    closeAllFieldPickers();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeAllFieldPickers();
  });
  document.addEventListener("scroll", (e) => {
    if (isInsideFieldPicker(e.target)) return;
    closeAllFieldPickers();
  }, true);

  let bookingsLoadSeq = 0;
  const ACTIVE_BOOKING_STATUSES = new Set(["pending", "confirmed"]);

  function dedupeBookings(rows) {
    const seen = new Set();
    return rows.filter((row) => {
      const id = String(row.id);
      if (seen.has(id)) return false;
      seen.add(id);
      return true;
    });
  }

  function clearBookingsListContent() {
    if (!bookingsList) return;
    bookingsList.querySelectorAll(".cabinet__booking, .cabinet__empty, .cabinet__error").forEach((el) => {
      el.remove();
    });
  }

  async function loadBookings() {
    if (!bookingsList || !bookingsLoading) return;
    const seq = ++bookingsLoadSeq;

    clearBookingsListContent();
    bookingsLoading.hidden = false;
    if (!bookingsList.contains(bookingsLoading)) {
      bookingsList.appendChild(bookingsLoading);
    }

    try {
      const rows = await apiFetch("/api/v1/company/appointments");
      if (seq !== bookingsLoadSeq) return;

      bookingsLoading.hidden = true;

      const bookings = dedupeBookings(rows).filter((b) => ACTIVE_BOOKING_STATUSES.has(b.status));

      if (!bookings.length) {
        const empty = document.createElement("p");
        empty.className = "cabinet__empty";
        empty.textContent = "Активных записей пока нет. Создайте через webhook или календарь.";
        bookingsList.appendChild(empty);
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
      if (seq !== bookingsLoadSeq) return;
      bookingsLoading.hidden = true;
      clearBookingsListContent();
      const error = document.createElement("p");
      error.className = "cabinet__error";
      error.textContent = err.message;
      bookingsList.appendChild(error);
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

  const TEMPLATE_GROUPS = {
    client: {
      label: "Для клиента",
      hint: "Сообщения клиентам в WhatsApp / SMS",
      order: 1,
    },
    telegram: {
      label: "Для сотрудников",
      hint: "Уведомления администраторам в Telegram",
      order: 2,
    },
  };

  const PLACEHOLDER_LABELS = {
    client_name: "имя клиента",
    company_name: "название компании",
    service_name: "услуга",
    appointment_date: "дата записи",
    appointment_time: "время записи",
    client_phone: "телефон клиента",
  };

  function buildPlaceholderLegend(usedKeys) {
    const legend = document.createElement("aside");
    legend.className = "cabinet-app__template-legend";
    legend.innerHTML = '<p class="cabinet-app__template-legend-title">Обозначения плейсхолдеров</p>';

    const list = document.createElement("ul");
    list.className = "cabinet-app__template-legend-list";

    usedKeys.forEach((key) => {
      const item = document.createElement("li");
      const code = document.createElement("code");
      code.textContent = `{${key}}`;
      const label = document.createElement("span");
      label.textContent = PLACEHOLDER_LABELS[key] || key;
      item.append(code, label);
      list.appendChild(item);
    });

    legend.appendChild(list);
    return legend;
  }

  function channelLabel(channel) {
    return channel === "telegram" ? "Telegram" : "Клиент";
  }

  function buildTemplateCard(tpl) {
    const card = document.createElement("article");
    card.className = "cabinet-app__template-editor";
    card.dataset.eventType = tpl.event_type;

    const head = document.createElement("div");
    head.className = "cabinet-app__template-editor-head";
    head.innerHTML = `
      <div>
        <h3></h3>
        <p></p>
      </div>
      <div class="cabinet-app__template-editor-meta">
        <span class="cabinet-app__template-channel"></span>
        <label class="cabinet-app__toggle">
          <input type="checkbox" class="cabinet-app__toggle-input" data-field="is_enabled">
          <span>Вкл.</span>
        </label>
      </div>`;
    head.querySelector("h3").textContent = tpl.title;
    head.querySelector("p").textContent = tpl.description;
    const channelBadge = head.querySelector(".cabinet-app__template-channel");
    channelBadge.textContent = channelLabel(tpl.channel);
    channelBadge.classList.add(
      tpl.channel === "telegram"
        ? "cabinet-app__template-channel--telegram"
        : "cabinet-app__template-channel--client"
    );
    head.querySelector('[data-field="is_enabled"]').checked = !!tpl.is_enabled;

    const textarea = document.createElement("textarea");
    textarea.className = "cabinet-app__template-text";
    textarea.rows = 5;
    textarea.dataset.field = "tg_template";
    textarea.value = tpl.tg_template;

    const actions = document.createElement("div");
    actions.className = "cabinet-app__template-actions";
    const saveBtn = document.createElement("button");
    saveBtn.type = "button";
    saveBtn.className = "btn btn--primary cabinet-app__template-save";
    saveBtn.dataset.eventType = tpl.event_type;
    saveBtn.textContent = "Сохранить";
    const savedEl = document.createElement("span");
    savedEl.className = "cabinet-app__saved cabinet-app__template-saved";
    savedEl.hidden = true;
    savedEl.textContent = "Сохранено";
    actions.append(saveBtn, savedEl);

    card.append(head, textarea, actions);
    return card;
  }

  function renderTemplateGroups(templates) {
    templatesList.innerHTML = "";
    const grouped = { client: [], telegram: [] };
    const usedPlaceholderKeys = new Set();

    templates.forEach((tpl) => {
      const key = tpl.channel === "telegram" ? "telegram" : "client";
      grouped[key].push(tpl);
      (tpl.placeholders || []).forEach((p) => usedPlaceholderKeys.add(p));
    });

    Object.entries(TEMPLATE_GROUPS)
      .sort((a, b) => a[1].order - b[1].order)
      .forEach(([channel, meta]) => {
        const items = grouped[channel];
        if (!items?.length) return;

        const section = document.createElement("section");
        section.className = "cabinet-app__template-group";
        section.dataset.channel = channel;

        const head = document.createElement("header");
        head.className = "cabinet-app__template-group-head";
        head.innerHTML = `<h3></h3><p></p>`;
        head.querySelector("h3").textContent = meta.label;
        head.querySelector("p").textContent = meta.hint;

        const list = document.createElement("div");
        list.className = "cabinet-app__template-group-list";
        items.forEach((tpl) => list.appendChild(buildTemplateCard(tpl)));

        section.append(head, list);
        templatesList.appendChild(section);
      });

    if (usedPlaceholderKeys.size) {
      const order = Object.keys(PLACEHOLDER_LABELS);
      const sortedKeys = [...usedPlaceholderKeys].sort(
        (a, b) => order.indexOf(a) - order.indexOf(b)
      );
      templatesList.appendChild(buildPlaceholderLegend(sortedKeys));
    }

    templatesList.querySelectorAll(".cabinet-app__template-save").forEach((btn) => {
      btn.addEventListener("click", () => saveTemplate(btn.dataset.eventType, btn));
    });
  }

  async function loadTemplates() {
    if (!templatesList || !templatesLoading) return;
    templatesList.innerHTML = "";
    templatesLoading.hidden = false;
    templatesList.appendChild(templatesLoading);

    try {
      const data = await apiFetch("/api/v1/templates");
      templatesLoading.remove();
      const templates = data.templates || [];
      templatesLoaded = true;

      document
        .querySelector('#setupChecklist li[data-check="templates"]')
        ?.classList.add("is-done");

      if (!templates.length) {
        templatesList.innerHTML =
          '<p class="cabinet__empty">Шаблоны не найдены. Обновите бэкенд на Amvera.</p>';
        return;
      }

      renderTemplateGroups(templates);
    } catch (err) {
      templatesLoading.remove();
      templatesList.innerHTML = `<p class="cabinet__error">${formatApiError(err.message)}</p>`;
    }
  }

  async function saveTemplate(eventType, btn) {
    const card = templatesList.querySelector(`[data-event-type="${eventType}"]`);
    if (!card) return;

    const tgTemplate = card.querySelector('[data-field="tg_template"]')?.value?.trim();
    const isEnabled = card.querySelector('[data-field="is_enabled"]')?.checked ?? true;
    const savedEl = card.querySelector(".cabinet-app__template-saved");

    if (!tgTemplate) {
      alert("Текст шаблона не может быть пустым.");
      return;
    }

    btn.disabled = true;
    warmUpBackend();
    try {
      await apiFetch(`/api/v1/templates/${eventType}`, {
        method: "PATCH",
        body: JSON.stringify({
          tg_template: tgTemplate,
          is_enabled: isEnabled,
        }),
      });
      if (savedEl) {
        savedEl.classList.remove("is-error");
        savedEl.textContent = "Сохранено";
        savedEl.hidden = false;
        setTimeout(() => {
          savedEl.hidden = true;
        }, 2000);
      }
      document
        .querySelector('#setupChecklist li[data-check="templates"]')
        ?.classList.add("is-done");
    } catch (err) {
      if (savedEl) {
        savedEl.classList.add("is-error");
        savedEl.textContent = `${formatApiError(err.message)} Попробуйте ещё раз.`;
        savedEl.hidden = false;
      } else {
        alert(err.message);
      }
    } finally {
      btn.disabled = false;
    }
  }

  staffCreateForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    showError(staffCreateError, "");
    const submitBtn = staffCreateForm.querySelector('button[type="submit"]');
    setButtonLoading(submitBtn, true, "Добавление…");

    const formData = new FormData(staffCreateForm);
    const payload = {
      full_name: String(formData.get("full_name") || "").trim(),
      telegram_username: String(formData.get("telegram_username") || "").trim() || null,
      phone: String(formData.get("phone") || "").trim() || null,
      role: String(formData.get("role") || "employee"),
    };

    try {
      await apiFetch("/api/v1/company/staff", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      staffCreateForm.reset();
      setStaffRole("employee");
      await loadStaffList();
      await loadTelegramStatus();
    } catch (err) {
      showError(staffCreateError, formatApiError(err.message));
    } finally {
      setButtonLoading(submitBtn, false);
    }
  });

  initStaffRolePicker();

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

    if (!payload.appointment_date || !payload.appointment_time) {
      showError(calendarCreateError, "Выберите дату и время записи.");
      setButtonLoading(submitBtn, false);
      return;
    }

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
      if (calendarDateTriggerText) {
        calendarDateTriggerText.textContent = formatDateTriggerText(calendarSelectedDate);
      }
      if (calendarTimeTriggerText) {
        calendarTimeTriggerText.textContent = payload.appointment_time || "—:—";
      }
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

  handleBillingReturn();

  ["landingProBtn", "landingMaxBtn"].forEach((id) => {
    document.getElementById(id)?.addEventListener("click", () => {
      document.getElementById("openCabinet")?.click();
    });
  });

  function initPlansPanels() {
    document.querySelectorAll(".plans-panel__frame").forEach((frame) => {
      if (frame.dataset.plansBound) return;
      frame.dataset.plansBound = "1";

      const highlight = document.createElement("div");
      highlight.className = "plans-panel__highlight";
      highlight.setAttribute("aria-hidden", "true");
      frame.prepend(highlight);

      const cards = [...frame.querySelectorAll(".plan-card")];
      if (!cards.length) return;

      function planTone(card) {
        const plan = card?.dataset.plan;
        return plan === "pro" || plan === "max" ? plan : "trial";
      }

      function positionHighlight(card, tone = "trial") {
        if (!card) {
          frame.classList.remove("is-highlight-ready", "is-highlight-pro", "is-highlight-max");
          return;
        }
        const y = card.offsetTop;
        const h = card.offsetHeight;
        highlight.style.transform = `translateY(${y}px)`;
        highlight.style.height = `${h}px`;
        frame.classList.toggle("is-highlight-pro", tone === "pro");
        frame.classList.toggle("is-highlight-max", tone === "max");
        frame.classList.add("is-highlight-ready");
      }

      function activeCard() {
        return frame.querySelector(".plan-card.is-active") || cards[0];
      }

      function syncHighlight() {
        const card = activeCard();
        positionHighlight(card, planTone(card));
      }

      function previewCard(card) {
        cards.forEach((c) => c.classList.remove("is-preview"));
        card.classList.add("is-preview");
        positionHighlight(card, planTone(card));
      }

      cards.forEach((card) => {
        card.addEventListener("mouseenter", () => previewCard(card));
        card.addEventListener("focusin", () => previewCard(card));
        card.addEventListener("mouseleave", () => {
          card.classList.remove("is-preview");
          syncHighlight();
        });
        card.addEventListener("focusout", () => {
          card.classList.remove("is-preview");
          syncHighlight();
        });
      });

      frame._syncPlanHighlight = syncHighlight;

      const resizeObserver = new ResizeObserver(() => syncHighlight());
      resizeObserver.observe(frame);
      cards.forEach((card) => resizeObserver.observe(card));

      requestAnimationFrame(syncHighlight);
    });
  }

  initPlansPanels();
})();
