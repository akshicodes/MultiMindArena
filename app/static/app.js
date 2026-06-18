const topicInput = document.getElementById("topicInput");
const roundsInput = document.getElementById("roundsInput");
const randomTopicBtn = document.getElementById("randomTopicBtn");
const startBtn = document.getElementById("startBtn");
const disconnectBtn = document.getElementById("disconnectBtn");
const sendMessageBtn = document.getElementById("sendMessageBtn");
const userMessageInput = document.getElementById("userMessageInput");
const loadSessionInput = document.getElementById("loadSessionInput");
const loadSessionBtn = document.getElementById("loadSessionBtn");
const endSessionBtn = document.getElementById("endSessionBtn");
const endDebateBtn = document.getElementById("endDebateBtn");

function setEndButtonsDisabled(disabled) {
  if (endSessionBtn) endSessionBtn.disabled = disabled;
  if (endDebateBtn) endDebateBtn.disabled = disabled;
}
const createSessionBtn = document.getElementById("createSessionBtn");
const newTopicInput = document.getElementById("newTopicInput");
const topicCategoryInput = document.getElementById("topicCategoryInput");
const topicDifficultyInput = document.getElementById("topicDifficultyInput");
const topicTagsInput = document.getElementById("topicTagsInput");
const createTopicBtn = document.getElementById("createTopicBtn");
const listTopicsBtn = document.getElementById("listTopicsBtn");
const topicsOutput = document.getElementById("topicsOutput");
const llmConfigInput = document.getElementById("llmConfigInput");
const createLlmConfigBtn = document.getElementById("createLlmConfigBtn");
const configOutput = document.getElementById("configOutput");
const transcript = document.getElementById("transcript");
const sessionIdLabel = document.getElementById("sessionId");
const connectionStateLabel = document.getElementById("connectionState");
const topicAttributedToLabel = document.getElementById("topicAttributedTo");
const liveHint = document.getElementById("liveHint");
const toggleFullscreenBtn = document.getElementById("toggleFullscreenBtn");
const transcriptPanel = document.getElementById("transcriptPanel");


let socket = null;
let activeSessionId = null;
let pendingLaunch = null;
let launchRequested = false;
const streamNodes = new Map();

function setConnectionState(value) {
  connectionStateLabel.textContent = value;
}

function setActiveSession(sessionId) {
  activeSessionId = sessionId;
  sessionIdLabel.textContent = sessionId || "Not started";
  sendMessageBtn.disabled = !sessionId;
  disconnectBtn.disabled = !socket;
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

function setOutput(element, value) {
  element.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    const message = typeof payload === "string" ? payload : JSON.stringify(payload);
    throw new Error(message || `Request failed: ${response.status}`);
  }

  return payload;
}

function renderMessages(messages) {
  transcript.innerHTML = "";
  streamNodes.clear();

  for (const message of messages) {
    appendStaticMessage(message);
  }
}

async function loadSession(sessionId, attachSocket = true) {
  if (!sessionId) {
    return;
  }

  const [session, messagesPayload] = await Promise.all([
    requestJson(`/sessions/${sessionId}`),
    requestJson(`/sessions/${sessionId}/messages?limit=200`),
  ]);

  setActiveSession(sessionId);
  loadSessionInput.value = sessionId;
  topicInput.value = session.topic || topicInput.value;
  topicAttributedToLabel.textContent = session.topic_attributed_to || "-";
  renderMessages(messagesPayload.messages || []);
  setConnectionState(session.status === "active" ? "Loaded active session" : `Loaded ${session.status}`);
  liveHint.textContent = `Loaded ${messagesPayload.messages?.length || 0} messages`;

  if (session.status === "active" && attachSocket) {
    connectSocket(sessionId);
  }
}

function connectSocket(sessionId) {
  if (socket) {
    socket.close();
  }

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  socket = new WebSocket(`${protocol}://${window.location.host}/sessions/${sessionId}/ws`);
  setConnectionState("Connecting");
  disconnectBtn.disabled = false;
  setEndButtonsDisabled(false);

  socket.onopen = () => {
    setConnectionState("Connected");
    liveHint.textContent = "Streaming debate events";

    if (pendingLaunch && !launchRequested) {
      launchRequested = true;
      launchDebate(pendingLaunch.sessionId, pendingLaunch.rounds).catch((error) => {
        liveHint.textContent = error.message;
      });
    }
  };

  socket.onmessage = (event) => {
    const payload = JSON.parse(event.data);

    if (payload.event === "speaker.thinking") {
      renderMessage(
        payload.message_id,
        payload.speaker,
        `${payload.speaker} is preparing an argument...`,
        { time: "thinking" },
        { streaming: true, variant: "thinking" }
      );
      return;
    }

    if (payload.event === "topic.injected") {
      topicAttributedToLabel.textContent = payload.attributed_to || "-";
      renderMessage(
        `topic-${payload.session_id}`,
        payload.attributed_to || "Topic",
        payload.topic,
        { time: "seed" }
      );
      return;
    }

    if (payload.event === "message.stream") {
      renderMessage(
        payload.message_id || `stream-${payload.speaker}`,
        payload.speaker,
        payload.content,
        { time: "streaming" },
        { streaming: true }
      );
      return;
    }

    if (payload.event === "message.final") {
      const message = payload.message;
      if (!message) {
        return;
      }
      renderMessage(
        message.message_id,
        message.sender,
        message.content,
        {
          time: new Date(message.timestamp).toLocaleTimeString(),
        },
        { streaming: false }
      );
    }
  };

  socket.onclose = () => {
    setConnectionState("Disconnected");
    liveHint.textContent = "Socket closed";
    disconnectBtn.disabled = true;
    setEndButtonsDisabled(!activeSessionId);
  };

  socket.onerror = () => {
    setConnectionState("Socket error");
  };
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
      console.error("Start debate error details:", errBody);
      throw new Error(`Failed to start debate: ${response.status} - ${errBody}`);
    }

    const payload = await response.json();
    setActiveSession(payload.session_id);
    topicAttributedToLabel.textContent = payload.topic_attributed_to || "-";
    setConnectionState("Starting stream");
    transcript.innerHTML = "";
    streamNodes.clear();
    pendingLaunch = { sessionId: payload.session_id, rounds };
    launchRequested = false;
    connectSocket(payload.session_id);
  } catch (error) {
    setConnectionState("Start failed");
    liveHint.textContent = error.message;
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

async function endSession() {
  if (!activeSessionId) {
    return;
  }

  const payload = await requestJson(`/sessions/${activeSessionId}`, {
    method: "DELETE",
  });

  if (socket) {
    socket.close();
    socket = null;
  }

  setConnectionState(`Session ${payload.status}`);
  setEndButtonsDisabled(true);
}

async function createSessionRecord() {
  const sessionId = crypto.randomUUID();
  const payload = {
    session_id: sessionId,
    topic: topicInput.value.trim() || "Untitled discussion",
    topic_attributed_to: "User",
    started_at: new Date().toISOString(),
    ended_at: null,
    participants: ["Gemini", "GPT", "Nemotron", "Step"],
    status: "active",
    total_messages: 0,
    persona_map: {
      Gemini: "Fact-Checker",
      GPT: "Contrarian",
      Nemotron: "Philosopher",
      Step: "Provocateur",
    },
  };

  const result = await requestJson("/sessions/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  loadSessionInput.value = result.session_id;
  liveHint.textContent = `Created session ${result.session_id}`;
}

async function createTopic() {
  const result = await requestJson("/topics/", {
    method: "POST",
    body: JSON.stringify({
      topic: newTopicInput.value.trim(),
      category: topicCategoryInput.value.trim(),
      difficulty: Number.parseInt(topicDifficultyInput.value, 10) || 3,
      tags: topicTagsInput.value.split(",").map((tag) => tag.trim()).filter(Boolean),
    }),
  });

  setOutput(topicsOutput, result);
}

async function listTopics() {
  const result = await requestJson("/topics/?limit=10");
  setOutput(topicsOutput, result);
}

async function createLlmConfig() {
  const payload = JSON.parse(llmConfigInput.value);
  const result = await requestJson("/topics/api/llm-configs", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  setOutput(configOutput, result);
}

async function fetchRandomTopic() {
  const response = await fetch("/topics/random");
  const payload = await response.json();
  if (payload.topic) {
    topicInput.value = payload.topic;
  }
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

  if (response.ok) {
    appendStaticMessage({ sender: "User", content, timestamp: new Date().toISOString() });
    userMessageInput.value = "";
  }
}

randomTopicBtn.addEventListener("click", () => {
  fetchRandomTopic().catch(() => {
    liveHint.textContent = "Could not load a random topic";
  });
});

loadSessionBtn.addEventListener("click", () => {
  loadSession(loadSessionInput.value.trim(), true).catch((error) => {
    liveHint.textContent = error.message;
  });
});

endSessionBtn.addEventListener("click", () => {
  endSession().catch((error) => {
    liveHint.textContent = error.message;
  });
});

createSessionBtn.addEventListener("click", () => {
  createSessionRecord().catch((error) => {
    liveHint.textContent = error.message;
  });
});

createTopicBtn.addEventListener("click", () => {
  createTopic().catch((error) => {
    setOutput(topicsOutput, error.message);
  });
});

listTopicsBtn.addEventListener("click", () => {
  listTopics().catch((error) => {
    setOutput(topicsOutput, error.message);
  });
});

createLlmConfigBtn.addEventListener("click", () => {
  createLlmConfig().catch((error) => {
    setOutput(configOutput, error.message);
  });
});

startBtn.addEventListener("click", () => {
  startDebate().catch((error) => {
    liveHint.textContent = error.message;
  });
});

disconnectBtn.addEventListener("click", () => {
  if (socket) {
    socket.close();
    socket = null;
  }
  pendingLaunch = null;
  launchRequested = false;
  setConnectionState("Disconnected");
  disconnectBtn.disabled = true;
  setEndButtonsDisabled(!activeSessionId);
});

sendMessageBtn.addEventListener("click", () => {
  sendUserMessage().catch((error) => {
    liveHint.textContent = error.message;
  });
});

userMessageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    sendUserMessage().catch((error) => {
      liveHint.textContent = error.message;
    });
  }
});

function toggleFullscreen() {
  const isFullscreen = transcriptPanel.classList.toggle("fullscreen");
  const expandIcon = toggleFullscreenBtn.querySelector(".icon-expand");
  const shrinkIcon = toggleFullscreenBtn.querySelector(".icon-shrink");
  
  if (isFullscreen) {
    expandIcon.classList.add("hidden");
    shrinkIcon.classList.remove("hidden");
    document.body.style.overflow = "hidden"; // Prevent scrolling main page behind fullscreen
  } else {
    expandIcon.classList.remove("hidden");
    shrinkIcon.classList.add("hidden");
    document.body.style.overflow = "";
  }
}

toggleFullscreenBtn.addEventListener("click", toggleFullscreen);

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && transcriptPanel.classList.contains("fullscreen")) {
    toggleFullscreen();
  }
});

endDebateBtn.addEventListener("click", () => {
  endSession().catch((error) => {
    liveHint.textContent = error.message;
  });
});


setConnectionState("Idle");

const initialSessionId = new URLSearchParams(window.location.search).get("session_id");
if (initialSessionId) {
  loadSession(initialSessionId, true).catch((error) => {
    liveHint.textContent = error.message;
  });
}