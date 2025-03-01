import { ChatUI } from './ui.js';

class WhatsAppMock {
    constructor() {
        this.ui = new ChatUI();
        this.ui.setupEventListeners((messageType) => this.sendMessage(messageType));
        this.ui.updateStatus();
    }


    async sendMessage(messageType = 'text') {
        const messageText = this.ui.messageInput.value.trim();
        if (!messageText) return;

        this.ui.disableSendButton(true);

        try {
            const payload = {
                type: messageType,
                message: messageType === 'text' ? messageText : {
                    type: "interactive",
                    interactive: {
                        type: messageText.startsWith('button:') ? 'button_reply' : 'list_reply',
                        [messageText.startsWith('button:') ? 'button_reply' : 'list_reply']: {
                            id: messageText.split(':')[1],
                            title: messageText.split(':')[1]
                        }
                    }
                },
                phone: this.ui.phoneInput.value
            };

            const response = await fetch(`${window.location.origin}/bot/webhook?target=${this.ui.targetSelect.value}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-Mock-Testing': 'mock_test_secret'  // Should match MOCK_TEST_KEY in server.py
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error(`Server responded with ${response.status}: ${await response.text()}`);
            }

            // Show refresh notification
            this.ui.showNotification('Click Refresh to update conversation. Wait a few seconds to make sure app response is included.');
            this.ui.disableSendButton(false);
        } catch (error) {
            console.error('Error:', error);
            this.ui.showNotification(`Error: ${error.message}`);
            this.ui.disableSendButton(false);
        }

        this.ui.clearInput();
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new WhatsAppMock();
});
