const chat = document.getElementById("chat");
const input = document.getElementById("msgInput");
const btn = document.getElementById("sendBtn");

function scrollToBottom() {
  chat.scrollTop = chat.scrollHeight;
}

function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function renderTable(rows) {
  if (!rows || rows.length === 0) return `<div class="hint"><em>No results.</em></div>`;
  const cols = Object.keys(rows[0]);

  let html = `<div class="table-wrap"><table><thead><tr>`;
  for (const c of cols) html += `<th>${escapeHtml(c)}</th>`;
  html += `</tr></thead><tbody>`;

  for (const r of rows) {
    html += `<tr>`;
    for (const c of cols) html += `<td>${escapeHtml(r[c])}</td>`;
    html += `</tr>`;
  }

  html += `</tbody></table></div>`;
  return html;
}

function renderCombined(combined) {
  let html = "";

  if (combined.student) {
    html += `<div class="bubble-title">Student</div>`;
    html += renderTable([combined.student]);
  }
  if (combined.fees) {
    html += `<div class="bubble-title" style="margin-top:10px;">Fees</div>`;
    html += renderTable([combined.fees]);
  }
  if (combined.courses && combined.courses.length) {
    html += `<div class="bubble-title" style="margin-top:10px;">Courses</div>`;
    html += renderTable(combined.courses);
  }
  if (combined.notes && combined.notes.length) {
    html += `<div class="bubble-title" style="margin-top:10px;">Notes</div>`;
    html += renderTable(combined.notes);
  }
  if (combined.discipline && combined.discipline.length) {
    html += `<div class="bubble-title" style="margin-top:10px;">Discipline</div>`;
    html += renderTable(combined.discipline);
  }

  if (!html) html = `<div class="hint"><em>No combined data.</em></div>`;
  return html;
}

function appendUser(text) {
  const div = document.createElement("div");
  div.className = "msg msg-user";
  div.innerHTML = `<div class="bubble">${escapeHtml(text)}</div>`;
  chat.appendChild(div);
  scrollToBottom();
}

function appendAssistant(payload) {
  const div = document.createElement("div");
  div.className = "msg msg-assistant";

  const title = payload?.title || "Result";
  const text = payload?.text || payload?.message || "";
  const rows = payload?.rows || null;
  const combined = payload?.combined || null;
  const debug = payload?.debug || null;

  let body = "";
  if (combined) body += renderCombined(combined);
  else if (rows) body += renderTable(rows);

  if (text) body += `<div class="hint" style="margin-top:8px;">${escapeHtml(text)}</div>`;

  let debugHtml = "";
  if (debug) {
    debugHtml = `
      <details>
        <summary>Debug</summary>
        <pre>${escapeHtml(JSON.stringify(debug, null, 2))}</pre>
      </details>
    `;
  }

  div.innerHTML = `
    <div class="bubble">
      <div class="bubble-title">${escapeHtml(title)}</div>
      ${body}
      ${debugHtml}
    </div>
  `;

  chat.appendChild(div);
  scrollToBottom();
}

async function send() {
  const q = input.value.trim();
  if (!q) return;

  appendUser(q);
  input.value = "";
  input.focus();

  const thinking = document.createElement("div");
  thinking.className = "msg msg-assistant";
  thinking.innerHTML = `<div class="bubble"><div class="hint">Thinking...</div></div>`;
  chat.appendChild(thinking);
  scrollToBottom();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ message: q })
    });

    const data = await res.json();
    thinking.remove();
    appendAssistant(data);
  } catch (e) {
    thinking.remove();
    appendAssistant({ title: "Error", text: "Server error. Check terminal logs.", debug: { error: String(e) } });
  }
}

btn.addEventListener("click", send);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") send();
});
