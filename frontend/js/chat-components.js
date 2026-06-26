/* js/chat-components.js - Message Rendering & Audio Player Components */

// Listen to transcript scrolling to manage auto-scroll state
if (transcript) {
  transcript.addEventListener("scroll", () => {
    const nearBottom =
      transcript.scrollHeight -
      transcript.scrollTop -
      transcript.clientHeight < 50;
    autoScroll = nearBottom;
  });
}

function showTypingIndicator(speaker) {
  if (!typingIndicator) return;
  typingIndicator.textContent = `${speaker} is thinking...`;
}

function removeTypingIndicator() {
  if (!typingIndicator) return;
  typingIndicator.textContent = "";
}

function scrollTranscriptToBottom() {
  if (autoScroll && transcript) {
    transcript.scrollTop = transcript.scrollHeight;
  }
}

function getSelectedTtsSpeakers() {
  return new Set(
    ttsSpeakerCheckboxes.filter((checkbox) => checkbox.checked).map((checkbox) => checkbox.value)
  );
}

function isSpeakerEnabledForTts(speaker) {
  return getSelectedTtsSpeakers().has(speaker);
}

function setMessageTtsStatus(key, status, variant = "") {
  const node = streamNodes.get(key);
  if (!node) return;

  const statusEl = node.querySelector(".tts-status");
  const buttonEl = node.querySelector(".tts-btn");
  if (statusEl) {
    statusEl.textContent = status || "";
    statusEl.className = `tts-status ${variant}`.trim();
  }

  if (buttonEl) {
    buttonEl.classList.toggle("loading", variant === "loading");
    buttonEl.classList.toggle("error", variant === "error");
  }
}

function enqueueAudio(item) {
  audioQueue.push(item);
  if (!audioPlaybackInProgress) {
    void processAudioQueue();
  }
}

async function deleteAudioFile(audioUrl) {
  try {
    await fetch(audioUrl, { method: "DELETE" });
  } catch (error) {
    console.error("Failed to delete temporary audio file:", error);
  }
}

async function processAudioQueue() {
  if (audioPlaybackInProgress || audioQueue.length === 0) {
    return;
  }

  const item = audioQueue.shift();
  if (!item) {
    return;
  }

  audioPlaybackInProgress = true;
  setMessageTtsStatus(item.messageKey, "Playing…", "loading");

  try {
    const audio = new Audio(item.audioUrl);
    audio.preload = "auto";
    audio.onended = () => {
      audioPlaybackInProgress = false;
      setMessageTtsStatus(item.messageKey, "", "");
      void deleteAudioFile(item.audioUrl);
      void processAudioQueue();
    };
    audio.onerror = () => {
      audioPlaybackInProgress = false;
      setMessageTtsStatus(item.messageKey, "Playback failed", "error");
      void deleteAudioFile(item.audioUrl);
      void processAudioQueue();
    };

    if (typeof window.updateSpeakingLLM === "function" && item.speaker) {
      window.updateSpeakingLLM(item.speaker);
    }

    await audio.play();
  } catch (error) {
    audioPlaybackInProgress = false;
    setMessageTtsStatus(item.messageKey, "Playback blocked", "error");
    void deleteAudioFile(item.audioUrl);
    void processAudioQueue();
  }
}

async function playTtsForMessage(message, options = {}) {
  const speaker = message?.sender || message?.speaker || "GPT";
  const content = message?.content || "";
  const messageKey = message?.message_id || `${speaker}-${content}`;

  if (!content) {
    return;
  }

  if (!options.force && !ttsEnableCheckbox?.checked) {
    return;
  }

  if (!options.force && !isSpeakerEnabledForTts(speaker)) {
    return;
  }

  setMessageTtsStatus(messageKey, "Generating…", "loading");

  try {
    const response = await fetch("/sessions/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider: ttsProviderSelect?.value || "edge",
        speaker,
        text: content,
      }),
    });

    if (!response.ok) {
      throw new Error(`TTS failed: ${response.status}`);
    }

    const payload = await response.json();
    if (!payload?.audio_url) {
      throw new Error("No audio URL returned");
    }

    enqueueAudio({
      messageKey,
      audioUrl: payload.audio_url,
      speaker,
    });
  } catch (error) {
    setMessageTtsStatus(messageKey, error.message || "TTS unavailable", "error");
  }
}

async function playTtsForChunk(messageKey, speaker, chunkContent, options = {}) {
  if (!chunkContent) {
    return;
  }

  if (!options.force && !ttsEnableCheckbox?.checked) {
    return;
  }

  if (!options.force && !isSpeakerEnabledForTts(speaker)) {
    return;
  }

  try {
    const response = await fetch("/sessions/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider: ttsProviderSelect?.value || "edge",
        speaker,
        text: chunkContent,
      }),
    });

    if (!response.ok) {
      throw new Error(`TTS chunk failed: ${response.status}`);
    }

    const payload = await response.json();
    if (!payload?.audio_url) {
      throw new Error("No audio URL returned for chunk");
    }

    enqueueAudio({
      messageKey,
      audioUrl: payload.audio_url,
      speaker,
    });
  } catch (error) {
    console.error("TTS chunk error:", error);
    setMessageTtsStatus(messageKey, error.message || "TTS chunk unavailable", "error");
  }
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
      <div class="message-actions">
        <button type="button" class="tts-btn" title="Play audio">🔊</button>
        <span class="tts-status"></span>
      </div>
    `;
    if (transcript) {
      transcript.appendChild(node);
    }
    streamNodes.set(key, node);
  }

  node.className = `message ${options.variant || ""}`.trim();
  node.querySelector(".speaker").textContent = speaker;
  node.querySelector(".content").textContent = content;
  node.querySelector(".time").textContent = meta.time || "live";

  const button = node.querySelector(".tts-btn");
  if (button) {
    button.disabled = !content;
    button.onclick = (event) => {
      event.preventDefault();
      void playTtsForMessage({ message_id: key, sender: speaker, content, speaker }, { force: true });
    };
  }

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
