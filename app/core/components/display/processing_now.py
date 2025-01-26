"""Processing status messages with Zimbabwe-first, globally inclusive approach"""
import random
from typing import Any, Dict
from ..base import DisplayComponent


class ProcessingNow(DisplayComponent):
    """Component for sending engaging processing status messages"""

    def __init__(self):
        super().__init__("processing_now")

    def display(self, value: Any) -> None:
        """Generate and send processing message"""
        # Generate message
        message = get_random_processing_message()

        # Send through messaging service
        self.state_manager.messaging.send_text(message)

    def to_message_content(self, value: Dict) -> str:
        """Convert validated value to message content"""
        if not value or not isinstance(value, dict):
            return "Processing your request..."
        return value.get("message", "Processing your request...")


# Emoji sets for different processing contexts
TECH_EMOJIS = [
    "⚡",    # Fast processing
    "🔄",    # Processing/loading
    "💫",    # Magic happening
    "✨",    # Sparkles (something special)
    "🚀",    # Fast/efficient
    "🔮",    # Crystal ball (checking)
    "🌟",    # Star (excellence)
]

FRIENDLY_EMOJIS = [
    "🤝🏿",   # Partnership
    "👋🏿",   # Wave
    "🙌🏿",   # Celebration
    "💪🏿",   # Strength
    "👊🏿",   # Fist bump
    "🫂",    # Support
]

NATURE_EMOJIS = [
    "🌿",    # Growth
    "🍃",    # Fresh
    "🌱",    # New beginnings
    "🌺",    # Flower (beauty)
    "🌸",    # Blossom
]

ZIMBABWE_TOUCH_EMOJIS = [
    "🇿🇼",   # Zimbabwe flag
    "🦁",    # Lion (strength)
    "🌍",    # Africa
    "🪘",    # Drum
    "🌞",    # Sun
]

# Processing message templates with cultural touches
PROCESSING_MESSAGES = [
    # Format: (message, formality_level, category)
    # Formality: 0.0 (very casual) to 1.0 (very formal)

    # Professional/Standard
    ("Just a moment while I process that", 0.7, "standard"),
    ("Processing your request", 0.8, "standard"),
    ("Working on that for you", 0.6, "standard"),
    ("Let me take care of that", 0.6, "standard"),

    # Shona-inspired
    ("Ndiri kubata basa renyu", 0.6, "shona"),  # I'm working on your task
    ("Mirai zvishoma", 0.5, "shona"),           # Wait a moment
    ("Ndiri kuona nezvazvo", 0.5, "shona"),     # I'm looking into it

    # Ndebele-inspired
    ("Ngiyasebenza kulokho", 0.6, "ndebele"),   # I'm working on that
    ("Lindani kancane", 0.5, "ndebele"),        # Wait a moment

    # Casual/Friendly
    ("On it, shamwari! ⚡", 0.3, "casual"),
    ("Just checking with headquarters", 0.4, "casual"),
    ("Making it happen", 0.3, "casual"),
    ("Working my magic", 0.2, "casual"),

    # Light humor
    ("Consulting with the wise ones 🦁", 0.2, "humor"),
    ("Asking the ancestors for guidance ✨", 0.2, "humor"),
    ("Brewing some digital tea for this one 🫖", 0.1, "humor"),
    ("Dancing with the data 💃🏿", 0.1, "humor"),

    # Tech-savvy
    ("Crunching the numbers", 0.5, "tech"),
    ("Running the calculations", 0.5, "tech"),
    ("Checking all systems", 0.5, "tech"),

    # Reassuring
    ("I've got this handled", 0.4, "reassuring"),
    ("Taking care of it now", 0.5, "reassuring"),
    ("Working on something special", 0.4, "reassuring"),
]

# Language weights for message selection
LANGUAGE_WEIGHTS = {
    "standard": 30,    # Professional messages
    "shona": 20,      # Primary local language
    "ndebele": 15,    # Secondary local language
    "casual": 15,     # Friendly messages
    "humor": 10,      # Light humor
    "tech": 5,        # Tech-savvy messages
    "reassuring": 5   # Reassuring messages
}


def get_random_processing_message() -> str:
    """Generate a processing message with appropriate cultural touch and tone"""
    # Select message category based on weights
    total_weight = sum(LANGUAGE_WEIGHTS.values())
    r = random.uniform(0, total_weight)
    cumulative_weight = 0
    selected_category = None

    for category, weight in LANGUAGE_WEIGHTS.items():
        cumulative_weight += weight
        if r <= cumulative_weight:
            selected_category = category
            break

    # Filter messages by selected category
    category_messages = [
        (msg, formality)
        for msg, formality, cat in PROCESSING_MESSAGES
        if cat == selected_category
    ]

    # Select message and formality
    message, formality = random.choice(category_messages)

    components = []

    # Add emoji (80% chance)
    if random.random() < 0.8:
        components.append(get_processing_emoji())

    # Add message
    components.append(message)

    return " ".join(components)


def get_processing_emoji() -> str:
    """Get contextual emoji for processing message"""
    # Weighted emoji selection
    emoji_sets = [
        (TECH_EMOJIS, 0.4),        # 40% chance
        (FRIENDLY_EMOJIS, 0.2),    # 20% chance
        (NATURE_EMOJIS, 0.2),      # 20% chance
        (ZIMBABWE_TOUCH_EMOJIS, 0.2)  # 20% chance
    ]

    selected_set = random.choices(
        [emoji_set for emoji_set, _ in emoji_sets],
        weights=[weight for _, weight in emoji_sets],
        k=1
    )[0]

    return random.choice(selected_set)
