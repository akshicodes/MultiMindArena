/* js/chat-vars.js - Shared DOM Selector Declarations */

// Lookup Cache Maps
const streamNodes = new Map();
const typingIndicators = new Map();

// TTS Element References
const typingIndicator = document.getElementById("typing-indicator");
const ttsEnableCheckbox = document.getElementById("ttsEnable");
const ttsProviderSelect = document.getElementById("ttsProvider");
const ttsSpeakerCheckboxes = Array.from(
  document.querySelectorAll('input[name="ttsSpeaker"]')
);
const ttsHint = document.getElementById("ttsHint");

// Chat Input & Control References
const topicInput = document.getElementById("topicInput");
const roundsInput = document.getElementById("roundsInput");
const startBtn = document.getElementById("startBtn");
const randomTopicBtn = document.getElementById("randomTopicBtn");
const endDebateBtn = document.getElementById("endDebateBtn");
const sendMessageBtn = document.getElementById("sendMessageBtn");
const userMessageInput = document.getElementById("userMessageInput");
const transcript = document.getElementById("transcript");

// Global Session States
let socket = null;
let activeSessionId = null;
let pendingLaunch = null;
let launchRequested = false;
let pollTimer = null;
let audioQueue = [];
let audioPlaybackInProgress = false;
let autoScroll = true;
