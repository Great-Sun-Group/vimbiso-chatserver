"""Culturally aware greeting system with Zimbabwe-first, globally inclusive approach"""
import random
from datetime import datetime
from typing import List, Tuple, Any, Dict
from ..base import DisplayComponent


class Greeting(DisplayComponent):
    """Component for sending culturally-aware greetings"""

    def __init__(self):
        super().__init__("greeting")

    def display(self, value: Any) -> None:
        """Generate and send greeting"""
        # Generate greeting
        greeting = get_random_greeting()

        # Send through messaging service
        self.state_manager.messaging.send_text(greeting)

    def to_message_content(self, value: Dict) -> str:
        """Convert validated value to message content"""
        if not value or not isinstance(value, dict):
            return "Processing your request..."
        return value.get("message", "Processing your request...")


# Emoji sets with cultural touches for Zimbabwe-centric global launch
MORNING_EMOJIS = [
    "🌅",  # Sunrise
    "🌞",  # Sun with face (warm/friendly)
    "🐓",  # Rooster (rural life)
    "🫖",  # Tea (morning ritual)
    "🌿",  # Herb (morning freshness)
]

AFTERNOON_EMOJIS = [
    "☀️",   # Sun
    "⛅",   # Sun behind cloud
    "🌾",   # Sheaf of rice (farming)
    "🏃🏿‍♂️",  # Running person (busy day)
    "🚶🏿‍♀️",  # Walking person (daily life)
]

EVENING_EMOJIS = [
    "🌆",   # Sunset buildings
    "🌇",   # Sunset
    "🏡",   # House (family time)
    "👨🏿‍👩🏿‍👧🏿‍👦🏿",  # Family (evening gathering)
    "🪵",   # Wood (evening fire)
]

NIGHT_EMOJIS = [
    "🌙",   # Crescent moon
    "✨",   # Sparkles
    "🦗",   # Cricket (evening ambiance)
    "🔥",   # Fire (evening gathering)
    "💫",   # Dizzy (night vibes)
]

# Zimbabwe seasonal and cultural touches
RAIN_EMOJIS = [
    "🌧️",  # Rain
    "⛈️",  # Storm
    "☔",   # Umbrella in rain
    "🌱",   # Growing plant
    "🌿",   # Herb (traditional medicine)
    "🍃"    # Leaf (cleansing rain)
]

HARVEST_EMOJIS = [
    "🌾",   # Harvest
    "🌿",   # Fresh crops
    "🍚",   # Rice/sadza
    "💪🏿",  # Hard work
    "🧺",   # Basket
    "🌽"    # Maize
]

CELEBRATION_EMOJIS = [
    "✨",    # Sparkles
    "🎊",    # Confetti
    "🎉",    # Party
    "🙌🏿",   # Celebration
    "🪘",    # Drum
    "💃🏿"    # Dancing
]

# Special events (reserved for future use)
INDEPENDENCE_EMOJIS = ["🇿🇼", "✊🏿", "🎉", "🌟"]  # April 18
HEROES_EMOJIS = ["🦁", "✊🏿", "🏆", "⭐"]         # August
UNITY_EMOJIS = ["🤝🏿", "🕊️", "💫", "🌟"]         # December 22

# Greeting phrases by language and context
GREETINGS: List[Tuple[str, str, List[str], float]] = [
    # Format: (phrase, language, [valid_periods], formality_level)
    # Formality: 0.0 (very casual) to 1.0 (very formal)

    # Shona greetings (core focus)
    ("Mangwanani", "Shona", ["morning"], 0.5),
    ("Mangwanani henyu", "Shona", ["morning"], 0.9),
    ("Masikati", "Shona", ["afternoon"], 0.5),
    ("Masikati henyu", "Shona", ["afternoon"], 0.9),
    ("Manheru", "Shona", ["evening"], 0.5),
    ("Manheru henyu", "Shona", ["evening"], 0.9),
    ("Usiku wakanaka", "Shona", ["night"], 0.7),
    ("Makadii", "Shona", ["anytime"], 0.6),
    ("Makadii henyu", "Shona", ["anytime"], 0.9),
    ("Maswera sei", "Shona", ["afternoon", "evening"], 0.6),
    ("Ndeipi", "Shona", ["anytime"], 0.2),
    ("Zvirisei", "Shona", ["anytime"], 0.3),
    ("Mhoro", "Shona", ["anytime"], 0.5),
    ("Uri sei?", "Shona", ["anytime"], 0.4),

    # Ndebele greetings (secondary focus)
    # Formal greetings
    ("Sawubona", "Ndebele", ["anytime"], 0.5),
    ("Salibonani", "Ndebele", ["anytime"], 0.6),

    # Time-specific
    ("Livukile", "Ndebele", ["morning"], 0.6),
    ("Livukile kuhle", "Ndebele", ["morning"], 0.8),
    ("Litshonile", "Ndebele", ["evening"], 0.6),
    ("Litshonile kuhle", "Ndebele", ["evening"], 0.8),
    ("Ubusuku obuhle", "Ndebele", ["night"], 0.7),

    # Casual/Friendly
    ("Kunjani", "Ndebele", ["anytime"], 0.4),
    ("Unjani wena", "Ndebele", ["anytime"], 0.5),
    ("Yebo", "Ndebele", ["anytime"], 0.3),

    # Pan-African touches
    ("Jambo", "Swahili", ["anytime"], 0.5),
    ("Habari", "Swahili", ["anytime"], 0.5),
    ("Dumela", "Setswana", ["anytime"], 0.5),

    # International greetings (inclusive touch)
    ("Hello", "English", ["anytime"], 0.5),
    ("Good morning", "English", ["morning"], 0.7),
    ("Good day", "English", ["afternoon"], 0.7),
    ("Good evening", "English", ["evening"], 0.7),
    ("Hi there", "English", ["anytime"], 0.3),
    ("Hey", "English", ["anytime"], 0.2),

    # Street/Youth culture (adds flavor)
    ("Zvakanaka", "Street", ["anytime"], 0.2),
    ("Sharp sharp", "Street", ["anytime"], 0.1),
    ("Heita", "Street", ["anytime"], 0.1),
]

# Casual suffixes with cultural touch
CASUAL_SUFFIXES = [
    # Relationship terms (weighted toward Zim culture)
    "shamwari 🤝🏿",     # Friend (Shona)
    "choms ⭐",        # Friend (slang)

    # Casual/Street
    "legend ✨",
    "chief 👑",
    "boss 💪🏿",

    # Universal
    "✌🏿",
    "🙌🏿",
    "👊🏿",
]

# Regional weighting (Zimbabwe-first, globally aware)
LANGUAGE_WEIGHTS = {
    "Shona": 45,      # Primary
    "Ndebele": 25,    # Secondary
    "Swahili": 8,     # Pan-African touch
    "Setswana": 7,    # Pan-African touch
    "English": 10,    # International accessibility
    "Street": 5,      # Youth culture
}


def get_time_period(hour: int = None) -> str:
    """Get time period, optionally from specific hour"""
    if hour is None:
        hour = datetime.now().hour

    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 20:
        return "evening"
    else:
        return "night"


def get_time_emoji(period: str = None) -> str:
    """Get contextual emoji based on time and season

    Occasionally adds humorous timezone confusion references
    """
    # Get current context
    month = datetime.now().month
    if period is None:
        period = get_time_period()

    # Define emoji sets
    emoji_sets = {
        "morning": MORNING_EMOJIS,
        "afternoon": AFTERNOON_EMOJIS,
        "evening": EVENING_EMOJIS,
        "night": NIGHT_EMOJIS
    }

    # Small chance for timezone humor (5%)
    if random.random() < 0.05:
        # Map current period to its opposite for humor
        opposite_period = {
            "morning": ("night", "🌙"),      # "Good morning! (or is it night? 🌙)")
            "afternoon": ("night", "💫"),     # Afternoon somewhere, late night elsewhere
            "evening": ("morning", "🌅"),     # Evening meets morning
            "night": ("day", "🌍✨")          # Night and day, somewhere in the world
        }.get(period)

        if opposite_period:
            # 50-50 chance between two humor styles
            if random.random() < 0.5:
                return opposite_period[1]  # Just the playful emoji
            else:
                # Return both time emojis to suggest global presence
                current_emoji = random.choice(emoji_sets[period])
                return f"{current_emoji}{opposite_period[1]}"

    # Get day for special events
    day = datetime.now().day

    # Special events and seasonal considerations
    if random.random() < 0.3:  # 30% chance for special/seasonal emoji
        # Special national days
        if month == 4 and day == 18:  # Independence Day
            return random.choice(INDEPENDENCE_EMOJIS)
        elif month == 8 and day in [11, 12]:  # Heroes & Defence Days
            return random.choice(HEROES_EMOJIS)
        elif month == 12 and day == 22:  # Unity Day
            return random.choice(UNITY_EMOJIS)
        # Seasonal periods
        elif month in [11, 12, 1]:  # Rainy season
            return random.choice(RAIN_EMOJIS)
        elif month in [4, 5, 6]:  # Harvest season
            return random.choice(HARVEST_EMOJIS)
        elif month == 12:  # Festive season
            return random.choice(CELEBRATION_EMOJIS)

    # Default to time-based emoji with occasional cultural touch
    if random.random() < 0.1:  # 10% chance for extra cultural touch
        cultural_emojis = {
            "morning": ["🇿🇼", "🌍"],    # Zimbabwe flag or Africa for international users
            "afternoon": ["🌍", "🌎"],    # Suggesting global presence
            "evening": ["🏡", "🫂"],      # Home/family values
            "night": ["✨", "💫"]         # Universal night vibes
        }.get(period, ["✨"])
        return random.choice(cultural_emojis)

    return random.choice(emoji_sets[period])


def get_random_greeting(include_emoji: bool = True, include_suffix: bool = True) -> str:
    """Generate a culturally appropriate greeting

    Weights heavily toward Zimbabwean culture while maintaining global inclusivity
    """
    # Get current context
    now = datetime.now()
    period = get_time_period()

    # Check for special days first
    if now.month == 4 and now.day == 18:  # Independence Day
        if random.random() < 0.4:  # 40% chance for special greeting
            emoji = random.choice(INDEPENDENCE_EMOJIS)
            return f"{emoji} Pamberi neZimbabwe! 🇿🇼"
    elif now.month == 8 and now.day in [11, 12]:  # Heroes & Defence Days
        if random.random() < 0.4:  # 40% chance for special greeting
            emoji = random.choice(HEROES_EMOJIS)
            return f"{emoji} Tichingotenda Magamba eZimbabwe ✊🏿"
    elif now.month == 12 and now.day == 22:  # Unity Day
        if random.random() < 0.4:  # 40% chance for special greeting
            emoji = random.choice(UNITY_EMOJIS)
            return f"{emoji} Unity Day • Zuva reUbatano 🤝🏿"
    elif now.month == 12 and now.day == 25:  # Christmas
        if random.random() < 0.3:  # 30% chance for special greeting
            return "✨ Merry Christmas • Kisimusi Yakanaka! 🎄"
    elif now.month == 12 and now.day == 31:  # New Year's Eve
        if random.random() < 0.3:  # 30% chance for special greeting
            return "🎊 Gore Ratsva Rakanaka! • Happy New Year! 🎆"
    elif now.month == 1 and now.day == 1:  # New Year's Day
        if random.random() < 0.3:  # 30% chance for special greeting
            return "✨ Gore Itsva Rakanaka! • Happy New Year! 🎊"

    # Filter greetings appropriate for time
    valid_greetings = [
        g for g in GREETINGS
        if period in g[2] or "anytime" in g[2]
    ]

    # Group by language
    by_language = {}
    for phrase, lang, _, formality in valid_greetings:
        if lang not in by_language:
            by_language[lang] = []
        by_language[lang].append((phrase, formality))

    # Select language based on weights
    total_weight = sum(LANGUAGE_WEIGHTS.get(lang, 1) for lang in by_language.keys())
    r = random.uniform(0, total_weight)
    cumulative_weight = 0
    selected_lang = None

    for lang in by_language.keys():
        cumulative_weight += LANGUAGE_WEIGHTS.get(lang, 1)
        if r <= cumulative_weight:
            selected_lang = lang
            break

    # Select greeting from chosen language
    greeting, formality = random.choice(by_language[selected_lang or "Shona"])

    # Build greeting components
    components = []

    # Add time emoji
    if include_emoji:
        components.append(get_time_emoji(period))

    # Add greeting
    components.append(greeting)

    # Add casual suffix based on formality
    if include_suffix:
        # More formal = less likely to have casual suffix
        suffix_chance = 0.4 * (1 - formality)
        if random.random() < suffix_chance:
            components.append(random.choice(CASUAL_SUFFIXES))

    return " ".join(components)
