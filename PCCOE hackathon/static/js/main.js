function toggleChat() {
    const body = document.getElementById('chatbot-body');
    const widget = document.getElementById('chatbot-widget');
    const icon = document.querySelector('.chatbot-header i.fa-chevron-up, .chatbot-header i.fa-chevron-down');

    if (body.style.display === 'none') {
        body.style.display = 'flex';
        if (icon) {
            icon.classList.remove('fa-chevron-up');
            icon.classList.add('fa-chevron-down');
        }
    } else {
        body.style.display = 'none';
        widget.classList.remove('maximized'); // Reset size on close
        if (icon) {
            icon.classList.remove('fa-chevron-down');
            icon.classList.add('fa-chevron-up');
        }
    }
}

function toggleMaximize(event) {
    event.stopPropagation(); // Prevent toggling chat close
    const widget = document.getElementById('chatbot-widget');
    const btn = document.getElementById('maximize-btn');

    widget.classList.toggle('maximized');

    if (widget.classList.contains('maximized')) {
        btn.innerHTML = '<i class="fas fa-compress"></i>';
        document.getElementById('chatbot-body').style.display = 'flex'; // Ensure body is visible
    } else {
        btn.innerHTML = '<i class="fas fa-expand"></i>';
    }
}

function formatMessage(text) {
    if (!text) return '';

    // 1. Bold: **text** -> <b>text</b>
    let formatted = text.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');

    // 2. Lists: - item -> <li>item</li>
    const lines = formatted.split('\n');
    let inList = false;
    let result = '';

    for (let line of lines) {
        line = line.trim();
        if (line.startsWith('- ') || line.startsWith('* ')) {
            if (!inList) {
                result += '<ul>';
                inList = true;
            }
            result += `<li>${line.substring(2)}</li>`;
        } else {
            if (inList) {
                result += '</ul>';
                inList = false;
            }
            if (line.length > 0) {
                result += line + '<br>';
            }
        }
    }
    if (inList) result += '</ul>';

    return result;
}

function handleChat(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    // Add user message
    const messagesDiv = document.getElementById('chat-messages');
    const userDiv = document.createElement('div');
    userDiv.className = 'user-msg animate-fade-in';
    userDiv.textContent = message;
    messagesDiv.appendChild(userDiv);

    input.value = '';
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    // Get Context from LocalStorage (for guests)
    let context = {};
    const storedResult = localStorage.getItem('ayurDoshaResult');
    if (storedResult) {
        try {
            context = JSON.parse(storedResult);
        } catch (e) {
            console.error("Error parsing stored result", e);
        }
    }

    // Call API
    fetch('/api/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            message: message,
            context: context
        })
    })
        .then(response => response.json())
        .then(data => {
            const formattedResponse = formatMessage(data.response);
            const botDiv = document.createElement('div');
            botDiv.className = 'bot-msg animate-fade-in';
            botDiv.innerHTML = formattedResponse;
            messagesDiv.appendChild(botDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        })
        .catch(error => {
            console.error('Error:', error);
            const errDiv = document.createElement('div');
            errDiv.className = 'bot-msg text-danger';
            errDiv.textContent = "Sorry, I'm having trouble connecting right now.";
            messagesDiv.appendChild(errDiv);
        });
}
