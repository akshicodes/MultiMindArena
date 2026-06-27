/* js/chat-api.js - WebSocket & Session HTTP API Operations */

const ttsStreamState = {};

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
      
      const speaker = payload.speaker;
      const messageId = payload.message_id;
      const content = payload.content;

      if (speaker && speaker !== "User" && isSpeakerEnabledForTts(speaker) && ttsEnableCheckbox?.checked) {
        if (!ttsStreamState[messageId]) {
          ttsStreamState[messageId] = { processedLength: 0 };
        }
        
        const state = ttsStreamState[messageId];
        const unprocessedText = content.substring(state.processedLength);
        
        // Match up to the last sentence boundary in the unprocessed text
        const match = unprocessedText.match(/.*[.!?\n](?=\s|$)/s);
        
        if (match) {
          const chunk = match[0];
          state.processedLength += chunk.length;
          if (chunk.trim()) {
            void playTtsForChunk(messageId, speaker, chunk.trim(), { auto: true });
          }
        }
      }
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
        
        if (speaker && speaker !== "User" && isSpeakerEnabledForTts(speaker) && ttsEnableCheckbox?.checked) {
          const messageId = payload.message.message_id || payload.message_id;
          const content = payload.message.content || "";
          if (messageId) {
            const state = ttsStreamState[messageId];
            const processedLength = state ? state.processedLength : 0;
            
            if (processedLength < content.length) {
              const chunk = content.substring(processedLength);
              if (chunk.trim()) {
                void playTtsForChunk(messageId, speaker, chunk.trim(), { auto: true });
              }
            }
            
            if (state) {
              delete ttsStreamState[messageId];
            }
          }
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

function setActiveSession(sessionId, readOnly = false) {

    activeSessionId = sessionId;

    if (sessionId) {
        localStorage.setItem("activeSessionId", sessionId);
    } else {
        localStorage.removeItem("activeSessionId");
    }

    if (sendMessageBtn)
        sendMessageBtn.disabled = !sessionId || readOnly;

    if (endDebateBtn)
        endDebateBtn.disabled = !sessionId || readOnly;

    if (userMessageInput)
        userMessageInput.disabled = !sessionId || readOnly;
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

function showNotification(message) {
  // Check if container exists, if not create it
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.style.cssText = `
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 9999;
      display: flex;
      flex-direction: column;
      gap: 12px;
      pointer-events: none;
    `;
    document.body.appendChild(container);
  }

  // Create toast element
  const toast = document.createElement("div");
  toast.className = "custom-toast";
  toast.style.cssText = `
    min-width: 280px;
    max-width: 380px;
    background-color: #111111;
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-left: 3px solid #ffffff;
    padding: 14px 16px;
    border-radius: 8px;
    font-family: var(--font-body, 'Plus Jakarta Sans', sans-serif);
    font-size: 0.88rem;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    gap: 12px;
    pointer-events: auto;
    opacity: 0;
    transform: translateY(20px) scale(0.95);
    transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  `;

  // Icon
  const icon = document.createElement("div");
  icon.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
  icon.style.cssText = `
    display: flex;
    align-items: center;
    color: #ffffff;
    flex-shrink: 0;
  `;

  // Text content
  const content = document.createElement("div");
  content.textContent = message;
  content.style.flex = "1";
  content.style.fontWeight = "500";

  // Close button
  const closeBtn = document.createElement("button");
  closeBtn.innerHTML = "&times;";
  closeBtn.style.cssText = `
    background: none;
    border: none;
    color: #888;
    font-size: 1.2rem;
    cursor: pointer;
    padding: 0 4px;
    line-height: 1;
    transition: color 0.2s;
  `;
  closeBtn.onmouseover = () => closeBtn.style.color = '#fff';
  closeBtn.onmouseout = () => closeBtn.style.color = '#888';
  closeBtn.onclick = () => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(20px) scale(0.95)";
    setTimeout(() => toast.remove(), 300);
  };

  toast.appendChild(icon);
  toast.appendChild(content);
  toast.appendChild(closeBtn);
  container.appendChild(toast);

  // Trigger show transition
  requestAnimationFrame(() => {
    toast.style.opacity = "1";
    toast.style.transform = "translateY(0) scale(1)";
  });

  // Auto-remove after 4 seconds
  setTimeout(() => {
    if (toast.parentNode) {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(20px) scale(0.95)";
      setTimeout(() => toast.remove(), 300);
    }
  }, 4000);
}

function stopPolling() {
  if (pollTimer !== null) {
    window.clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function startDebate() {
  const topic = topicInput ? topicInput.value.trim() : "";
  if (!topic) {
    showNotification("Enter a topic to start the debate.");
    return;
  }
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

    if (response.status === 422) {
      showNotification("Enter a topic to start the debate.");
      return;
    }

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

    // Display the active debate topic
    const topicEl = document.getElementById("arenaTopicDisplay");
    if (topicEl) {
      topicEl.textContent = payload.topic || "";
      topicEl.title = payload.topic || "";
      topicEl.style.display = "inline-block";
    }

    startPolling(payload.session_id);
    launchDebate(payload.session_id, payload.topic, rounds).catch((error) => {
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

async function launchDebate(sessionId, topic, rounds) {
  const response = await fetch(`/sessions/${sessionId}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, rounds }),
  });

  if (!response.ok) {
    throw new Error(`Failed to launch debate: ${response.status}`);
  }
}

async function endDebate() {
  // --- Immediate cleanup: stop everything now, don't wait for server ---

  // Capture session ID before we clear it
  const sessionIdToDelete = activeSessionId;

  // 1. Stop audio playback and clear the queue right away
  if (typeof window.stopAllAudio === "function") {
    window.stopAllAudio();
  }

  // 2. Close WebSocket so no more text chunks arrive
  if (socket) {
    try { socket.close(); } catch (e) { console.error("WS close error:", e); }
    socket = null;
  }

  // 3. Stop message polling
  stopPolling();

  // 4. Clear session state and navigate to landing page immediately
  pendingLaunch = null;
  launchRequested = false;
  setActiveSession(null);

  // Clear/hide the topic display
  const topicEl = document.getElementById("arenaTopicDisplay");
  if (topicEl) {
    topicEl.textContent = "";
    topicEl.style.display = "none";
  }

  document.body.className = "state-landing";

  // 5. Fire-and-forget server DELETE (non-blocking)
  if (sessionIdToDelete) {
    fetch(`/sessions/${sessionIdToDelete}`, { method: "DELETE" })
      .catch((e) => console.error("Failed to end session on server:", e));
  }
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

async function loadHistory() {

    try {

        const response =
            await fetch("/sessions");

        if (!response.ok)
            throw new Error("Couldn't load history");

        const sessions =
            await response.json();

        renderHistory(sessions);

    } catch (err) {

        console.error(err);

    }

}


function formatHistoryTime(dateString) {

    const date = new Date(dateString);
    const now = new Date();

    const yesterday = new Date();
    yesterday.setDate(now.getDate() - 1);

    if (date.toDateString() === now.toDateString()) {
        return `Today • ${date.toLocaleTimeString([], {
            hour: "numeric",
            minute: "2-digit"
        })}`;
    }

    if (date.toDateString() === yesterday.toDateString()) {
        return `Yesterday • ${date.toLocaleTimeString([], {
            hour: "numeric",
            minute: "2-digit"
        })}`;
    }

    return `${date.toLocaleDateString([], {
        day: "numeric",
        month: "short"
    })} • ${date.toLocaleTimeString([], {
        hour: "numeric",
        minute: "2-digit"
    })}`;
}
function renderHistory(sessions) {

    const history =
        document.getElementById("historyList");
        

    if (!history)
        return;

    history.innerHTML = "";

    sessions.forEach(session => {

        const item =
            document.createElement("div");

        item.className =
            "history-item";
            item.dataset.sessionId = session.session_id;
item.dataset.status = session.status;

        item.innerHTML = `
    <div class="history-topic">
        ${session.topic}
    </div>

    <div class="history-meta">
        ${formatHistoryTime(session.started_at)}
    </div>
`;

item.addEventListener("click", () => {
    openHistorySession(
        session.session_id,
        session.status
    );
});

        history.appendChild(item);

    });

}



async function openHistorySession(sessionId) {

    try {

        const response =
            await fetch(`/sessions/${sessionId}/messages?limit=200`);

        if (!response.ok)
            throw new Error("Couldn't load messages");

        const data =
            await response.json();

        // Load the session topic
        const sessionResponse = await fetch(`/sessions/${sessionId}`);
        if (sessionResponse.ok) {
            const sessionData = await sessionResponse.json();
            const topicEl = document.getElementById("arenaTopicDisplay");
            if (topicEl) {
                topicEl.textContent = sessionData.topic || "";
                topicEl.title = sessionData.topic || "";
                topicEl.style.display = "inline-block";
            }
        }

          transcript.innerHTML = "";

        streamNodes.clear();
        setActiveSession(sessionId, true);

        renderMessages(data.messages);

        document.body.className = "state-debate";


    } catch(err){

        console.error(err);

    }

}

function startNewDebate() {
  console.log("STEP 1");
    // Close the sidebar
    document
        .getElementById("leftSidebar")
        ?.classList.remove("open");

    document
        .getElementById("leftSidebarOverlay")
        ?.classList.remove("visible");

    // Clear transcript
    transcript.innerHTML = "";
    streamNodes.clear();

    // Clear current session
    setActiveSession(null);

    // Clear input
    if (userMessageInput) {
        userMessageInput.value = "";
    }

    // Clear/hide the topic display
    const topicEl = document.getElementById("arenaTopicDisplay");
    if (topicEl) {
      topicEl.textContent = "";
      topicEl.style.display = "none";
    }

    // Return to landing page
    document.body.className = "state-landing";

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
    fetch("/topics/random")
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(data => {
        if (data && data.topic && topicInput) {
          topicInput.value = data.topic;
        }
      })
      .catch(error => {
        console.error("Error fetching random topic:", error);
      });
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

document.addEventListener(
    "DOMContentLoaded",
    () => {

        loadHistory();

    }
);

const newDebateBtn =
    document.getElementById("newDebateBtn");

if (newDebateBtn) {

    newDebateBtn.addEventListener(
        "click",
        startNewDebate
    );

}