(function applyLegalConfig() {
  const legal = window.ICS_LEGAL;
  if (!legal) return;

  document.querySelectorAll("[data-legal]").forEach((el) => {
    const key = el.dataset.legal;
    const value = legal[key];
    if (value !== undefined && value !== "") {
      el.textContent = value;
    }
  });

  const innEl = document.getElementById("footerInn");
  if (innEl && legal.inn) {
    innEl.textContent = `ИНН ${legal.inn}`;
    innEl.hidden = false;
  }

  const ownerEl = document.getElementById("footerOwner");
  if (ownerEl && legal.ownerName) {
    ownerEl.textContent = legal.ownerName;
    ownerEl.hidden = false;
  }
})();
