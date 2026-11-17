/**
 * JARVIS Client Application Controller
 * Manages push-to-talk speech recognition, speech synthesis,
 * central Arc Reactor visualizer states, session conversational memory,
 * and communication with the local Flask backend.
 */

// DOM Elements
const chatBox = document.getElementById('chat-box');
const inputText = document.getElementById('input-text');
const sendBtn = document.getElementById('send-btn');
const voiceBtn = document.getElementById('voice-btn');
const stopBtn = document.getElementById('stop-btn');
const muteBtn = document.getElementById('mute-btn');
const clearChatBtn = document.getElementById('clear-chat-btn');
const settingsToggleBtn = document.getElementById('settings-toggle-btn');
const closeSettingsBtn = document.getElementById('close-settings-btn');
const settingsDrawer = document.getElementById('settings-drawer');

// HUD & Visualizer Elements
const arcReactor = document.getElementById('arc-reactor');
const orbStateLabel = document.getElementById('orb-state-label');
const statusText = document.getElementById('status-text');
const hudClock = document.getElementById('hud-clock');
const aiStatusIndicator = document.getElementById('ai-status-indicator');
const quickCommands = document.getElementById('quick-commands');

// Voice Settings Elements
const voiceSelect = document.getElementById('voice-select');
const pitchSlider = document.getElementById('pitch-slider');
const rateSlider = document.getElementById('rate-slider');
const volumeSlider = document.getElementById('volume-slider');
const pitchVal = document.getElementById('pitch-val');
const rateVal = document.getElementById('rate-val');
const volumeVal = document.getElementById('volume-val');

// Application State
let isMuted = false;
let isSpeaking = false;
let isListening = false;
let selectedVoice = null;
let sessionHistory = []; // In-memory multi-turn conversational session
let recognition = null;

// Backend API Base URL (defaults to current origin or port 5000)
const API_BASE = window.location.origin.includes('5000') 
  ? window.location.origin 
  : (window.location.protocol === 'file:' ? 'http://127.0.0.1:5000' : window.location.origin);

/* ==============================================================
   Visualizer & State Manager
   ============================================================== */
function setAssistantState(state, labelText) {
  arcReactor.classList.remove('state-idle', 'state-listening', 'state-processing', 'state-speaking', 'state-error');
  arcReactor.classList.add(`state-${state}`);

  if (labelText) {
    orbStateLabel.textContent = labelText;
  } else {
    switch (state) {
      case 'idle':
        orbStateLabel.textContent = 'ONLINE // AWAITING COMMAND';
        break;
      case 'listening':
        orbStateLabel.textContent = 'LISTENING // AUDIO INPUT ACTIVE';
        break;
      case 'processing':
        orbStateLabel.textContent = 'PROCESSING // NEURAL CORE ENGAGED';
        break;
      case 'speaking':
        orbStateLabel.textContent = 'VOCALIZING // AUDIO TRANSMISSION';
        break;
      case 'error':
        orbStateLabel.textContent = 'DIAGNOSTIC ALERT // ATTENTION REQUIRED';
        break;
    }
  }
}

/* ==============================================================
   Clock & Status Heartbeat
   ============================================================== */
function updateClock() {
  const now = new Date();
  hudClock.textContent = now.toLocaleTimeString([], { hour12: false });
}
setInterval(updateClock, 1000);
updateClock();

async function checkSystemStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/status`);
    if (res.ok) {
      const data = await res.json();
      statusText.textContent = 'ONLINE // CORE ACTIVE';
      statusText.style.color = '#00f0ff';
      if (data.ai_configured) {
        aiStatusIndicator.textContent = `AI Engine: ${data.ai_provider.toUpperCase()} (Online) | OS: ${data.os}`;
      } else {
        aiStatusIndicator.textContent = `AI Engine: Offline (Set GEMINI_API_KEY in .env) | OS: ${data.os}`;
      }
    } else {
      throw new Error(`HTTP ${res.status}`);
    }
  } catch (err) {
    statusText.textContent = 'STANDALONE // SERVER OFFLINE';
    statusText.style.color = '#ffb703';
    aiStatusIndicator.textContent = 'Backend server unreachable. Start server via "python app.py"';
  }
}

/* ==============================================================
   Speech Synthesis (TTS)
   ============================================================== */
function populateVoiceList() {
  if (!('speechSynthesis' in window)) return;
  const voices = window.speechSynthesis.getVoices();
  voiceSelect.innerHTML = '';

  if (voices.length === 0) return;

  // Prefer British / English male voice fitting JARVIS, fallback to English
  const preferredVoice = voices.find(v => 
    (v.name.includes('UK English Male') || v.name.includes('George') || v.name.includes('David') || v.name.includes('Oliver'))
  ) || voices.find(v => v.lang.startsWith('en-GB'))
    || voices.find(v => v.lang.startsWith('en'))
    || voices[0];

  voices.forEach(voice => {
    const option = document.createElement('option');
    option.value = voice.name;
    option.textContent = `${voice.name} (${voice.lang})`;
    if (preferredVoice && voice.name === preferredVoice.name) {
      option.selected = true;
      selectedVoice = voice;
    }
    voiceSelect.appendChild(option);
  });

  if (!selectedVoice) selectedVoice = preferredVoice;
}

if ('speechSynthesis' in window) {
  window.speechSynthesis.onvoiceschanged = populateVoiceList;
  populateVoiceList();
}

voiceSelect.addEventListener('change', () => {
  const voices = window.speechSynthesis.getVoices();
  selectedVoice = voices.find(v => v.name === voiceSelect.value) || voices[0];
});

// Slider display updates
pitchSlider.oninput = () => { pitchVal.textContent = pitchSlider.value; };
rateSlider.oninput = () => { rateVal.textContent = rateSlider.value; };
volumeSlider.oninput = () => { volumeVal.textContent = `${Math.round(volumeSlider.value * 100)}%`; };

function speakText(text) {
  if (isMuted || !('speechSynthesis' in window)) {
    setAssistantState('idle');
    return;
  }

  window.speechSynthesis.cancel();

  // Strip markdown formatting characters for natural speech
  const cleanSpeech = text
    .replace(/[*_#`~\[\]\(\)]/g, '')
    .replace(/https?:\/\/\S+/g, 'link')
    .trim();

  if (!cleanSpeech) {
    setAssistantState('idle');
    return;
  }

  const utterance = new SpeechSynthesisUtterance(cleanSpeech);
  if (selectedVoice) utterance.voice = selectedVoice;
  utterance.pitch = parseFloat(pitchSlider.value);
  utterance.rate = parseFloat(rateSlider.value);
  utterance.volume = parseFloat(volumeSlider.value);

  utterance.onstart = () => {
    isSpeaking = true;
    setAssistantState('speaking');
    const allJarvisCards = chatBox.querySelectorAll('.message-card.jarvis');
    if (allJarvisCards.length > 0) {
      allJarvisCards[allJarvisCards.length - 1].classList.add('speaking');
    }
  };

  utterance.onend = () => {
    isSpeaking = false;
    setAssistantState('idle');
    chatBox.querySelectorAll('.message-card.jarvis.speaking').forEach(el => el.classList.remove('speaking'));
  };

  utterance.onerror = () => {
    isSpeaking = false;
    setAssistantState('idle');
    chatBox.querySelectorAll('.message-card.jarvis.speaking').forEach(el => el.classList.remove('speaking'));
  };

  window.speechSynthesis.speak(utterance);
}

function stopSpeaking() {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
  isSpeaking = false;
  setAssistantState('idle');
  chatBox.querySelectorAll('.message-card.jarvis.speaking').forEach(el => el.classList.remove('speaking'));
}

/* ==============================================================
   Speech Recognition (Push-to-Talk)
   ============================================================== */
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

function setupSpeechRecognition() {
  if (!SpeechRecognition) {
    voiceBtn.disabled = true;
    voiceBtn.title = 'Speech Recognition is not supported in this browser.';
    voiceBtn.querySelector('.voice-btn-label').textContent = 'Voice Unavailable';
    return;
  }

  recognition = new SpeechRecognition();
  recognition.continuous = false; // Push-to-talk: single utterance per activation
  recognition.interimResults = false;
  recognition.lang = 'en-US';

  recognition.onstart = () => {
    isListening = true;
    voiceBtn.classList.add('listening');
    voiceBtn.querySelector('.voice-btn-label').textContent = 'Listening... (Speak Now)';
    setAssistantState('listening');
  };

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript.trim();
    if (transcript) {
      inputText.value = transcript;
      handleSendMessage(transcript);
    }
  };

  recognition.onerror = (event) => {
    console.error('Speech recognition error:', event.error);
    isListening = false;
    resetVoiceButton();
    setAssistantState('idle');

    if (event.error === 'not-allowed') {
      appendMessage('Microphone access was denied. Please allow microphone permissions in your browser to use voice input, sir.', 'jarvis', false, true);
    } else if (event.error !== 'no-speech') {
      appendMessage(`Voice recognition issue encountered (${event.error}), sir. You may type your message instead.`, 'jarvis', false, true);
    }
  };

  recognition.onend = () => {
    isListening = false;
    resetVoiceButton();
    if (!isSpeaking) {
      setAssistantState('idle');
    }
  };
}

function resetVoiceButton() {
  voiceBtn.classList.remove('listening');
  voiceBtn.querySelector('.voice-btn-label').textContent = 'Push To Talk';
}

function togglePushToTalk() {
  if (!recognition) return;

  if (isListening) {
    recognition.stop();
    isListening = false;
    resetVoiceButton();
    setAssistantState('idle');
  } else {
    // If JARVIS is currently speaking, stop him so user can speak
    stopSpeaking();
    try {
      recognition.start();
    } catch (e) {
      console.warn('Recognition start exception:', e);
    }
  }
}

/* ==============================================================
   Chat Rendering & Session Logic
   ============================================================== */
function appendMessage(text, sender, actionBadge = null, isError = false) {
  const card = document.createElement('div');
  card.className = `message-card ${sender}${isError ? ' error' : ''}`;

  const meta = document.createElement('div');
  meta.className = 'message-meta';

  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const senderLabel = sender === 'user' ? 'USER' : 'JARVIS';

  meta.innerHTML = `<span>${senderLabel}</span><span>${time}</span>`;
  card.appendChild(meta);

  const content = document.createElement('div');
  content.className = 'message-content';
  content.textContent = text;
  card.appendChild(content);

  if (actionBadge) {
    const badge = document.createElement('div');
    badge.className = 'action-badge';
    badge.innerHTML = `⚡ Directive: ${actionBadge}`;
    card.appendChild(badge);
  }

  chatBox.appendChild(card);
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function handleSendMessage(customText = null) {
  const text = (customText || inputText.value).trim();
  if (!text) return;

  inputText.value = '';
  appendMessage(text, 'user');

  // Set visualizer to processing
  setAssistantState('processing');

  try {
    const response = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        history: sessionHistory
      })
    });

    if (!response.ok) {
      throw new Error(`Server returned status ${response.status}`);
    }

    const data = await response.json();
    const replyText = data.reply || "I received no response from the system core, sir.";

    // Render message
    appendMessage(replyText, 'jarvis', data.is_command ? data.action : null, !data.success);

    // Update in-memory session history for conversational context
    sessionHistory.push({ role: 'user', text: text });
    sessionHistory.push({ role: 'assistant', text: replyText });
    if (sessionHistory.length > 20) sessionHistory = sessionHistory.slice(-20);

    // Speak response
    speakText(replyText);

  } catch (err) {
    console.error('Chat transmission failure:', err);
    setAssistantState('error');
    const errMsg = "I apologize, sir, but I am unable to connect to the backend server. Please confirm the server is running via 'python app.py'.";
    appendMessage(errMsg, 'jarvis', null, true);
    speakText(errMsg);
  }
}

/* ==============================================================
   Event Listeners & Initialization
   ============================================================== */
sendBtn.onclick = () => handleSendMessage();

inputText.onkeydown = (e) => {
  if (e.key === 'Enter') {
    e.preventDefault();
    handleSendMessage();
  }
};

voiceBtn.onclick = togglePushToTalk;
stopBtn.onclick = stopSpeaking;

muteBtn.onclick = () => {
  isMuted = !isMuted;
  const muteIcon = document.getElementById('mute-icon');
  if (isMuted) {
    muteIcon.textContent = '🔇';
    muteBtn.title = 'Unmute Spoken Responses';
    stopSpeaking();
  } else {
    muteIcon.textContent = '🔊';
    muteBtn.title = 'Mute Spoken Responses';
  }
};

clearChatBtn.onclick = () => {
  chatBox.innerHTML = '';
  sessionHistory = [];
  appendMessage('Session conversational memory has been reset, sir. All systems standing by.', 'jarvis');
  setAssistantState('idle');
};

settingsToggleBtn.onclick = () => {
  settingsDrawer.classList.toggle('collapsed');
};

closeSettingsBtn.onclick = () => {
  settingsDrawer.classList.add('collapsed');
};

// Quick Command Chips
quickCommands.addEventListener('click', (e) => {
  const chip = e.target.closest('.chip');
  if (!chip) return;
  const cmd = chip.getAttribute('data-cmd');
  if (cmd) {
    handleSendMessage(cmd);
  }
});

// Initial Welcome Sequence
window.addEventListener('DOMContentLoaded', () => {
  setupSpeechRecognition();
  checkSystemStatus();
  setAssistantState('idle');

  // Initial welcome message from JARVIS
  setTimeout(() => {
    appendMessage(
      "Good evening, sir. JARVIS interface operational. All neural matrices and local command directives are standing by.",
      'jarvis'
    );
  }, 400);
});
