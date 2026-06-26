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