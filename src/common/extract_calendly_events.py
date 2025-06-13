import re
from datetime import datetime

def extract_calendly_events(text: str):
    events = []
    lines = text.strip().splitlines()

    for line in lines:
        # Skip markdown header/separator if present
        if any(x in line.lower() for x in ["action item", "responsible", "due date"]):
            continue
        if set(line.strip()) <= {'-', '|'}:
            continue

        parts = [cell.strip() for cell in line.split('|') if cell.strip()]
        if len(parts) != 3:
            continue  # Skip malformed lines

        title, responsible, due_date = parts

        # Clean up date suffix (e.g., '4th' -> '4')
        cleaned_date = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', due_date)

        try:
            parsed_date = datetime.strptime(cleaned_date, "%B %d")
            parsed_date = parsed_date.replace(year=datetime.now().year)
            date_str = parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            date_str = cleaned_date  # Fallback if parsing fails

        events.append({
            "title": title,
            "description": f"Responsible: {responsible}",
            "date": date_str
        })

    return events
