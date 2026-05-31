const conversation = document.getElementById('conversation');
const form = document.getElementById('chatForm');
const messageField = document.getElementById('message');
const statusText = document.getElementById('statusText');

function appendMessage(role, text) {
  const wrapper = document.createElement('div');
  wrapper.className = `message ${role}`;
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  wrapper.appendChild(bubble);
  conversation.appendChild(wrapper);
  conversation.scrollTop = conversation.scrollHeight;
}

function setStatus(text) {
  if (statusText) {
    statusText.textContent = text;
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const text = messageField.value.trim();
  if (!text) {
    return;
  }

  appendMessage('user', text);
  messageField.value = '';
  setStatus('Sending to Ollama...');
  appendMessage('bot', 'Thinking...');

  try {
    const response = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    });

    const data = await response.json();
    const lastMessage = conversation.lastElementChild;
    if (lastMessage && lastMessage.textContent === 'Thinking...') {
      conversation.removeChild(lastMessage);
    }

    if (!response.ok) {
      appendMessage('bot', `Error: ${data.details || data.error || 'Unexpected server error'}`);
      setStatus('Failed to get response.');
      return;
    }

    appendMessage('bot', data.reply || 'No reply received from Ollama.');
    setStatus('Response received.');
  } catch (error) {
    appendMessage('bot', `Network error: ${error.message}`);
    setStatus('Unable to contact the server.');
  }
});
