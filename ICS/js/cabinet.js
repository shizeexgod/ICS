/**
 * Личный кабинет: анимированный оверлей с OTP-авторизацией и списком записей.
 * API: POST /api/v1/auth/login, POST /api/v1/auth/verify,
 *      GET /api/v1/bookings/my, POST /api/v1/bookings/:id/cancel
 */
(function initCabinet() {
  const TOKEN_KEY = "ics:auth_token";
  const USER_KEY = "ics:auth_user";

  const cabinet = document.getElementById("cabinet");
  const backdrop = document.getElementById("cabinetBackdrop");
  const openBtn = document.getElementById("openCabinet");
  const closeBtn = document.getElementById("closeCabinet");
  const stepRegister = document.getElementById("cabinetStepRegister");
  const stepVerify = document.getElementById("cabinetStepVerify");
  const stepDashboard = document.getElementById("cabinetStepDashboard");
  const registerForm = document.getElementById("registerForm");
  const verifyForm = document.getElementById("verifyForm");
  const registerError = document.getElementById("registerError");
  const verifyError = document.getElementById("verifyError");
  const verifyPhoneDisplay = document.getElementById("verifyPhoneDisplay");
  const verifyDevHint = document.getElementById("verifyDevHint");
  const backToRegister = document.getElementById("backToRegister");
  const logoutBtn = document.getElementById("cabinetLogout");
  const bookingsList = document.getElementById("bookingsList");
  const bookingsLoading = document.getElementById("bookingsLoading");
  const dashboardUserName = document.getElementById("dashboardUserName");
  const nav = document.getElementById("nav");

  let pendingPhone = "";
  let pendingName = "";

  function apiBase() {
    return (window.ICS_API_BASE || "").replace(/\/$/, "");
  }

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function setSession(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  function clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  function getStoredUser() {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY) || "null");
    } catch {
      return null;
    }
  }

  function showError(el, msg) {
    el.textContent = msg;
    el.hidden = !msg;
  }

  function showStep(step) {
    [stepRegister, stepVerify, stepDashboard].forEach((s) => {
      s.hidden = s !== step;
    });
  }

  function openCabinet() {
    document.body.classList.add("cabinet-open");
    cabinet.classList.add("is-open");
    cabinet.setAttribute("aria-hidden", "false");
    nav.classList.remove("open");

    const token = getToken();
    if (token) {
      showStep(stepDashboard);
      const user = getStoredUser();
      dashboardUserName.textContent = user?.name || "клиент";
      loadBookings();
    } else {
      showStep(stepRegister);
      registerForm.reset();
      showError(registerError, "");
    }
  }

  function closeCabinet() {
    document.body.classList.remove("cabinet-open");
    cabinet.classList.remove("is-open");
    cabinet.setAttribute("aria-hidden", "true");
  }

  async function apiFetch(path, options = {}) {
    const base = apiBase();
    if (!base) {
      throw new Error("API не настроен. Задайте ICS_API_BASE в Vercel или js/config.js.");
    }
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    const token = getToken();
    if (token && !headers.Authorization) {
      headers.Authorization = `Bearer ${token}`;
    }
    const res = await fetch(`${base}${path}`, { ...options, headers });
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
    pendingPhone = (fd.get("phone") || "").toString().trim();
    const btn = registerForm.querySelector("button[type=submit]");
    btn.disabled = true;

    try {
      const data = await apiFetch("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ phone: pendingPhone, name: pendingName }),
      });
      verifyPhoneDisplay.textContent = pendingPhone;
      if (data.dev_code && verifyDevHint) {
        verifyDevHint.textContent = `Режим разработки: код ${data.dev_code} (SMS не настроен)`;
        verifyDevHint.hidden = false;
      } else if (verifyDevHint) {
        verifyDevHint.hidden = true;
        verifyDevHint.textContent = "";
      }
      verifyForm.reset();
      showError(verifyError, "");
      showStep(stepVerify);
    } catch (err) {
      showError(registerError, err.message);
    } finally {
      btn.disabled = false;
    }
  });

  verifyForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    showError(verifyError, "");
    const code = new FormData(verifyForm).get("code").toString().trim();
    const btn = verifyForm.querySelector("button[type=submit]");
    btn.disabled = true;

    try {
      const data = await apiFetch("/api/v1/auth/verify", {
        method: "POST",
        body: JSON.stringify({ phone: pendingPhone, code }),
      });
      setSession(data.access_token, { name: data.name || pendingName, phone: pendingPhone });
      dashboardUserName.textContent = data.name || pendingName;
      showStep(stepDashboard);
      loadBookings();
    } catch (err) {
      showError(verifyError, err.message);
    } finally {
      btn.disabled = false;
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

  logoutBtn.addEventListener("click", () => {
    clearSession();
    showStep(stepRegister);
    registerForm.reset();
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
    bookingsList.innerHTML = "";
    bookingsLoading.hidden = false;
    bookingsList.appendChild(bookingsLoading);

    try {
      const bookings = await apiFetch("/api/v1/bookings/my");
      bookingsLoading.remove();

      if (!bookings.length) {
        bookingsList.innerHTML = '<p class="cabinet__empty">Активных записей пока нет.</p>';
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
            ${b.status !== "cancelled" && b.status !== "completed"
              ? `<button type="button" class="cabinet__cancel" data-id="${b.id}">Отменить</button>`
              : ""}
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
