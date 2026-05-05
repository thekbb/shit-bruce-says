const CONFIG = {
  API_BASE: (() => {
    const raw = document.querySelector('meta[name="api-base"]')?.content || '';
    return raw.replace(/\/$/, '');
  })(),
  HIGHLIGHT_DURATION: 3000,
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
    hour12: false,
    timeZone: "UTC",
    timeZoneName: "short",
  });
}

function getQuoteUrl(quoteId) {
  return `${window.location.origin}/quotes/${quoteId}/`;
}

async function createQuote(quote) {
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

function createQuoteElement(quote) {
  const article = document.createElement("article");
  article.className = "quote";
  article.id = quote.quoteId;
  article.innerHTML = `
    <h3 class="visually-hidden">Quote from ${formatEnglish(quote.createdAt)}</h3>
    <blockquote cite="${getQuoteUrl(quote.quoteId)}">
      <p>"${escapeHtml(quote.quote)}"</p>
      <footer>
        <cite>— Bruce</cite>
      </footer>
    </blockquote>
    <div class="quote-meta">
      <time class="timestamp" datetime="${quote.createdAt}">
        <a href="${getQuoteUrl(quote.quoteId)}" aria-label="Permalink to this quote">${formatEnglish(quote.createdAt)}</a>
      </time>
      <div class="share-buttons">
        <button class="share-btn" data-quote-id="${quote.quoteId}" data-quote-text="${escapeHtml(quote.quote)}" data-platform="linkedin" title="Share on LinkedIn" type="button">
          <i class="fab fa-linkedin"></i>
        </button>
        <button class="share-btn" data-quote-id="${quote.quoteId}" data-quote-text="${escapeHtml(quote.quote)}" data-platform="bluesky" title="Share on Bluesky" type="button">
          <i class="fas fa-cloud"></i>
        </button>
        <button class="share-btn copy-btn" data-quote-id="${quote.quoteId}" title="Copy link" type="button">
          <i class="fas fa-link"></i>
        </button>
      </div>
    </div>
  `;
  return article;
}

function setFormStatus(message, isError = false) {
  const status = document.getElementById("form-status");
  if (!status) return;

  status.textContent = message;
  status.style.color = isError ? "#b00" : "#666";
}

function removeEmptyState() {
  document.querySelector(".empty-state")?.remove();
}

function prependQuote(quote) {
  const container = document.getElementById("quotes");
  if (!container) return;

  removeEmptyState();
  container.prepend(createQuoteElement(quote));
}

async function handleFormSubmit(event) {
  event.preventDefault();

  const form = event.currentTarget;
  const input = document.getElementById("quote");
  const submit = form.querySelector('input[type="submit"]');
  const quote = input.value.trim();
  if (!quote) return;

  input.disabled = true;
  submit.disabled = true;
  setFormStatus("Submitting quote...");

  try {
    const created = await createQuote(quote);
    input.value = "";
    prependQuote(created);
    setFormStatus("Quote submitted. The static pages will catch up within a few seconds.");
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (err) {
    setFormStatus(err.message || "Failed to add quote.", true);
    console.error(err);
  } finally {
    input.disabled = false;
    submit.disabled = false;
  }
}

function tryHighlightHash() {
  const anchorId = window.location.hash.slice(1);
  if (!anchorId) return;

  const el = document.getElementById(anchorId);
  if (!el) return;

  el.scrollIntoView({ behavior: "smooth", block: "start" });
  el.classList.add("highlight");
  window.setTimeout(() => el.classList.remove("highlight"), CONFIG.HIGHLIGHT_DURATION);
}

function shareQuote(quoteId, quoteText, platform) {
  const quoteUrl = getQuoteUrl(quoteId);
  const encodedUrl = encodeURIComponent(quoteUrl);
  const encodedText = encodeURIComponent(`"${quoteText}"\n— Bruce`);

  const shareUrls = {
    linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodedUrl}`,
    bluesky: `https://bsky.app/intent/compose?text=${encodedText}%20${encodedUrl}`,
    facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`,
    whatsapp: `https://wa.me/?text=${encodedText}%20${encodedUrl}`,
  };

  if (shareUrls[platform]) {
    const popup = window.open(shareUrls[platform], "_blank", "width=600,height=400");
    if (!popup || popup.closed || typeof popup.closed === "undefined") {
      window.location.href = shareUrls[platform];
    }
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
    document.execCommand("copy");
    showCopyFeedback();
  } catch (err) {
    console.error("Failed to copy:", err);
  }

  document.body.removeChild(textArea);
}

function copyQuoteUrl(quoteId) {
  const quoteUrl = getQuoteUrl(quoteId);

  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(quoteUrl).then(() => {
      showCopyFeedback();
    }).catch(() => {
      fallbackCopyToClipboard(quoteUrl);
    });
  } else {
    fallbackCopyToClipboard(quoteUrl);
  }
}

function showCopyFeedback() {
  const feedback = document.createElement("div");
  feedback.textContent = "Link copied!";
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
  window.setTimeout(() => document.body.removeChild(feedback), 2000);
}

function handleShareButtonClick(event) {
  const button = event.target.closest(".share-btn");
  if (!button) return;

  event.preventDefault();

  const quoteId = button.dataset.quoteId;
  const quoteText = button.dataset.quoteText;
  const platform = button.dataset.platform;

  if (button.classList.contains("copy-btn")) {
    copyQuoteUrl(quoteId);
  } else if (platform) {
    shareQuote(quoteId, quoteText, platform);
  }
}

function initializeApp() {
  document.getElementById("quote-form")?.addEventListener("submit", handleFormSubmit);
  document.addEventListener("click", handleShareButtonClick);
  tryHighlightHash();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeApp);
} else {
  initializeApp();
}

window.addEventListener("hashchange", tryHighlightHash);
