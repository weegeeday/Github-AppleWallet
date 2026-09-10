"""
Module for generating a sleek 1080x360 PNG banner for Apple Wallet (storeCard stripURL).
Matches GitHub's official dark mode contribution graph.
"""
import io
import base64
import os
from datetime import datetime, date
from typing import Dict, List, Any
from PIL import Image, ImageDraw, ImageFont

# Color palette: GitHub Dark Mode
BG_COLOR = (13, 17, 23)        # #0d1117
CARD_BG = (22, 27, 34)         # #161b22
CARD_BORDER = (48, 54, 61)     # #30363d
TEXT_WHITE = (240, 246, 252)   # #f0f6fc
TEXT_MUTED = (139, 148, 158)   # #8b949e
TEXT_GREEN = (57, 211, 83)     # #39d353

LEVEL_COLORS = [
    (22, 27, 34),     # Level 0: #161b22
    (14, 68, 41),     # Level 1: #0e4429
    (0, 109, 50),     # Level 2: #006d32
    (38, 166, 65),    # Level 3: #26a641
    (57, 211, 83),    # Level 4: #39d353
]

def get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    font_candidates = []
    if bold:
        font_candidates = [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "DejaVuSans-Bold.ttf",
            "arialbd.ttf"
        ]
    else:
        font_candidates = [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "DejaVuSans.ttf",
            "arial.ttf"
        ]

    for path in font_candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
        # Also try loading by name
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue

    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()

def generate_banner_image(data: Dict[str, Any], output_path: str = None) -> str:
    """
    Renders 1080x360 px image of GitHub contribution calendar.
    Returns data URI string: data:image/png;base64,...
    """
    width = 1080
    height = 360
    img = Image.new("RGBA", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Outer decorative card panel
    panel_margin_x = 24
    panel_margin_y = 20
    draw.rounded_rectangle(
        [panel_margin_x, panel_margin_y, width - panel_margin_x, height - panel_margin_y],
        radius=16,
        fill=(18, 22, 28),
        outline=CARD_BORDER,
        width=2
    )

    # Header fonts
    font_title = get_font(26, bold=True)
    font_sub = get_font(20, bold=False)
    font_small = get_font(15, bold=False)
    font_legend = get_font(13, bold=False)

    # Header text
    username = data.get("username", "developer")
    total_commits = data.get("total_last_year", 0)
    current_streak = data.get("current_streak", 0)
    
    # Left Header: "@username • Contributions"
    title_text = f"@{username}"
    draw.text((48, 40), title_text, font=font_title, fill=TEXT_WHITE)
    
    title_bbox = draw.textbbox((48, 40), title_text, font=font_title)
    sub_x = title_bbox[2] + 12
    draw.text((sub_x, 44), "•  Contribution Heatmap", font=font_sub, fill=TEXT_MUTED)

    # Right Header: Streak badge
    streak_text = f"🔥 {current_streak} Day Streak" if current_streak > 0 else f"{total_commits} in past year"
    streak_bbox = draw.textbbox((0, 0), streak_text, font=font_sub)
    streak_w = streak_bbox[2] - streak_bbox[0]
    streak_x = width - panel_margin_x - 32 - streak_w
    draw.text((streak_x, 44), streak_text, font=font_sub, fill=TEXT_GREEN if current_streak > 0 else TEXT_WHITE)

    # Prepare 52-53 weeks of data
    days = data.get("days", [])
    if len(days) > 371:
        # Keep last 53 weeks (53 * 7 = 371 days)
        days = days[-371:]

    # Organize days into columns (weeks of 7 days: Sun=0 to Sat=6)
    # Each column has up to 7 items
    weeks: List[List[Dict[str, Any]]] = []
    current_week = []
    
    for d in days:
        dt = datetime.strptime(d["date"], "%Y-%m-%d")
        weekday = (dt.weekday() + 1) % 7 # Python Monday=0, we want Sunday=0
        if weekday == 0 and current_week:
            weeks.append(current_week)
            current_week = []
        current_week.append(d)
    if current_week:
        weeks.append(current_week)

    # Ensure max 53 weeks for display
    if len(weeks) > 53:
        weeks = weeks[-53:]

    # Grid geometry
    cell_size = 12
    gap = 4
    col_width = cell_size + gap
    grid_start_x = 76
    grid_start_y = 114

    # Day labels on the left (Mon, Wed, Fri)
    day_labels = [("Mon", 1), ("Wed", 3), ("Fri", 5)]
    for label, row_idx in day_labels:
        y_pos = grid_start_y + row_idx * (cell_size + gap) - 2
        draw.text((44, y_pos), label, font=font_legend, fill=TEXT_MUTED)

    # Draw month labels along the top
    months_drawn = set()
    for col_idx, week in enumerate(weeks):
        for d in week:
            dt = datetime.strptime(d["date"], "%Y-%m-%d")
            # If 1st day of month or first week
            m_key = dt.strftime("%Y-%m")
            if dt.day <= 7 and m_key not in months_drawn:
                months_drawn.add(m_key)
                m_label = dt.strftime("%b")
                col_x = grid_start_x + col_idx * col_width
                draw.text((col_x, grid_start_y - 22), m_label, font=font_legend, fill=TEXT_MUTED)
                break

    # Draw cells
    for col_idx, week in enumerate(weeks):
        col_x = grid_start_x + col_idx * col_width
        for d in week:
            dt = datetime.strptime(d["date"], "%Y-%m-%d")
            row_idx = (dt.weekday() + 1) % 7 # 0 is Sunday, 6 is Saturday
            row_y = grid_start_y + row_idx * (cell_size + gap)

            level = d.get("level", 0)
            if level < 0: level = 0
            if level > 4: level = 4
            color = LEVEL_COLORS[level]

            # Cell shape: rounded rectangle
            draw.rounded_rectangle(
                [col_x, row_y, col_x + cell_size, row_y + cell_size],
                radius=2.5,
                fill=color,
                outline=(255, 255, 255, 12) if level == 0 else None,
                width=1
            )

    # Bottom footer info
    footer_y = height - panel_margin_y - 40
    
    # Left stats: total year & today
    stats_text = f"Total: {total_commits} commits  |  Today: {data.get('today_commits', 0)}"
    draw.text((48, footer_y), stats_text, font=font_small, fill=TEXT_MUTED)

    # Right: Legend (Less [0][1][2][3][4] More)
    legend_x = width - panel_margin_x - 180
    draw.text((legend_x - 36, footer_y + 1), "Less", font=font_legend, fill=TEXT_MUTED)
    
    for i, c in enumerate(LEVEL_COLORS):
        cx = legend_x + i * (cell_size + 3)
        draw.rounded_rectangle(
            [cx, footer_y + 2, cx + cell_size, footer_y + 2 + cell_size],
            radius=2,
            fill=c
        )
    draw.text((legend_x + 5 * (cell_size + 3) + 4, footer_y + 1), "More", font=font_legend, fill=TEXT_MUTED)

    # Save to path if requested
    if output_path:
        img.save(output_path, "PNG")

    # Encode to Base64 PNG data URI
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_data}"

if __name__ == "__main__":
    from fetch_github import fetch_contributions
    contributions = fetch_contributions("weegeeday")
    data_uri = generate_banner_image(contributions, "preview_card.png")
    print(f"Banner generated! Length: {len(data_uri)} chars. Saved to preview_card.png")
