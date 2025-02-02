import { formatWhatsAppText, formatInteractiveMessage } from './handlers.js';

export class ChatUI {
    constructor() {
        this.messageInput = document.getElementById('messageInput');
        this.phoneInput = document.getElementById('phoneNumber');
        this.targetSelect = document.getElementById('target');
        this.sendButton = document.getElementById('sendButton');
        this.chatContainer = document.getElementById('chatContainer');
        this.statusDiv = document.getElementById('status');

        // Format any existing messages
        this.formatExistingMessages();
    }

    formatExistingMessages() {
        // Format text messages
        const textMessages = document.querySelectorAll('.message.whatsapp-text');
        textMessages.forEach(message => {
            const rawText = message.getAttribute('data-raw-text');
            if (rawText) {
                message.innerHTML = formatWhatsAppText(rawText);
            }
        });

        // Format interactive messages
        const interactiveMessages = document.querySelectorAll('.message.whatsapp-interactive');
        interactiveMessages.forEach(message => {
            const interactiveData = message.getAttribute('data-interactive');
            if (interactiveData) {
                try {
                    const interactive = JSON.parse(interactiveData);
                    message.innerHTML = formatInteractiveMessage(interactive);

                    // Add click handlers for buttons and list items
                    message.querySelectorAll('.whatsapp-button:not(.list-select-button), .list-item').forEach(element => {
                        element.addEventListener('click', () => {
                            const id = element.getAttribute('data-id');
                            const type = element.classList.contains('whatsapp-button') ? 'button' : 'list';
                            const title = element.querySelector('.item-description')?.textContent || id;

                            // Simulate user selecting this option with WhatsApp standard format
                            this.messageInput.value = `${type}:${id}`;
                            if (this.onSendMessage) {
                                this.onSendMessage('interactive');
                            }
                        });
                    });

                    // Add click handler for list select button
                    message.querySelectorAll('.list-select-button').forEach(button => {
                        button.addEventListener('click', () => {
                            const listContainer = button.closest('.interactive-list');
                            if (listContainer) {
                                listContainer.classList.add('active');
                            }
                        });
                    });
                } catch (e) {
                    console.error('Error parsing interactive message:', e);
                    message.innerHTML = '<div class="error">Error displaying interactive message</div>';
                }
            }
        });
    }

    showNotification(text) {
        const notificationDiv = document.createElement('div');
        notificationDiv.className = 'message notification';
        notificationDiv.textContent = text;
        this.chatContainer.appendChild(notificationDiv);
        this.chatContainer.scrollTop = this.chatContainer.scrollHeight;

        // Format any new messages that were added
        this.formatExistingMessages();
    }

    updateStatus() {
        let text;
        switch (this.targetSelect.value) {
            case 'local':
                text = 'Local Server (localhost:8000)';
                break;
            case 'development':
                text = 'Development Server (dev.vimbiso-chatserver.vimbisopay.africa)';
                break;
            case 'production':
                text = 'Production Server (vimbiso-chatserver.vimbisopay.africa)';
                break;
            default:
                text = 'Unknown Server';
        }
        this.statusDiv.innerHTML = `Connected to: ${text}`;
        this.statusDiv.className = `status ${this.targetSelect.value}`;
    }

    disableSendButton(disabled = true) {
        this.sendButton.disabled = disabled;
    }

    clearInput() {
        this.messageInput.value = '';
    }

    setupEventListeners(onSendMessage) {
        // Store callback for interactive messages
        this.onSendMessage = onSendMessage;

        // Send message button
        this.sendButton.addEventListener('click', () => {
            const messageText = this.messageInput.value.trim();
            if (!messageText) return;

            // Check if this is an interactive response
            if (messageText.startsWith('button:') || messageText.startsWith('list:')) {
                onSendMessage('interactive');
            } else {
                onSendMessage('text');
            }
        });

        // Enter key handling
        this.messageInput.addEventListener('keypress', e => {
            if (e.key === 'Enter' && !this.sendButton.disabled) {
                const messageText = this.messageInput.value.trim();
                if (!messageText) return;

                // Check if this is an interactive response
                if (messageText.startsWith('button:') || messageText.startsWith('list:')) {
                    onSendMessage('interactive');
                } else {
                    onSendMessage('text');
                }
            }
        });

        // Target change
        this.targetSelect.addEventListener('change', () => this.updateStatus());

        // Set up refresh button
        const refreshButton = document.getElementById('refreshButton');
        refreshButton.onclick = () => window.location.reload();

        // Set up clear button
        const clearButton = document.getElementById('clearButton');
        clearButton.onclick = async () => {
            try {
                const response = await fetch(`${window.location.origin}/clear-conversation`);
                if (!response.ok) {
                    throw new Error(`Server responded with ${response.status}`);
                }
                window.location.reload();
            } catch (error) {
                console.error('Error clearing conversation:', error);
                this.showNotification(`Error: ${error.message}`);
            }
        };
    }

    getLastMessageId() {
        return this.lastMessageId;
    }
}
