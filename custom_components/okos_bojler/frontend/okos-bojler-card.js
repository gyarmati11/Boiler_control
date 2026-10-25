/*
 * Okos Bojler kártya – Home Assistant Lovelace
 * Használat:
 *   type: custom:okos-bojler-card
 *   entity: sensor.okos_bojler_allapot
 *   title: Bojler            (opcionális)
 *   show_settings: true      (opcionális, a beállítás panel megjelenítése)
 */
const OB_VERSION = "1.1.0";

const REASON_STYLE = {
  napelem:     { icon: "mdi:solar-power-variant", color: "#f5a524" },
  tartalek:    { icon: "mdi:clock-time-three-outline", color: "#3b82f6" },
  turbo:       { icon: "mdi:rocket-launch", color: "#ef4444" },
  kezi:        { icon: "mdi:hand-back-right", color: "#a855f7" },
  kikapcsolva: { icon: "mdi:power-off", color: "#6b7280" },
  ejszaka:     { icon: "mdi:weather-night", color: "#6366f1" },
  autotoltes:  { icon: "mdi:ev-station", color: "#0ea5e9" },
  teljesitve:  { icon: "mdi:check-circle-outline", color: "#22c55e" },
  var:         { icon: "mdi:sleep", color: "#64748b" },
};

const MODES = [
  { value: "Automatikus", label: "Auto", icon: "mdi:robot-outline" },
  { value: "Mindig ki", label: "Ki", icon: "mdi:power-off" },
  { value: "Mindig be", label: "Be", icon: "mdi:power" },
];

const SLIDERS = [
  { key: "bekapcsolasi_kuszob", label: "Akku bekapcsolási küszöb", unit: "%" },
  { key: "kikapcsolasi_kuszob", label: "Akku kikapcsolási küszöb", unit: "%" },
  { key: "napi_minimum", label: "Napi minimum fűtés", unit: "perc" },
  { key: "turbo_idotartam", label: "Turbó időtartam", unit: "óra" },
  { key: "teljesitmeny", label: "Bojler teljesítmény", unit: "kW" },
  { key: "autotoltes_kuszob", label: "Autótöltés érzékelési küszöb", unit: "W", needEv: true },
];

const TOGGLES = [
  { key: "napelemes_futes", label: "Napelemes fűtés (akku alapján)" },
  { key: "tartalek_futes", label: "Tartalék minimum fűtés" },
  { key: "napi_beszamitas", label: "Napközbeni fűtés beszámít a minimumba" },
  { key: "ejszakai_tiltas", label: "Éjszakai tiltás" },
  { key: "autotoltes_tiltas", label: "Tiltás autótöltés alatt", needEv: true },
];

function fmtMin(min) {
  min = Math.max(0, Math.round(Number(min) || 0));
  const h = Math.floor(min / 60);
  const m = min % 60;
  if (h === 0) return `${m} perc`;
  return `${h} ó ${String(m).padStart(2, "0")} p`;
}
function fmtClock(min) {
  const s = Math.max(0, Math.round((Number(min) || 0) * 60));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return `${h}:${String(m).padStart(2, "0")}`;
}
function hhmm(t) {
  return String(t || "").slice(0, 5);
}

class OkosBojlerCard extends HTMLElement {
  static getStubConfig(hass) {
    const id = Object.keys(hass.states).find(
      (e) => e.startsWith("sensor.") && hass.states[e].attributes.okos_bojler
    );
    return { entity: id || "sensor.okos_bojler_allapot" };
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Add meg az 'entity' mezőt, pl. sensor.okos_bojler_allapot");
    }
    this._config = { show_settings: true, ...config };
    if (this._built) this._update();
  }

  getCardSize() {
    return 7;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) this._build();
    this._update();
  }

  /* ----------------------------------------------------------- helpers */
  _ent(key) {
    const st = this._hass.states[this._config.entity];
    return st && st.attributes.entities ? st.attributes.entities[key] : undefined;
  }
  _call(domain, service, data) {
    this._hass.callService(domain, service, data);
  }
  _$(sel) {
    return this.shadowRoot.querySelector(sel);
  }

  /* -------------------------------------------------------------- build */
  _build() {
    this._built = true;
    const root = this.attachShadow({ mode: "open" });
    const sliders = SLIDERS.map(
      (s) => `
      <div class="row slider" data-key="${s.key}">
        <div class="row-head"><span>${s.label}</span><b class="val">–</b></div>
        <input type="range" />
      </div>`
    ).join("");
    const toggles = TOGGLES.map(
      (t) => `
      <label class="row toggle" data-key="${t.key}">
        <span>${t.label}</span>
        <span class="sw"><input type="checkbox" /><i></i></span>
      </label>`
    ).join("");
    const modes = MODES.map(
      (m) => `<button class="mode" data-mode="${m.value}"><ha-icon icon="${m.icon}"></ha-icon>${m.label}</button>`
    ).join("");

    root.innerHTML = `
      <style>${this._css()}</style>
      <ha-card>
        <div class="hero">
          <div class="orb"><div class="ring"></div><ha-icon class="orb-icon" icon="mdi:water-boiler"></ha-icon></div>
          <div class="hero-text">
            <div class="title"></div>
            <div class="status"></div>
            <div class="sub"></div>
          </div>
          <div class="heat-chip"><ha-icon icon="mdi:fire"></ha-icon><span></span></div>
        </div>

        <div class="blocks">
          <span class="bchip night"><ha-icon icon="mdi:weather-night"></ha-icon><span></span></span>
          <span class="bchip ev"><ha-icon icon="mdi:ev-station"></ha-icon><span></span></span>
        </div>

        <div class="meters">
          <div class="meter batt">
            <div class="m-head"><span><ha-icon icon="mdi:battery-high"></ha-icon>Akkumulátor</span><b class="m-val"></b></div>
            <div class="bar"><div class="fill"></div><div class="mark on"></div><div class="mark off"></div></div>
            <div class="m-foot"></div>
          </div>
          <div class="meter mini">
            <div class="m-head"><span><ha-icon icon="mdi:timer-sand"></ha-icon>Napi minimum</span><b class="m-val"></b></div>
            <div class="bar"><div class="fill"></div></div>
            <div class="m-foot"></div>
          </div>
        </div>

        <div class="stats">
          <div class="stat" data-p="ma"><div class="s-lbl">Ma</div><div class="s-val"></div><div class="s-sub"></div></div>
          <div class="stat" data-p="het"><div class="s-lbl">Ezen a héten</div><div class="s-val"></div><div class="s-sub"></div></div>
          <div class="stat" data-p="honap"><div class="s-lbl">Ebben a hónapban</div><div class="s-val"></div><div class="s-sub"></div></div>
        </div>
        <div class="breakdown"></div>

        <div class="modes">${modes}</div>

        <button class="turbo">
          <ha-icon icon="mdi:rocket-launch"></ha-icon>
          <span class="t-main"></span>
          <span class="t-sub"></span>
          <div class="t-progress"></div>
        </button>

        <details class="settings">
          <summary><ha-icon icon="mdi:tune-variant"></ha-icon>Beállítások<ha-icon class="chev" icon="mdi:chevron-down"></ha-icon></summary>
          <div class="set-body">
            <div class="row times">
              <span>Tartalék fűtés időablaka</span>
              <div class="tw">
                <input type="time" data-key="tartalek_kezdete" />
                <span>–</span>
                <input type="time" data-key="tartalek_vege" />
              </div>
            </div>
            <div class="row times">
              <span>Éjszakai tiltás</span>
              <div class="tw">
                <input type="time" data-key="ejszaka_kezdete" />
                <span>–</span>
                <input type="time" data-key="ejszaka_vege" />
              </div>
            </div>
            ${sliders}
            ${toggles}
            <button class="reset"><ha-icon icon="mdi:restore"></ha-icon>Statisztika nullázása</button>
          </div>
        </details>
        <div class="warn" hidden></div>
      </ha-card>`;

    // Üzemmód gombok
    root.querySelectorAll(".mode").forEach((b) =>
      b.addEventListener("click", () => {
        const id = this._ent("uzemmod");
        if (id) this._call("select", "select_option", { entity_id: id, option: b.dataset.mode });
      })
    );

    // Turbó gomb
    root.querySelector(".turbo").addEventListener("click", () => {
      const a = this._attrs();
      const key = a.turbo_aktiv ? "turbo_leallitas" : "turbo_inditas";
      const id = this._ent(key);
      if (id) this._call("button", "press", { entity_id: id });
    });

    // Csúszkák
    this._dragging = {};
    root.querySelectorAll(".row.slider").forEach((row) => {
      const key = row.dataset.key;
      const input = row.querySelector("input");
      const val = row.querySelector(".val");
      const unit = SLIDERS.find((s) => s.key === key).unit;
      input.addEventListener("pointerdown", () => (this._dragging[key] = true));
      input.addEventListener("input", () => {
        this._dragging[key] = true;
        val.textContent = `${input.value} ${unit}`;
      });
      input.addEventListener("change", () => {
        const id = this._ent(key);
        if (id) this._call("number", "set_value", { entity_id: id, value: Number(input.value) });
        setTimeout(() => (this._dragging[key] = false), 1500);
      });
    });

    // Kapcsolók
    root.querySelectorAll(".row.toggle").forEach((row) => {
      const input = row.querySelector("input");
      input.addEventListener("change", () => {
        const id = this._ent(row.dataset.key);
        if (id) this._call("switch", input.checked ? "turn_on" : "turn_off", { entity_id: id });
      });
    });

    // Időpontok
    root.querySelectorAll("input[type=time]").forEach((input) =>
      input.addEventListener("change", () => {
        const id = this._ent(input.dataset.key);
        if (id && input.value) this._call("time", "set_value", { entity_id: id, time: `${input.value}:00` });
      })
    );

    // Nullázás
    root.querySelector(".reset").addEventListener("click", () => {
      if (!confirm("Biztosan nullázod a fűtési statisztikát?")) return;
      const id = this._ent("statisztika_nullazas");
      if (id) this._call("button", "press", { entity_id: id });
    });

    // Turbó visszaszámláló frissítése percenként a két állapotfrissítés között
    this._timer = setInterval(() => this._built && this._hass && this._update(), 30000);
  }

  disconnectedCallback() {
    if (this._timer) clearInterval(this._timer);
    this._timer = null;
  }
  connectedCallback() {
    if (this._built && !this._timer) {
      this._timer = setInterval(() => this._hass && this._update(), 30000);
    }
  }

  _attrs() {
    const st = this._hass && this._hass.states[this._config.entity];
    return st ? st.attributes : {};
  }

  /* ------------------------------------------------------------- update */
  _update() {
    if (!this._hass || !this._config) return;
    const st = this._hass.states[this._config.entity];
    const card = this._$("ha-card");
    const warn = this._$(".warn");
    if (!st) {
      warn.hidden = false;
      warn.textContent = `Nem található: ${this._config.entity}`;
      return;
    }
    const a = st.attributes;
    const style = REASON_STYLE[a.allapot_kulcs] || REASON_STYLE.var;
    const heating = !!a.futes_aktiv;
    card.style.setProperty("--ob-accent", style.color);
    card.classList.toggle("heating", heating);

    // Fejléc
    this._$(".title").textContent = this._config.title || a.friendly_name?.replace(/ Állapot$/, "") || "Bojler";
    this._$(".status").textContent = st.state;
    this._$(".orb-icon").setAttribute("icon", style.icon);
    const batt = a.akkumulator;
    const sub = [];
    sub.push(`Üzemmód: ${a.uzemmod}`);
    if (a.tartalek_ablakban) sub.push("tartalék ablak aktív");
    this._$(".sub").textContent = sub.join(" · ");
    this._$(".heat-chip span").textContent = heating ? "FŰT" : "KI";

    if (!a.kapcsolo_elerheto) {
      warn.hidden = false;
      warn.textContent = `A kapcsoló (${a.kapcsolo}) nem elérhető!`;
    } else {
      warn.hidden = true;
    }

    // Tiltások
    const night = this._$(".bchip.night");
    night.hidden = !a.ejszakai_tiltas;
    night.classList.toggle("on", !!a.ejszakai_tiltas_aktiv);
    night.querySelector("span").textContent =
      `Éjszaka ${hhmm(a.ejszaka_kezdete)}–${hhmm(a.ejszaka_vege)}` + (a.ejszakai_tiltas_aktiv ? " · TILTVA" : "");
    const ev = this._$(".bchip.ev");
    ev.hidden = !a.autotolto;
    ev.classList.toggle("on", !!a.autotoltes_tiltas_aktiv);
    ev.querySelector("span").textContent = a.autotoltes_folyamatban
      ? (a.autotoltes_tiltas ? "Autó tölt · TILTVA" : "Autó tölt")
      : "Autó nem tölt";

    // Akkumulátor
    const bm = this._$(".meter.batt");
    const bv = batt === null || batt === undefined ? null : Number(batt);
    bm.querySelector(".m-val").textContent = bv === null ? "n/a" : `${Math.round(bv)}%`;
    bm.querySelector(".fill").style.width = `${bv === null ? 0 : Math.min(100, Math.max(0, bv))}%`;
    bm.querySelector(".mark.on").style.left = `${a.bekapcsolasi_kuszob}%`;
    bm.querySelector(".mark.off").style.left = `${Math.min(a.kikapcsolasi_kuszob, a.bekapcsolasi_kuszob)}%`;
    bm.querySelector(".m-foot").textContent = a.napelemes_futes
      ? `Be: ≥ ${a.bekapcsolasi_kuszob}% · Ki: < ${Math.min(a.kikapcsolasi_kuszob, a.bekapcsolasi_kuszob)}%`
      : "Napelemes fűtés kikapcsolva";
    bm.classList.toggle("ok", bv !== null && bv >= a.bekapcsolasi_kuszob);

    // Napi minimum
    const mm = this._$(".meter.mini");
    const minimum = Number(a.napi_minimum_perc) || 0;
    const done = Number(a.beszamitott_ma_perc) || 0;
    const pct = minimum > 0 ? Math.min(100, (done / minimum) * 100) : 100;
    mm.querySelector(".m-val").textContent = `${Math.round(done)}/${Math.round(minimum)} p`;
    mm.querySelector(".fill").style.width = `${pct}%`;
    mm.classList.toggle("ok", pct >= 100);
    mm.querySelector(".m-foot").textContent = a.tartalek_futes
      ? `Tartalék: ${hhmm(a.tartalek_kezdete)} – ${hhmm(a.tartalek_vege)}` +
        (a.minimumbol_hatra_perc > 0 ? ` · még ${fmtMin(a.minimumbol_hatra_perc)}` : " · teljesítve ✓")
      : "Tartalék fűtés kikapcsolva";

    // Statisztika
    const kw = Number(a.teljesitmeny_kw) || 0;
    const stat = (p, min, prevLbl, prev) => {
      const el = this._$(`.stat[data-p="${p}"]`);
      el.querySelector(".s-val").textContent = fmtMin(min);
      el.querySelector(".s-sub").textContent =
        `≈ ${((min / 60) * kw).toFixed(1)} kWh · ${prevLbl}: ${fmtMin(prev)}`;
    };
    stat("ma", a.ma_perc, "tegnap", a.tegnap_perc);
    stat("het", a.het_perc, "előző", a.elozo_het_perc);
    stat("honap", a.honap_perc, "előző", a.elozo_honap_perc);

    // Mai bontás
    const b = a.ma_bontas_perc || {};
    const parts = [
      ["napelem", "Napelem", REASON_STYLE.napelem.color],
      ["tartalek", "Tartalék", REASON_STYLE.tartalek.color],
      ["turbo", "Turbó", REASON_STYLE.turbo.color],
      ["kezi", "Kézi", REASON_STYLE.kezi.color],
      ["egyeb", "Egyéb", "#94a3b8"],
    ];
    const total = parts.reduce((s, [k]) => s + (Number(b[k]) || 0), 0);
    this._$(".breakdown").innerHTML =
      total > 0
        ? `<div class="bd-bar">${parts
            .filter(([k]) => b[k] > 0)
            .map(([k, , c]) => `<span style="flex:${b[k]};background:${c}"></span>`)
            .join("")}</div>
           <div class="bd-legend">${parts
             .filter(([k]) => b[k] > 0)
             .map(([k, l, c]) => `<span><i style="background:${c}"></i>${l} ${fmtMin(b[k])}</span>`)
             .join("")}</div>`
        : `<div class="bd-empty">Ma még nem volt fűtés</div>`;

    // Üzemmód
    this.shadowRoot.querySelectorAll(".mode").forEach((btn) =>
      btn.classList.toggle("active", btn.dataset.mode === a.uzemmod)
    );

    // Turbó
    const tb = this._$(".turbo");
    tb.classList.toggle("active", !!a.turbo_aktiv);
    let remain = Number(a.turbo_hatra_perc) || 0;
    if (a.turbo_aktiv && a.turbo_vege) {
      remain = Math.max(0, (new Date(a.turbo_vege) - Date.now()) / 60000);
    }
    const hours = Number(a.turbo_ora) || 3;
    if (a.turbo_aktiv) {
      tb.querySelector(".t-main").textContent = `TURBÓ AKTÍV · még ${fmtClock(remain)}`;
      const paused = a.allapot_kulcs === "ejszaka" || a.allapot_kulcs === "autotoltes";
      tb.querySelector(".t-sub").textContent = paused
        ? `Szünetel: ${a.allapot_kulcs === "ejszaka" ? "éjszakai tiltás" : "autó tölt"} · koppints a leállításhoz`
        : "Koppints a leállításhoz";
      tb.querySelector(".t-progress").style.width = `${Math.min(100, (remain / (hours * 60)) * 100)}%`;
    } else {
      const hl = Number.isInteger(hours) ? hours : hours.toFixed(1).replace(".", ",");
      tb.querySelector(".t-main").textContent = `TURBÓ · ${hl} óra`;
      tb.querySelector(".t-sub").textContent = "Azonnali fűtés, akkutól függetlenül";
      tb.querySelector(".t-progress").style.width = "0%";
    }

    // Beállítások
    const settings = this._$(".settings");
    settings.hidden = this._config.show_settings === false;
    const active = this.shadowRoot.activeElement;
    this.shadowRoot.querySelectorAll(".row.slider").forEach((row) => {
      const key = row.dataset.key;
      const id = this._ent(key);
      const ns = id && this._hass.states[id];
      const input = row.querySelector("input");
      const needEv = SLIDERS.find((s) => s.key === key).needEv;
      row.hidden = !ns || (needEv && !a.autotolto);
      if (!ns || this._dragging[key] || active === input) return;
      input.min = ns.attributes.min;
      input.max = ns.attributes.max;
      input.step = ns.attributes.step;
      input.value = ns.state;
      const unit = SLIDERS.find((s) => s.key === key).unit;
      const v = Number(ns.state);
      row.querySelector(".val").textContent = `${Number.isInteger(v) ? v : v.toFixed(1)} ${unit}`;
    });
    this.shadowRoot.querySelectorAll(".row.toggle").forEach((row) => {
      const id = this._ent(row.dataset.key);
      const ns = id && this._hass.states[id];
      const needEv = TOGGLES.find((t) => t.key === row.dataset.key).needEv;
      row.hidden = !ns || (needEv && !a.autotolto);
      if (ns) row.querySelector("input").checked = ns.state === "on";
    });
    this.shadowRoot.querySelectorAll("input[type=time]").forEach((input) => {
      const id = this._ent(input.dataset.key);
      const ns = id && this._hass.states[id];
      if (ns && active !== input) input.value = hhmm(ns.state);
    });
  }

  /* ---------------------------------------------------------------- css */
  _css() {
    return `
    :host { --ob-accent: #64748b; }
    ha-card { padding: 16px; overflow: hidden; position: relative; }
    ha-icon { --mdc-icon-size: 18px; }
    .hero { display: flex; align-items: center; gap: 14px; margin-bottom: 16px; }
    .orb { position: relative; width: 58px; height: 58px; flex: none; border-radius: 50%;
      display: grid; place-items: center; color: #fff;
      background: radial-gradient(circle at 30% 30%, color-mix(in srgb, var(--ob-accent) 70%, #fff), var(--ob-accent));
      box-shadow: 0 6px 18px color-mix(in srgb, var(--ob-accent) 40%, transparent); }
    .orb-icon { --mdc-icon-size: 30px; }
    .ring { position: absolute; inset: -5px; border-radius: 50%; border: 2px solid var(--ob-accent); opacity: 0; }
    .heating .ring { animation: pulse 2s ease-out infinite; }
    @keyframes pulse { 0% { transform: scale(.9); opacity: .8; } 100% { transform: scale(1.35); opacity: 0; } }
    .hero-text { flex: 1; min-width: 0; }
    .title { font-size: 13px; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: .06em; }
    .status { font-size: 20px; font-weight: 600; color: var(--primary-text-color); line-height: 1.25; }
    .sub { font-size: 12px; color: var(--secondary-text-color); margin-top: 2px; }
    .heat-chip { display: flex; align-items: center; gap: 4px; padding: 6px 10px; border-radius: 999px;
      font-size: 12px; font-weight: 700; letter-spacing: .05em;
      background: var(--secondary-background-color, rgba(127,127,127,.12)); color: var(--secondary-text-color); }
    .heating .heat-chip { background: linear-gradient(135deg, #f97316, #ef4444); color: #fff; }
    .heating .heat-chip ha-icon { animation: flicker 1.2s ease-in-out infinite; }
    @keyframes flicker { 0%,100% { transform: scale(1) rotate(-3deg); } 50% { transform: scale(1.15) rotate(3deg); } }

    .blocks { display: flex; flex-wrap: wrap; gap: 6px; margin: -6px 0 12px; }
    .bchip { display: inline-flex; align-items: center; gap: 5px; padding: 4px 10px; border-radius: 999px;
      font-size: 11.5px; color: var(--secondary-text-color);
      background: var(--secondary-background-color, rgba(127,127,127,.1)); }
    .bchip[hidden] { display: none; }
    .bchip ha-icon { --mdc-icon-size: 15px; }
    .bchip.night.on { background: rgba(99,102,241,.18); color: #6366f1; font-weight: 600; }
    .bchip.ev.on { background: rgba(14,165,233,.18); color: #0ea5e9; font-weight: 600; }
    .row[hidden] { display: none; }
    .meters { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px; }
    @media (max-width: 420px) { .meters { grid-template-columns: 1fr; } }
    .meter { padding: 10px 12px; border-radius: 12px; background: var(--secondary-background-color, rgba(127,127,127,.08)); }
    .m-head { display: flex; justify-content: space-between; align-items: center; font-size: 13px; color: var(--secondary-text-color); }
    .m-head span { display: flex; align-items: center; gap: 6px; }
    .m-head b { color: var(--primary-text-color); font-size: 14px; white-space: nowrap; }
    .bar { position: relative; height: 8px; border-radius: 6px; margin: 8px 0 6px;
      background: color-mix(in srgb, var(--primary-text-color) 12%, transparent); }
    .fill { height: 100%; border-radius: 6px; background: #94a3b8; transition: width .6s ease; }
    .batt.ok .fill { background: linear-gradient(90deg, #84cc16, #22c55e); }
    .batt:not(.ok) .fill { background: linear-gradient(90deg, #f59e0b, #eab308); }
    .mini .fill { background: linear-gradient(90deg, #3b82f6, #6366f1); }
    .mini.ok .fill { background: linear-gradient(90deg, #22c55e, #16a34a); }
    .mark { position: absolute; top: -3px; width: 2px; height: 14px; border-radius: 1px; transform: translateX(-1px); }
    .mark.on { background: #16a34a; }
    .mark.off { background: #dc2626; opacity: .7; }
    .m-foot { font-size: 11px; color: var(--secondary-text-color); }

    .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
    .stat { padding: 10px; border-radius: 12px; text-align: center;
      border: 1px solid color-mix(in srgb, var(--primary-text-color) 10%, transparent); }
    .s-lbl { font-size: 11px; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: .04em; }
    .s-val { font-size: 17px; font-weight: 600; color: var(--primary-text-color); margin: 4px 0 2px; white-space: nowrap; }
    .s-sub { font-size: 10.5px; color: var(--secondary-text-color); }
    .breakdown { margin: 10px 0 14px; }
    .bd-bar { display: flex; height: 6px; border-radius: 4px; overflow: hidden; gap: 2px; }
    .bd-legend { display: flex; flex-wrap: wrap; gap: 4px 12px; margin-top: 6px; font-size: 11px; color: var(--secondary-text-color); }
    .bd-legend i { display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 4px; }
    .bd-empty { font-size: 11px; color: var(--secondary-text-color); text-align: center; }

    .modes { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; padding: 4px; border-radius: 12px;
      background: var(--secondary-background-color, rgba(127,127,127,.1)); margin-bottom: 12px; }
    .mode { display: flex; align-items: center; justify-content: center; gap: 6px; padding: 8px; border: none;
      border-radius: 9px; background: transparent; color: var(--secondary-text-color); font: inherit;
      font-size: 14px; cursor: pointer; transition: all .2s; }
    .mode.active { background: var(--card-background-color, #fff); color: var(--primary-text-color); font-weight: 600;
      box-shadow: 0 1px 4px rgba(0,0,0,.15); }

    .turbo { position: relative; width: 100%; display: grid; grid-template-columns: auto 1fr; grid-template-rows: auto auto;
      column-gap: 12px; align-items: center; text-align: left; padding: 12px 16px; border: none; border-radius: 14px;
      cursor: pointer; overflow: hidden; color: #fff; font: inherit;
      background: linear-gradient(135deg, #f97316, #ef4444); box-shadow: 0 4px 14px rgba(239,68,68,.35); }
    .turbo ha-icon { grid-row: span 2; --mdc-icon-size: 26px; }
    .t-main { font-weight: 700; letter-spacing: .04em; font-size: 15px; z-index: 1; }
    .t-sub { font-size: 11.5px; opacity: .9; z-index: 1; }
    .turbo ha-icon { z-index: 1; }
    .t-progress { position: absolute; left: 0; bottom: 0; height: 4px; background: rgba(255,255,255,.75); transition: width .6s; }
    .turbo.active { background: linear-gradient(135deg, #dc2626, #9f1239); }
    .turbo.active ha-icon { animation: flicker 1s ease-in-out infinite; }
    .turbo:active { transform: scale(.985); }

    .settings { margin-top: 12px; border-radius: 12px;
      border: 1px solid color-mix(in srgb, var(--primary-text-color) 10%, transparent); }
    .settings summary { list-style: none; display: flex; align-items: center; gap: 8px; padding: 10px 12px;
      cursor: pointer; font-size: 14px; color: var(--primary-text-color); }
    .settings summary::-webkit-details-marker { display: none; }
    .chev { margin-left: auto; transition: transform .2s; }
    .settings[open] .chev { transform: rotate(180deg); }
    .set-body { padding: 0 12px 12px; display: grid; gap: 12px; }
    .row { font-size: 13px; color: var(--primary-text-color); }
    .row-head { display: flex; justify-content: space-between; margin-bottom: 4px; }
    .row-head b { color: var(--ob-accent); }
    input[type=range] { width: 100%; accent-color: var(--ob-accent); }
    .times { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; }
    .tw { display: flex; align-items: center; gap: 6px; }
    input[type=time] { font: inherit; padding: 4px 6px; border-radius: 8px; color: var(--primary-text-color);
      background: var(--secondary-background-color, transparent);
      border: 1px solid color-mix(in srgb, var(--primary-text-color) 20%, transparent); }
    .toggle { display: flex; justify-content: space-between; align-items: center; cursor: pointer; gap: 10px; }
    .sw { position: relative; width: 38px; height: 22px; flex: none; }
    .sw input { opacity: 0; width: 0; height: 0; position: absolute; }
    .sw i { position: absolute; inset: 0; border-radius: 22px; transition: .2s;
      background: color-mix(in srgb, var(--primary-text-color) 25%, transparent); }
    .sw i::after { content: ""; position: absolute; width: 16px; height: 16px; left: 3px; top: 3px;
      border-radius: 50%; background: #fff; transition: .2s; box-shadow: 0 1px 3px rgba(0,0,0,.3); }
    .sw input:checked + i { background: var(--ob-accent); }
    .sw input:checked + i::after { transform: translateX(16px); }
    .reset { justify-self: start; display: flex; align-items: center; gap: 6px; border: none; background: none;
      color: var(--error-color, #dc2626); font: inherit; font-size: 12px; cursor: pointer; padding: 4px 0; }
    .warn { margin-top: 10px; padding: 8px 10px; border-radius: 8px; font-size: 12px;
      background: rgba(220,38,38,.12); color: var(--error-color, #dc2626); }
    `;
  }
}

if (!customElements.get("okos-bojler-card")) {
  customElements.define("okos-bojler-card", OkosBojlerCard);
}
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "okos-bojler-card")) {
  window.customCards.push({
    type: "okos-bojler-card",
    name: "Okos Bojler kártya",
    description: "Napelemes bojlervezérlés: állapot, statisztika, turbó és beállítások",
    preview: true,
  });
}
console.info(`%c OKOS-BOJLER-CARD %c v${OB_VERSION} `, "background:#ef4444;color:#fff;font-weight:700", "background:#333;color:#fff");
