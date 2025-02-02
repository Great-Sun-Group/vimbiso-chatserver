#!/usr/bin/env python3
"""Mock WhatsApp CLI client."""
import argparse
import json
import sys
import time
from urllib.parse import urlencode

import requests


def send_message(args: argparse.Namespace) -> None:
    """Send message to mock server."""
    # Create simple payload matching UI format
    payload = {
        "type": args.type,
        "message": args.message,
        "phone": args.phone
    }

    # Send request
    params = {'target': args.target}
    url = f"http://localhost:{args.port}/bot/webhook?{urlencode(params)}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Mock-Testing": "true"
    }

    try:
        print(f"Sending request to: {url}")
        print(f"Headers: {headers}")
        print(f"Payload: {json.dumps(payload, indent=2)}")

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        # Display raw response
        print("\nServer Response:")
        print(response.text)

        # Start polling for messages
        last_check = int(time.time() * 1000)  # Start from current time
        print("\nWaiting for responses...")

        while True:
            try:
                # Poll messages endpoint
                messages_url = f"http://localhost:{args.port}/messages?since={last_check}"
                response = requests.get(messages_url)
                response.raise_for_status()

                # Process any new messages
                messages = response.json()
                if messages:
                    for message in messages:
                        print(f"\nReceived: {json.dumps(message, indent=2)}")
                        # Update last check time from filename
                        last_check = max(last_check, int(time.time() * 1000))

                # Wait before next poll
                time.sleep(1)

            except KeyboardInterrupt:
                print("\nStopping message polling...")
                break
            except Exception as e:
                print(f"Error polling messages: {e}")
                time.sleep(1)  # Wait before retry

    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Response text: {e.response.text}")
        sys.exit(1)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Mock WhatsApp CLI Client",
        epilog="""
Examples:
  # Text message
  %(prog)s "Hello, world!"

  # Menu option
  %(prog)s --type interactive "handleactionoffercredex"

  # Flow navigation
  %(prog)s --type interactive "flow:MAKE_SECURE_OFFER"

  # Button response
  %(prog)s --type button "accept_offer_123"

  # Form submission
  %(prog)s --type interactive "form:amount=100,recipientAccountHandle=@user123"

  # List selection
  %(prog)s --type list '{"id":"credex_offer","title":"Offer Secured Credex","description":"Create a new secured Credex offer"}' --context-id wamid.123 --context-from 15550783881
        """
    )

    parser.add_argument(
        "--phone",
        default="1234567890",
        help="Phone number (default: 1234567890)"
    )
    parser.add_argument(
        "--type",
        choices=["text", "button", "interactive", "list"],
        default="text",
        help="Message type (default: text)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Server port (default: 8001)"
    )
    parser.add_argument(
        "--phone_number_id",
        default="123456789",
        help="WhatsApp Phone Number ID (default: 123456789)"
    )
    parser.add_argument(
        "--target",
        choices=["local", "development", "production"],
        default="local",
        help="Target environment (default: local)"
    )
    parser.add_argument(
        "--context-id",
        help="Message ID of the original message that triggered this interaction"
    )
    parser.add_argument(
        "--context-from",
        help="Phone number that sent the original message"
    )
    parser.add_argument(
        "message",
        help="Message to send"
    )

    args = parser.parse_args()
    send_message(args)


if __name__ == "__main__":
    main()
