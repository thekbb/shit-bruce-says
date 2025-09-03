// Resolve API base from <meta name="api-base" content="...">
function apiBase() {
  const raw = document.querySelector('meta[name="api-base"]')?.content || '';
  return raw.replace(/\/$/, '');
}
const API_BASE = apiBase();

// Escape HTML to prevent injection
function escapeHtml(text) {
  const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
  return text.replace(/[&<>"']/g, (m) => map[m]);
}

// Format exactly like the original: "August 23, 2025 16:06:12"
function formatEnglish(dt) {
  const d = new Date(dt);
  const months = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
  ];
  const pad = (n) => String(n).padStart(2, "0");
  return `${months[d.getMonth()]} ${pad(d.getDate())}, ${d.getFullYear()} ` +
         `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

// Render list of quotes
async function fetchQuotes() {
  const container = document.getElementById("quotes");
  try {
    const res = await fetch(`${API_BASE}/quotes?limit=50`, { cache: "no-store" });
    if (!res.ok) throw new Error(`GET /quotes failed (${res.status})`);
    const data = await res.json();

    container.innerHTML = "";
    (data.items || []).forEach((q) => {
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
    });

    // Deep-link: scroll to and highlight an anchored quote id
    const anchor = window.location.hash.slice(1);
    if (anchor) {
      const el = document.getElementById(anchor);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        el.classList.add("highlight");
        setTimeout(() => el.classList.remove("highlight"), 3000);
      }
    }
  } catch (err) {
    console.error(err);
    container.innerHTML = `<p style="color:#b00;text-align:left;">Error loading quotes: ${escapeHtml(err.message || String(err))}</p>`;
  }
}

// Submit handler
document.getElementById("quote-form").addEventListener("submit", async (e) => {
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
    await fetchQuotes();
  } catch (err) {
    alert(err.message || "Failed to add quote.");
    console.error(err);
  }
});

// Initial load
window.addEventListener("load", fetchQuotes);
