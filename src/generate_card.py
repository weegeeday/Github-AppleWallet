"""
High-resolution supersampled renderer for GitHub contribution heatmap.
Renders at 2x and downsamples with Lanczos for ultra-crisp retina display on iOS.
No borders, no fake card frames, no burned-in username.
"""
import io
import base64
import os
from datetime import datetime
from typing import Dict, List, Any
from PIL import Image, ImageDraw, ImageFont

# Canonical GitHub Dark Mode Colors
BG_COLOR = (13, 17, 23, 255)       # #0d1117 (seamless pass background)
TEXT_MUTED = (139, 148, 158, 255)   # #8b949e

LEVEL_COLORS = [
    (22, 27, 34, 255),     # Level 0: #161b22
    (14, 68, 41, 255),     # Level 1: #0e4429
    (0, 109, 50, 255),     # Level 2: #006d32
    (38, 166, 65, 255),    # Level 3: #26a641
    (57, 211, 83, 255),    # Level 4: #39d353
]

def get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    font_candidates = []
    if bold:
        font_candidates = [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/sf-pro-display_bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "DejaVuSans-Bold.ttf",
            "arialbd.ttf"
        ]
    else:
        font_candidates = [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/sf-pro-display_regular.ttf",
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
    Uses 2x supersampling (2160x720) for crystal clear retina rendering.
    """
    SCALE = 2
    w_2x = 1080 * SCALE
    h_2x = 360 * SCALE

    img_2x = Image.new("RGBA", (w_2x, h_2x), BG_COLOR)
    draw = ImageDraw.Draw(img_2x)

    font_month = get_font(13 * SCALE, bold=False)
    font_day = get_font(12 * SCALE, bold=False)
    font_legend = get_font(12 * SCALE, bold=False)

    days = data.get("days", [])
    if len(days) > 371:
        days = days[-371:]

    # Organize days into columns (weeks of 7 days: Sun=0 to Sat=6)
    weeks: List[List[Dict[str, Any]]] = []
    current_week = []
    for d in days:
        dt = datetime.strptime(d["date"], "%Y-%m-%d")
        weekday = (dt.weekday() + 1) % 7  # Sun=0, Mon=1, ..., Sat=6
        if weekday == 0 and current_week:
            weeks.append(current_week)
            current_week = []
        current_week.append(d)
    if current_week:
        weeks.append(current_week)

    # Display exactly 52 weeks
    if len(weeks) > 52:
        weeks = weeks[-52:]

    num_weeks = len(weeks)

    # Geometry at 2x
    # Target 52 cols in ~1000px: cell = 15px, gap = 4px -> 52 * 19 = 988px
    cell_size = 14 * SCALE
    gap = 4 * SCALE
    col_pitch = cell_size + gap

    total_grid_w = num_weeks * col_pitch - gap
    grid_start_x = (w_2x - total_grid_w) // 2 + (15 * SCALE)  # leave room for Mon/Wed/Fri labels on left
    grid_start_y = 90 * SCALE

    # Day labels on the left (Mon=1, Wed=3, Fri=5)
    day_labels = [("Mon", 1), ("Wed", 3), ("Fri", 5)]
    for label, row_idx in day_labels:
        y_pos = grid_start_y + row_idx * col_pitch + (2 * SCALE)
        draw.text((grid_start_x - (28 * SCALE), y_pos), label, font=font_day, fill=TEXT_MUTED)

    # Month labels along the top
    months_drawn = set()
    for col_idx, week in enumerate(weeks):
        for d in week:
            dt = datetime.strptime(d["date"], "%Y-%m-%d")
            m_key = dt.strftime("%Y-%m")
            if dt.day <= 7 and m_key not in months_drawn:
                months_drawn.add(m_key)
                m_label = dt.strftime("%b")
                col_x = grid_start_x + col_idx * col_pitch
                draw.text((col_x, grid_start_y - (24 * SCALE)), m_label, font=font_month, fill=TEXT_MUTED)
                break

    # Draw cells
    corner_radius = 2.5 * SCALE
    for col_idx, week in enumerate(weeks):
        col_x = grid_start_x + col_idx * col_pitch
        for d in week:
            dt = datetime.strptime(d["date"], "%Y-%m-%d")
            row_idx = (dt.weekday() + 1) % 7
            row_y = grid_start_y + row_idx * col_pitch

            level = d.get("level", 0)
            if level < 0: level = 0
            if level > 4: level = 4
            color = LEVEL_COLORS[level]

            # Crisp rounded tile
            draw.rounded_rectangle(
                [col_x, row_y, col_x + cell_size, row_y + cell_size],
                radius=corner_radius,
                fill=color
            )

    # Minimalist Legend at the bottom right
    legend_y = grid_start_y + 7 * col_pitch + (20 * SCALE)
    legend_cell_size = 11 * SCALE
    legend_gap = 3 * SCALE
    
    # Position legend right-aligned with the grid
    legend_total_w = 5 * (legend_cell_size + legend_gap) + (70 * SCALE)
    legend_start_x = grid_start_x + total_grid_w - legend_total_w

    draw.text((legend_start_x, legend_y - (1 * SCALE)), "Less", font=font_legend, fill=TEXT_MUTED)
    squares_start_x = legend_start_x + (32 * SCALE)

    for i, c in enumerate(LEVEL_COLORS):
        sx = squares_start_x + i * (legend_cell_size + legend_gap)
        draw.rounded_rectangle(
            [sx, legend_y, sx + legend_cell_size, legend_y + legend_cell_size],
            radius=2 * SCALE,
            fill=c
        )
    draw.text((squares_start_x + 5 * (legend_cell_size + legend_gap) + (6 * SCALE), legend_y - (1 * SCALE)), "More", font=font_legend, fill=TEXT_MUTED)

    # Downsample from 2160x720 to 1080x360 using high quality Lanczos filter
    final_img = img_2x.resize((1080, 360), resample=Image.Resampling.LANCZOS)

    if output_path:
        final_img.save(output_path, "PNG")

    buf = io.BytesIO()
    final_img.save(buf, format="PNG", optimize=True)
    b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_data}"
