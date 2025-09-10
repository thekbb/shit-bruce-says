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

const API = {
  async fetchQuotes(cursor = null) {
    const url = new URL(`${CONFIG.API_BASE}/quotes`);
    url.searchParams.set("limit", String(CONFIG.PAGE_SIZE));
    if (cursor) url.searchParams.set("cursor", JSON.stringify(cursor));

    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`GET /quotes failed (${response.status})`);
    }
    return response.json();
  },

  async createQuote(quote) {
    const response = await fetch(`${CONFIG.API_BASE}/quotes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ quote }),
    });

    if (!response.ok) {
      let message = `POST /quotes failed (${response.status})`;
      try {
        const error = await response.json();
        if (error?.error) message = error.error;
      } catch {}
      throw new Error(message);
    }

    return response.json();
  }
};

const DOM = {

  createQuoteElement(quote) {
    const article = document.createElement("article");
    article.className = "quote";
    article.id = quote.SK;
    article.innerHTML = `
      <h3 class="visually-hidden">Quote from ${formatEnglish(quote.createdAt)}</h3>
      <blockquote cite="#${quote.SK}">
        <p>${escapeHtml(quote.quote)}</p>
        <footer>
          <cite>— Bruce</cite>
        </footer>
      </blockquote>
      <time class="timestamp" datetime="${quote.createdAt}">
        <a href="#${quote.SK}" aria-label="Link to this quote">${formatEnglish(quote.createdAt)}</a>
      </time>
    `;
    return article;
  },

  createLoadingSkeleton() {
    return `
      <div class="loading-skeleton">
        <div class="quote skeleton-quote">
          <h2>Loading quotes...</h2>
          <div class="skeleton-line"></div>
          <div class="skeleton-line short"></div>
          <div class="skeleton-timestamp"></div>
        </div>
      </div>
    `;
  },

  createErrorMessage(message) {
    return `<p style="color:#b00;text-align:left;">Error loading quotes: ${escapeHtml(message)}</p>`;
  }
};

let container;
let cursor = null;
let hasMore = true;
let loading = false;
let infScroll;

function renderQuotes(items) {
  return (items || []).map(quote => DOM.createQuoteElement(quote));
}

async function loadInitial() {
  if (loading) return;
  loading = true;

  try {
    const data = await API.fetchQuotes();
    container.innerHTML = '';
    const items = transform(data);
    const elements = renderQuotes(items);
    elements.forEach(el => container.appendChild(el));

  } catch (err) {
    console.error(err);
    container.innerHTML = DOM.createErrorMessage(err.message || String(err));
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
      const data = await API.fetchQuotes(cursor);
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
      await API.createQuote(quote);
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

  container.innerHTML = DOM.createLoadingSkeleton();

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
