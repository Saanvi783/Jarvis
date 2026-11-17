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
const clearChatBtn = document.getElementById('clear-chat-btn');
const settingsToggleBtn = document.getElementById('settings-toggle-btn');
const closeSettingsBtn = document.getElementById('close-settings-btn');
const settingsDrawer = document.getElementById('settings-drawer');

// HUD & Visualizer Elements
const arcReactor = document.getElementById('arc-reactor');
const orbStateLabel = document.getElementById('orb-state-label');
const statusText = document.getElementById('status-text');

// Voice Settings Elements
const voiceSelect = document.getElementById('voice-select');
const pitchSlider = document.getElementById('pitch-slider');
const rateSlider = document.getElementById('rate-slider');
const volumeSlider = document.getElementById('volume-slider');
const pitchVal = document.getElementById('pitch-val');
const rateVal = document.getElementById('rate-val');
const volumeVal = document.getElementById('volume-val');

// Application State
let isSpeaking = false;
let isListening = false;
let selectedVoice = null;
let sessionHistory = [];
let recognition = null;

// Backend API Base URL
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
        orbStateLabel.textContent = 'Ready';
        break;
      case 'listening':
        orbStateLabel.textContent = 'Listening...';
        break;
      case 'processing':
        orbStateLabel.textContent = 'Thinking...';
        break;
      case 'speaking':
        orbStateLabel.textContent = 'Speaking...';
        break;
      case 'error':
        orbStateLabel.textContent = 'Alert';
        break;
    }
  }
}

/* ==============================================================
   Speech Synthesis (TTS) - Curated 2-3 English Voices
   ============================================================== */
function populateVoiceList() {
  if (!('speechSynthesis' in window)) return;
  const allVoices = window.speechSynthesis.getVoices();
  if (allVoices.length === 0) return;

  voiceSelect.innerHTML = '';

  // 1. Preferred JARVIS-style British Male Voice
  const jarvisVoice = allVoices.find(v => 
    (v.name.includes('UK English Male') || v.name.includes('George') || v.name.includes('Oliver') || (v.lang === 'en-GB' && !v.name.includes('Female') && !v.name.includes('Hazel') && !v.name.includes('Susan')))
  );

  // 2. Standard Natural US Voice
  const usVoice = allVoices.find(v => 
    (v.name.includes('David') || v.name.includes('Google US English') || (v.lang === 'en-US' && !v.name.includes('Zira')))
  );

  // 3. Alternative Natural UK Voice
  const ukAltVoice = allVoices.find(v => 
    (v.name.includes('Hazel') || v.name.includes('Susan') || v.name.includes('UK English Female') || v.lang === 'en-GB')
  );

  // Build curated list of 2 to 3 basic English voices maximum
  const curated = [];
  if (jarvisVoice) curated.push({ voice: jarvisVoice, label: 'British English (JARVIS)' });
  if (usVoice && !curated.some(c => c.voice.name === usVoice.name)) {
    curated.push({ voice: usVoice, label: 'US English' });
  }
  if (ukAltVoice && !curated.some(c => c.voice.name === ukAltVoice.name) && curated.length < 3) {
    curated.push({ voice: ukAltVoice, label: 'UK English (Natural)' });
  }

  // Fallback if none matched
  if (curated.length === 0) {
    const englishFallback = allVoices.filter(v => v.lang.startsWith('en')).slice(0, 3);
    englishFallback.forEach((v, idx) => {
      curated.push({ voice: v, label: `English Voice ${idx + 1}` });
    });
  }

  // Populate select element with clean names
  curated.forEach((item, index) => {
    const option = document.createElement('option');
    option.value = item.voice.name;
    option.textContent = item.label;
    if (index === 0) {
      option.selected = true;
      selectedVoice = item.voice;
    }
    voiceSelect.appendChild(option);
  });

  if (!selectedVoice && curated.length > 0) {
    selectedVoice = curated[0].voice;
  }
}

if ('speechSynthesis' in window) {
  window.speechSynthesis.onvoiceschanged = populateVoiceList;
  populateVoiceList();
}

voiceSelect.addEventListener('change', () => {
  const voices = window.speechSynthesis.getVoices();
  selectedVoice = voices.find(v => v.name === voiceSelect.value) || voices[0];
});

pitchSlider.oninput = () => { pitchVal.textContent = pitchSlider.value; };
rateSlider.oninput = () => { rateVal.textContent = rateSlider.value; };
volumeSlider.oninput = () => { volumeVal.textContent = `${Math.round(volumeSlider.value * 100)}%`; };

function speakText(text) {
  if (!('speechSynthesis' in window)) {
    setAssistantState('idle');
    return;
  }

  window.speechSynthesis.cancel();

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
    const cards = chatBox.querySelectorAll('.message-card.jarvis');
    if (cards.length > 0) {
      cards[cards.length - 1].classList.add('speaking');
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
    voiceBtn.querySelector('.voice-btn-label').textContent = 'Unavailable';
    return;
  }

  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = 'en-US';

  recognition.onstart = () => {
    isListening = true;
    voiceBtn.classList.add('listening');
    voiceBtn.querySelector('.voice-btn-label').textContent = 'Listening...';
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
      appendMessage('Microphone access was denied. Please allow microphone permissions in your browser.', 'jarvis', true);
    } else if (event.error !== 'no-speech') {
      appendMessage(`Voice input issue (${event.error}). You can type your command below.`, 'jarvis', true);
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
  voiceBtn.querySelector('.voice-btn-label').textContent = 'Voice';
}

function toggleVoice() {
  if (!recognition) return;

  if (isListening) {
    recognition.stop();
    isListening = false;
    resetVoiceButton();
    setAssistantState('idle');
  } else {
    stopSpeaking();
    try {
      recognition.start();
    } catch (e) {
      console.warn('Recognition start exception:', e);
    }
  }
}

/* ==============================================================
   Chat Rendering & Communication
   ============================================================== */
function appendMessage(text, sender, isError = false) {
  const card = document.createElement('div');
  card.className = `message-card ${sender}${isError ? ' error' : ''}`;

  const meta = document.createElement('div');
  meta.className = 'message-meta';

  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const senderLabel = sender === 'user' ? 'Saanvi' : 'JARVIS';

  meta.innerHTML = `<span>${senderLabel}</span><span>${time}</span>`;
  card.appendChild(meta);

  const content = document.createElement('div');
  content.className = 'message-content';
  content.textContent = text;
  card.appendChild(content);

  chatBox.appendChild(card);
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function handleSendMessage(customText = null) {
  const text = (customText || inputText.value).trim();
  if (!text) return;

  inputText.value = '';
  appendMessage(text, 'user');
  stopSpeaking();

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
    const replyText = data.reply || "I received no response from the system.";

    appendMessage(replyText, 'jarvis', false);

    sessionHistory.push({ role: 'user', text: text });
    sessionHistory.push({ role: 'assistant', text: replyText });
    if (sessionHistory.length > 20) sessionHistory = sessionHistory.slice(-20);

    speakText(replyText);

  } catch (err) {
    console.error('Chat transmission failure:', err);
    setAssistantState('error');
    const errMsg = "Unable to connect to the backend server. Please confirm the server is running via 'python app.py'.";
    appendMessage(errMsg, 'jarvis', true);
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

voiceBtn.onclick = toggleVoice;

clearChatBtn.onclick = () => {
  chatBox.innerHTML = '';
  sessionHistory = [];
  appendMessage('Conversation cleared. Ready when you are.', 'jarvis');
  setAssistantState('idle');
};

settingsToggleBtn.onclick = () => {
  settingsDrawer.classList.toggle('collapsed');
};

closeSettingsBtn.onclick = () => {
  settingsDrawer.classList.add('collapsed');
};

window.addEventListener('DOMContentLoaded', () => {
  setupSpeechRecognition();
  setAssistantState('idle');

  setTimeout(() => {
    appendMessage(
      "Good evening, Saanvi. All systems are operational and ready.",
      'jarvis'
    );
  }, 350);
});
