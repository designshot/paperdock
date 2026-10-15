"use strict";

// Apply before the stylesheet paints, including when browser storage is blocked.
(() => {
  const storageKey = "paperdock.theme";
  const valid = (value) => ["light", "dark", "system"].includes(value);
  const system = window.matchMedia("(prefers-color-scheme: dark)");
  let preference = "system";
  try {
    const saved = window.localStorage.getItem(storageKey);
    if (valid(saved)) preference = saved;
  } catch { /* An unavailable browser store must not prevent opening the app. */ }

  function apply() {
    const theme = preference === "system" ? (system.matches ? "dark" : "light") : preference;
    document.documentElement.dataset.theme = theme;
    document.documentElement.dataset.themePreference = preference;
    document.documentElement.style.colorScheme = theme;
    const chrome = document.querySelector('meta[name="theme-color"]');
    if (chrome) chrome.content = theme === "dark" ? "#101918" : "#f5f6f2";
    const select = document.getElementById("theme-select");
    if (select) select.value = preference;
  }

  function bind() {
    const select = document.getElementById("theme-select");
    if (!select) return;
    select.value = preference;
    select.addEventListener("change", () => {
      if (!valid(select.value)) return;
      preference = select.value;
      try { window.localStorage.setItem(storageKey, preference); } catch { /* Keep the current session usable. */ }
      apply();
    });
  }

  apply();
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind, { once: true });
  else bind();
  const systemChanged = () => { if (preference === "system") apply(); };
  if (system.addEventListener) system.addEventListener("change", systemChanged);
  else system.addListener(systemChanged);
  window.addEventListener("storage", (event) => {
    if (event.key !== storageKey && event.key !== null) return;
    preference = valid(event.newValue) ? event.newValue : "system";
    apply();
  });
})();
