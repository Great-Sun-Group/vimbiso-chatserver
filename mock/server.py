"""Mock WhatsApp server implementation."""
import json
import logging
import os
import socketserver
import time
from http.server import SimpleHTTPRequestHandler

import requests

# Configure logging - show important messages only
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Silence connection and http logs
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("http.server").setLevel(logging.WARNING)

# The app endpoints we're testing
APP_ENDPOINTS = {
    'local': 'http://app:8000/bot/webhook',
    'development': 'https://dev-vimbiso-chatserver.dailycredcoin.com/bot/webhook',
    'production': 'https://vimbiso-chatserver.vimbisopay.africa/bot/webhook'
}

# Directory to store messages
MESSAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "messages")

# Create messages directory if it doesn't exist
os.makedirs(MESSAGES_DIR, exist_ok=True)


class MockWhatsAppHandler(SimpleHTTPRequestHandler):
    """Handler for serving mock WhatsApp interface and handling webhooks."""

    def __init__(self, *args, directory=None, **kwargs):
        # Serve from current directory
        directory = os.path.dirname(os.path.abspath(__file__))
        super().__init__(*args, directory=directory, **kwargs)

    def guess_type(self, path):
        """Guess the type of a file based on its path.

        Override to ensure proper MIME types for our files.
        """
        if path.endswith('.js'):
            return 'application/javascript'
        if path.endswith('.css'):
            return 'text/css'
        if path.endswith('.html'):
            return 'text/html'
        return super().guess_type(path)

    def _send_200(self, content=None):
        """Send 200 OK with optional JSON content"""
        try:
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            if content:
                self.wfile.write(json.dumps(content).encode('utf-8'))
                self.wfile.flush()
        except Exception as e:
            # Ignore all errors - client probably disconnected
            logger.debug("Connection closed: %s", e)

    def _save_message(self, message):
        """Save message to file for UI/CLI to read."""
        try:
            # Ensure message is JSON serializable
            if isinstance(message, str):
                try:
                    message = json.loads(message)
                except json.JSONDecodeError as e:
                    logger.error("Failed to parse message as JSON: %s", e)
                    return

            # Save actual messages (text and interactive), not acknowledgments
            if isinstance(message, dict) and (
                (message.get("type") == "text" and message.get("text", {}).get("body")) or
                (message.get("type") == "interactive" and message.get("interactive"))
            ):
                # Create timestamp-based filename
                timestamp = int(time.time() * 1000)  # millisecond precision
                filename = f"{timestamp}.json"
                filepath = os.path.join(MESSAGES_DIR, filename)

                # Add filename to message data for timestamp tracking
                message_with_meta = {
                    **message,
                    "_filename": filename  # Add filename to message data
                }

                # Save message to file
                with open(filepath, 'w') as f:
                    json.dump(message_with_meta, f, indent=2)

        except Exception as e:
            logger.error("Failed to save message: %s", e)

    def _get_messages(self, since=None):
        """Get messages from file storage, optionally after a timestamp."""
        messages = []
        try:
            # List all message files
            files = sorted(os.listdir(MESSAGES_DIR))
            for filename in files:
                if not filename.endswith('.json'):
                    continue

                # Get timestamp from filename
                timestamp = int(filename[:-5])  # Remove .json
                if since and timestamp <= since:
                    continue

                # Read message
                filepath = os.path.join(MESSAGES_DIR, filename)
                with open(filepath) as f:
                    message = json.load(f)
                    # Ensure filename is included in message data
                    if '_filename' not in message:
                        message['_filename'] = filename
                    messages.append(message)

        except Exception as e:
            logger.error("Error reading messages: %s", e)

        return messages

    def _forward_to_app(self, message, target='local'):
        """Transform and forward message to app."""
        try:
            # Transform simple message to WhatsApp webhook format
            webhook_message = {
                "object": "whatsapp_business_account",
                "entry": [{
                    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                    "changes": [{
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "263787274250",
                                "phone_number_id": "390447444143042"
                            },
                            "contacts": [{
                                "profile": {
                                    "name": "Test User"
                                },
                                "wa_id": message.get("phone")
                            }],
                            "messages": [{
                                "from": message.get("phone"),
                                "id": f"wamid.{hex(int.from_bytes(os.urandom(16), 'big'))[2:]}",
                                "timestamp": str(int(time.time())),
                                "type": message.get("type", "text"),
                                **(
                                    {"text": {"body": message.get("message")}}
                                    if message.get("type") == "text"
                                    else {
                                        "type": "interactive",
                                        "interactive": message.get("message", {}).get("interactive", {})
                                    }
                                    if isinstance(message.get("message"), dict) and message.get("message", {}).get("type") == "interactive"
                                    else {"interactive": message.get("interactive", {})}
                                )
                            }]
                        },
                        "field": "messages"
                    }]
                }]
            }

            # Set headers based on target
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Mock-Testing": "true"
            }

            # Get endpoint based on target
            endpoint = APP_ENDPOINTS.get(target, APP_ENDPOINTS['local'])
            logger.info(f"Forwarding to {target} endpoint: {endpoint}")

            # Send request and handle response
            response = requests.post(
                endpoint,
                json=webhook_message,
                headers=headers,
                timeout=30  # Match CLI client timeout
            )

            if response.status_code != 200:
                logger.error("App error response: %s", response.text)
                return

        except Exception as e:
            # Log but continue
            logger.error("Failed to forward to app: %s", e)

    def _handle_webhook(self):
        """Handle webhook POST request."""
        try:
            # Read and process request
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length)
                message = json.loads(body.decode('utf-8'))

                # Handle UI->Server messages
                if "type" in message and "message" in message and "phone" in message:
                    # Save outgoing message
                    if message["type"] == "text":
                        outgoing_message = {
                            "type": "text",
                            "text": {"body": message["message"]},
                            "to": message["phone"]
                        }
                    elif message["type"] == "interactive":
                        outgoing_message = {
                            "type": "interactive",
                            "interactive": message["message"],
                            "to": message["phone"]
                        }
                    self._save_message(outgoing_message)

                    # Acknowledge receipt immediately and close connection
                    self._send_200({"success": True})
                    # Get target from query params
                    target = 'local'
                    if '?' in self.path:
                        query_string = self.path.split('?')[1]
                        logger.info(f"Query string: {query_string}")
                        query_params = dict(param.split('=') for param in query_string.split('&'))
                        logger.info(f"Query params: {query_params}")
                        target = query_params.get('target', 'local')
                    logger.info(f"Selected target: {target}")

                    # Start forwarding to app in a separate thread
                    import threading
                    threading.Thread(target=self._forward_to_app, args=(message, target)).start()
                    logger.info("UI -> Server-> app-1 complete: %s", message["message"])
                    return

                # Handle App->Server messages
                # Extract message content from WhatsApp format
                if message.get("messaging_product") == "whatsapp":
                    # Extract message from WhatsApp format
                    if "entry" in message:
                        # Message from app in WhatsApp format
                        value = message.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {})
                        messages = value.get("messages", [{}])[0]
                    else:
                        # Direct message from app
                        messages = message

                    # Create outgoing message
                    outgoing_message = {
                        "from": "app",  # Explicitly mark as from app
                        "to": None,  # App messages don't have a to field
                        "type": messages.get("type", "text")
                    }

                    # Handle message content
                    if outgoing_message["type"] == "text":
                        text_content = messages.get("text", {}).get("body", "") if isinstance(messages.get("text"), dict) else messages.get("text", "")
                        outgoing_message["text"] = {"body": text_content}
                        logger.info("app-1 -> Server -> save complete: %s", text_content)
                    elif outgoing_message["type"] == "interactive":
                        interactive_content = messages.get("interactive", {})
                        outgoing_message["interactive"] = interactive_content
                        logger.info("app-1 -> Server -> save complete: %s", interactive_content.get('body', {}).get('text', '').split('\n')[0])

                    # Save message
                    self._save_message(outgoing_message)

                # Acknowledge receipt to app
                self._send_200({
                    "messaging_product": "whatsapp",
                    "contacts": [{"input": message.get("to"), "wa_id": message.get("to")}],
                    "messages": [{"id": f"wamid.{hex(int.from_bytes(os.urandom(16), 'big'))[2:]}"}]
                })

        except Exception as e:
            # Just log and continue
            logger.error("Error handling webhook: %s", e)

    def log_request(self, code='-', size='-'):
        """Log an accepted request."""
        if hasattr(self, 'requestline') and self.path == "/":
            logger.info("VimbisoPay Mock reloaded")
        return

    def log_error(self, format, *args):
        """Log an error."""
        logger.error(format, *args)

    def log_message(self, format, *args):
        """Log a message."""
        pass  # Suppress default logging

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/" or self.path == "" or self.path == "/index.html":
            # Get all messages
            messages = self._get_messages()

            # Read the index.html template
            with open(os.path.join(os.path.dirname(__file__), 'index.html'), 'r') as f:
                html_content = f.read()

            # Create message elements
            messages_html = ''
            for msg in messages:
                if msg.get('type') == 'text' and msg.get('text', {}).get('body'):
                    direction = 'incoming' if msg.get('from') else 'outgoing'
                    body = msg['text']['body']
                    # Escape special characters for HTML attribute
                    escaped_body = body.replace('"', '&quot;').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    messages_html += f"""
                    <div class="message {direction}-message whatsapp-text" data-raw-text="{escaped_body}"></div>
                    """
                elif msg.get('type') == 'interactive':
                    direction = 'incoming' if msg.get('from') else 'outgoing'
                    interactive = msg.get('interactive', {})
                    # Convert interactive message to JSON string and escape for HTML attribute
                    escaped_json = json.dumps(interactive).replace('"', '&quot;')
                    # Add debug info
                    messages_html += f"""
                    <div class="message whatsapp-interactive {direction}-message" data-interactive="{escaped_json}"></div>
                    """

            # Replace placeholder with messages
            html_content = html_content.replace('{messages_placeholder}', messages_html)

            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(html_content.encode())
            return

        if self.path == "/clear-conversation":
            try:
                # Delete all files in messages directory
                for filename in os.listdir(MESSAGES_DIR):
                    if filename.endswith('.json'):
                        os.remove(os.path.join(MESSAGES_DIR, filename))
                logger.info("VimbisoPay Mock cleared")
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode())
            except Exception as e:
                logger.error("Error clearing conversation: %s", e)
                self.send_response(500)
                self.end_headers()
            return

        if self.path.startswith("/messages"):
            # Get since parameter if provided
            since = None
            if "?" in self.path:
                query = self.path.split("?")[1]
                params = dict(param.split("=") for param in query.split("&"))
                since = int(params.get("since", 0))

            # Get messages
            messages = self._get_messages(since)

            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(messages).encode())
            return

        try:
            file_path = self.translate_path(self.path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                with open(file_path, 'rb') as f:
                    content = f.read()
                    # Send response with CORS headers
                    self.send_response(200)
                    self.send_header('Content-Type', self.guess_type(file_path))
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(content)
                    return
        except Exception as e:
            logger.error("Error checking file path: %s", e)

        # Fall back to default handler if file not found
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Mock-Testing')
        self.end_headers()

    def _send_cors_headers(self):
        """Send CORS headers."""
        # Get the origin from the request headers
        origin = self.headers.get('Origin', '*')
        # If it's a GitHub Codespaces domain, use that specific origin
        if '.app.github.dev' in origin:
            self.send_header('Access-Control-Allow-Origin', origin)
        else:
            self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Mock-Testing')

    def do_POST(self):
        """Handle POST requests."""
        if self.path.startswith("/bot/webhook"):
            self._handle_webhook()
        else:
            try:
                self.send_response(404)
                self.end_headers()
            except Exception as e:
                logger.debug("Error sending 404: %s", e)


def run_server(port=8001):
    """Run the mock server."""
    logger.info("VimbisoPay Mock up at: http://localhost:%d", port)

    server = socketserver.TCPServer(("", port), MockWhatsAppHandler)
    server.allow_reuse_address = True

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
