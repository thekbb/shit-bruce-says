function apiBase() {
  const raw = document.querySelector('meta[name="api-base"]')?.content || '';
  return raw.replace(/\/$/, '');
}
const API_BASE = apiBase();

const PAGE_SIZE = 10;             // initial + subsequent page size
const MAX_PAGES_FOR_ANCHOR = 30;  // safety bound when chasing a deep link

function escapeHtml(text) {
  const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
  return text.replace(/[&<>"']/g, (m) => map[m]);
}

function formatEnglish(dt) {
  const d = new Date(dt);
  const months = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
  ];
  const pad = (n) => String(n).padStart(2, "0");
  return `${months[d.getMonth()]} ${pad(d.getDate())}, ${d.getFullYear()} `
       + `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

let container;
let sentinel;
let cursor = null;
let hasMore = true;
let loading = false;
let pagesLoaded = 0;
let io; // IntersectionObserver

function renderQuotes(items, { append = true } = {}) {
  if (!append) container.innerHTML = "";
  for (const q of (items || [])) {
    const div = document.createElement("div");
    div.className = "quote";
    div.id = q.SK;
    div.innerHTML = `
      <h2>Bruce Said:</h2>
      <blockquote><p>${escapeHtml(q.quote)}</p></blockquote>
      <p class="timestamp">
        <a href="#${q.SK}">${formatEnglish(q.createdAt)}</a>
      </p>
    `;
    container.appendChild(div);
  }
}

async function fetchPage({ append = true } = {}) {
  if (loading || !hasMore) return;
  loading = true;

  try {
    const url = new URL(`${API_BASE}/quotes`);
    url.searchParams.set("limit", String(PAGE_SIZE));
    if (cursor) url.searchParams.set("cursor", JSON.stringify(cursor));

    const res = await fetch(url.toString(), { cache: "no-store" });
    if (!res.ok) throw new Error(`GET /quotes failed (${res.status})`);
    const data = await res.json();

    renderQuotes(data.items || [], { append });
    cursor = data.cursor || null;
    hasMore = Boolean(cursor);
    pagesLoaded += 1;
  } catch (err) {
    console.error(err);
    if (!append) {
      container.innerHTML = `<p style="color:#b00;text-align:left;">Error loading quotes: ${escapeHtml(err.message || String(err))}</p>`;
    }
    hasMore = false;
  } finally {
    loading = false;
  }
}

async function ensureAnchorVisible() {
  const anchorId = window.location.hash.slice(1);
  if (!anchorId) return;

  function tryHighlight() {
    const el = document.getElementById(anchorId);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.classList.add("highlight");
      setTimeout(() => el.classList.remove("highlight"), 3000);
      return true;
    }
    return false;
  }

  if (tryHighlight()) return;

  for (let i = 0; i < MAX_PAGES_FOR_ANCHOR && hasMore; i += 1) {
    await fetchPage({ append: true });
    if (tryHighlight()) return;
  }
}

function initInfiniteScroll() {
  io = new IntersectionObserver(async (entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        await fetchPage({ append: true });
      }
    }
  }, {
    root: null,
    rootMargin: "1000px 0px", // prefetch ~1000px before bottom
    threshold: 0
  });
  io.observe(sentinel);
}

function initFormHandler() {
  const form = document.getElementById("quote-form");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const input = document.getElementById("quote");
    const quote = input.value.trim();
    if (!quote) return;

    try {
      const resp = await fetch(`${API_BASE}/quotes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ quote }),
      });

      if (!resp.ok) {
        let msg = `POST /quotes failed (${resp.status})`;
        try { const err = await resp.json(); if (err?.error) msg = err.error; } catch {}
        throw new Error(msg);
      }

      input.value = "";

      cursor = null;
      hasMore = true;
      pagesLoaded = 0;
      await fetchPage({ append: false });
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      alert(err.message || "Failed to add quote.");
      console.error(err);
    }
  });
}

window.addEventListener("load", async () => {
  container = document.getElementById("quotes");

  sentinel = document.createElement("div");
  sentinel.id = "infinite-scroll-sentinel";
  container.after(sentinel);

  initFormHandler();
  initInfiniteScroll();

  await fetchPage({ append: false });

  ensureAnchorVisible();
});
