# Contact-pagina + Navigatie-overflow Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `contact.html` page (company info + anti-spam contact form) to the tessar.nl public
site, add a "Contact" nav link across the site, and fix a nav-overflow bug where the "Plan gesprek"
button disappears off-screen at certain browser widths.

**Architecture:** Plain static HTML pages under `preview/` (no build step, no templating for these
pages — `index.html` is the one exception, it uses a `{{ }}` runtime templating layer for bilingual
NL/EN copy, everything else in this plan is hand-authored static markup). Each page repeats the same
header/nav/footer boilerplate inline (established pattern in this repo — do not introduce a shared
include/component system, that would be a bigger refactor out of scope here).

**Tech Stack:** Vanilla HTML/CSS (inline styles, oklch colors, `clamp()`), vanilla JS (no framework),
`fetch` to an existing `/api/contact` backend (out of scope — not touched by this plan).

## Global Constraints

- Company info to add: phone `+31625577016` (display `+31 6 25577016`, `tel:+31625577016`), email
  `info@tessar.nl`, BTW `NL004739184B63`, KVK `89498593`.
- New/changed form fields must POST the exact same JSON shape the existing homepage form
  (`preview/index.html#contact`) sends to `/api/contact` — `name`, `email`, `phone`, `industry`,
  `message`, `website` (honeypot), `started_at` (timestamp) — so the backend needs zero changes.
- Nav hamburger breakpoint changes from `max-width: 680px` to `max-width: 960px` on every page this
  plan touches.
- Nav gap is normalized to `gap:clamp(12px,1.5vw,24px)` with `flex-wrap:wrap;row-gap:10px;` added,
  on every page this plan touches.
- Root `index.html` (the "Binnenkort online" placeholder) is NOT touched — out of scope, stays as is.
- No changes to `/api/contact` backend, to Caddy/deploy config, or to the orphaned `.dc.html` pages.
- Work happens on a feature branch, not directly on `main` (push to `main` triggers a production
  deploy via GitHub Actions — do not push until the user explicitly asks for it).

---

### Task 1: Create feature branch and the new `contact.html` page

**Files:**
- Create: `preview/contact.html`

**Interfaces:**
- Produces: a page at `preview/contact.html` with `<form id="contact-form">` containing
  `#cf-name`, `#cf-email`, `#cf-phone`, `#cf-message`, `#cf-website` (honeypot), `#cf-submit`,
  `#cf-status` — same element ID scheme Task 3 (nav-link additions) and later verification steps
  rely on when checking this page's nav matches the others.

- [ ] **Step 1: Create and switch to a feature branch**

```bash
cd /Users/hamdeco/development/hamdoun
git checkout -b contact-page-nav-fix
```

Expected: `Switched to a new branch 'contact-page-nav-fix'`

- [ ] **Step 2: Create `preview/contact.html` with this exact content**

```html
<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Contact — Tessar | AI-implementatie voor het mkb</title>
<meta name="description" content="Neem contact op met Tessar voor AI-automatisering en AI-geintegreerde applicaties. Telefoon, e-mail en bedrijfsgegevens, of stuur direct een bericht.">
<link rel="canonical" href="https://tessar.nl/contact.html">
<meta name="theme-color" content="#0a0a0f">
<link rel="icon" type="image/png" sizes="32x32" href="./assets/favicon-32.png">
<link rel="icon" type="image/png" sizes="16x16" href="./assets/favicon-16.png">
<link rel="apple-touch-icon" href="./assets/apple-touch-icon.png">

<meta property="og:type" content="website">
<meta property="og:locale" content="nl_NL">
<meta property="og:url" content="https://tessar.nl/contact.html">
<meta property="og:title" content="Contact — Tessar">
<meta property="og:description" content="Telefoon, e-mail en bedrijfsgegevens van Tessar, of stuur direct een bericht.">
<meta property="og:image" content="https://tessar.nl/Tessar-logo-symbol.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Contact — Tessar">
<meta name="twitter:description" content="Telefoon, e-mail en bedrijfsgegevens van Tessar, of stuur direct een bericht.">
<meta name="twitter:image" content="https://tessar.nl/Tessar-logo-symbol.png">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  html, body { margin:0; padding:0; background:oklch(98% 0.004 90); }
  html { scroll-behavior:smooth; }
  body { font-family:'IBM Plex Sans', -apple-system, 'Segoe UI', sans-serif; color:oklch(18% 0.02 255); line-height:1.55; -webkit-font-smoothing:antialiased; }
  a { color:oklch(18% 0.02 255); text-decoration:none; }
  a:hover { color:oklch(48% 0.12 230); }
  [data-reveal] { opacity:0; transform:translateY(18px); transition:opacity 600ms ease, transform 600ms ease; }
  [data-reveal].is-visible { opacity:1; transform:translateY(0); }
  .nav-toggle { display:none; background:none; border:none; cursor:pointer; padding:8px; flex-direction:column; gap:5px; margin-left:4px; }
  .nav-toggle span { display:block; width:22px; height:2px; background:oklch(18% 0.02 255); border-radius:2px; transition:transform 200ms ease, opacity 200ms ease; }
  .nav-mobile-panel { display:none; }
  @media (max-width: 960px) {
    .nav-link { display:none; }
    .nav-toggle { display:flex; }
    .nav-mobile-panel { display:none; flex-direction:column; padding:8px 20px 20px; background:oklch(98% 0.004 90); border-top:1px solid oklch(90% 0.006 90); }
    .nav-mobile-panel.nav-open { display:flex; }
    .nav-mobile-panel a { display:block; padding:14px 0; font:500 1rem/1.3 'IBM Plex Sans'; color:oklch(24% 0.02 255); border-bottom:1px solid oklch(91% 0.006 90); }
    .nav-mobile-panel a:last-child { border-bottom:none; margin-top:8px; }
    .nav-toggle.nav-toggle-active span:nth-child(1) { transform:translateY(7px) rotate(45deg); }
    .nav-toggle.nav-toggle-active span:nth-child(2) { opacity:0; }
    .nav-toggle.nav-toggle-active span:nth-child(3) { transform:translateY(-7px) rotate(-45deg); }
  }
  /* Sits left of the fixed Tess concierge launcher (60px circle at bottom:24px/right:24px, see
     tessar-concierge-widget.js), same row, so it never collides with the launcher or its hint bubble
     (which pops up above the launcher, not beside it). */
  #back-to-top { position:fixed; right:100px; bottom:24px; z-index:40; width:48px; height:48px; border-radius:50%; border:none; background:oklch(70% 0.14 220); color:#001a2e; display:flex; align-items:center; justify-content:center; cursor:pointer; box-shadow:0 8px 24px oklch(20% 0.02 255 / 0.25); opacity:0; transform:translateY(12px); pointer-events:none; transition:opacity 260ms ease, transform 260ms ease, box-shadow 200ms ease; }
  #back-to-top.is-visible { opacity:1; transform:translateY(0); pointer-events:auto; }
  #back-to-top:hover { transform:translateY(-3px); box-shadow:0 12px 32px rgba(0,212,255,0.35); }
  #back-to-top:focus-visible { outline:2px solid oklch(48% 0.12 230); outline-offset:3px; }
  @media (max-width: 480px) { #back-to-top { right:92px; bottom:16px; } }
  @media (prefers-reduced-motion: reduce) {
    [data-reveal] { opacity:1; transform:none; transition:none; }
    html { scroll-behavior:auto; }
    #back-to-top { transition:opacity 200ms ease; transform:none; }
  }
  .contact-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:clamp(24px,4vw,40px); }
  .contact-field { background:oklch(100% 0 0 / 0.95); border:1px solid oklch(70% 0.14 220 / 0.3); border-radius:6px; padding:14px 18px; font:400 0.95rem/1.5 'IBM Plex Sans'; color:oklch(18% 0.02 255); transition:all 200ms ease; width:100%; box-sizing:border-box; }
  .contact-field:focus { border-color:oklch(70% 0.14 220); box-shadow:0 0 0 2px oklch(70% 0.14 220 / 0.1); outline:none; }
</style>
</head>
<body>

<header style="position:sticky;top:0;z-index:30;background:color-mix(in oklch, oklch(98% 0.004 90) 92%, transparent);backdrop-filter:blur(12px);border-bottom:1px solid oklch(90% 0.006 90);padding:16px clamp(20px,5vw,40px);">
  <div style="display:flex;align-items:center;justify-content:space-between;max-width:1400px;margin:0 auto;">
    <a href="./index.html" style="display:flex;align-items:center;gap:10px;flex-shrink:0;">
      <img src="./assets/tessar-icon-optimized.png" width="32" height="35" alt="Tessar logo" style="height:32px;width:auto;">
      <span style="font:700 1rem/1 'IBM Plex Sans';letter-spacing:-0.015em;color:oklch(18% 0.02 255);">Tessar</span>
    </a>
    <nav style="display:flex;flex-wrap:wrap;align-items:center;row-gap:10px;gap:clamp(12px,1.5vw,24px);font-size:0.9375rem;">
      <a href="./services.html" class="nav-link" style="color:oklch(46% 0.012 140);transition:color 200ms ease;">Diensten</a>
      <a href="./index.html#industries" class="nav-link" style="color:oklch(46% 0.012 140);transition:color 200ms ease;">Sectoren</a>
      <a href="./index.html#cases" class="nav-link" style="color:oklch(46% 0.012 140);transition:color 200ms ease;">Cases</a>
      <a href="./prijzen.html" class="nav-link" style="color:oklch(46% 0.012 140);transition:color 200ms ease;">Prijzen</a>
      <a href="./chatbots.html" class="nav-link" style="color:oklch(46% 0.012 140);transition:color 200ms ease;">Chatbots</a>
      <a href="./contact.html" class="nav-link" style="color:oklch(18% 0.02 255);font-weight:600;">Contact</a>
      <a href="./index.html#contact" style="background:oklch(70% 0.14 220);color:#001a2e;padding:10px 20px;border-radius:6px;font-weight:600;transition:all 200ms ease;">Plan gesprek</a>
    </nav>
    <button type="button" class="nav-toggle" id="nav-toggle-btn" aria-label="Menu" aria-expanded="false" aria-controls="nav-mobile-panel">
      <span></span><span></span><span></span>
    </button>
  </div>
  <div class="nav-mobile-panel" id="nav-mobile-panel">
      <a href="./services.html" style="color:oklch(46% 0.012 140);transition:color 200ms ease;">Diensten</a>
      <a href="./index.html#industries" style="color:oklch(46% 0.012 140);transition:color 200ms ease;">Sectoren</a>
      <a href="./index.html#cases" style="color:oklch(46% 0.012 140);transition:color 200ms ease;">Cases</a>
      <a href="./prijzen.html" style="color:oklch(46% 0.012 140);transition:color 200ms ease;">Prijzen</a>
      <a href="./chatbots.html" style="color:oklch(46% 0.012 140);transition:color 200ms ease;">Chatbots</a>
      <a href="./contact.html" style="color:oklch(18% 0.02 255);font-weight:600;">Contact</a>
      <a href="./index.html#contact" style="background:oklch(70% 0.14 220);color:#001a2e;padding:10px 20px;border-radius:6px;font-weight:600;transition:all 200ms ease;">Plan gesprek</a>
  </div>
</header>

<section style="position:relative;overflow:hidden;background:linear-gradient(135deg, oklch(6% 0 0) 0%, oklch(12% 0.03 260) 100%);color:#FFF;padding:clamp(64px,9vw,100px) clamp(20px,5vw,40px) clamp(56px,7vw,80px);text-align:center;">
  <div style="max-width:800px;margin:0 auto;position:relative;z-index:1;">
    <div style="display:inline-block;background:oklch(70% 0.14 220 / 0.15);border:1px solid oklch(70% 0.14 220 / 0.3);padding:10px 16px;border-radius:20px;margin-bottom:24px;font-size:0.8125rem;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:oklch(70% 0.14 220);">Contact</div>
    <h1 style="font:800 clamp(2rem,4.5vw,3rem)/1.2 'IBM Plex Sans';margin:0 0 18px;letter-spacing:-0.02em;">Neem contact op</h1>
    <p style="font:400 clamp(1rem,1.6vw,1.125rem)/1.7 'IBM Plex Sans';color:oklch(75% 0.10 250);margin:0;">Vragen, een concreet idee of gewoon kennismaken — bereik ons rechtstreeks of stuur een bericht.</p>
  </div>
</section>

<section style="padding:clamp(56px,7vw,88px) clamp(20px,5vw,40px);background:#FFF;">
  <div class="contact-grid" style="max-width:1100px;margin:0 auto;align-items:start;">

    <div data-reveal style="border:1px solid oklch(91% 0.006 90);border-radius:12px;padding:clamp(28px,4vw,40px);transition:opacity 600ms ease, transform 600ms ease;">
      <h2 style="font:600 1.375rem/1.3 'IBM Plex Sans';margin:0 0 20px;color:oklch(18% 0.02 255);">Bedrijfsgegevens</h2>
      <dl style="margin:0;display:flex;flex-direction:column;gap:20px;">
        <div>
          <dt style="font:600 0.75rem/1.2 'IBM Plex Mono';letter-spacing:0.05em;text-transform:uppercase;color:oklch(48% 0.12 230);margin-bottom:6px;">Telefoon</dt>
          <dd style="margin:0;font:400 1rem/1.5 'IBM Plex Sans';"><a href="tel:+31625577016" style="color:oklch(18% 0.02 255);">+31 6 25577016</a></dd>
        </div>
        <div>
          <dt style="font:600 0.75rem/1.2 'IBM Plex Mono';letter-spacing:0.05em;text-transform:uppercase;color:oklch(48% 0.12 230);margin-bottom:6px;">E-mail</dt>
          <dd style="margin:0;font:400 1rem/1.5 'IBM Plex Sans';"><a href="mailto:info@tessar.nl" style="color:oklch(18% 0.02 255);">info@tessar.nl</a></dd>
        </div>
        <div>
          <dt style="font:600 0.75rem/1.2 'IBM Plex Mono';letter-spacing:0.05em;text-transform:uppercase;color:oklch(48% 0.12 230);margin-bottom:6px;">BTW-nummer</dt>
          <dd style="margin:0;font:400 1rem/1.5 'IBM Plex Sans';color:oklch(40% 0.012 140);">NL004739184B63</dd>
        </div>
        <div>
          <dt style="font:600 0.75rem/1.2 'IBM Plex Mono';letter-spacing:0.05em;text-transform:uppercase;color:oklch(48% 0.12 230);margin-bottom:6px;">KVK-nummer</dt>
          <dd style="margin:0;font:400 1rem/1.5 'IBM Plex Sans';color:oklch(40% 0.012 140);">89498593</dd>
        </div>
      </dl>
    </div>

    <div data-reveal style="border:1px solid oklch(91% 0.006 90);border-radius:12px;padding:clamp(28px,4vw,40px);transition:opacity 600ms ease, transform 600ms ease;">
      <h2 style="font:600 1.375rem/1.3 'IBM Plex Sans';margin:0 0 20px;color:oklch(18% 0.02 255);">Stuur een bericht</h2>
      <form id="contact-form" style="display:flex;flex-direction:column;gap:16px;">
        <input type="text" name="name" id="cf-name" required placeholder="Naam" class="contact-field"/>
        <input type="email" name="email" id="cf-email" required placeholder="E-mailadres" class="contact-field"/>
        <input type="tel" name="phone" id="cf-phone" placeholder="Telefoonnummer (optioneel)" class="contact-field"/>
        <textarea name="message" id="cf-message" required placeholder="Je bericht" rows="5" class="contact-field" style="resize:none;"></textarea>
        <input type="text" name="website" id="cf-website" autocomplete="off" tabindex="-1" aria-hidden="true" style="position:absolute;left:-9999px;width:1px;height:1px;opacity:0;">
        <button type="submit" id="cf-submit" style="background:linear-gradient(135deg, oklch(70% 0.14 220), oklch(60% 0.12 230));color:#001a2e;padding:14px 28px;border:none;border-radius:6px;font-weight:700;font-size:0.95rem;cursor:pointer;transition:all 280ms ease;">Verstuur bericht</button>
        <p id="cf-status" role="status" style="font:400 0.9rem/1.5 'IBM Plex Sans';margin:0;min-height:1.4em;"></p>
      </form>
      <script>
      (function () {
        var pageLoadTime = Date.now();

        document.addEventListener("submit", function (e) {
          var form = e.target;
          if (!form || form.id !== "contact-form") return;
          e.preventDefault();

          var submitBtn = form.querySelector("#cf-submit");
          var status = form.querySelector("#cf-status");
          var originalBtnText = submitBtn.textContent;
          submitBtn.disabled = true;
          submitBtn.textContent = "Versturen...";
          status.textContent = "";
          status.style.color = "";

          fetch("/api/contact", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              name: form.querySelector("#cf-name").value,
              email: form.querySelector("#cf-email").value,
              phone: form.querySelector("#cf-phone").value,
              industry: "",
              message: form.querySelector("#cf-message").value,
              website: form.querySelector("#cf-website").value,
              started_at: pageLoadTime
            })
          })
            .then(function (res) { return res.json().then(function (data) { return { ok: res.ok, data: data }; }); })
            .then(function (result) {
              if (result.ok && result.data.ok) {
                form.reset();
                status.style.color = "oklch(70% 0.14 220)";
                status.textContent = "Bedankt! We nemen zo snel mogelijk contact op.";
              } else {
                status.style.color = "oklch(65% 0.20 30)";
                status.textContent = (result.data && result.data.error) || "Er ging iets mis, probeer het later opnieuw.";
              }
            })
            .catch(function () {
              status.style.color = "oklch(65% 0.20 30)";
              status.textContent = "Er ging iets mis, probeer het later opnieuw.";
            })
            .finally(function () {
              submitBtn.disabled = false;
              submitBtn.textContent = originalBtnText;
            });
        });
      })();
      </script>
    </div>

  </div>
</section>

<footer style="padding:32px clamp(20px,5vw,40px);background:oklch(6% 0 0);color:oklch(60% 0.02 250);text-align:center;font:400 0.85rem/1.6 'IBM Plex Sans';">
  <a href="./index.html" style="color:oklch(70% 0.10 250);">Tessar</a>. AI-implementatie en AI-geintegreerde applicaties voor Nederlandse en Europese mkb-bedrijven. <a href="/login" style="color:oklch(60% 0.02 250);">Login</a>
</footer>

<button type="button" id="back-to-top" aria-label="Naar boven" title="Naar boven">
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5"/><path d="m5 12 7-7 7 7"/></svg>
</button>

<script>
(function () {
  "use strict";
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var els = document.querySelectorAll("[data-reveal]");
  if (reduceMotion || !("IntersectionObserver" in window)) {
    els.forEach(function (el) { el.classList.add("is-visible"); });
    return;
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
  els.forEach(function (el) { io.observe(el); });
})();
</script>
<script>
(function () {
  "use strict";
  document.addEventListener("click", function (e) {
    var toggle = e.target.closest && e.target.closest("#nav-toggle-btn");
    if (toggle) {
      var panel = document.getElementById("nav-mobile-panel");
      var open = panel.classList.toggle("nav-open");
      toggle.classList.toggle("nav-toggle-active", open);
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      return;
    }
    var link = e.target.closest && e.target.closest("#nav-mobile-panel a");
    if (link) {
      var panel2 = document.getElementById("nav-mobile-panel");
      var btn2 = document.getElementById("nav-toggle-btn");
      panel2.classList.remove("nav-open");
      if (btn2) {
        btn2.classList.remove("nav-toggle-active");
        btn2.setAttribute("aria-expanded", "false");
      }
    }
  });
})();
</script>
<script>
(function () {
  "use strict";
  var btn = document.getElementById("back-to-top");
  if (!btn) return;
  var threshold = 480;

  function onScroll() {
    var y = window.scrollY || window.pageYOffset || 0;
    btn.classList.toggle("is-visible", y > threshold);
  }

  var ticking = false;
  window.addEventListener("scroll", function () {
    if (!ticking) {
      requestAnimationFrame(function () { onScroll(); ticking = false; });
      ticking = true;
    }
  }, { passive: true });
  onScroll();

  btn.addEventListener("click", function () {
    var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
  });
})();
</script>
<script src="./tessar-concierge-widget.js" defer></script>
</body>
</html>
```

- [ ] **Step 3: Verify the file was created correctly**

Run:
```bash
cd /Users/hamdeco/development/hamdoun
grep -c '<form id="contact-form">' preview/contact.html
grep -c 'NL004739184B63' preview/contact.html
grep -c '89498593' preview/contact.html
grep -c 'tel:+31625577016' preview/contact.html
python3 -c "
import re
html = open('preview/contact.html').read()
for tag in ['div','section','header','footer','form','nav','dl','dt','dd','button','script','style']:
    opens = len(re.findall(r'<'+tag+r'(\s|>)', html))
    closes = len(re.findall(r'</'+tag+r'>', html))
    assert opens == closes, f'{tag}: open={opens} close={closes} MISMATCH'
print('all tags balanced')
"
```

Expected: each grep prints `1`, and the Python script prints `all tags balanced` with no
AssertionError.

- [ ] **Step 4: Commit**

```bash
git add preview/contact.html
git commit -m "Add contact.html: company info + anti-spam contact form"
```

---

### Task 2: Fix nav overflow + normalize nav gap across all five pages

**Files:**
- Modify: `preview/services.html` (nav `<style>` block ~line 77-87, nav gap ~line 123)
- Modify: `preview/chatbots.html` (nav `<style>` block ~line 42-52, nav gap ~line 75)
- Modify: `preview/prijzen.html` (nav `<style>` block ~line 30-40, nav gap ~line 82)
- Modify: `preview/index.html` (nav `<style>` block ~line 161-172, nav gap ~line 257)
- Modify: `preview/contact.html` (created in Task 1 — already has the fixed values baked in, only
  needs the verification in Step 5 below, no edit)

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: every page's `@media` breakpoint is `960px` (was `680px`), every page's nav `<nav>`
  opening tag contains `flex-wrap:wrap;` and `row-gap:10px;` and `gap:clamp(12px,1.5vw,24px)`. Task 3
  relies on the breakpoint/gap being identical across pages before adding the Contact link (so it
  doesn't need to special-case any page's CSS).

- [ ] **Step 1: Fix the breakpoint in `services.html`**

In `preview/services.html`, find:
```
  @media (max-width: 680px) {
    .nav-link { display:none; }
```
Replace with:
```
  @media (max-width: 960px) {
    .nav-link { display:none; }
```

- [ ] **Step 2: Fix the nav gap/wrap in `services.html`**

Find:
```
    <nav style="display:flex;align-items:center;gap:clamp(16px,2vw,32px);font-size:0.9375rem;">
```
Replace with:
```
    <nav style="display:flex;flex-wrap:wrap;align-items:center;row-gap:10px;gap:clamp(12px,1.5vw,24px);font-size:0.9375rem;">
```

- [ ] **Step 3: Repeat Steps 1-2 for `chatbots.html`**

Breakpoint — find:
```
  @media (max-width: 680px) {
    .nav-link { display:none; }
```
Replace with:
```
  @media (max-width: 960px) {
    .nav-link { display:none; }
```

Nav gap — find:
```
    <nav style="display:flex;align-items:center;gap:clamp(16px,2vw,32px);font-size:0.9375rem;">
```
Replace with:
```
    <nav style="display:flex;flex-wrap:wrap;align-items:center;row-gap:10px;gap:clamp(12px,1.5vw,24px);font-size:0.9375rem;">
```

- [ ] **Step 4: Repeat for `prijzen.html`**

Breakpoint — find:
```
  @media (max-width: 680px) {
    .nav-link { display:none; }
```
Replace with:
```
  @media (max-width: 960px) {
    .nav-link { display:none; }
```

Nav gap — find (note: `prijzen.html` has a different original gap than the other pages):
```
    <nav style="display:flex;align-items:center;gap:clamp(14px,2vw,28px);font-size:0.9375rem;">
```
Replace with:
```
    <nav style="display:flex;flex-wrap:wrap;align-items:center;row-gap:10px;gap:clamp(12px,1.5vw,24px);font-size:0.9375rem;">
```

- [ ] **Step 5: Repeat for `index.html`**

Breakpoint — find:
```
  @media (max-width: 680px) {
    .nav-link { display:none; }
```
Replace with:
```
  @media (max-width: 960px) {
    .nav-link { display:none; }
```

Nav gap — find (note: `index.html` has its own original gap, different from the other three):
```
    <nav style="display:flex;align-items:center;gap:clamp(12px,2vw,28px);font-size:0.9375rem;">
```
Replace with:
```
    <nav style="display:flex;flex-wrap:wrap;align-items:center;row-gap:10px;gap:clamp(12px,1.5vw,24px);font-size:0.9375rem;">
```

- [ ] **Step 6: Verify all five pages now match**

Run:
```bash
cd /Users/hamdeco/development/hamdoun/preview
for f in index.html services.html chatbots.html prijzen.html contact.html; do
  echo "=== $f ==="
  grep -c '@media (max-width: 960px) {' "$f"
  grep -c '@media (max-width: 680px)' "$f"
  grep -c 'gap:clamp(12px,1.5vw,24px)' "$f"
  grep -c 'flex-wrap:wrap' "$f"
done
```

Expected: for every file, the first grep prints `1`, the second prints `0` (no more `680px`
breakpoint left anywhere), the third prints `1` (the normalized nav gap), the fourth prints at least
`1`.

- [ ] **Step 7: Commit**

```bash
cd /Users/hamdeco/development/hamdoun
git add preview/index.html preview/services.html preview/chatbots.html preview/prijzen.html
git commit -m "Fix nav overflow: raise hamburger breakpoint to 960px, add flex-wrap, normalize nav gap"
```

---

### Task 3: Add "Contact" nav link across all five pages

**Files:**
- Modify: `preview/services.html` (desktop nav + mobile panel)
- Modify: `preview/chatbots.html` (desktop nav + mobile panel)
- Modify: `preview/prijzen.html` (desktop nav + mobile panel)
- Modify: `preview/index.html` (desktop nav + mobile panel)
- (`preview/contact.html` already has its own nav-link in the "active" bold state from Task 1 — no
  change needed here.)

**Interfaces:**
- Consumes: the normalized nav markup from Task 2 (breakpoint/gap already fixed, so this task only
  adds a link, it doesn't need to touch CSS).
- Produces: every page's desktop nav and mobile panel contains
  `<a href="./contact.html" ...>Contact</a>` positioned between the "Chatbots" link and the
  "Plan gesprek" CTA. Task 4's verification checks for this exact link text/href on every page.

- [ ] **Step 1: Add the link to `services.html` desktop nav**

Find:
```
      <a href="./chatbots.html" class="nav-link" style="color:oklch(46% 0.012 140);transition:color 200ms ease;">Chatbots</a>
      <a href="./index.html#contact" style="background:oklch(70% 0.14 220);color:#001a2e;padding:10px 20px;border-radius:6px;font-weight:600;transition:all 200ms ease;">Plan gesprek</a>
    </nav>
```
Replace with:
```
      <a href="./chatbots.html" class="nav-link" style="color:oklch(46% 0.012 140);transition:color 200ms ease;">Chatbots</a>
      <a href="./contact.html" class="nav-link" style="color:oklch(46% 0.012 140);transition:color 200ms ease;">Contact</a>
      <a href="./index.html#contact" style="background:oklch(70% 0.14 220);color:#001a2e;padding:10px 20px;border-radius:6px;font-weight:600;transition:all 200ms ease;">Plan gesprek</a>
    </nav>
```

- [ ] **Step 2: Add the link to `services.html` mobile panel**

Find:
```
      <a href="./chatbots.html" style="color:oklch(46% 0.012 140);transition:color 200ms ease;">Chatbots</a>
      <a href="./index.html#contact" style="background:oklch(70% 0.14 220);color:#001a2e;padding:10px 20px;border-radius:6px;font-weight:600;transition:all 200ms ease;">Plan gesprek</a>
  </div>
```
Replace with:
```
      <a href="./chatbots.html" style="color:oklch(46% 0.012 140);transition:color 200ms ease;">Chatbots</a>
      <a href="./contact.html" style="color:oklch(46% 0.012 140);transition:color 200ms ease;">Contact</a>
      <a href="./index.html#contact" style="background:oklch(70% 0.14 220);color:#001a2e;padding:10px 20px;border-radius:6px;font-weight:600;transition:all 200ms ease;">Plan gesprek</a>
  </div>
```

- [ ] **Step 3: Add the link to `chatbots.html` desktop nav**

`chatbots.html`'s "Chatbots" link is the bold/active one on this page. Find:
```
      <a href="./chatbots.html" class="nav-link" style="color:oklch(18% 0.02 255);font-weight:600;">Chatbots</a>
      <a href="./index.html#contact" style="background:oklch(70% 0.14 220);color:#001a2e;padding:10px 20px;border-radius:6px;font-weight:600;transition:all 200ms ease;">Plan gesprek</a>
    </nav>
```
Replace with:
```
      <a href="./chatbots.html" class="nav-link" style="color:oklch(18% 0.02 255);font-weight:600;">Chatbots</a>
      <a href="./contact.html" class="nav-link" style="color:oklch(46% 0.012 140);transition:color 200ms ease;">Contact</a>
      <a href="./index.html#contact" style="background:oklch(70% 0.14 220);color:#001a2e;padding:10px 20px;border-radius:6px;font-weight:600;transition:all 200ms ease;">Plan gesprek</a>
    </nav>
```

- [ ] **Step 4: Add the link to `chatbots.html` mobile panel**

Find:
```
      <a href="./chatbots.html" style="color:oklch(18% 0.02 255);font-weight:600;">Chatbots</a>
      <a href="./index.html#contact" style="background:oklch(70% 0.14 220);color:#001a2e;padding:10px 20px;border-radius:6px;font-weight:600;transition:all 200ms ease;">Plan gesprek</a>
  </div>
```
Replace with:
```
      <a href="./chatbots.html" style="color:oklch(18% 0.02 255);font-weight:600;">Chatbots</a>
      <a href="./contact.html" style="color:oklch(46% 0.012 140);transition:color 200ms ease;">Contact</a>
      <a href="./index.html#contact" style="background:oklch(70% 0.14 220);color:#001a2e;padding:10px 20px;border-radius:6px;font-weight:600;transition:all 200ms ease;">Plan gesprek</a>
  </div>
```

- [ ] **Step 5: Add the link to `prijzen.html` desktop nav**

Find:
```
      <a href="./chatbots.html" class="nav-link" style="color:oklch(46% 0.012 140);transition:color 200ms ease;">Chatbots</a>
      <a href="./index.html#contact" style="background:oklch(70% 0.14 220);color:#001a2e;padding:10px 20px;border-radius:6px;font-weight:600;transition:all 200ms ease;">Plan gesprek</a>
    </nav>
```
Replace with:
```
      <a href="./chatbots.html" class="nav-link" style="color:oklch(46% 0.012 140);transition:color 200ms ease;">Chatbots</a>
      <a href="./contact.html" class="nav-link" style="color:oklch(46% 0.012 140);transition:color 200ms ease;">Contact</a>
      <a href="./index.html#contact" style="background:oklch(70% 0.14 220);color:#001a2e;padding:10px 20px;border-radius:6px;font-weight:600;transition:all 200ms ease;">Plan gesprek</a>
    </nav>
```

- [ ] **Step 6: Add the link to `prijzen.html` mobile panel**

`prijzen.html`'s mobile panel links have no inline style (plain `<a href="...">text</a>`, unlike
`services.html`/`chatbots.html`). Find:
```
      <a href="./chatbots.html">Chatbots</a>
      <a href="./index.html#contact" style="background:oklch(70% 0.14 220);color:#001a2e !important;text-align:center;border-radius:6px;font-weight:600;">Plan gesprek</a>
  </div>
```
Replace with:
```
      <a href="./chatbots.html">Chatbots</a>
      <a href="./contact.html">Contact</a>
      <a href="./index.html#contact" style="background:oklch(70% 0.14 220);color:#001a2e !important;text-align:center;border-radius:6px;font-weight:600;">Plan gesprek</a>
  </div>
```

- [ ] **Step 7: Add the link to `index.html` desktop nav**

`index.html` uses `{{ }}` template placeholders for i18n but "Contact" is identical in NL and EN, so
it's hardcoded directly rather than added to the NL/EN data objects (avoids touching the templating
data layer for a one-word label that never changes between languages). Find:
```
      <a href="./chatbots.html" class="nav-link" style="color:oklch(46% 0.012 140);transition:color 200ms ease;" style-hover="color:oklch(18% 0.02 255);">{{ navChatbots }}</a>
      <div style="display:flex;align-items:center;gap:2px;border:1px solid oklch(88% 0.006 90);border-radius:6px;padding:3px;">
```
Replace with:
```
      <a href="./chatbots.html" class="nav-link" style="color:oklch(46% 0.012 140);transition:color 200ms ease;" style-hover="color:oklch(18% 0.02 255);">{{ navChatbots }}</a>
      <a href="./contact.html" class="nav-link" style="color:oklch(46% 0.012 140);transition:color 200ms ease;" style-hover="color:oklch(18% 0.02 255);">Contact</a>
      <div style="display:flex;align-items:center;gap:2px;border:1px solid oklch(88% 0.006 90);border-radius:6px;padding:3px;">
```

- [ ] **Step 8: Add the link to `index.html` mobile panel**

Find:
```
    <a href="./chatbots.html">{{ navChatbots }}</a>
    <div class="nav-mobile-lang">
```
Replace with:
```
    <a href="./chatbots.html">{{ navChatbots }}</a>
    <a href="./contact.html">Contact</a>
    <div class="nav-mobile-lang">
```

- [ ] **Step 9: Verify the link is present on every page, both desktop and mobile**

Run:
```bash
cd /Users/hamdeco/development/hamdoun/preview
for f in index.html services.html chatbots.html prijzen.html contact.html; do
  count=$(grep -c 'href="./contact.html"' "$f")
  echo "$f: $count occurrence(s) of href=\"./contact.html\""
done
```

Expected: all five files print `2` — one desktop nav-link + one mobile-panel link, each pointing to
`./contact.html` (this also holds for `contact.html` itself, whose own nav-link points back to
itself, matching how `services.html`/`chatbots.html`/`prijzen.html` already self-link on their own
active nav item).

- [ ] **Step 10: Commit**

```bash
cd /Users/hamdeco/development/hamdoun
git add preview/index.html preview/services.html preview/chatbots.html preview/prijzen.html
git commit -m "Add Contact link to nav on all pages"
```

---

### Task 4: Full-suite verification

**Files:** none modified — read-only checks over `preview/index.html`, `preview/services.html`,
`preview/chatbots.html`, `preview/prijzen.html`, `preview/contact.html`.

**Interfaces:**
- Consumes: the final state of all five pages from Tasks 1-3.
- Produces: a pass/fail report used as the gate before offering to push/deploy (pushing itself is a
  separate, explicit step — not part of this task).

- [ ] **Step 1: Confirm no page still has the old 680px breakpoint or old gap values**

Run:
```bash
cd /Users/hamdeco/development/hamdoun/preview
grep -rn "680px" index.html services.html chatbots.html prijzen.html contact.html || echo "none found (expected)"
grep -rn "gap:clamp(16px,2vw,32px)\|gap:clamp(14px,2vw,28px)\|gap:clamp(12px,2vw,28px)" index.html services.html chatbots.html prijzen.html contact.html || echo "none found (expected)"
```

Expected: both commands print `none found (expected)`.

- [ ] **Step 2: Confirm every page's nav has `flex-wrap:wrap` and the 960px breakpoint**

Run:
```bash
cd /Users/hamdeco/development/hamdoun/preview
for f in index.html services.html chatbots.html prijzen.html contact.html; do
  ok="yes"
  grep -q "max-width: 960px" "$f" || ok="no"
  grep -q "flex-wrap:wrap" "$f" || ok="no"
  echo "$f: $ok"
done
```

Expected: `yes` for all five files.

- [ ] **Step 3: Confirm root `index.html` (the coming-soon gate) was NOT touched**

Run:
```bash
cd /Users/hamdeco/development/hamdoun
git diff main --stat contact-page-nav-fix -- index.html
```

Expected: empty output (no diff on the root `index.html`, only `preview/index.html` should show
changes).

- [ ] **Step 4: Visual check in a real browser**

Serve the `preview/` directory locally and open `contact.html`, `services.html`, `chatbots.html`,
`prijzen.html`, `index.html`:

```bash
cd /Users/hamdeco/development/hamdoun/preview
python3 -m http.server 8811
```

Open `http://localhost:8811/contact.html` (and the other four pages) in a browser. For each page,
confirm:
- The "Contact" link appears in the nav and, on `contact.html`, is visually marked as active.
- Resizing the browser window between roughly 680px and 1000px never clips or hides the "Plan
  gesprek" button — either the full row fits, it wraps to a second line, or the hamburger menu has
  already taken over.
- On `contact.html`: phone/e-mail/BTW/KVK are visible and correct, and submitting the form (with
  real or dummy data) shows the "Versturen..." state and then a status message (success or error
  depending on whether `/api/contact` is reachable from `localhost` — a network error here is
  expected when testing locally without the production backend, that's fine, it confirms the JS
  wiring works).

Stop the server with Ctrl-C when done.

- [ ] **Step 5: Report status to the user**

Summarize: branch name (`contact-page-nav-fix`), commits made, and that the work is ready for the
user to review and explicitly approve before merging/pushing to `main` (which triggers the
production deploy).
