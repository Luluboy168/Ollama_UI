const sessionList = document.getElementById("session-list");
const chatBox = document.getElementById("chat-box");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const newSessionBtn = document.getElementById("new-session-btn");

let currentSessionId = null;

async function loadSessions() {
  const res = await fetch("/sessions/");
  const sessions = await res.json();
  sessionList.innerHTML = "";
  sessions.forEach((s) => {
    const li = document.createElement("li");
    li.textContent = s.title || `聊天室 ${s.id}`;
    li.onclick = () => selectSession(s.id);
    if (s.id === currentSessionId) li.classList.add("active");
    sessionList.appendChild(li);
  });
}

async function createSession() {
  const title = prompt("聊天室標題？") || "新聊天室";
  const res = await fetch("/sessions/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  const newSession = await res.json();
  currentSessionId = newSession.id;
  await loadSessions();
  await loadMessages(currentSessionId);
}

async function selectSession(sessionId) {
  currentSessionId = sessionId;
  await loadSessions();
  await loadMessages(sessionId);
}

async function loadMessages(sessionId) {
  const res = await fetch(`/msgs/${sessionId}`);
  const msgs = await res.json();
  chatBox.innerHTML = "";
  msgs.forEach((m) => {
    const div = document.createElement("div");
    div.classList.add("message", m.role);
    div.textContent = m.content;
    chatBox.appendChild(div);
  });
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendMessage() {
  const content = chatInput.value.trim();
  if (!content || !currentSessionId) return;
  chatInput.value = "";

  const res = await fetch(`/msgs/${currentSessionId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_msg: content }),
  });

  await loadMessages(currentSessionId);
}

sendBtn.onclick = sendMessage;
chatInput.addEventListener("keypress", (e) => {
  if (e.key === "Enter") sendMessage();
});
newSessionBtn.onclick = createSession;

loadSessions();
