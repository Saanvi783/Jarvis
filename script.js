const chatBox = document.getElementById('chat-box');
const inputText = document.getElementById('input-text');
const sendBtn = document.getElementById('send-btn');
const voiceBtn = document.getElementById('voice-btn');
const stopBtn = document.getElementById('stop-btn');

const pitchSlider = document.getElementById('pitch-slider');
const rateSlider = document.getElementById('rate-slider');
const volumeSlider = document.getElementById('volume-slider');

let femaleVoice = null;

// Update voices (same as before)
function updateVoices() {
  const voices = speechSynthesis.getVoices();
  femaleVoice = voices.find(v =>
    (v.name && v.name.toLowerCase().includes('zira')) ||
    (v.name && v.name.toLowerCase().includes('susan')) ||
    (v.name && v.name.toLowerCase().includes('female')) ||
    (v.gender && v.gender.toLowerCase() === 'female') ||
    (v.lang && v.lang.startsWith('en') && ['UK English Female', 'Google UK English Female', 'Google US English'].includes(v.name))
  ) || voices[0];
}
speechSynthesis.onvoiceschanged = updateVoices;
updateVoices();

function appendMessage(text, sender) {
  const msgDiv = document.createElement('div');
  msgDiv.className = `message ${sender}`;
  msgDiv.textContent = text;
  chatBox.appendChild(msgDiv);
  chatBox.scrollTop = chatBox.scrollHeight;
}

// Wikipedia summary fetcher (REST API)
async function fetchWikipediaSummary(query) {
  const url = `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(query)}`;
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error('Article not found.');
    const data = await response.json();
    return data.extract || "Sorry, I couldn't find information on that topic.";
  } catch (error) {
    return "Sorry, I couldn't retrieve information from Wikipedia.";
  }
}

// Main response function using Wikipedia API
async function getKarenResponse(text) {
  const lower = text.toLowerCase();

  if (lower.includes('hello') || lower.includes('hi'))
    return 'Hi there!';

  if (lower.includes('your name') || lower.includes('who are you'))
    return "I'm Karen, your Spider-Man AI assistant powered by Wikipedia knowledge.";

  if (lower.startsWith('who is ') || lower.startsWith('what is ') || lower.startsWith('tell me about ') || lower.startsWith('wikipedia ')) {
    const subject = lower.replace(/^(who is|what is|tell me about|wikipedia)/, '').trim();
    if (subject.length > 0) {
      return await fetchWikipediaSummary(subject);
    }
  }

  return "Sorry, I didn't understand that.'";
}

// Speak Karen's response with voice control
function speakText(text) {
  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.voice = femaleVoice;
  utterance.pitch = parseFloat(pitchSlider.value);
  utterance.rate = parseFloat(rateSlider.value);
  utterance.volume = parseFloat(volumeSlider.value);

  setTimeout(() => {
    const allKaren = chatBox.querySelectorAll('.karen');
    if (allKaren.length > 0) {
      allKaren[allKaren.length - 1].classList.add('speaking');
    }
  }, 10);

  utterance.onend = () => {
    const allKaren = chatBox.querySelectorAll('.karen.speaking');
    allKaren.forEach(el => el.classList.remove('speaking'));
  };
  window.speechSynthesis.speak(utterance);
}

// Stop speaking event handler
stopBtn.onclick = () => {
  window.speechSynthesis.cancel();
};

// Send message event handler
async function sendMessage() {
  const input = inputText.value.trim();
  if (!input) return;
  appendMessage(input, 'user');
  inputText.value = '';

  const response = await getKarenResponse(input);
  appendMessage(response, 'karen');
  speakText(response);
}

sendBtn.onclick = sendMessage;
inputText.onkeypress = e => { if (e.key === 'Enter') sendMessage(); };

// --- Wake word detection setup ---
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

let recognition;
let listening = false;

if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.continuous = true;  // keep listening
  recognition.interimResults = false;
  recognition.lang = 'en-US';

  recognition.onresult = (event) => {
    let transcript = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      transcript += event.results[i][0].transcript.toLowerCase();
    }

    if (transcript.includes('hey karen')) {
      const command = transcript.split('hey karen')[1].trim();
      if (command.length > 0) {
        console.log('Wake word detected with command:', command);
        handleVoiceCommand(command);
      } else {
        speakText('Yes, how may I assist you?');
      }
    }
  };

  recognition.onerror = (e) => {
    console.error('Speech recognition error:', e.error);
  };

  recognition.onend = () => {
    if (listening) {
      recognition.start(); // auto restart to keep listening
    }
  };

  function startWakeWordListening() {
    if (!listening) {
      recognition.start();
      listening = true;
      console.log('Wake word listening started.');
    }
  }

  function stopWakeWordListening() {
    if (listening) {
      recognition.stop();
      listening = false;
      console.log('Wake word listening stopped.');
    }
  }

  // Automatically start wake word detection on load
  startWakeWordListening();

} else {
  voiceBtn.disabled = true;
  voiceBtn.textContent = 'Voice Not Supported';
}

// Voice button toggles voice recognition (kept for fallback or manual)
voiceBtn.onclick = () => {
  if (!recognition) return;
  if (listening) {
    stopWakeWordListening();
    voiceBtn.textContent = '🎤 Start Voice';
  } else {
    startWakeWordListening();
    voiceBtn.textContent = '🛑 Stop Voice';
  }
  listening = !listening;
}

// Command handler for wake word commands
async function handleVoiceCommand(command) {
  if (command.includes('shutdown') || command.includes('restart')) {
    speakText("Sorry, system commands like shutdown and restart are not supported by the browser for security reasons.");
  } else {
    const response = await getKarenResponse(command);
    appendMessage(response, 'karen');
    speakText(response);
  }
}
