/* js/ui-controller.js - UI Slide Drawer Animations, Siri visualizer Observers, and Audio Monkey-patches */

document.addEventListener("DOMContentLoaded", () => {
  // 1. Sidebar Slide Controls (Left hamburger sidebar)
  const hamburgerBtn = document.getElementById("hamburgerBtn");
  const leftSidebar = document.getElementById("leftSidebar");
  const leftSidebarOverlay = document.getElementById("leftSidebarOverlay");
  const closeSidebarBtn = document.getElementById("closeSidebarBtn");

  if (hamburgerBtn && leftSidebar && leftSidebarOverlay) {
    const openSidebar = () => {
      leftSidebar.classList.add("open");
      leftSidebarOverlay.classList.add("visible");
    };
    const closeSidebar = () => {
      leftSidebar.classList.remove("open");
      leftSidebarOverlay.classList.remove("visible");
    };

    hamburgerBtn.addEventListener("click", openSidebar);
    leftSidebarOverlay.addEventListener("click", closeSidebar);
    if (closeSidebarBtn) {
      closeSidebarBtn.addEventListener("click", closeSidebar);
    }
  }

  // 2. Right Analytics Drawer Toggle Controls
  const openAnalyticsBtn = document.getElementById("openAnalyticsBtn");
  const analyticsSidebar = document.getElementById("analyticsSidebar");
  const analyticsOverlay = document.getElementById("analyticsOverlay");
  const closeAnalyticsBtn = document.getElementById("closeAnalyticsBtn");

  if (openAnalyticsBtn && analyticsSidebar && analyticsOverlay) {
    const openDrawer = () => {
      analyticsSidebar.classList.add("open");
      analyticsOverlay.classList.add("visible");
      // Dispatch window resize event so Chart.js recalculates layout inside the drawer
      setTimeout(() => {
        window.dispatchEvent(new Event('resize'));
      }, 100);
    };
    const closeDrawer = () => {
      analyticsSidebar.classList.remove("open");
      analyticsOverlay.classList.remove("visible");
    };

    openAnalyticsBtn.addEventListener("click", openDrawer);
    analyticsOverlay.addEventListener("click", closeDrawer);
    if (closeAnalyticsBtn) {
      closeAnalyticsBtn.addEventListener("click", closeDrawer);
    }
  }

  // 3. CSS Audio Interceptor / Monkey-patching to stop TTS
  let activeAudioInstance = null;
  const OriginalAudioConstructor = window.Audio;
  window.Audio = function(...args) {
    const audioObject = new OriginalAudioConstructor(...args);
    activeAudioInstance = audioObject;
    return audioObject;
  };

  const stopTtsBtn = document.getElementById("stopTtsBtn");
  const ttsEnableCheckbox = document.getElementById("ttsEnable");

  if (stopTtsBtn) {
    stopTtsBtn.addEventListener("click", () => {
      // Pause currently playing audio
      if (activeAudioInstance) {
        activeAudioInstance.pause();
        activeAudioInstance.currentTime = 0;
      }
      // Turn off TTS checkbox so future statements aren't synthesized
      if (ttsEnableCheckbox) {
        ttsEnableCheckbox.checked = false;
      }
    });
  }

  // 4. Two-State visual controller observer
  const bodyEl = document.body;
  const ttsProviderSelect = document.getElementById("ttsProvider");
  const activeTtsBadge = document.getElementById("activeTtsBadge");

  // Set initial TTS Provider label on page load
  if (ttsProviderSelect && activeTtsBadge) {
    activeTtsBadge.textContent = ttsProviderSelect.value === "edge" ? "Edge TTS" : "ElevenLabs";
    ttsProviderSelect.addEventListener("change", () => {
      activeTtsBadge.textContent = ttsProviderSelect.value === "edge" ? "Edge TTS" : "ElevenLabs";
    });
  }

  // Clear any stale session so page always opens on the landing view
  localStorage.removeItem("activeSessionId");

  const syncViewStates = () => {
    const activeSession = localStorage.getItem("activeSessionId");
    if (activeSession && activeSession !== "null") {
      bodyEl.className = "state-debate";
    } else {
      bodyEl.className = "state-landing";
    }
  };

  // Periodic synchronization check of local storage to animate state switch
  syncViewStates();
  setInterval(syncViewStates, 500);

  // 5. Active Speaker Observer and Voice Orb Synchronization
  const transcriptEl = document.getElementById("transcript");
  const typingIndicatorEl = document.getElementById("typing-indicator");
  const speakingModelNameEl = document.getElementById("speakingModelName");
  const leftSpeakerOrbEl = document.getElementById("leftSpeakerOrb");

  const updateSpeakingLLM = (speaker) => {
    if (!speaker || speaker.toLowerCase() === "system") {
      return;
    }
    if (speakingModelNameEl) {
      speakingModelNameEl.textContent = speaker;
      speakingModelNameEl.className = `speaker-text-${speaker.toLowerCase()}`;
    }
    if (leftSpeakerOrbEl) {
      leftSpeakerOrbEl.className = `voice-orb active-${speaker.toLowerCase()}`;
    }
  };

  // Observe when typing indicator is active
  if (typingIndicatorEl) {
    const typingObserver = new MutationObserver(() => {
      const text = typingIndicatorEl.textContent.trim();
      if (text) {
        // Text is format: "Gemini is thinking..."
        const parts = text.split(" ");
        if (parts.length > 0) {
          updateSpeakingLLM(parts[0]);
        }
      }
    });
    typingObserver.observe(typingIndicatorEl, { childList: true, characterData: true, subtree: true });
  }

  // Observe newly inserted message items in the transcript
  if (transcriptEl) {
    const tagNode = (node) => {
      if (node.nodeType === Node.ELEMENT_NODE && node.classList.contains("message")) {
        // Tag node speaker attribute for custom chat color styling
        const speakerEl = node.querySelector(".speaker");
        if (speakerEl) {
          const speakerName = speakerEl.textContent.trim();
          node.setAttribute("data-speaker", speakerName);
          updateSpeakingLLM(speakerName);
        }
      }
    };

    transcriptEl.childNodes.forEach(tagNode);

    const transcriptObserver = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === "childList") {
          mutation.addedNodes.forEach(tagNode);
        }
      }
    });
    transcriptObserver.observe(transcriptEl, { childList: true, subtree: true });
  }

  // 6. Calculate and Update Debate Progress
  const roundsInputSelect = document.getElementById("roundsInput");
  const debateProgressTextEl = document.getElementById("debateProgressText");
  const debateProgressBarEl = document.getElementById("debateProgressBar");

  const recalculateProgress = () => {
    const listItems = transcriptEl ? transcriptEl.querySelectorAll(".message").length : 0;
    const rounds = parseInt(roundsInputSelect ? roundsInputSelect.value : "3", 10);
    // Assuming 4 AI LLM participants per round
    const totalEstimatedTurns = rounds * 4;
    const progressPercentage = Math.min(100, Math.round((listItems / totalEstimatedTurns) * 100)) || 0;
    
    if (debateProgressTextEl) {
      debateProgressTextEl.textContent = `${progressPercentage}% Completed`;
    }
    if (debateProgressBarEl) {
      debateProgressBarEl.style.width = `${progressPercentage}%`;
    }
  };

  // Periodic progress check
  setInterval(recalculateProgress, 1200);
});
