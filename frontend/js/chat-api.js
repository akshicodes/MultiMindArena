/* js/chat-api.js - WebSocket & Session HTTP API Operations */

function connectWebSocket(sessionId) {
  if (socket) {
    socket.close();
  }

  const protocol =
    window.location.protocol === "https:"
      ? "wss:"
      : "ws:";

  socket = new WebSocket(
    `${protocol}//${window.location.host}/sessions/${sessionId}/ws`
  );

  socket.onopen = () => {
    console.log("WebSocket connected");
  };

  socket.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    console.log("WS EVENT:", payload);

    if (payload.event === "speaker.thinking") {
      showTypingIndicator(payload.speaker);
      return;
    }

    if (payload.event === "message.stream") {
      removeTypingIndicator();
      return;
    }

    if (payload.event === "message.final") {
      const speaker =
        payload.message?.sender ||
        payload.message?.speaker;

      if (speaker) {
        removeTypingIndicator();
      }

      if (payload.message) {
        appendStaticMessage(payload.message);
        if (speaker && speaker !== "User") {
          void playTtsForMessage(payload.message, { auto: true });
        }
      }

      return;
    }
  };

  socket.onclose = () => {
    console.log("WebSocket disconnected");
  };

  socket.onerror = (err) => {
    console.error("WebSocket error", err);
  };
}

function setActiveSession(sessionId) {
  activeSessionId = sessionId;

  if (sessionId) {
    localStorage.setItem("activeSessionId", sessionId);
  } else {
    localStorage.removeItem("activeSessionId");
  }

  if (sendMessageBtn) sendMessageBtn.disabled = !sessionId;
  if (endDebateBtn) endDebateBtn.disabled = !sessionId;
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
  const topic = topicInput ? topicInput.value.trim() : null;
  const rounds = Number.parseInt(roundsInput ? roundsInput.value : "3", 10) || 3;

  if (startBtn) {
    startBtn.disabled = true;
    startBtn.textContent = "Starting...";
  }

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
    connectWebSocket(payload.session_id);
    if (transcript) transcript.innerHTML = "";
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
    if (startBtn) {
      startBtn.disabled = false;
      startBtn.textContent = "Start Debate";
    }
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

  const content = userMessageInput ? userMessageInput.value.trim() : "";
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

  if (userMessageInput) userMessageInput.value = "";
  const payload = await response.json();
  if (payload?.message) {
    appendStaticMessage(payload.message);
  }
}

// Bind Action Listeners
if (startBtn) {
  startBtn.addEventListener("click", () => {
    startDebate().catch((error) => console.error(error.message));
  });
}

if (sendMessageBtn) {
  sendMessageBtn.addEventListener("click", () => {
    sendUserMessage().catch((error) => console.error(error.message));
  });
}

if (randomTopicBtn) {
  randomTopicBtn.addEventListener("click", () => {
    if (topicInput) topicInput.value = "";
    startDebate().catch((error) => console.error(error.message));
  });
}

if (userMessageInput) {
  userMessageInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      sendUserMessage().catch((error) => console.error(error.message));
    }
  });
}

if (endDebateBtn) {
  endDebateBtn.addEventListener("click", () => {
    endDebate().catch((error) => console.error(error.message));
  });
}
