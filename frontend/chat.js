const topicInput = document.getElementById("topicInput");
const roundsInput = document.getElementById("roundsInput");
const startBtn = document.getElementById("startBtn");
const endDebateBtn = document.getElementById("endDebateBtn");
const sendMessageBtn = document.getElementById("sendMessageBtn");
const userMessageInput = document.getElementById("userMessageInput");
const transcript = document.getElementById("transcript");

let activeSessionId = null;
let pendingLaunch = null;
let launchRequested = false;
let pollTimer = null;
const streamNodes = new Map();

function setActiveSession(sessionId) {
    activeSessionId = sessionId;

    if (sessionId) {
        localStorage.setItem(
            "activeSessionId",
            sessionId
        );
    } else {
        localStorage.removeItem(
            "activeSessionId"
        );
    }

    sendMessageBtn.disabled = !sessionId;
    endDebateBtn.disabled = !sessionId;
}

function scrollTranscriptToBottom() {
  transcript.scrollTop = transcript.scrollHeight;
}

function renderMessage(key, speaker, content, meta = {}, options = {}) {
  let node = streamNodes.get(key);
  if (!node) {
    node = document.createElement("article");
    node.className = `message ${options.variant || ""}`.trim();
    node.innerHTML = `
      <div class="meta">
        <span class="speaker"></span>
        <span class="time"></span>
      </div>
      <div class="content"></div>
    `;
    transcript.appendChild(node);
    streamNodes.set(key, node);
  }

  node.className = `message ${options.variant || ""}`.trim();
  node.querySelector(".speaker").textContent = speaker;
  node.querySelector(".content").textContent = content;
  node.querySelector(".time").textContent = meta.time || "live";

  if (options.streaming) {
    node.classList.add("streaming");
  } else {
    node.classList.remove("streaming");
  }

  scrollTranscriptToBottom();
}

function renderMessages(messages) {
  for (const message of messages) {
    appendStaticMessage(message);
  }
}

function appendStaticMessage(data) {
  const key = data.message_id || `${data.sender}-${data.turn_index}-${Date.now()}`;
  renderMessage(
    key,
    data.sender || data.speaker || "system",
    data.content || "",
    {
      time: data.timestamp ? new Date(data.timestamp).toLocaleTimeString() : "live",
    },
    {
      variant: data.sender === "User" ? "user" : "",
      streaming: false,
    }
  );
}

async function pollSessionMessages(sessionId) {
  const response = await fetch(`/sessions/${sessionId}/messages?limit=200`);
  if (!response.ok) {
    throw new Error(`Failed to poll messages: ${response.status}`);
  }

  const payload = await response.json();
  renderMessages(payload.messages || []);
}

function startPolling(sessionId) {
  stopPolling();
  pollSessionMessages(sessionId).catch((error) => console.error(error.message));
  pollTimer = window.setInterval(() => {
    pollSessionMessages(sessionId).catch((error) => console.error(error.message));
  }, 1200);
}

function stopPolling() {
  if (pollTimer !== null) {
    window.clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function startDebate() {
  const topic = topicInput.value.trim() || null;
  const rounds = Number.parseInt(roundsInput.value, 10) || 3;

  startBtn.disabled = true;
  startBtn.textContent = "Starting...";

  try {
    const response = await fetch("/sessions/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic, rounds }),
    });

    if (!response.ok) {
      const errBody = await response.text();
      throw new Error(`Failed to start debate: ${response.status} - ${errBody}`);
    }

    const payload = await response.json();
    setActiveSession(payload.session_id);
    transcript.innerHTML = "";
    streamNodes.clear();
    pendingLaunch = { sessionId: payload.session_id, rounds };
    launchRequested = false;
    startPolling(payload.session_id);
    launchDebate(payload.session_id, rounds).catch((error) => {
      console.error(error.message);
    });
  } catch (error) {
    console.error(error.message);
  } finally {
    startBtn.disabled = false;
    startBtn.textContent = "Start debate";
  }
}

async function launchDebate(sessionId, rounds) {
  const response = await fetch(`/sessions/${sessionId}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rounds }),
  });

  if (!response.ok) {
    throw new Error(`Failed to launch debate: ${response.status}`);
  }
}

async function endDebate() {
  if (!activeSessionId) {
    return;
  }

  const response = await fetch(`/sessions/${activeSessionId}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error(`Failed to end session: ${response.status}`);
  }

  stopPolling();
  setActiveSession(null);
  pendingLaunch = null;
  launchRequested = false;
}

async function sendUserMessage() {
  if (!activeSessionId) {
    return;
  }

  const content = userMessageInput.value.trim();
  if (!content) {
    return;
  }

  const response = await fetch(`/sessions/${activeSessionId}/user-message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });

  if (!response.ok) {
    throw new Error(`Failed to send message: ${response.status}`);
  }

  userMessageInput.value = "";
  const payload = await response.json();
  if (payload?.message) {
    appendStaticMessage(payload.message);
  }
}

startBtn.addEventListener("click", () => {
  startDebate().catch((error) => console.error(error.message));
});

sendMessageBtn.addEventListener("click", () => {
  sendUserMessage().catch((error) => console.error(error.message));
});

userMessageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    sendUserMessage().catch((error) => console.error(error.message));
  }
});

endDebateBtn.addEventListener("click", () => {
  endDebate().catch((error) => console.error(error.message));
});

// setActiveSession(null);
