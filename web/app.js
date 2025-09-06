function apiBase() {
  const raw = document.querySelector('meta[name="api-base"]')?.content || '';
  return raw.replace(/\/$/, '');
}
const API_BASE = apiBase();

const PAGE_SIZE = 10;
const MAX_PAGES_FOR_ANCHOR = 30;

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

  if (sentinel && sentinel.parentNode !== container) {
    container.appendChild(sentinel);
  }
}

async function fetchPage({ append = true } = {}) {
  if (loading || !hasMore) return;
  loading = true;

  // Show loading indicator
  if (append && sentinel) {
    sentinel.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">Loading more quotes...</p>';
  }

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

    // Auto-load more if viewport is too tall and we have more content
    await autoLoadIfNeeded();

  } catch (err) {
    console.error(err);
    if (!append) {
      container.innerHTML = `<p style="color:#b00;text-align:left;">Error loading quotes: ${escapeHtml(err.message || String(err))}</p>`;
    }
    hasMore = false;
  } finally {
    loading = false;
    // Clear loading indicator
    if (sentinel) {
      sentinel.innerHTML = '';
    }
  }
}

// Auto-load content if viewport is taller than content (no scrollbar)
async function autoLoadIfNeeded() {
  await new Promise(resolve => setTimeout(resolve, 100));

  const viewportHeight = window.innerHeight;
  const contentHeight = document.body.scrollHeight;
  const hasScrollbar = contentHeight > viewportHeight;

  // If no scrollbar and we have more content, load another page
  if (!hasScrollbar && hasMore && !loading) {
    console.log('Auto-loading more content (no scrollbar detected)');
    await fetchPage({ append: true });
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
  sentinel.style.height = "1px";
  sentinel.style.background = "transparent";
  container.appendChild(sentinel);

  initFormHandler();

  io = new IntersectionObserver(async (entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting && hasMore && !loading) {
        console.log('Sentinel intersected, loading more...');
        await fetchPage({ append: true });
      }
    }
  }, {
    root: null,
    rootMargin: "0px 0px 200px 0px", // Load when 200px from bottom
    threshold: 0
  });

  io.observe(sentinel);

  // Backup scroll listener for fast scrolling edge cases
  const nearBottom = () => {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const windowHeight = window.innerHeight;
    const docHeight = document.documentElement.scrollHeight;
    return scrollTop + windowHeight >= docHeight - 400; // 400px threshold
  };

  let scrollTimeout;
  window.addEventListener("scroll", () => {
    // Clear any existing timeout
    clearTimeout(scrollTimeout);

    // Set a new timeout to check after scrolling stops/slows
    scrollTimeout = setTimeout(async () => {
      if (nearBottom() && hasMore && !loading) {
        console.log('Near bottom detected via scroll fallback, loading more...');
        await fetchPage({ append: true });
      }
    }, 150); // Check 150ms after scroll activity
  }, { passive: true });

  // Initial load
  await fetchPage({ append: false });
  await ensureAnchorVisible();
});
