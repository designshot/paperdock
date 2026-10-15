"use strict";

(() => {
  const $ = (id) => document.getElementById(id);
  const paths = {
    layers: '<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5"/>',
    folder: '<path d="M3 7V5a1 1 0 0 1 1-1h5l2 3h9a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7Z"/><path d="M3 9h18"/>',
    settings: '<path d="m9 3-.7 2.2-2.2 1L4 5.7 2 9l1.7 1.7v2.6L2 15l2 3.3 2.1-.5 2.2 1L9 21h4l.7-2.2 2.2-1 2.1.5 2-3.3-1.7-1.7v-2.6L20 9l-2-3.3-2.1.5-2.2-1L13 3H9Z"/><circle cx="11" cy="12" r="3"/>',
    shield: '<path d="m12 3 8 3v6c0 4-4 7-8 9-4-2-8-5-8-9V6l8-3Z"/><path d="m8 12 3 3 5-6"/>',
    lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/>',
    "arrow-up-right": '<path d="M6 18 18 6M6 6h12v12"/>',
    "arrow-right": '<path d="M4 12h16m-6-6 6 6-6 6"/>',
    scan: '<path d="M7 3H4a1 1 0 0 0-1 1v3M17 3h3a1 1 0 0 1 1 1v3M21 17v3a1 1 0 0 1-1 1h-3M7 21H4a1 1 0 0 1-1-1v-3M3 12h18"/><path d="M7 8h10M7 16h10"/>',
    sparkles: '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3ZM20 2v4M18 4h4"/>',
    inbox: '<path d="m5 4-3 9v6a1 1 0 0 0 1 1h18a1 1 0 0 0 1-1v-6l-3-9H5Z"/><path d="M2 13h5l2 3h6l2-3h5"/>',
    scanner: '<path d="M4 10 7 3h10l3 7M5 10h14a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-6a2 2 0 0 1 2-2Z"/><path d="M7 15h7M17 15h.01"/>',
    file: '<path d="M13 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V9l-6-6Z"/><path d="M13 3v6h6M9 13h6M9 17h4"/>',
    leaf: '<path d="M20 3c-7 0-13 2-15 7-2 4 0 8 4 8 7 1 11-6 11-15Z"/><path d="M4 21c2-6 6-10 11-13"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    rotate: '<path d="M3 9h5V4M3 9a9 9 0 1 1 0 7"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    minus: '<path d="M5 12h14"/>',
    trash: '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',
    "chevron-left": '<path d="m15 5-7 7 7 7"/>',
    "chevron-right": '<path d="m9 5 7 7-7 7"/>',
    sliders: '<path d="M4 4v7M4 15v5M12 4v3M12 11v9M20 4v11M20 19v1M1 11h6M9 7h6M17 15h6"/>',
    refresh: '<path d="M20 4v5h-5M4 20v-5h5M20 9a8 8 0 0 0-14-4M4 15a8 8 0 0 0 14 4"/>',
    "file-check": '<path d="M13 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V9l-6-6Z"/><path d="M13 3v6h6m-11 6 3 3 5-6"/>',
    download: '<path d="M12 3v12m-5-5 5 5 5-5M4 16v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4"/>',
    upload: '<path d="M12 16V4m-5 5 5-5 5 5M4 16v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4"/>',
    x: '<path d="m6 6 12 12M6 18 18 6"/>',
    eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    plug: '<path d="M8 3v5M16 3v5M5 8h14M7 8v4a5 5 0 0 0 10 0V8M12 17v5"/>',
    wifi: '<path d="M3 8a15 15 0 0 1 18 0M6 12a10 10 0 0 1 12 0M9 16a5 5 0 0 1 6 0"/><circle cx="12" cy="20" r=".7" fill="currentColor"/>',
    alert: '<path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v5M12 17h.01"/>',
    photo: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8" cy="8" r="1.5"/><path d="m3 17 5-5 4 4 4-6 5 7"/>',
    receipt: '<path d="M5 3 8 5l4-2 4 2 3-2v18l-3-2-4 2-4-2-3 2V3Z"/><path d="M9 9h6M9 13h6M9 17h3"/>'
  };
  function icon(name) {
    const span = document.createElement("span");
    span.setAttribute("data-icon", name);
    span.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (paths[name] || paths.file) + "</svg>";
    return span;
  }
  document.querySelectorAll("[data-icon]").forEach((el) => el.replaceChildren(...icon(el.dataset.icon).childNodes));
  const state = { token: "", data: null, devices: [], selectedJob: null, selectedPage: null, titleJobId: null, titleDirty: false, profile: null, options: null, optionsLoading: false, paperSizeChoices: new Map(), busy: new Set(), zoom: 1, poll: null, connected: false, imageRevision: 0, metadataLoaded: false, signature: "", deviceRequest: 0 };
  const running = (job) => job && ["queued", "scanning", "processing", "orienting", "exporting", "uploading"].includes(job.status);
  const selectedJob = () => state.data?.jobs?.find((job) => job.id === state.selectedJob) || null;
  const pagesOf = (job) => Array.isArray(job?.pages) ? job.pages : [];
  const locked = (job) => running(job) || !!(job?.paperless && !["failed", "error", "failure"].includes(String(job.paperless.status).toLowerCase()));
  const statusNames = { queued: "Wartet", scanning: "Wird gescannt", processing: "Wird verarbeitet", orienting: "Wird ausgerichtet", ready: "Bereit", completed: "Bereit", done: "Bereit", error: "Fehler", cancelled: "Abgebrochen", exporting: "PDF entsteht", uploading: "Wird übertragen" };
  const modeNames = { color: "Farbe", colour: "Farbe", gray: "Graustufen", grey: "Graustufen", grayscale: "Graustufen", lineart: "Schwarzweiß", binary: "Schwarzweiß" };
  const orientationWarnings = new Set(["uncertain", "unavailable", "timeout", "invalid", "error"]);
  const orientationAvailable = () => !!state.data?.system?.orientation;
  const preferences = () => ({ auto_orient: true, naming_template: "Scan_{date}_{time}", ...state.data?.preferences });
  const settingsTabs = ["general", "paperless", "wifi"];
  const settingsPanels = { general: "preferences-form", paperless: "paperless-form", wifi: "wifi-form" };
  const scannerBusy = () => state.optionsLoading || ["scan", "orient", "devices"].some((key) => state.busy.has(key)) || !!state.data?.jobs?.some(running);
  function sampleName(template) {
    const now = new Date();
    const pad = (value) => String(value).padStart(2, "0");
    const values = { date: `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`, time: `${pad(now.getHours())}-${pad(now.getMinutes())}-${pad(now.getSeconds())}`, counter: "001" };
    return template.replace(/\{(date|time|counter)\}/g, (_, key) => values[key]);
  }

  async function api(path, body) {
    let response;
    try { response = await fetch(path, { method: body === undefined ? "GET" : "POST", headers: { "X-Paperdock-Token": state.token, ...(body === undefined ? {} : { "Content-Type": "application/json" }) }, body: body === undefined ? undefined : JSON.stringify(body), cache: "no-store" }); }
    catch { throw new Error("Die lokale Anwendung ist nicht erreichbar. Bitte PaperDock starten und die Seite neu laden."); }
    const data = await response.json().catch(() => ({ error: "Die Anwendung hat eine unerwartete Antwort gesendet." }));
    if (!response.ok) throw new Error(data.error || `Die Anfrage konnte nicht abgeschlossen werden (${response.status}).`);
    return data;
  }
  function node(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
  }
  function toast(message, error = false) {
    const el = node("div", "toast" + (error ? " error" : ""));
    el.append(icon(error ? "alert" : "check"), node("span", "", message));
    const close = node("button", "toast-close"); close.type = "button"; close.setAttribute("aria-label", "Meldung schließen"); close.append(icon("x")); close.onclick = () => el.remove(); el.append(close);
    $("toasts").append(el); setTimeout(() => el.remove(), error ? 14000 : 6000);
  }
  async function action(key, fn) {
    if (state.busy.has(key)) return;
    state.busy.add(key); renderControls();
    try { return await fn(); } catch (error) { toast(error.message, true); }
    finally { state.busy.delete(key); renderControls(); }
  }
  function safeUrl(value) {
    try { const url = new URL(value, location.origin); return url.origin === location.origin && url.protocol === location.protocol ? url.href : ""; } catch { return ""; }
  }
  function dateText(value) {
    if (!value) return "Heute";
    const date = new Date(typeof value === "number" && value < 1e12 ? value * 1000 : value);
    if (Number.isNaN(date.getTime())) return "";
    const today = new Date();
    return date.toDateString() === today.toDateString() ? date.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" }) : date.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" });
  }
  function selectJob(id) {
    state.selectedJob = id; state.selectedPage = pagesOf(selectedJob())[0]?.id || null; state.zoom = 1;
    state.titleJobId = null; state.titleDirty = false;
    render();
  }
  async function refreshState() {
    const data = await api("/api/state");
    const reconnected = !state.connected; state.connected = true;
    const signature = JSON.stringify(data);
    const initial = !state.data;
    state.data = data;
    if (!data.jobs?.some((job) => job.id === state.selectedJob)) {
      state.selectedJob = data.active_job_id || data.jobs?.[0]?.id || null;
      state.titleJobId = null; state.titleDirty = false;
    }
    if (initial || reconnected || signature !== state.signature) { state.signature = signature; render(); }
    if (initial && data.warning) toast(data.warning, true);
    renderControls(); schedulePoll();
    return data;
  }
  function schedulePoll() {
    clearTimeout(state.poll);
    if (state.data?.jobs?.some(running)) state.poll = setTimeout(() => refreshState().catch((error) => {
      state.connected = false; $("runtime-status").textContent = "Lokale Verbindung unterbrochen · neuer Versuch in 5 Sekunden";
      state.poll = setTimeout(() => refreshState().catch(() => { toast(error.message, true); renderControls(); }), 5000);
      renderControls();
    }), 1100);
  }
  function render() {
    renderJobs(); renderProfiles(); renderPaperless(); renderPreferences(); renderWifi(); renderPreview(); renderControls();
    const system = state.data?.system || {};
    $("runtime-status").textContent = `v${state.data?.version || "0.2.1"} · ${system.scanimage ? "SANE bereit" : "SANE nicht verfügbar"} · ${system.pillow === false ? "PDF-Modul nicht verfügbar" : "Lokal verbunden"}`;
  }
  function renderPreferences() {
    const preview = state.data?.name_preview || sampleName(preferences().naming_template);
    $("document-title").placeholder = preview;
    $("next-name-hint").textContent = `Leer lassen für einen automatischen Namen, z. B. ${preview}.`;
    $("auto-orient-summary").textContent = !orientationAvailable()
      ? "Automatisches Ausrichten ist noch nicht verfügbar. Die lokale Orientierungserkennung muss installiert sein. Manuelles Drehen bleibt möglich."
      : preferences().auto_orient ? "Neue Scans werden automatisch ausgerichtet. Unsichere Seiten bleiben unverändert und erhalten einen Hinweis." : "Automatisches Ausrichten ist ausgeschaltet. Du kannst einzelne Seiten weiterhin in der Vorschau ausrichten.";
  }
  function renderWifi() {
    const wifi = state.data?.wifi;
    $("wifi-setup-notice").hidden = !wifi;
    const title = !wifi ? "WLAN-Status nicht verfügbar" : !wifi.available ? "WLAN hier nicht einrichtbar" : wifi.configured ? "WLAN-Adresse gespeichert" : "Deine WLAN-Adresse fehlt noch";
    const description = !wifi ? "Die Anwendung stellt die WLAN-Einrichtung noch nicht bereit." : !wifi.available ? wifi.message || "Für WLAN wird eine PaperDock-Installation mit zusätzlichem ScanSnap-Treiber benötigt." : wifi.configured ? `Gespeichert: ${wifi.address}. Die Gerätesuche prüft, ob dein Scanner erreichbar ist.` : "Der WLAN-Treiber ist bereit. Trage die IP-Adresse deines Scanners ein, damit PaperDock ihn finden kann.";
    $("wifi-setup-title").textContent = title;
    $("wifi-setup-description").textContent = description;
    $("wifi-status-title").textContent = title;
    $("wifi-status-description").textContent = description;
    $("wifi-setup-notice").classList.toggle("needs-setup", !!wifi?.available && !wifi.configured);
    $("wifi-connection-status").classList.toggle("unavailable", !wifi?.available);
    $("setup-wifi").replaceChildren(document.createTextNode(!wifi?.available ? "WLAN-Details ansehen " : wifi.configured ? "WLAN-Adresse ändern " : "WLAN einrichten "), icon("arrow-right"));
  }
  function compatibilityText() {
    if (isWirelessScanSnap()) return "Experimenteller WLAN-Treiber: Farbe mit 300 dpi. Papiergröße und Zuschnitt werden automatisch erkannt. ADF und Return Path sind getrennte Geräte.";
    return state.data?.wifi?.available ? "USB-Scanner werden weiterhin über SANE gesucht. WLAN kannst du hier über die Scanner-Adresse einrichten." : "USB über SANE; WLAN benötigt einen zusätzlichen experimentellen Treiber.";
  }
  function renderJobs() {
    const jobs = state.data?.jobs || [];
    $("job-count").textContent = jobs.length; $("list-empty").hidden = jobs.length > 0;
    const elements = jobs.map((job) => {
      const button = node("button", "job-card" + (job.id === state.selectedJob ? " selected" : ""));
      button.type = "button"; button.setAttribute("aria-label", `${job.title}, ${pagesOf(job).length} Seiten, ${statusNames[job.status] || job.status}${job.demo ? ", Demo" : ""}`); button.setAttribute("aria-pressed", String(job.id === state.selectedJob));
      const thumb = node("span", "job-card-thumb");
      const page = pagesOf(job)[0];
      if (page?.url && safeUrl(page.url)) { const img = node("img"); img.src = safeUrl(page.url) + (page.url.includes("?") ? "&" : "?") + "v=" + state.imageRevision; img.alt = ""; img.loading = "lazy"; thumb.append(img); } else thumb.append(icon("file"));
      const copy = node("span", "job-card-copy"); copy.append(node("span", "job-card-title", job.title || "Unbenanntes Dokument"), node("span", "job-card-meta", `${pagesOf(job).length} ${pagesOf(job).length === 1 ? "Seite" : "Seiten"} · ${dateText(job.created_at)}`));
      if (job.demo) copy.append(node("span", "job-card-demo", "BEISPIEL"));
      const indicator = node("span", "job-card-indicator" + (job.error ? " error" : running(job) ? " busy" : ""));
      button.append(thumb, copy, indicator); button.addEventListener("click", () => selectJob(job.id));
      const item = node("div"); item.setAttribute("role", "listitem"); item.append(button); return item;
    });
    $("job-list").replaceChildren(...elements);
  }
  function renderProfiles() {
    const profiles = state.data?.profiles || [];
    if (!state.profile && profiles.length) state.profile = profiles[0].id;
    $("profile-list").replaceChildren(...profiles.map((profile, index) => {
      const button = node("button", "profile-button" + (state.profile === profile.id ? " active" : "")); button.type = "button";
      const unsupported = !profileSupported(profile);
      button.dataset.unsupported = String(unsupported);
      button.disabled = unsupported || state.optionsLoading || state.busy.has("scan") || !!state.data?.jobs?.some((job) => ["scanning", "queued", "orienting"].includes(job.status));
      button.setAttribute("aria-pressed", String(state.profile === profile.id)); button.title = unsupported ? "Dieses Profil wird vom gewählten Scanner nicht unterstützt. Verwende die angebotenen Scan-Einstellungen." : profile.description || profile.name;
      const copy = node("span"); copy.append(node("strong", "", profile.name), node("small", "", `${profile.dpi} dpi · ${modeNames[String(profile.mode).toLowerCase()] || profile.mode}`));
      button.append(icon(/photo|foto/i.test(profile.id + profile.name) ? "photo" : /beleg|receipt/i.test(profile.id + profile.name) ? "receipt" : index === 0 ? "file" : "layers"), copy);
      button.onclick = () => { state.profile = profile.id; applyProfile(profile); renderProfiles(); };
      return button;
    }));
  }
  function setChoice(id, value, alias) {
    const control = $(id); const options = [...control.options];
    const target = options.find((option) => option.value === String(value)) || options.find((option) => alias && alias(option.value, value));
    if (target) control.value = target.value;
  }
  function applyProfile(profile) {
    if (!profileSupported(profile)) return;
    setChoice("resolution", profile.dpi);
    setChoice("mode", profile.mode, (a, b) => modeNames[a.toLowerCase()] === modeNames[String(b).toLowerCase()]);
    setChoice("source", profile.source, (a, b) => /duplex/i.test(a) && /duplex/i.test(String(b)));
    updatePaperSizes();
  }
  function profileSupported(profile) {
    if (!state.options) return true;
    const { resolutions = [], modes = [], sources = [] } = state.options;
    return (!resolutions.length || resolutions.some((dpi) => Number(dpi) === Number(profile.dpi)))
      && (!modes.length || modes.some((mode) => mode === profile.mode || (modeNames[mode.toLowerCase()] && modeNames[mode.toLowerCase()] === modeNames[String(profile.mode).toLowerCase()])))
      && (!sources.length || sources.some((source) => source === profile.source || (/duplex/i.test(source) && /duplex/i.test(String(profile.source)))));
  }
  function isWirelessScanSnap() { return $("device").value.startsWith("scansnap:net:"); }
  function paperSizeKey() { return `${$("device").value}|${$("source").value}`; }
  function paperSizesAvailable() {
    const offered = state.options?.paper_sizes;
    return Array.isArray(offered) && offered.length ? offered.filter((value) => ["Driver", "A4", "Letter"].includes(value)) : ["Driver"];
  }
  function updatePaperSizes() {
    const isAdf = /^ADF(?:\s|$)/i.test($("source").value);
    const offered = paperSizesAvailable();
    const sizes = isAdf && offered.length ? offered : ["Driver"];
    const labels = { Driver: "Treiberstandard", A4: "A4 · 210 × 297 mm", Letter: "Letter · 216 × 279 mm" };
    const remembered = state.paperSizeChoices.get(paperSizeKey());
    const preferred = isAdf && sizes.includes(remembered) ? remembered : isAdf && sizes.includes("A4") ? "A4" : "Driver";
    $("paper-size").replaceChildren(...sizes.map((value) => { const option = node("option", "", labels[value]); option.value = value; return option; }));
    $("paper-size").value = sizes.includes(preferred) ? preferred : sizes[0];
    $("paper-size-hint").textContent = !state.options ? "Verfügbare Formate werden vom Scanner gelesen." : isWirelessScanSnap() ? "Papiergröße und Zuschnitt erfolgen automatisch im Scanner." : !isAdf ? "Für diesen Einzug gilt der Treiberstandard." : sizes.length === 1 ? "Dieser Treiber bietet keine weitere Formatauswahl." : "Passend zum eingelegten Papier wählen, damit nichts abgeschnitten wird.";
    renderControls();
  }
  function renderPaperless() {
    const config = state.data?.paperless || {};
    $("connection-button").classList.toggle("connected", !!config.configured);
    $("connection-label").textContent = config.configured ? "Paperless eingerichtet" : "Paperless verbinden";
    $("integration-badge").textContent = config.configured ? "EINGERICHTET" : "NICHT VERBUNDEN";
    $("integration-badge").classList.toggle("connected", !!config.configured);
    $("setup-paperless").hidden = !!config.configured;
    $("paperless-metadata").hidden = !config.configured;
    $("paperless-description").textContent = config.configured ? "Titel und Zuordnung mitgeben. Texterkennung übernimmt Paperless." : "Direkt ins Archiv. Mit Titel, Tags und allem, was dazugehört.";
    if (config.configured && !state.metadataLoaded && !state.busy.has("metadata")) loadMetadata();
  }
  function renderPreview() {
    const job = selectedJob(); const pages = pagesOf(job);
    if (!pages.some((page) => page.id === state.selectedPage)) state.selectedPage = pages[0]?.id || null;
    const page = pages.find((item) => item.id === state.selectedPage);
    const pageIndex = pages.indexOf(page);
    $("preview-title").textContent = job?.title || "Dein nächstes Dokument";
    $("preview-title").title = job?.title || "";
    $("job-title-fields").hidden = !job;
    if (state.titleJobId !== job?.id || !state.titleDirty) {
      $("job-title").value = job?.title || "";
      state.titleJobId = job?.id || null; state.titleDirty = false;
    }
    $("demo-badge").hidden = !job?.demo;
    $("page-counter").textContent = page ? `Seite ${pageIndex + 1} von ${pages.length}` : "Noch keine Seiten";
    $("welcome").hidden = !!job; $("loading-preview").hidden = !job || !!page || !running(job); $("empty-pages").hidden = !job || !!page || running(job);
    $("page-wrap").hidden = !page; $("preview-tools").hidden = !page; $("page-strip").hidden = !page;
    $("empty-pages-description").textContent = job?.error ? "Der Scan konnte keine Seiten erstellen. Prüfe die Meldung oben und deine Scanner-Verbindung." : "Dieses Dokument enthält noch keine Seiten.";
    if (page) {
      const url = safeUrl(page.url);
      const src = url + (url.includes("?") ? "&" : "?") + "v=" + state.imageRevision;
      if ($("page-image").getAttribute("src") !== src) $("page-image").src = src;
      $("page-image").alt = `${job.demo ? "Beispielseite" : "Gescannte Seite"} ${pageIndex + 1} von ${pages.length}: ${job.title}`;
      applyZoom();
    } else $("page-image").removeAttribute("src");
    $("document-format").textContent = job ? `${job.settings?.dpi || "–"} dpi · ${job.pdf_ready ? "PDF bereit" : "PDF nach Export"}` : "PDF · für deine Ablage";
    renderPageOrientation(page);
    renderJobStatus(job);
    renderThumbnails(pages);
    if (page) requestAnimationFrame(applyZoom);
    const paperless = job?.paperless;
    $("paperless-status-button").hidden = !paperless?.task_id;
    const pstatus = String(paperless?.status || "").toLowerCase();
    $("paperless-job-status").textContent = paperless ? (paperless.error || (paperless.document_id ? `Archiviert · Dokument ${paperless.document_id}` : ["success", "completed", "complete"].includes(pstatus) ? "Erfolgreich in Paperless verarbeitet." : ["failed", "failure", "error"].includes(pstatus) ? "Paperless konnte das Dokument nicht verarbeiten." : pstatus === "unknown" ? "Übertragung unklar. Bitte zuerst den Status bei Paperless prüfen." : "An Paperless übergeben. Die Verarbeitung läuft dort weiter.")) : "";
    $("paperless-job-status").classList.toggle("error", !!paperless?.error);
  }
  function renderPageOrientation(page) {
    $("orientation-actions").hidden = !page;
    $("restore-orientation").hidden = !page?.can_restore_orientation;
    const result = page?.orientation;
    const warning = orientationWarnings.has(result?.reason);
    const message = !orientationAvailable()
      ? "Automatisches Ausrichten benötigt die lokale Orientierungserkennung (Tesseract mit osd). Du kannst diese Seite unten manuell drehen."
      : result?.message || (result?.applied ? "Die Schreibrichtung dieser Seite wurde automatisch korrigiert." : "Erkennt die Schreibrichtung und dreht nur bei einer sicheren Erkennung.");
    $("page-orientation-status").textContent = message;
    $("page-orientation-status").classList.toggle("warning", warning);
  }
  function renderJobStatus(job) {
    const box = $("job-status"); box.replaceChildren(); box.className = "job-status";
    if (!job) { box.hidden = true; return; }
    let message = ""; let type = "";
    if (running(job)) message = job.status === "orienting" ? "Seiten werden lokal auf ihre Schreibrichtung geprüft und ausgerichtet. Das kann einen Moment dauern." : job.status === "uploading" ? "Dein PDF wird an Paperless übertragen …" : job.status === "exporting" ? "Dein PDF wird erstellt …" : job.demo ? "Das Beispieldokument wird vorbereitet …" : "Der Scanner arbeitet. Neue Seiten erscheinen automatisch.";
    else if (job.error) { message = job.error; type = job.status === "error" ? "error" : "warning"; }
    else if (job.warning) { message = job.warning; type = "warning"; }
    else if (job.orientation_note) { message = job.orientation_note; type = pagesOf(job).some((page) => orientationWarnings.has(page.orientation?.reason)) ? "warning" : ""; }
    else if (job.demo) message = "Beispieldokument · Diese Seiten wurden erzeugt, nicht mit einem Scanner eingelesen.";
    else if (locked(job)) message = "An Paperless übergeben · Die Seiten sind vor weiteren Änderungen geschützt.";
    if (!message) { box.hidden = true; return; }
    box.hidden = false; if (type) box.classList.add(type);
    box.append(icon(type ? "alert" : job.demo ? "sparkles" : "check"), node("span", "", message));
    if (["scanning", "queued", "orienting"].includes(job.status)) { const button = node("button", "cancel-link", "Abbrechen"); button.onclick = cancelScan; box.append(button); }
  }
  function renderThumbnails(pages) {
    $("thumbnail-list").replaceChildren(...pages.map((page, index) => {
      const button = node("button", "page-thumbnail" + (page.id === state.selectedPage ? " selected" : "")); button.type = "button";
      button.setAttribute("aria-label", `Seite ${index + 1} auswählen`); button.setAttribute("aria-pressed", String(page.id === state.selectedPage));
      button.draggable = !locked(selectedJob());
      const img = node("img"); const url = safeUrl(page.url); img.src = url + (url.includes("?") ? "&" : "?") + "v=" + state.imageRevision; img.alt = ""; img.draggable = false;
      button.append(img, node("span", "", String(index + 1)));
      if (orientationWarnings.has(page.orientation?.reason)) {
        const marker = node("span", "thumbnail-warning"); marker.append(icon("alert")); marker.setAttribute("aria-hidden", "true"); button.append(marker);
        button.title = page.orientation.message || "Ausrichtung dieser Seite prüfen";
        button.setAttribute("aria-label", `Seite ${index + 1} auswählen · Ausrichtung prüfen`);
      }
      button.onclick = () => { state.selectedPage = page.id; state.zoom = 1; renderPreview(); renderControls(); };
      button.ondragstart = (event) => { event.dataTransfer.setData("text/plain", page.id); event.dataTransfer.effectAllowed = "move"; };
      button.ondragover = (event) => { if (!locked(selectedJob())) { event.preventDefault(); button.classList.add("drag-over"); } };
      button.ondragleave = () => button.classList.remove("drag-over");
      button.ondrop = (event) => { event.preventDefault(); button.classList.remove("drag-over"); const id = event.dataTransfer.getData("text/plain"); if (!locked(selectedJob()) && id !== page.id && pages.some((p) => p.id === id)) reorderPage(id, index); };
      return button;
    }));
  }
  function renderControls() {
    const job = selectedJob(); const pages = pagesOf(job); const index = pages.findIndex((page) => page.id === state.selectedPage);
    const anyScan = state.data?.jobs?.some((item) => ["scanning", "queued", "orienting"].includes(item.status));
    const starting = state.busy.has("scan") || state.busy.has("orient"); const editing = ["edit", "export", "upload", "orient", "rename"].some((key) => state.busy.has(key));
    const loadingScanner = state.busy.has("devices") || state.optionsLoading || state.busy.has("wifi");
    $("scan-button").disabled = !state.connected || !$("device").value || !state.options || loadingScanner || anyScan || starting;
    $("scan-button").title = !$("device").value ? "Verbinde deinen Scanner und suche erneut nach SANE-Geräten." : loadingScanner ? "Scanneroptionen werden geladen. Bitte einen Moment warten." : !state.options ? "Scanneroptionen fehlen. Bitte erneut nach Scannern suchen." : "Mit den gewählten Einstellungen scannen";
    $("demo-button").disabled = $("welcome-demo").disabled = !state.connected || starting || anyScan || state.busy.has("wifi");
    $("refresh-devices").disabled = loadingScanner || !!anyScan;
    $("export-button").disabled = !pages.length || running(job) || state.busy.has("export") || editing;
    $("upload-button").disabled = !state.data?.paperless?.configured || !pages.length || locked(job) || state.busy.has("upload") || editing;
    $("rotate-page").disabled = $("delete-page").disabled = !pages.length || locked(job) || editing;
    $("auto-orient-page").disabled = $("auto-orient-job").disabled = !orientationAvailable() || !pages.length || locked(job) || editing || !!anyScan;
    $("restore-orientation").disabled = !pages.length || locked(job) || editing;
    $("job-title").disabled = !job || locked(job) || editing;
    $("rename-job").disabled = !job || !state.titleDirty || !$("job-title").value.trim() || locked(job) || editing;
    $("page-left").disabled = index <= 0 || locked(job) || editing;
    $("page-right").disabled = index < 0 || index >= pages.length - 1 || locked(job) || editing;
    $("paperless-status-button").disabled = state.busy.has("paperless-status");
    $("cancel-scan").disabled = state.busy.has("cancel");
    $("cancel-scan").hidden = !["scanning", "queued", "orienting"].includes(job?.status);
    $("zoom-out").disabled = state.zoom <= .6;
    $("zoom-in").disabled = state.zoom >= 2;
    ["device", "resolution", "mode", "source", "page-limit"].forEach((id) => { $(id).disabled = !!anyScan || starting || state.busy.has("wifi"); });
    $("paper-size").disabled = !!anyScan || starting || !/^ADF(?:\s|$)/i.test($("source").value) || paperSizesAvailable().length < 2;
    document.querySelectorAll(".profile-button").forEach((button) => { button.disabled = !!anyScan || starting || state.optionsLoading || button.dataset.unsupported === "true"; });
    const wifiSaving = state.busy.has("wifi"); const wifiBlocked = scannerBusy();
    $("save-wifi").disabled = !state.connected || !state.data?.wifi?.available || wifiSaving || wifiBlocked;
    $("wifi-address").disabled = !state.data?.wifi?.available || wifiSaving;
    $("wifi-busy-hint").hidden = !wifiSaving && !wifiBlocked;
    $("wifi-busy-hint").textContent = wifiSaving ? "WLAN-Einstellung wird übernommen und die Gerätesuche läuft …" : "Bitte warte, bis die laufende Verarbeitung oder Gerätesuche abgeschlossen ist. Danach kannst du die WLAN-Adresse speichern.";
  }
  function sourceLabel(source) {
    if (/duplex/i.test(source)) return source + " · beidseitig";
    if (/flatbed/i.test(source)) return "Flachbett";
    return source;
  }
  function fillSelect(id, options, selected, label) {
    const list = Array.isArray(options) ? [...new Set(options)] : [];
    if (!list.length) return;
    const control = $(id); const previous = selected ?? control.value;
    control.replaceChildren(...list.map((value) => { const option = node("option", "", label ? label(value) : String(value)); option.value = value; return option; }));
    if (list.some((item) => String(item) === String(previous))) control.value = previous;
  }
  async function refreshDevices() {
    return action("devices", async () => {
      $("scanner-summary").textContent = "Geräte werden gesucht";
      let data;
      try { data = await api("/api/devices"); }
      catch (error) {
        state.devices = []; state.options = null; updatePaperSizes();
        const placeholder = node("option", "", "Bitte erneut nach Scannern suchen"); placeholder.value = "";
        $("device").replaceChildren(placeholder);
        $("scanner-summary").textContent = "Gerätesuche nicht abgeschlossen";
        $("scanner-detail").textContent = "Suche über ↻ wiederholen";
        $("scanner-led").classList.remove("connected");
        $("compatibility-note").textContent = compatibilityText();
        const temporarilyUnavailable = /beschäftigt/i.test(error.message);
        const message = temporarilyUnavailable ? "Die Gerätesuche ist gerade nicht verfügbar. Bitte kurz warten und erneut suchen." : error.message;
        $("device-warning").textContent = temporarilyUnavailable ? message : `${message} Bitte die Gerätesuche erneut starten.`;
        $("device-warning").classList.toggle("error", !temporarilyUnavailable);
        throw new Error(message);
      }
      state.devices = data.devices || [];
      const previous = $("device").value;
      const missingWifiAddress = state.data?.wifi?.available && !state.data.wifi.configured;
      const placeholder = node("option", "", state.devices.length ? "Scanner auswählen" : missingWifiAddress ? "WLAN-Adresse noch nicht eingerichtet" : "Kein Scanner erkannt"); placeholder.value = "";
      $("device").replaceChildren(placeholder, ...state.devices.map((device) => { const option = node("option", "", [device.vendor, device.model].filter(Boolean).join(" ") || device.id); option.value = device.id; return option; }));
      $("device").value = state.devices.some((device) => device.id === previous) ? previous : state.devices[0]?.id || "";
      $("device-warning").textContent = data.warning || (state.devices.length ? "Gerät über SANE verfügbar. Optionen werden vom Treiber gelesen." : missingWifiAddress ? "Für deinen WLAN-Scanner fehlt noch die IP-Adresse. Richte WLAN unten ein. USB-Scanner wurden bereits gesucht." : state.data?.wifi?.configured ? "Kein Scanner gefunden. Prüfe die gespeicherte WLAN-Adresse, die blaue WLAN-Leuchte und dein Netzwerk. Danach erneut suchen." : "Kein USB-Scanner gefunden. Verbinde einen Scanner oder prüfe unten die Voraussetzungen für WLAN.");
      $("device-warning").classList.toggle("error", !!data.warning);
      updateScannerSummary();
      if ($("device").value) await loadDeviceOptions();
      else { state.options = null; updatePaperSizes(); }
      return data;
    });
  }
  function updateScannerSummary() {
    const device = state.devices.find((item) => item.id === $("device").value);
    const missingWifiAddress = state.data?.wifi?.available && !state.data.wifi.configured;
    $("scanner-summary").textContent = device ? device.model || device.vendor || "Scanner bereit" : missingWifiAddress ? "WLAN-Adresse fehlt" : "Kein Scanner gefunden";
    $("scanner-detail").textContent = device ? isWirelessScanSnap() ? "WLAN · experimentell" : "SANE bereit" : missingWifiAddress ? "Unter Setup WLAN einrichten" : state.data?.wifi?.configured ? "WLAN-Adresse und Verbindung prüfen" : "USB verbinden oder WLAN prüfen";
    $("compatibility-note").textContent = compatibilityText();
    $("scanner-led").classList.toggle("connected", !!device);
    renderControls();
  }
  async function loadDeviceOptions() {
    const device = $("device").value; const request = ++state.deviceRequest;
    state.options = null; state.optionsLoading = !!device; updatePaperSizes();
    if (!device) { updateScannerSummary(); return; }
    $("device-warning").textContent = "Scanneroptionen werden geladen. Danach kannst du den Scan starten.";
    $("device-warning").classList.remove("error");
    try {
      const options = await api("/api/device-options?device=" + encodeURIComponent(device));
      if (request !== state.deviceRequest || device !== $("device").value) return;
      state.options = options;
      fillSelect("source", options.sources, undefined, sourceLabel);
      fillSelect("mode", options.modes, undefined, (mode) => modeNames[mode.toLowerCase()] || mode);
      fillSelect("resolution", options.resolutions, undefined, (dpi) => `${dpi} dpi`);
      const profile = state.data?.profiles?.find((item) => item.id === state.profile);
      if (profile && profileSupported(profile)) applyProfile(profile);
      else if (profile) state.profile = "custom";
      renderProfiles();
      updatePaperSizes();
      $("device-warning").textContent = isWirelessScanSnap() ? "WLAN · experimentell. Dieser Treiber bietet ausschließlich Farbe mit 300 dpi." : "Scanneroptionen geladen. Papierformat und Einzug vor dem Scan prüfen.";
      $("device-warning").classList.remove("error");
      updateScannerSummary();
    } catch (error) {
      if (request !== state.deviceRequest || device !== $("device").value) return;
      $("device-warning").textContent = `${error.message} Der Scan bleibt gesperrt. Bitte über ↻ erneut nach Scannern suchen.`;
      $("device-warning").classList.add("error");
      $("paper-size-hint").textContent = "Papierformat noch nicht bestätigt. Scanneroptionen erneut laden.";
      $("scanner-summary").textContent = "Scanneroptionen fehlen";
      $("scanner-detail").textContent = "Suche über ↻ wiederholen";
      $("scanner-led").classList.remove("connected");
    } finally {
      if (request === state.deviceRequest) { state.optionsLoading = false; renderControls(); }
    }
  }
  async function startScan(demo) {
    if (!demo && !$("device").value) return toast("Bitte zuerst einen Scanner verbinden und als SANE-Gerät auswählen.", true);
    if (!demo && (state.busy.has("devices") || state.optionsLoading)) return toast("Scanneroptionen werden noch geladen. Bitte einen Moment warten.", true);
    if (!demo && !state.options) return toast("Scanneroptionen fehlen. Bitte über ↻ erneut nach Scannern suchen, bevor du einen Scan startest.", true);
    return action("scan", async () => {
      const pageLimit = Number($("page-limit").value);
      if (!Number.isInteger(pageLimit) || pageLimit < 1 || pageLimit > 100) throw new Error("Die maximale Seitenzahl muss zwischen 1 und 100 liegen.");
      const job = await api("/api/jobs", { demo, device: $("device").value, title: demo ? "Beispieldokument" : $("document-title").value.trim(), dpi: Number($("resolution").value), mode: $("mode").value, source: $("source").value, paper_size: $("paper-size").value || "Driver", page_limit: pageLimit });
      if (!demo) $("document-title").value = "";
      await refreshState(); selectJob(job.id); schedulePoll();
      toast(demo ? "Demo gestartet. Es wird kein Scanner angesprochen." : "Scan gestartet. Dein Papier kommt ins Digitale.");
    });
  }
  async function cancelScan() {
    const job = selectedJob(); if (!job) return;
    return action("cancel", async () => { await api(`/api/jobs/${encodeURIComponent(job.id)}/cancel`, {}); await refreshState(); toast("Abbruch angefordert. Bereits verarbeitete Seiten bleiben erhalten."); });
  }
  async function orientPages(allPages = false) {
    const job = selectedJob();
    if (!pagesOf(job).length || locked(job) || !orientationAvailable()) return;
    return action("orient", async () => {
      const body = allPages ? {} : { page_id: state.selectedPage };
      await api(`/api/jobs/${encodeURIComponent(job.id)}/auto-orient`, body);
      await refreshState();
      toast(allPages ? "Alle Seiten werden auf ihre Schreibrichtung geprüft." : "Die ausgewählte Seite wird auf ihre Schreibrichtung geprüft.");
    });
  }
  async function persistJobTitle(job) {
    const title = state.titleJobId === job.id ? $("job-title").value.trim() : job.title;
    if (!title) throw new Error("Bitte gib einen Namen für dieses Dokument ein.");
    if (title === job.title) return job.title;
    if (locked(job)) throw new Error("Der Dokumentname kann während der Verarbeitung oder nach der Paperless-Übertragung nicht geändert werden.");
    const updated = await api(`/api/jobs/${encodeURIComponent(job.id)}/rename`, { title });
    if (state.selectedJob === job.id) { state.titleDirty = false; $("job-title").value = updated.title || title; }
    await refreshState();
    return updated.title || title;
  }
  async function renameDocument() {
    const job = selectedJob(); if (!job || locked(job)) return;
    return action("rename", async () => { await persistJobTitle(job); toast("Dokumentname gespeichert. Dein PDF verwendet denselben Namen."); });
  }
  async function editPage(operation, body) {
    const job = selectedJob(); if (!job || locked(job)) return;
    return action("edit", async () => { await api(`/api/jobs/${encodeURIComponent(job.id)}/${operation}`, body); state.imageRevision += 1; await refreshState(); renderPreview(); });
  }
  function reorderPage(id, index) {
    const ids = pagesOf(selectedJob()).map((page) => page.id); const old = ids.indexOf(id);
    if (old < 0 || index < 0 || index >= ids.length) return;
    ids.splice(old, 1); ids.splice(index, 0, id); return editPage("reorder", { page_ids: ids });
  }
  function applyZoom() {
    const canvas = $("preview-canvas");
    const image = $("page-image");
    if (!$("page-wrap").hidden) {
      const padding = getComputedStyle($("page-wrap"));
      const availableHeight = canvas.clientHeight - parseFloat(padding.paddingTop) - parseFloat(padding.paddingBottom) - 2;
      image.style.maxHeight = `${Math.max(80, availableHeight)}px`;
    }
    image.style.transform = state.zoom === 1 ? "" : `scale(${state.zoom})`;
    if (state.zoom === 1) { canvas.scrollTop = 0; canvas.scrollLeft = 0; }
    $("zoom-reset").textContent = `${Math.round(state.zoom * 100)} %`;
  }
  async function exportPdf() {
    const job = selectedJob(); if (!job) return;
    return action("export", async () => {
      await persistJobTitle(job);
      toast("Dein PDF wird erstellt …");
      const result = await api(`/api/jobs/${encodeURIComponent(job.id)}/export`, { ocr: false });
      const url = safeUrl(result.url); if (!url) throw new Error("Die Anwendung hat keinen gültigen Download-Link geliefert.");
      const anchor = node("a"); anchor.href = url; anchor.download = ""; document.body.append(anchor); anchor.click(); anchor.remove();
      await refreshState(); toast("PDF erstellt. Der Download wurde gestartet.");
    });
  }
  async function uploadDocument() {
    const job = selectedJob(); if (!job || locked(job)) return;
    return action("upload", async () => {
      const idValue = (id) => $(id).value ? Number($(id).value) : null;
      const title = await persistJobTitle(job);
      await api(`/api/jobs/${encodeURIComponent(job.id)}/upload`, { title, tags: [...$("paperless-tags").selectedOptions].map((option) => Number(option.value)), correspondent: idValue("paperless-correspondent"), document_type: idValue("paperless-document-type") });
      await refreshState(); toast("Übertragung an Paperless gestartet. Den Status siehst du beim Dokument.");
    });
  }
  async function loadMetadata() {
    state.busy.add("metadata"); state.metadataLoaded = true;
    try {
      const metadata = await api("/api/paperless/metadata");
      const populate = (id, values, blank) => {
        const control = $(id); const selected = [...control.selectedOptions].map((option) => option.value);
        const options = [];
        if (blank) { const option = node("option", "", "Automatisch erkennen"); option.value = ""; options.push(option); }
        (values || []).forEach((item) => { const option = node("option", "", item.name); option.value = String(item.id); option.selected = selected.includes(option.value); options.push(option); });
        if (!blank && !options.length) { const option = node("option", "", "Noch keine Tags in Paperless"); option.disabled = true; options.push(option); }
        control.replaceChildren(...options);
      };
      populate("paperless-tags", metadata.tags, false); populate("paperless-correspondent", metadata.correspondents, true); populate("paperless-document-type", metadata.document_types, true);
    } catch (error) { $("paperless-description").textContent = "Metadaten konnten nicht geladen werden. Verbindung in den Einstellungen prüfen."; toast(error.message, true); }
    finally { state.busy.delete("metadata"); }
  }
  function showSettingsTab(tab, focus = false) {
    settingsTabs.forEach((name) => {
      const selected = name === tab;
      const button = $("settings-tab-" + name);
      button.setAttribute("aria-selected", String(selected)); button.tabIndex = selected ? 0 : -1;
      $(settingsPanels[name]).hidden = !selected;
      if (selected && focus) button.focus();
    });
  }
  function updateNamingPreview(useSavedPreview = false) {
    const template = $("naming-template").value.trim();
    const invalidTokens = /[{}]/.test(template.replace(/\{(?:date|time|counter)\}/g, ""));
    $("naming-template").setCustomValidity(!template ? "Bitte gib eine Namensvorlage ein." : invalidTokens ? "Erlaubt sind nur die Platzhalter {date}, {time} und {counter}." : "");
    const preview = useSavedPreview && state.data?.name_preview ? state.data.name_preview : sampleName(template);
    $("naming-preview").textContent = template && !invalidTokens ? `${preview.replace(/\.pdf$/i, "")}.pdf` : "Bitte eine gültige Vorlage eingeben";
    $("naming-preview").classList.toggle("invalid", !template || invalidTokens);
  }
  function fillPreferenceForm() {
    const prefs = preferences();
    const preset = [...$("naming-preset").options].find((option) => option.value === prefs.naming_template);
    $("naming-preset").value = preset ? preset.value : "custom";
    $("naming-template").value = prefs.naming_template;
    $("custom-template-field").hidden = !!preset;
    $("auto-orient-preference").checked = orientationAvailable() && prefs.auto_orient;
    $("auto-orient-preference").disabled = !orientationAvailable();
    $("orientation-setting-hint").textContent = orientationAvailable()
      ? "Die Schreibrichtung wird lokal erkannt. Das kann etwas Zeit brauchen. Bei unsicherer Erkennung bleibt die Seite unverändert und erhält einen Hinweis."
      : "Noch nicht verfügbar: Die lokale Orientierungserkennung benötigt Tesseract mit den Orientierungsdaten „osd“. Nach der Installation PaperDock neu starten. Manuelles Drehen funktioniert weiterhin.";
    updateNamingPreview(true);
  }
  async function savePreferences() {
    updateNamingPreview();
    if (!$("preferences-form").reportValidity() || state.busy.has("preferences")) return;
    state.busy.add("preferences");
    $("save-preferences").disabled = true;
    $("preferences-feedback").classList.remove("error"); $("preferences-feedback").textContent = "Allgemeine Einstellungen werden gespeichert …";
    try {
      const result = await api("/api/preferences", { auto_orient: orientationAvailable() ? $("auto-orient-preference").checked : preferences().auto_orient, naming_template: $("naming-template").value.trim() });
      if (state.data) { state.data.preferences = result.preferences; state.data.name_preview = result.name_preview; }
      await refreshState();
      fillPreferenceForm();
      $("preferences-feedback").textContent = "Gespeichert. Diese Einstellungen gelten für deine nächsten Scans.";
    } catch (error) { $("preferences-feedback").classList.add("error"); $("preferences-feedback").textContent = error.message; }
    finally { state.busy.delete("preferences"); $("save-preferences").disabled = false; }
  }
  async function saveWifi() {
    if (state.busy.has("wifi")) return;
    $("wifi-feedback").classList.remove("error");
    if (!state.connected || !state.data?.wifi?.available || scannerBusy()) {
      $("wifi-feedback").textContent = scannerBusy() ? "Bitte warte, bis die laufende Verarbeitung oder Gerätesuche abgeschlossen ist." : state.data?.wifi?.message || "Die WLAN-Einrichtung ist gerade nicht verfügbar.";
      $("wifi-feedback").classList.add("error");
      return;
    }
    const address = $("wifi-address").value.trim();
    if (!$("wifi-form").reportValidity()) return;
    state.busy.add("wifi"); renderControls();
    $("wifi-feedback").textContent = "WLAN-Einstellung wird gespeichert …";
    try {
      const wifi = await api("/api/wifi", { address });
      if (state.data) state.data.wifi = wifi;
      $("wifi-address").value = wifi.address || "";
      state.options = null; state.deviceRequest += 1;
      renderWifi(); updatePaperSizes();
      $("wifi-feedback").textContent = wifi.configured ? "Adresse gespeichert. PaperDock sucht jetzt nach Scannern …" : "WLAN ausgeschaltet. PaperDock sucht jetzt nach USB-Scannern …";
      await refreshState();
      const result = await refreshDevices();
      const foundWifi = state.devices.some((device) => device.id.startsWith("scansnap:net:"));
      if (!result) {
        $("wifi-feedback").classList.add("error");
        $("wifi-feedback").textContent = `Einstellung gespeichert. ${$("device-warning").textContent}`;
      } else if (wifi.configured && !foundWifi) {
        $("wifi-feedback").classList.add("error");
        $("wifi-feedback").textContent = "Adresse gespeichert, aber kein WLAN-Scanner gefunden. Prüfe die Adresse im Router, die blaue WLAN-Leuchte und ob Rechner und Scanner im selben Netzwerk sind. Danach erneut suchen.";
      } else if (state.devices.length && !state.options) {
        $("wifi-feedback").classList.add("error");
        $("wifi-feedback").textContent = `Scanner gefunden. ${$("device-warning").textContent}`;
      } else {
        $("wifi-feedback").textContent = wifi.configured ? "WLAN-Scanner gefunden. Du kannst den passenden Einzug in den Scan-Einstellungen auswählen. Es wurde kein Scan gestartet." : state.devices.length ? "WLAN ausgeschaltet. USB-Scanner gefunden und weiterhin verfügbar." : "WLAN ausgeschaltet. Zurzeit wurde kein USB-Scanner gefunden. Du kannst ihn jederzeit verbinden und erneut suchen.";
      }
    } catch (error) {
      $("wifi-feedback").classList.add("error"); $("wifi-feedback").textContent = error.message;
    } finally { state.busy.delete("wifi"); renderControls(); }
  }
  function openSettings(tab = "general") {
    $("paperless-url").value = state.data?.paperless?.url || "";
    $("paperless-token").value = ""; $("paperless-token").type = "password";
    $("toggle-token").setAttribute("aria-label", "API-Token anzeigen");
    $("paperless-token").placeholder = state.data?.paperless?.configured ? "Token gespeichert · leer lassen zum Beibehalten" : "Deinen API-Token einfügen";
    $("settings-feedback").textContent = ""; $("settings-feedback").classList.remove("error");
    $("preferences-feedback").textContent = ""; $("preferences-feedback").classList.remove("error");
    $("wifi-address").value = state.data?.wifi?.address || "";
    $("wifi-feedback").textContent = ""; $("wifi-feedback").classList.remove("error");
    fillPreferenceForm(); renderWifi(); renderControls(); showSettingsTab(tab); $("settings-dialog").showModal();
  }
  async function saveSettings(testOnly = false) {
    if (!$("paperless-form").reportValidity()) return;
    $("save-settings").disabled = $("test-paperless").disabled = true;
    $("settings-feedback").classList.remove("error"); $("settings-feedback").textContent = testOnly ? "Einstellungen werden gespeichert und die Verbindung wird geprüft …" : "Verbindung wird gespeichert …";
    try {
      const result = await api("/api/settings/paperless", { url: $("paperless-url").value.trim(), token: $("paperless-token").value.trim() });
      $("paperless-token").value = "";
      state.metadataLoaded = false;
      if (state.data) state.data.paperless = result.paperless || result;
      if (testOnly) {
        await api("/api/paperless/test", {});
        $("settings-feedback").textContent = "Verbindung erfolgreich. Dein Paperless ist erreichbar.";
      } else {
        $("settings-dialog").close(); toast("Paperless-Verbindung gespeichert.");
      }
      await refreshState(); renderPaperless();
    } catch (error) {
      $("settings-feedback").classList.add("error"); $("settings-feedback").textContent = error.message;
      await refreshState().catch(() => {});
    } finally { $("save-settings").disabled = $("test-paperless").disabled = false; }
  }

  const compatibility = node("p", "compatibility-note", "USB über SANE; WLAN benötigt einen zusätzlichen experimentellen Treiber.");
  compatibility.id = "compatibility-note";
  $("device-warning").after(compatibility);
  $("scan-button").onclick = () => startScan(false);
  $("demo-button").onclick = $("welcome-demo").onclick = () => startScan(true);
  $("refresh-devices").onclick = refreshDevices;
  $("device").onchange = () => { updateScannerSummary(); loadDeviceOptions(); };
  $("cancel-scan").onclick = cancelScan;
  $("rotate-page").onclick = () => editPage("rotate", { page_id: state.selectedPage, degrees: 90 });
  $("auto-orient-page").onclick = () => orientPages(false);
  $("auto-orient-job").onclick = () => orientPages(true);
  $("restore-orientation").onclick = () => editPage("restore-orientation", { page_id: state.selectedPage });
  $("rename-job").onclick = renameDocument;
  $("job-title").addEventListener("input", () => { state.titleDirty = $("job-title").value.trim() !== selectedJob()?.title; renderControls(); });
  $("job-title").addEventListener("keydown", (event) => { if (event.key === "Enter") { event.preventDefault(); if (!$("rename-job").disabled) renameDocument(); } });
  $("delete-page").onclick = () => editPage("delete-page", { page_id: state.selectedPage });
  $("page-left").onclick = () => reorderPage(state.selectedPage, pagesOf(selectedJob()).findIndex((page) => page.id === state.selectedPage) - 1);
  $("page-right").onclick = () => reorderPage(state.selectedPage, pagesOf(selectedJob()).findIndex((page) => page.id === state.selectedPage) + 1);
  $("zoom-out").onclick = () => { state.zoom = Math.max(.6, Math.round((state.zoom - .2) * 10) / 10); applyZoom(); renderControls(); };
  $("zoom-in").onclick = () => { state.zoom = Math.min(2, Math.round((state.zoom + .2) * 10) / 10); applyZoom(); renderControls(); };
  $("zoom-reset").onclick = () => { state.zoom = 1; applyZoom(); renderControls(); };
  $("export-button").onclick = exportPdf;
  $("upload-button").onclick = uploadDocument;
  $("paperless-status-button").onclick = () => action("paperless-status", async () => { const job = selectedJob(); if (!job) return; await api(`/api/jobs/${encodeURIComponent(job.id)}/paperless-status`, {}); await refreshState(); toast("Paperless-Status aktualisiert."); });
  document.querySelectorAll("[data-open-settings]").forEach((button) => button.addEventListener("click", () => openSettings(button.dataset.settingsTab || "general")));
  settingsTabs.forEach((name, index) => {
    const button = $("settings-tab-" + name);
    button.onclick = () => showSettingsTab(name);
    button.onkeydown = (event) => {
      if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
        event.preventDefault();
        const target = event.key === "Home" ? 0 : event.key === "End" ? settingsTabs.length - 1 : (index + (event.key === "ArrowRight" ? 1 : -1) + settingsTabs.length) % settingsTabs.length;
        showSettingsTab(settingsTabs[target], true);
      }
    };
  });
  $("naming-preset").onchange = () => {
    const custom = $("naming-preset").value === "custom";
    $("custom-template-field").hidden = !custom;
    if (!custom) $("naming-template").value = $("naming-preset").value;
    updateNamingPreview();
    if (custom) $("naming-template").focus();
  };
  $("naming-template").addEventListener("input", () => updateNamingPreview());
  $("preferences-form").onsubmit = (event) => { event.preventDefault(); savePreferences(); };
  $("wifi-form").onsubmit = (event) => { event.preventDefault(); saveWifi(); };
  $("close-settings").onclick = () => $("settings-dialog").close();
  $("settings-dialog").addEventListener("close", () => { $("paperless-token").value = ""; });
  $("settings-dialog").addEventListener("click", (event) => { if (event.target === $("settings-dialog")) { const rect = event.target.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) event.target.close(); } });
  $("toggle-token").onclick = () => { const visible = $("paperless-token").type === "password"; $("paperless-token").type = visible ? "text" : "password"; $("toggle-token").setAttribute("aria-label", visible ? "API-Token verbergen" : "API-Token anzeigen"); };
  $("paperless-form").onsubmit = (event) => { event.preventDefault(); saveSettings(); };
  $("test-paperless").onclick = () => saveSettings(true);
  $("nav-documents").onclick = () => { const target = $("job-list").querySelector("button"); if (target) target.focus(); else { $("list-empty").scrollIntoView({ behavior: "smooth", block: "center" }); toast("Deine Dokumente erscheinen nach dem ersten Scan hier."); } };
  $("nav-studio").onclick = () => { $("workspace").scrollIntoView({ behavior: "smooth", block: "start" }); $("workspace").focus({ preventScroll: true }); };
  ["resolution", "mode", "source"].forEach((id) => $(id).addEventListener("change", () => { state.profile = "custom"; renderProfiles(); }));
  $("source").addEventListener("change", updatePaperSizes);
  $("paper-size").addEventListener("change", () => state.paperSizeChoices.set(paperSizeKey(), $("paper-size").value));
  document.addEventListener("visibilitychange", () => { if (!document.hidden && state.token) refreshState().catch(() => {}); });
  $("page-image").addEventListener("load", applyZoom);
  if (typeof ResizeObserver !== "undefined") new ResizeObserver(() => requestAnimationFrame(applyZoom)).observe($("preview-canvas"));
  else window.addEventListener("resize", applyZoom);

  async function init() {
    renderControls();
    try {
      const session = await fetch("/api/session", { cache: "no-store" }).then((response) => { if (!response.ok) throw new Error("Die lokale Anwendung ist nicht erreichbar."); return response.json(); });
      state.token = session.token;
      await refreshState();
      const profile = state.data?.profiles?.find((item) => item.id === state.profile); if (profile) applyProfile(profile);
      await refreshDevices();
    } catch (error) {
      state.connected = false; $("runtime-status").textContent = "Lokale Anwendung nicht erreichbar · Seite neu laden";
      $("scanner-summary").textContent = "Verbindung fehlt";
      $("scanner-detail").textContent = "PaperDock starten und neu laden";
      $("device").replaceChildren(Object.assign(document.createElement("option"), { value: "", textContent: "Anwendung nicht erreichbar" }));
      $("device-warning").textContent = error.message; toast(error.message, true); renderControls();
    }
  }
  init();
})();
