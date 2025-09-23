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

function escapeJs(text) {
  return JSON.stringify(text).slice(1, -1);
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
        <p>"${escapeHtml(quote.quote)}"</p>
        <footer>
          <cite>— Bruce</cite>
        </footer>
      </blockquote>
      <div class="quote-meta">
        <time class="timestamp" datetime="${quote.createdAt}">
          <a href="#${quote.SK}" aria-label="Link to this quote">${formatEnglish(quote.createdAt)}</a>
        </time>
        <div class="share-buttons">
          <button class="share-btn" data-quote-id="${quote.SK}" data-quote-text="${escapeHtml(quote.quote)}" data-platform="linkedin" title="Share on LinkedIn">
            <i class="fab fa-linkedin"></i>
          </button>
          <button class="share-btn" data-quote-id="${quote.SK}" data-quote-text="${escapeHtml(quote.quote)}" data-platform="bluesky" title="Share on Bluesky">
            <i class="fas fa-cloud"></i>
          </button>
          <button class="share-btn copy-btn" data-quote-id="${quote.SK}" title="Copy link">
            <i class="fas fa-link"></i>
          </button>
        </div>
      </div>
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

const State = {
  container: null,
  cursor: null,
  hasMore: true,
  loading: false,
  infScroll: null,

  reset() {
    this.cursor = null;
    this.hasMore = true;
    this.loading = false;
  },

  setLoading(isLoading) {
    this.loading = isLoading;
  },

  updateFromApiResponse(data) {
    this.cursor = data.cursor || null;
    this.hasMore = Boolean(data.cursor);
  }
};

function renderQuotes(items) {
  return (items || []).map(quote => DOM.createQuoteElement(quote));
}

function needsMoreContent() {
  const documentHeight = Math.max(
    document.body.scrollHeight,
    document.body.offsetHeight,
    document.documentElement.clientHeight,
    document.documentElement.scrollHeight,
    document.documentElement.offsetHeight
  );
  const viewportHeight = window.innerHeight;

  return documentHeight <= viewportHeight + 100;
}

async function loadInitial() {
  if (State.loading) return;
  State.setLoading(true);

  try {
    const data = await API.fetchQuotes();
    State.container.innerHTML = '';
    const items = transform(data);
    const elements = renderQuotes(items);
    elements.forEach(el => State.container.appendChild(el));

    let loadAttempts = 0;
    const maxLoadAttempts = 5;

    while (needsMoreContent() && State.hasMore && loadAttempts < maxLoadAttempts) {
      loadAttempts++;
      console.log(`Loading additional content (attempt ${loadAttempts}) to ensure scrolling is possible`);

      const moreData = await API.fetchQuotes(State.cursor);
      const moreItems = transform(moreData);
      const moreElements = renderQuotes(moreItems);
      moreElements.forEach(el => State.container.appendChild(el));

      await new Promise(resolve => setTimeout(resolve, 50));
    }

  } catch (err) {
    console.error(err);
    State.container.innerHTML = DOM.createErrorMessage(err.message || String(err));
    State.hasMore = false;
  } finally {
    State.setLoading(false);
  }
}

function getPath() {
  if (!State.hasMore) return false;

  const url = new URL(`${CONFIG.API_BASE}/quotes`);
  url.searchParams.set("limit", String(CONFIG.PAGE_SIZE));
  if (State.cursor) url.searchParams.set("cursor", JSON.stringify(State.cursor));

  return url.toString();
}

function transform(data) {
  State.updateFromApiResponse(data);
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

  for (let i = 0; i < CONFIG.MAX_PAGES_FOR_ANCHOR && State.hasMore; i += 1) {
    try {
      const data = await API.fetchQuotes(State.cursor);
      const items = transform(data);
      const elements = renderQuotes(items);
      elements.forEach(el => State.container.appendChild(el));

      if (tryHighlight()) return;
    } catch (err) {
      console.error(err);
      break;
    }
  }
}

const EventHandlers = {
  async handleFormSubmit(e) {
    e.preventDefault();
    const input = document.getElementById("quote");
    const quote = input.value.trim();
    if (!quote) return;

    try {
      await API.createQuote(quote);
      input.value = "";

      State.reset();
      await loadInitial();
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      alert(err.message || "Failed to add quote.");
      console.error(err);
    }
  },

  handleInfiniteScrollRequest() {
    State.setLoading(true);
  },

  handleInfiniteScrollLoad(data) {
    const items = transform(data);
    const elements = renderQuotes(items);
    elements.forEach(el => State.container.appendChild(el));
    State.setLoading(false);
  },

  handleInfiniteScrollError(error) {
    console.error(error);
    State.hasMore = false;
    State.setLoading(false);
  }
};

function initFormHandler() {
  const form = document.getElementById("quote-form");
  form.addEventListener("submit", EventHandlers.handleFormSubmit);
}

function initInfiniteScroll() {
  State.infScroll = new InfiniteScroll(State.container, {
    path: getPath,
    responseBody: 'json',
    outlayer: false,
    loadOnScroll: true,
    scrollThreshold: CONFIG.SCROLL_THRESHOLD,
    history: false
  });

  State.infScroll.on('request', EventHandlers.handleInfiniteScrollRequest);
  State.infScroll.on('load', EventHandlers.handleInfiniteScrollLoad);
  State.infScroll.on('error', EventHandlers.handleInfiniteScrollError);
}

function initializeApp() {
  State.container = document.getElementById("quotes");
  if (!State.container) return;

  State.container.innerHTML = DOM.createLoadingSkeleton();

  initFormHandler();
  initInfiniteScroll();
  setupShareButtonHandlers();
  loadInitial();
}

function setupShareButtonHandlers() {
  State.container.addEventListener('click', (event) => {
    const button = event.target.closest('.share-btn');
    if (!button) return;

    event.preventDefault();

    const quoteId = button.dataset.quoteId;
    const quoteText = button.dataset.quoteText;
    const platform = button.dataset.platform;

    if (button.classList.contains('copy-btn')) {
      copyQuoteUrl(quoteId);
    } else if (platform) {
      shareQuote(quoteId, quoteText, platform);
    }
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeApp);
} else {
  initializeApp();
}

function shareQuote(quoteId, quoteText, platform) {
  const quoteUrl = `${window.location.origin}/quote/${quoteId}.html`;
  const encodedUrl = encodeURIComponent(quoteUrl);
  const encodedText = encodeURIComponent(`"${quoteText}"\n— Bruce`);

  const shareUrls = {
    linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodedUrl}`,
    bluesky: `https://bsky.app/intent/compose?text=${encodedText}%20${encodedUrl}`,
    facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`,
    whatsapp: `https://wa.me/?text=${encodedText}%20${encodedUrl}`
  };

  if (shareUrls[platform]) {
    const popup = window.open(shareUrls[platform], '_blank', 'width=600,height=400');
    if (!popup || popup.closed || typeof popup.closed == 'undefined') {
      window.location.href = shareUrls[platform];
    }
  }
}

function copyQuoteUrl(quoteId) {
  const quoteUrl = `${window.location.origin}/quote/${quoteId}.html`;

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(quoteUrl).then(() => {
      showCopyFeedback();
    }).catch(() => {
      fallbackCopyToClipboard(quoteUrl);
    });
  } else {
    fallbackCopyToClipboard(quoteUrl);
  }
}

function fallbackCopyToClipboard(text) {
  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.style.position = "fixed";
  textArea.style.left = "-999999px";
  textArea.style.top = "-999999px";
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();

  try {
    document.execCommand('copy');
    showCopyFeedback();
  } catch (err) {
    console.error('Failed to copy: ', err);
  }

  document.body.removeChild(textArea);
}

function showCopyFeedback() {
  const feedback = document.createElement('div');
  feedback.textContent = 'Link copied!';
  feedback.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: #007acc;
    color: white;
    padding: 8px 16px;
    border-radius: 4px;
    z-index: 1000;
    font-size: 14px;
  `;

  document.body.appendChild(feedback);

  setTimeout(() => {
    document.body.removeChild(feedback);
  }, 2000);
}

window.addEventListener("load", async () => {
  if (State.container) {
    await ensureAnchorVisible();
  }
});
