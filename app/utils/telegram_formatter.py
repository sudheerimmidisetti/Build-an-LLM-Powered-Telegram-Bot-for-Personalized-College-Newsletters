import re
import logging

logger = logging.getLogger(__name__)

def escape_markdown_v2(text: str) -> str:
    """
    Escapes all reserved Telegram MarkdownV2 characters while preserving 
    matched '*' pairs for bold formatting and escaping standalone asterisks.
    """
    if not text:
        return ""
    
    # 1. Escape all reserved characters except '*' first
    escape_chars = r"_[]()~`>#+-=|{}.!"
    escaped = re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)
    
    # 2. Handle asterisks (*). Match pairs and keep them unescaped; escape standalone ones.
    parts = escaped.split("*")
    processed_parts = []
    
    # If the length of parts is odd, all asterisks are matched.
    # If even, there is an unmatched asterisk at the end.
    is_odd = (len(parts) % 2 == 1)
    
    for i, part in enumerate(parts):
        if i == len(parts) - 1 and not is_odd:
            # Escape the trailing unmatched asterisk
            processed_parts.append("\\*" + part)
        elif i % 2 == 1 and i < len(parts) - 1:
            # This is inside a matched pair: restore the unescaped bold boundary
            processed_parts.append("*" + part + "*")
        elif i % 2 == 1 and i == len(parts) - 1:
            # Edge case: odd count but it's the last element (should not happen with split logic, but safe)
            processed_parts.append("\\*" + part)
        else:
            # Outside a bold block
            processed_parts.append(part)
            
    return "".join(processed_parts)

def build_newsletter_message(events_sec: str, courses_sec: str, weather_sec: str) -> str:
    """
    Combines escaped newsletter sections with the mandatory bold headers.
    Headers themselves must be unescaped to render correctly as bold.
    """
    # Escape each individual section to ensure no reserved characters crash the bot
    esc_events = escape_markdown_v2(events_sec)
    esc_courses = escape_markdown_v2(courses_sec)
    esc_weather = escape_markdown_v2(weather_sec)
    
    # Assemble the newsletter with exact header syntax
    # Note: the asterisks around headers are unescaped so Telegram renders them as bold.
    message = (
        f"*Events This Week*\n"
        f"{esc_events}\n\n"
        f"*Course Reminders*\n"
        f"{esc_courses}\n\n"
        f"*Weather Outlook*\n"
        f"{esc_weather}"
    )
    
    return message
