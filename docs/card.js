(() => {
  "use strict";

  const CFG = Object.assign(
    { SHARE_BASE: "", INVITE_URL: "", TWEMOJI_BASE: "https://cdn.jsdelivr.net/gh/jdecked/twemoji@15.1.0/assets/svg/" },
    window.WRAPPED_CONFIG || {}
  );

  const CARD_W = 667;
  const CARD_H = 711;
  const QR_QUIET = 1;            
  const QR_COLOR = "#262624";
  const TRANSPARENT_PX = "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==";

  
  const LIMITS = { channel: 440, total: 418, chatter: 562 };
  const MIN_SCALE = 0.4;        

  const $ = (id) => document.getElementById(id);

 

  const clip = (v, n) => {
    const a = Array.from(String(v == null ? "" : v));
    return a.length <= n ? a.join("") : a.slice(0, n - 1).join("") + "…";
  };

  function decodePayload(s) {
    const b64 = s.replace(/-/g, "+").replace(/_/g, "/");
    const bin = atob(b64 + "=".repeat((4 - (b64.length % 4)) % 4));
    const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
    const a = JSON.parse(new TextDecoder().decode(bytes));
    if (!Array.isArray(a) || a[0] !== 1) throw new Error("unknown payload version");

    const num = (v) => (Number.isFinite(+v) && +v >= 0 ? Math.floor(+v) : 0);
    const id = (v) => (/^\d{1,20}$/.test(String(v)) ? String(v) : "");
    const hash = (v) => (/^(a_)?[a-f0-9]{32}$/i.test(String(v)) ? String(v) : "");
    const day = (v) => (/^\d{4}-\d{2}-\d{2}$/.test(String(v)) && !isNaN(Date.parse(v)) ? String(v) : "");
    const emoji = (v) => {
      const e = clip(v, 24);
      return /^:\d{1,20}$/.test(e) || (e && !e.startsWith(":")) ? e : "";
    };

    return {
      server: clip(a[1], 40),
      channel: clip(a[2], 32),
      days: num(a[3]) || 30,
      end: day(a[4]),
      total: num(a[5]),
      name: clip(a[6], 32),
      uid: id(a[7]),
      avatar: hash(a[8]),
      emoji: emoji(a[9]),
    };
  }

  function encodePayload(d) {
    const arr = [1, d.server, d.channel, d.days, d.end, d.total, d.name, d.uid || "", d.avatar || "", d.emoji || ""];
    const bytes = new TextEncoder().encode(JSON.stringify(arr));
    let bin = "";
    bytes.forEach((b) => (bin += String.fromCharCode(b)));
    return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  
  const DEMO = {
    server: "Hack Club", channel: "channel", days: 30, end: "2026-10-26",
    total: 54045, name: "username", uid: "", avatar: "", emoji: "😂",
  };
  const DEMO_LONG = {
    server: "The Extremely Long Server Name That Keeps Going", channel: "super-duper-long-channel-name-here",
    days: 30, end: "2026-10-26", total: 1234567890,
    name: "Řehoř Žlutoučký-Kůň the Magnificent", uid: "", avatar: "", emoji: "👨‍👩‍👧‍👦",
  };

  
  function shareBase() {
    const c = CFG.SHARE_BASE;
    if (c && !/YOUR-USERNAME/i.test(c)) return c;
    if (/^https?:$/.test(location.protocol)) return location.origin + location.pathname;
    return c || "";
  }
  const shareUrl = (payload) => shareBase() + "#" + payload;

  
  function fit(el, maxW) {
    el.classList.remove("clip");
    el.style.fontSize = "";
    el.style.maxWidth = "";
    const base = parseFloat(getComputedStyle(el).fontSize);
    let size = base;
    for (let i = 0; i < 4 && el.offsetWidth > maxW + 0.5; i++) {
      size = Math.max(base * MIN_SCALE, size * (maxW / el.offsetWidth) * 0.995);
      el.style.fontSize = size + "px";
      if (size <= base * MIN_SCALE) break;
    }
    if (el.offsetWidth > maxW + 0.5) {
      el.classList.add("clip");
      el.style.maxWidth = maxW + "px";
    }
  }

  

  const SILHOUETTE =
    '<svg viewBox="0 0 240 240" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">' +
    '<rect width="240" height="240" fill="#d9d9d5"/>' +
    '<g fill="none" stroke="#262624" stroke-width="11">' +
    '<circle cx="120" cy="92" r="31"/>' +
    '<path d="M36 214 A84 62 0 0 1 204 214"/></g></svg>';

  function loadImage(box, src, onFail) {
    return new Promise((resolve) => {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.decoding = "async";
      img.alt = "";
      let done = false;
      const finish = () => { if (!done) { done = true; resolve(); } };
      img.onload = () => { box.appendChild(img); finish(); };
      img.onerror = () => { onFail(); finish(); };
      setTimeout(() => { if (!done) { onFail(); finish(); } }, 8000);
      img.src = src;
    });
  }

  function renderAvatar(box, d) {
    box.textContent = "";
    let url = "";
    if (d.uid && d.avatar) {
      url = `https://cdn.discordapp.com/avatars/${d.uid}/${d.avatar}.png?size=512`;
    } else if (d.uid) {
      try { url = `https://cdn.discordapp.com/embed/avatars/${Number((BigInt(d.uid) >> 22n) % 6n)}.png`; } catch (e) { /* no BigInt */ }
    }
    const fallback = () => { box.textContent = ""; box.innerHTML = SILHOUETTE; };
    return url ? loadImage(box, url, fallback) : (fallback(), Promise.resolve());
  }

  function twemojiUrl(str) {
    const cps = Array.from(str).map((c) => c.codePointAt(0).toString(16));
    const parts = cps.includes("200d") ? cps : cps.filter((c) => c !== "fe0f");
    return CFG.TWEMOJI_BASE + parts.join("-") + ".svg";
  }

  function renderEmoji(box, e) {
    box.textContent = "";
    box.classList.remove("native");
    if (!e) { box.textContent = "—"; return Promise.resolve(); }
    const custom = e.startsWith(":");
    const src = custom ? `https://cdn.discordapp.com/emojis/${e.slice(1)}.png?size=128` : twemojiUrl(e);
    const fallback = () => {
      box.textContent = custom ? "—" : e;
      if (!custom) box.classList.add("native");
    };
    return loadImage(box, src, fallback);
  }

  function renderQR(box, text) {
    const qr = qrcode(0, "L");           
    qr.addData(text, "Byte");
    qr.make();
    const n = qr.getModuleCount();
    const size = n + QR_QUIET * 2;
    let path = "";
    for (let r = 0; r < n; r++) {        
      for (let c = 0; c < n; ) {
        if (!qr.isDark(r, c)) { c++; continue; }
        let len = 1;
        while (c + len < n && qr.isDark(r, c + len)) len++;
        path += `M${c + QR_QUIET} ${r + QR_QUIET}h${len}v1h-${len}z`;
        c += len;
      }
    }
    box.innerHTML =
      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${size} ${size}" shape-rendering="crispEdges" aria-hidden="true">` +
      `<path d="${path}" fill="${QR_COLOR}"/></svg>`;
  }

 

  const fmtNum = (n) => new Intl.NumberFormat("en-US").format(n);
  const fmtDay = (ms) =>
    new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" }).format(new Date(ms));
  const slug = (s) =>
    String(s).toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "card";

  function periodText(d) {
    const label = d.days === 1 ? "Last day" : `Last ${d.days} days`;
    if (!d.end) return label;
    const end = Date.parse(d.end + "T00:00:00Z");
    return `${label} · ${fmtDay(end - d.days * 864e5)} – ${fmtDay(end)}`;
  }

  function fontsFor(d) {
    const f = document.fonts;
    return Promise.all([
      f.load("300 65px Inter", "#" + d.channel),
      f.load("400 22px Inter", "Total Messages Top Chatter Favorite Emoji Share it!"),
      f.load("700 68px Inter", d.name + "@0123456789,"),
      f.load("700 32px Inter", "Scan the QR"),
    ]).then(() => f.ready).catch(() => {});
  }

  

  function showEmpty() {
    $("empty").hidden = false;
    window.__cardReady = true;
  }

  function layout() {
    const render = document.documentElement.classList.contains("render");
    const s = render ? 1 : Math.min(1, (document.documentElement.clientWidth - 32) / CARD_W);
    document.documentElement.style.setProperty("--s", String(Math.max(0.3, s)));
  }

  async function main() {
    const q = new URLSearchParams(location.search);
    if (q.has("render")) document.documentElement.classList.add("render");  
    layout();
    window.addEventListener("resize", layout);

    let payload = location.hash.slice(1);
    let data = null;
    try {
      if (!payload && q.has("demo")) {
        payload = encodePayload(q.get("demo") === "long" ? DEMO_LONG : DEMO);
      }
      if (payload) data = decodePayload(payload);
    } catch (e) {
      data = null;
    }
    if (!data) return showEmpty();

    const url = shareUrl(payload);


    document.title = `${data.server || "Server"} · Wrapped`;
    $("serverName").textContent = data.server || "Wrapped";
    $("period").textContent = periodText(data);
    $("intro").hidden = false;
    $("stage").hidden = false;
    $("actions").hidden = false;
    if (CFG.INVITE_URL && /^https:\/\//.test(CFG.INVITE_URL)) {
      $("inviteLink").href = CFG.INVITE_URL;
      $("invite").hidden = false;
    }


    const card = $("card");
    const total = fmtNum(data.total);
    const chatter = "@" + data.name;
    $("channel").textContent = data.channel;
    $("total").textContent = total;
    $("chatter").textContent = chatter;
    card.setAttribute(
      "aria-label",
      `Wrapped for #${data.channel}: ${total} messages, top chatter ${chatter}${data.emoji && !data.emoji.startsWith(":") ? ", favorite emoji " + data.emoji : ""}`
    );
    renderQR($("qr"), url);

    await fontsFor(data);
    fit($("channel"), LIMITS.channel);
    fit($("total"), LIMITS.total);
    fit($("chatter"), LIMITS.chatter);

    await Promise.all([renderAvatar($("avatar"), data), renderEmoji($("emoji"), data.emoji)]);

    window.__cardReady = true;                      
    document.documentElement.dataset.ready = "1";

    wireButtons(data, url);
  }

  function wireButtons(data, url) {
    const status = $("status");
    const say = (msg) => {
      status.textContent = msg;
      status.hidden = false;
      clearTimeout(say.t);
      say.t = setTimeout(() => (status.hidden = true), 3500);
    };

    $("copyBtn").addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(url);
      } catch (e) {
        const ta = document.createElement("textarea");
        ta.value = url;
        ta.style.cssText = "position:fixed;opacity:0";
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand("copy"); } catch (e2) { /* ignore */ }
        ta.remove();
      }
      say("Link copied");
    });

    $("downloadBtn").addEventListener("click", async (ev) => {
      const btn = ev.currentTarget;
      btn.disabled = true;
      say("Making the image…");
      try {
        const png = await htmlToImage.toPng($("card"), {
          pixelRatio: 3, width: CARD_W, height: CARD_H, imagePlaceholder: TRANSPARENT_PX,
        });
        const a = document.createElement("a");
        a.href = png;
        a.download = `wrapped-${slug(data.channel)}${data.end ? "-" + data.end : ""}.png`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        say("Image saved");
      } catch (e) {
        console.error(e);
        say("Couldn't make the image. A screenshot works too.");
      } finally {
        btn.disabled = false;
      }
    });
  }

  main();
})();
