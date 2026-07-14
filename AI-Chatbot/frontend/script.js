// Configure marked to use highlight.js
marked.setOptions({
  highlight: function (code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value;
    }
    return hljs.highlightAuto(code).value;
  },
  breaks: true,
});

const els = {
  sidebar: document.getElementById('sidebar'),
  toggleSidebarBtn: document.getElementById('toggleSidebarBtn'),
  newChatBtn: document.getElementById('newChatBtn'),
  conversationList: document.getElementById('conversationList'),
  messages: document.getElementById('messages'),
  input: document.getElementById('input'),
  sendBtn: document.getElementById('sendBtn'),
  stopBtn: document.getElementById('stopBtn'),
  regenerateBtn: document.getElementById('regenerateBtn'),
  modelSelect: document.getElementById('modelSelect'),
  themeBtn: document.getElementById('themeBtn'),
  loadingSkeleton: document.getElementById('loadingSkeleton'),
  deleteChatBtn: document.getElementById('deleteChatBtn'),
  shareBtn: document.getElementById('shareBtn'),
  exportPdfBtn: document.getElementById('exportPdfBtn'),
  exportTxtBtn: document.getElementById('exportTxtBtn'),
  attachBtn: document.getElementById('attachBtn'),
  pdfInput: document.getElementById('pdfInput'),
  micBtn: document.getElementById('micBtn'),
};

function toggleChatButtons(show) {
  els.deleteChatBtn.hidden = !show;
  els.shareBtn.hidden = !show;
  els.exportPdfBtn.hidden = !show;
  els.exportTxtBtn.hidden = !show;
}

let activeConversationId = null;
let abortController = null;
let lastUserMessage = null;

// The raw markdown text for the current streaming assistant message
let currentAssistantBuffer = '';
// A reference to the current streaming bubble's content div
let currentAssistantBubble = null;

function getTheme() { return localStorage.getItem('theme') || 'dark'; }
function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);
}

els.themeBtn.addEventListener('click', () => {
  const t = getTheme() === 'dark' ? 'light' : 'dark';
  setTheme(t);
});
setTheme(getTheme());

els.toggleSidebarBtn.addEventListener('click', () => {
  els.sidebar.classList.toggle('open');
});

// Auto-resize textarea
els.input.addEventListener('input', function() {
  this.style.height = 'auto';
  this.style.height = (this.scrollHeight) + 'px';
  if(this.value === '') {
    this.style.height = 'auto';
  }
});

els.newChatBtn.addEventListener('click', async () => {
  activeConversationId = null;
  els.messages.innerHTML = '';
  toggleChatButtons(false);
  await refreshConversations();
  els.input.focus();
  // On mobile, hide sidebar after selecting new chat
  if (window.innerWidth <= 768) {
    els.sidebar.classList.remove('open');
  }
});

els.deleteChatBtn.addEventListener('click', async () => {
  if (!activeConversationId) return;
  if (!confirm("Are you sure you want to delete this chat?")) return;
  
  try {
    await fetch(`/api/history/conversations/${activeConversationId}`, { method: 'DELETE' });
    activeConversationId = null;
    els.messages.innerHTML = '';
    toggleChatButtons(false);
    await refreshConversations();
  } catch (e) {
    console.error("Failed to delete chat", e);
  }
});

function addSpeakerButton(msgWrap, text) {
  if (msgWrap.querySelector('.speaker-btn')) return;

  const speakerBtn = document.createElement('button');
  speakerBtn.className = 'icon-btn speaker-btn';
  speakerBtn.innerHTML = '🔊';
  speakerBtn.title = 'Speak message';
  speakerBtn.addEventListener('click', async () => {
    speakerBtn.innerHTML = '⏳';
    try {
      const formData = new FormData();
      formData.append('text', text);
      const res = await fetch('/text-to-speech', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (data.success && data.audio && data.audio.audio_base64) {
        const audioSrc = `data:audio/${data.audio.format || 'wav'};base64,${data.audio.audio_base64}`;
        const audio = new Audio(audioSrc);
        await audio.play();
      } else {
        alert('TTS failed: ' + (data.message || 'unknown error'));
      }
    } catch (e) {
      console.error(e);
      alert('Error playing speech: ' + e.message);
    } finally {
      speakerBtn.innerHTML = '🔊';
    }
  });
  msgWrap.appendChild(speakerBtn);
}

function addSystemMessage(text) {
  const wrap = document.createElement('div');
  wrap.className = 'msg system';

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = '⚙️';

  const bubble = document.createElement('div');
  bubble.className = 'bubble system-bubble';
  bubble.textContent = text;

  wrap.appendChild(avatar);
  wrap.appendChild(bubble);

  els.messages.appendChild(wrap);
  els.messages.scrollTop = els.messages.scrollHeight;
}

function addMessage(role, text) {
  const wrap = document.createElement('div');
  wrap.className = `msg ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'user' ? '👤' : '✦';

  const bubble = document.createElement('div');
  bubble.className = 'bubble markdown-body';
  
  if (role === 'user') {
    // User messages typically don't render full markdown or we can render safely
    bubble.textContent = text;
  } else {
    // Render markdown for assistant
    bubble.innerHTML = DOMPurify.sanitize(marked.parse(text));
  }

  wrap.appendChild(avatar);
  wrap.appendChild(bubble);

  if (role === 'assistant') {
    addSpeakerButton(wrap, text);
  }

  els.messages.appendChild(wrap);
  els.messages.scrollTop = els.messages.scrollHeight;

  return bubble;
}

// Prepare the UI for a new streaming message
function startAssistantMessage() {
  currentAssistantBuffer = '';
  const wrap = document.createElement('div');
  wrap.className = `msg assistant`;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = '✦';

  currentAssistantBubble = document.createElement('div');
  currentAssistantBubble.className = 'bubble markdown-body';

  wrap.appendChild(avatar);
  wrap.appendChild(currentAssistantBubble);

  els.messages.appendChild(wrap);
  els.messages.scrollTop = els.messages.scrollHeight;
}

// Update the current streaming message
function updateAssistantMessage(delta) {
  if (!currentAssistantBubble) return;
  currentAssistantBuffer += delta;
  currentAssistantBubble.innerHTML = DOMPurify.sanitize(marked.parse(currentAssistantBuffer));
  els.messages.scrollTop = els.messages.scrollHeight;
}

async function fetchModels() {
  try {
    const res = await fetch('/api/chat/models');
    const data = await res.json();
    els.modelSelect.innerHTML = '';
    for (const m of data.models) {
      const opt = document.createElement('option');
      opt.value = m;
      opt.textContent = m;
      els.modelSelect.appendChild(opt);
    }
  } catch(e) {
    console.error("Failed to fetch models", e);
  }
}

async function refreshConversations() {
  try {
    const res = await fetch('/api/history/conversations');
    const list = await res.json();
    els.conversationList.innerHTML = '';
    for (const c of list) {
      const item = document.createElement('div');
      item.className = 'conv-item' + (c.id === activeConversationId ? ' active' : '');
      item.textContent = c.title;
      item.addEventListener('click', async () => {
        activeConversationId = c.id;
        els.messages.innerHTML = '';
        toggleChatButtons(true);
        
        // Reflect model if possible, though select might not have it if it's an old model
        if(c.model) {
          const opt = Array.from(els.modelSelect.options).find(o => o.value === c.model);
          if (opt) els.modelSelect.value = c.model;
        }

        await loadConversation(c.id);
        refreshConversations();
        
        if (window.innerWidth <= 768) {
          els.sidebar.classList.remove('open');
        }
      });
      els.conversationList.appendChild(item);
    }
  } catch (e) {
    console.error("Failed to refresh conversations", e);
  }
}

async function loadConversation(id) {
  try {
    const res = await fetch(`/api/history/conversations/${id}`);
    const data = await res.json();
    if (data.error) return;
    for (const m of data.messages) {
      addMessage(m.role, m.content);
    }
  } catch (e) {
    console.error("Failed to load conversation", e);
  }
}

els.sendBtn.addEventListener('click', () => sendMessage());
els.input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

els.stopBtn.addEventListener('click', () => {
  if (abortController) { abortController.abort(); }
});

async function sendMessage() {
  const message = (els.input.value || '').trim();
  if (!message) return;

  lastUserMessage = message;
  els.input.value = '';
  els.input.style.height = 'auto'; // reset height
  els.sendBtn.disabled = true;
  els.loadingSkeleton.hidden = false;
  els.stopBtn.disabled = false;

  addMessage('user', message);
  startAssistantMessage();

  abortController = new AbortController();

  try {
    const payload = {
      conversation_id: activeConversationId,
      message,
      model: els.modelSelect.value,
      temperature: 0.7,
      top_p: 1.0,
      max_tokens: 1024,
    };

    const res = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: abortController.signal,
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');

    let buf = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });

      const lines = buf.split('\n');
      buf = lines.pop(); // keep the last incomplete chunk in the buffer

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const evt = JSON.parse(line);
          if (evt.conversation_id) {
            activeConversationId = evt.conversation_id;
            toggleChatButtons(true);
          }
          if (evt.delta) {
            els.loadingSkeleton.hidden = true; // hide skeleton once we get data
            updateAssistantMessage(evt.delta);
          }
          if (evt.error) {
            updateAssistantMessage(`\n\n**Error:** ${evt.error}`);
          }
          if (evt.done) {
            els.stopBtn.disabled = true;
            els.regenerateBtn.disabled = false;
            if (currentAssistantBubble && currentAssistantBubble.parentElement) {
              addSpeakerButton(currentAssistantBubble.parentElement, currentAssistantBuffer);
            }
          }
        } catch(err) {
          console.error("JSON Parse error on line:", line, err);
        }
      }
    }

    els.loadingSkeleton.hidden = true;
    els.sendBtn.disabled = false;
    els.input.focus();
    refreshConversations();
  } catch (e) {
    if (e.name === 'AbortError') {
      updateAssistantMessage('\n\n*[Stopped by user]*');
    } else {
      console.error(e);
      updateAssistantMessage(`\n\n**Connection Error:** ${e.message}`);
    }
    els.loadingSkeleton.hidden = true;
    els.sendBtn.disabled = false;
    els.stopBtn.disabled = true;
  }
}

els.regenerateBtn.addEventListener('click', async () => {
  if (!lastUserMessage) return;
  els.input.value = lastUserMessage;
  await sendMessage();
});

// PDF RAG Upload Events
els.attachBtn.addEventListener('click', () => {
  if (!activeConversationId) {
    alert('Please start or select a conversation first.');
    return;
  }
  els.pdfInput.click();
});

els.pdfInput.addEventListener('change', async function() {
  const file = this.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);
  formData.append('conversation_id', activeConversationId);

  els.attachBtn.textContent = '⏳';
  try {
    const res = await fetch('/api/upload/pdf', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (data.success) {
      addSystemMessage(`Indexed "${file.name}" successfully (${data.chunks} chunks). Now you can query it!`);
    } else {
      alert('Upload failed: ' + (data.error || 'unknown error'));
    }
  } catch (e) {
    console.error(e);
    alert('Error uploading PDF: ' + e.message);
  } finally {
    els.attachBtn.textContent = '📎';
    this.value = '';
  }
});

// Export events
els.exportPdfBtn.addEventListener('click', () => {
  if (!activeConversationId) return;
  window.open(`/api/export/pdf/${activeConversationId}`);
});

els.exportTxtBtn.addEventListener('click', () => {
  if (!activeConversationId) return;
  window.open(`/api/export/txt/${activeConversationId}`);
});

// Share event
els.shareBtn.addEventListener('click', async () => {
  if (!activeConversationId) return;
  els.shareBtn.textContent = '⏳';
  try {
    const res = await fetch('/api/share/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conversation_id: activeConversationId })
    });
    const data = await res.json();
    if (data.share_url) {
      navigator.clipboard.writeText(data.share_url);
      alert(`Conversation shared successfully! URL copied to clipboard:\n${data.share_url}`);
    } else {
      alert('Failed to generate share link.');
    }
  } catch (e) {
    console.error(e);
    alert('Error sharing conversation: ' + e.message);
  } finally {
    els.shareBtn.textContent = '🔗';
  }
});

// Microphone (Speech-to-text) events
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

els.micBtn.addEventListener('click', async () => {
  if (!isRecording) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      audioChunks = [];

      mediaRecorder.addEventListener('dataavailable', event => {
        audioChunks.push(event.data);
      });

      mediaRecorder.addEventListener('stop', async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        const formData = new FormData();
        formData.append('file', audioBlob, 'recording.wav');

        els.micBtn.textContent = '⏳';
        try {
          const res = await fetch('/speech-to-text', {
            method: 'POST',
            body: formData
          });
          const data = await res.json();
          if (data.success && data.text) {
            els.input.value = (els.input.value + ' ' + data.text).trim();
            els.input.dispatchEvent(new Event('input'));
          } else {
            alert('Speech transcription failed: ' + (data.message || 'unknown error'));
          }
        } catch (e) {
          console.error(e);
          alert('Error transcribing audio: ' + e.message);
        } finally {
          els.micBtn.textContent = '🎤';
        }
      });

      mediaRecorder.start();
      isRecording = true;
      els.micBtn.textContent = '🛑';
      els.micBtn.classList.add('recording');
    } catch (err) {
      console.error('Error accessing microphone', err);
      alert('Could not access microphone. Ensure permissions are granted.');
    }
  } else {
    if (mediaRecorder) {
      mediaRecorder.stop();
      mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
    isRecording = false;
    els.micBtn.textContent = '🎤';
    els.micBtn.classList.remove('recording');
  }
});

(async function init() {
  await fetchModels();
  await refreshConversations();
})();
