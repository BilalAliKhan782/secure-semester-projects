const chat = document.getElementById("chat");
const input = document.getElementById("msgInput");
const btn = document.getElementById("sendBtn");

function scrollToBottom() {
  chat.scrollTop = chat.scrollHeight;
}

function createElement(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
}

function renderTable(rows) {
  if (!rows || rows.length === 0) {
    const hint = createElement("div", "hint");
    hint.appendChild(createElement("em", "", "No results."));
    return hint;
  }

  const wrapper = createElement("div", "table-wrap");
  const table = document.createElement("table");
  const header = document.createElement("thead");
  const headerRow = document.createElement("tr");
  const columns = Object.keys(rows[0]);

  for (const column of columns) {
    headerRow.appendChild(createElement("th", "", column));
  }
  header.appendChild(headerRow);
  table.appendChild(header);

  const body = document.createElement("tbody");
  for (const row of rows) {
    const tableRow = document.createElement("tr");
    for (const column of columns) {
      tableRow.appendChild(createElement("td", "", row[column] ?? ""));
    }
    body.appendChild(tableRow);
  }
  table.appendChild(body);
  wrapper.appendChild(table);
  return wrapper;
}

function appendSection(container, title, rows) {
  const heading = createElement("div", "bubble-title", title);
  heading.style.marginTop = "10px";
  container.appendChild(heading);
  container.appendChild(renderTable(rows));
}

function renderCombined(combined) {
  const container = document.createElement("div");
  let hasContent = false;

  if (combined.student) {
    appendSection(container, "Student", [combined.student]);
    hasContent = true;
  }
  if (combined.fees) {
    appendSection(container, "Fees", [combined.fees]);
    hasContent = true;
  }
  if (combined.courses?.length) {
    appendSection(container, "Courses", combined.courses);
    hasContent = true;
  }
  if (combined.notes?.length) {
    appendSection(container, "Notes", combined.notes);
    hasContent = true;
  }
  if (combined.discipline?.length) {
    appendSection(container, "Discipline", combined.discipline);
    hasContent = true;
  }

  if (!hasContent) {
    const hint = createElement("div", "hint");
    hint.appendChild(createElement("em", "", "No combined data."));
    container.appendChild(hint);
  }
  return container;
}

function appendUser(text) {
  const message = createElement("div", "msg msg-user");
  message.appendChild(createElement("div", "bubble", text));
  chat.appendChild(message);
  scrollToBottom();
}

function appendAssistant(payload) {
  const message = createElement("div", "msg msg-assistant");
  const bubble = createElement("div", "bubble");
  bubble.appendChild(createElement("div", "bubble-title", payload?.title || "Result"));

  if (payload?.combined) {
    bubble.appendChild(renderCombined(payload.combined));
  } else if (payload?.rows) {
    bubble.appendChild(renderTable(payload.rows));
  }

  const text = payload?.text || payload?.message || "";
  if (text) {
    const hint = createElement("div", "hint", text);
    hint.style.marginTop = "8px";
    bubble.appendChild(hint);
  }

  if (payload?.debug) {
    const details = document.createElement("details");
    details.appendChild(createElement("summary", "", "Debug"));
    details.appendChild(createElement("pre", "", JSON.stringify(payload.debug, null, 2)));
    bubble.appendChild(details);
  }

  message.appendChild(bubble);
  chat.appendChild(message);
  scrollToBottom();
}

async function send() {
  const question = input.value.trim();
  if (!question) return;

  appendUser(question);
  input.value = "";
  input.focus();

  const thinking = createElement("div", "msg msg-assistant");
  const thinkingBubble = createElement("div", "bubble");
  thinkingBubble.appendChild(createElement("div", "hint", "Thinking..."));
  thinking.appendChild(thinkingBubble);
  chat.appendChild(thinking);
  scrollToBottom();

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({message: question}),
    });
    const data = await response.json();
    thinking.remove();
    appendAssistant(data);
  } catch (error) {
    thinking.remove();
    appendAssistant({title: "Error", text: "Server error. Check terminal logs."});
  }
}

btn.addEventListener("click", send);
input.addEventListener("keydown", (event) => {
  if (event.key === "Enter") send();
});
