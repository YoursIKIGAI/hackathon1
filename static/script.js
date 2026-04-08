// GLOBAL ERROR CATCHER FOR DEBUGGING
window.onerror = function(msg, url, line) {
    console.warn("❌ SCRIPT ERROR: " + msg + " at line " + line);
    return false;
};

console.log("⚖️ NyayaVoice Frontend Initializing (v3.0)...");

const micBtn = document.getElementById('mic-btn');
const agentVisual = document.getElementById('agent-visual');
const statusText = document.getElementById('status-text');
const transcriptArea = document.getElementById('transcript-scroll-area');

// 1. Initialize Speech Systems
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let isListening = false;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US'; 
    console.log("✅ Speech Recognition system armed.");
} else {
    console.error("❌ Critical: Web Speech API is not supported in this browser.");
    if (statusText) statusText.textContent = "Your browser does not support Web Speech API. Use Chrome/Edge.";
}

if (recognition) {
    recognition.onstart = () => {
        isListening = true;
        setAgentState('listening', 'Actively listening to your inquiry...');
        micBtn.classList.add('recording');
        document.getElementById('btn-label').textContent = 'Conclude Consultation';
    };

    recognition.onaudiostart = () => console.log("Audio pipeline opened.");
    recognition.onspeechstart = () => console.log("Speech detected.");
    
    // Fired when audio is caught but NO words could be extracted (mumbling / static)
    recognition.onnomatch = () => {
        stopListeningUi();
        setAgentState('idle', 'Inquiry unclear. Please state your query again.');
    };

    recognition.onresult = async (event) => {
        const transcript = event.results[0][0].transcript;
        
        appendUserMessage(transcript);
        setAgentState('processing', 'Analyzing constitutional context...');
        stopListeningUi();

        // NO CHANGES TO BACKEND LOGIC: Connecting to existing server_v2 brain
        const SERVER_URL = 'http://127.0.0.1:5005/api/chat';
        console.log(`📡 Consulting backend inference at: ${SERVER_URL}`);
        
        try {
            const response = await fetch(SERVER_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: transcript })
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.response) {
                    appendAgentMessage(data.response);
                    speakResponse(data.response);
                } else {
                    handleBackendError("Malformed response structure.");
                }
            } else {
                handleBackendError("Service unavailable.");
            }
        } catch (err) {
            console.error("Fetch Error:", err);
            handleBackendError("Failed to connect to NyayaVoice engine.");
        }
    };

    recognition.onerror = (event) => {
        console.error("Speech Error:", event.error);
        stopListeningUi();
        let errorMsg = "Microphone Error: " + event.error;
        if (event.error === 'not-allowed') errorMsg = "Permission required. Please allow access.";
        if (event.error === 'no-speech') errorMsg = "Silence detected. Please try again.";
        setAgentState('idle', errorMsg);
    };

    recognition.onend = () => {
        if(isListening) {
             stopListeningUi();
             // Only reset to idle if we aren't currently processing the server response
             if (!agentVisual.classList.contains('processing')) {
                setAgentState('idle', 'Awaiting your inquiry.');
             }
        }
    };
} else {
    statusText.textContent = "Your browser does not support Web Speech API.";
    micBtn.style.display = 'none';
}

function appendUserMessage(text) {
    if (!transcriptArea) return;
    const msg = document.createElement('div');
    msg.className = "message user-message glass-panel";
    msg.innerHTML = `<strong>Citizen Query:</strong> <span>${text}</span>`;
    transcriptArea.appendChild(msg);
    transcriptArea.scrollTop = transcriptArea.scrollHeight;
}

function appendAgentMessage(text) {
    if (!transcriptArea) return;
    const msg = document.createElement('div');
    msg.className = "message agent-message glass-panel";
    msg.innerHTML = `<strong>NyayaVoice Counsel:</strong> <span class="agent-typing"></span>`;
    transcriptArea.appendChild(msg);
    transcriptArea.scrollTop = transcriptArea.scrollHeight;
    
    const textNode = msg.querySelector('.agent-typing');
    typeText(textNode, text, 25);
}

function stopListeningUi() {
    isListening = false;
    micBtn.classList.remove('recording');
    document.getElementById('btn-label').textContent = 'Consult NyayaVoice';
}

micBtn.addEventListener('click', async () => {
    if (window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
    }

    if (isListening) {
        try { recognition.stop(); } catch(e){}
        stopListeningUi();
    } else {
        setAgentState('idle', 'Requesting microphone access...');
        try {
            const tempStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            tempStream.getTracks().forEach(track => track.stop());
            recognition.start();
        } catch(e) {
            console.error("Mic Access Error:", e);
            let userMsg = "Unknown Error";
            if (e.name === 'NotAllowedError' || e.name === 'PermissionDeniedError') {
                userMsg = 'Microphone permission denied. Please allow access in browser settings.';
            } else if (e.name === 'NotFoundError') {
                userMsg = 'No audio input unattached. Please connect a microphone.';
            } else {
                userMsg = 'Audio subsystem busy. Refresh and try again.';
            }
            
            setAgentState('idle', userMsg);
            try { recognition.stop(); } catch(err){}
        }
    }
});

function typeText(element, text, speed) {
    element.innerHTML = '';
    let i = 0;
    const interval = setInterval(() => {
        if (i < text.length) {
            element.innerHTML += text.charAt(i);
            i++;
            if (transcriptArea) transcriptArea.scrollTop = transcriptArea.scrollHeight;
        } else {
            clearInterval(interval);
        }
    }, speed);
}

function speakResponse(text) {
    if (!('speechSynthesis' in window)) {
        setAgentState('idle', 'Awaiting your inquiry.');
        return;
    }
    
    setAgentState('speaking', 'Presenting guidance...');
    
    // Remove markdown formatting (like **bold**) before speaking so TTS doesn't read the asterisks
    const cleanText = text.replace(/[*_#]/g, '');

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.0; 
    utterance.pitch = 0.95; // Slightly deeper, authoritative pitch
    
    const voices = window.speechSynthesis.getVoices();
    // Try to find a clear, authoritative default voice
    const profVoice = voices.find(v => (v.name.includes('India') || v.name.includes('UK') || v.name.includes('Mark') || v.name.includes('Ravi')));
    if (profVoice) utterance.voice = profVoice;

    utterance.onend = () => {
        setAgentState('idle', 'Awaiting your inquiry.');
    };

    utterance.onerror = (e) => {
        console.error("TTS Error:", e);
        setAgentState('idle', 'Awaiting your inquiry.');
    }

    try {
        window.speechSynthesis.speak(utterance);
    } catch(e) {
        console.error(e);
        setAgentState('idle', 'Awaiting your inquiry.');
    }
}

function setAgentState(stateClass, text) {
    agentVisual.className = `agent-visual ${stateClass}`;
    statusText.textContent = text;
}

function handleBackendError(reason) {
    console.warn("NyayaVoice Core Error:", reason);
    
    const mockResponses = {
        "hello": "Greetings. I am NyayaVoice, your constitutional guide. (My legal backend server is currently offline. Please ensure server_v2.py is running.)",
        "constitution": "The Constitution of India is the supreme law of the land. (Note: Offline mode. Please start the server for full details.)",
    };

    let reply = `Unable to process your legal query at this time. The NyayaVoice backend engine is disconnected: ${reason}`;
    
    if (reason.includes("connect")) {
        reply = "Connection severed. Please ensure your local Flask server (server_v2.py) is initialized and active.";
    }
    
    const lastMsg = document.querySelector('.user-message:last-child span');
    if (lastMsg) {
        const text = lastMsg.textContent.toLowerCase();
        for (const [key, val] of Object.entries(mockResponses)) {
            if (text.includes(key)) {
                reply = val;
                break;
            }
        }
    }
    
    appendAgentMessage(reply);
    speakResponse(reply);
}

// Pre-load voices for TTS to prevent delay during first speak
if ('speechSynthesis' in window) {
    window.speechSynthesis.onvoiceschanged = () => {
        // Just trigger the load
        window.speechSynthesis.getVoices();
    };
}
