const CONFIG = {
  API_BASE: (() => {
    const raw = document.querySelector('meta[name="api-base"]')?.content || '';
    return raw.replace(/\/$/, '');
  })(),
  PAGE_SIZE: 10,
  MAX_PAGES_FOR_ANCHOR: 30,
  SCROLL_THRESHOLD: 400,
  HIGHLIGHT_DURATION: 3000,
  THROTTLE_DELAY: 100
};

function escapeHtml(text) {
  const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
  return text.replace(/[&<>"']/g, (m) => map[m]);
}

function formatEnglish(dt) {
  return new Date(dt).toLocaleString("en-US", {
    year: "numeric",
    month: "long",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  });
}

let container;
let cursor = null;
let hasMore = true;
let loading = false;
let infScroll;

function renderQuotes(items) {
  const elements = [];

  for (const q of (items || [])) {
    const article = document.createElement("article");
    article.className = "quote";
    article.id = q.SK;
    article.innerHTML = `
      <h3 class="visually-hidden">Quote from ${formatEnglish(q.createdAt)}</h3>
      <blockquote cite="#${q.SK}">
        <p>${escapeHtml(q.quote)}</p>
        <footer>
          <cite>— Bruce</cite>
        </footer>
      </blockquote>
      <time class="timestamp" datetime="${q.createdAt}">
        <a href="#${q.SK}" aria-label="Link to this quote">${formatEnglish(q.createdAt)}</a>
      </time>
    `;
    elements.push(article);
  }

  return elements;
}

async function loadInitial() {
  if (loading) return;
  loading = true;

  try {
    const url = new URL(`${CONFIG.API_BASE}/quotes`);
    url.searchParams.set("limit", String(CONFIG.PAGE_SIZE));

    const res = await fetch(url.toString());
    if (!res.ok) throw new Error(`GET /quotes failed (${res.status})`);
    const data = await res.json();

    container.innerHTML = '';
    const items = transform(data);
    const elements = renderQuotes(items);
    elements.forEach(el => container.appendChild(el));

  } catch (err) {
    console.error(err);
    container.innerHTML = `<p style="color:#b00;text-align:left;">Error loading quotes: ${escapeHtml(err.message || String(err))}</p>`;
    hasMore = false;
  } finally {
    loading = false;
  }
}

function getPath() {
  if (!hasMore) return false;

  const url = new URL(`${CONFIG.API_BASE}/quotes`);
  url.searchParams.set("limit", String(CONFIG.PAGE_SIZE));
  if (cursor) url.searchParams.set("cursor", JSON.stringify(cursor));

  return url.toString();
}

function transform(data) {
  cursor = data.cursor || null;
  hasMore = Boolean(data.cursor);
  return data.items || [];
}


async function ensureAnchorVisible() {
  const anchorId = window.location.hash.slice(1);
  if (!anchorId) return;

  function tryHighlight() {
    const el = document.getElementById(anchorId);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.classList.add("highlight");
      setTimeout(() => el.classList.remove("highlight"), CONFIG.HIGHLIGHT_DURATION);
      return true;
    }
    return false;
  }

  if (tryHighlight()) return;

  for (let i = 0; i < CONFIG.MAX_PAGES_FOR_ANCHOR && hasMore; i += 1) {
    try {
      const url = new URL(`${CONFIG.API_BASE}/quotes`);
      url.searchParams.set("limit", String(CONFIG.PAGE_SIZE));
      if (cursor) url.searchParams.set("cursor", JSON.stringify(cursor));

      const res = await fetch(url.toString());
      if (!res.ok) throw new Error(`GET /quotes failed (${res.status})`);
      const data = await res.json();

      const items = transform(data);
      const elements = renderQuotes(items);
      elements.forEach(el => container.appendChild(el));

      if (tryHighlight()) return;
    } catch (err) {
      console.error(err);
      break;
    }
  }
}

function initFormHandler() {
  const form = document.getElementById("quote-form");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const input = document.getElementById("quote");
    const quote = input.value.trim();
    if (!quote) return;

    try {
      const resp = await fetch(`${CONFIG.API_BASE}/quotes`, {
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
      await loadInitial();
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      alert(err.message || "Failed to add quote.");
      console.error(err);
    }
  });
}

function initializeApp() {
  container = document.getElementById("quotes");
  if (!container) return;

  container.innerHTML = `
    <div class="loading-skeleton">
      <div class="quote skeleton-quote">
        <h2>Loading quotes...</h2>
        <div class="skeleton-line"></div>
        <div class="skeleton-line short"></div>
        <div class="skeleton-timestamp"></div>
      </div>
    </div>
  `;

  initFormHandler();

  infScroll = new InfiniteScroll(container, {
    path: getPath,
    responseBody: 'json',
    outlayer: false,
    loadOnScroll: true,
    scrollThreshold: CONFIG.SCROLL_THRESHOLD
  });

  infScroll.on('request', () => {
    loading = true;
  });

  infScroll.on('load', (data) => {
    const items = transform(data);
    const elements = renderQuotes(items);
    elements.forEach(el => container.appendChild(el));
    loading = false;
  });

  infScroll.on('error', (error) => {
    console.error(error);
    hasMore = false;
    loading = false;
  });

  loadInitial();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeApp);
} else {
  initializeApp();
}

window.addEventListener("load", async () => {
  if (container) {
    await ensureAnchorVisible();
  }
});
