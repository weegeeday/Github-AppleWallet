"""
High-resolution supersampled renderer for GitHub contribution heatmap.
Optimized for Apple Wallet 1080x360 strip banner:
- Shows the last 6 months (26 weeks) so contribution squares are large, chunky, and fill the space.
- Tactile 6px rounded squares with canonical GitHub greens.
- 2x supersampling (2160x720) downscaled via Lanczos for retina sharpness.
"""
import io
import base64
import os
from datetime import datetime
from typing import Dict, List, Any
from PIL import Image, ImageDraw, ImageFont

# Canonical GitHub Dark Mode Colors
BG_COLOR = (13, 17, 23, 255)         # #0d1117 (seamless pass background)
TEXT_MUTED = (139, 148, 158, 255)     # #8b949e
TEXT_SUBTLE = (110, 118, 129, 255)    # #6e7681

LEVEL_COLORS = [
    (22, 27, 34, 255),       # Level 0: #161b22
    (14, 68, 41, 255),       # Level 1: #0e4429
    (0, 109, 50, 255),       # Level 2: #006d32
    (38, 166, 65, 255),      # Level 3: #26a641
    (57, 211, 83, 255),      # Level 4: #39d353
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
    Renders 1080x360 px image showing the last 6 months (26 weeks) of contributions.
    Fills the banner with large, tactile rounded squares.
    """
    SCALE = 2
    w_2x = 1080 * SCALE
    h_2x = 360 * SCALE

    img_2x = Image.new("RGBA", (w_2x, h_2x), BG_COLOR)
    draw = ImageDraw.Draw(img_2x)

    font_month = get_font(15 * SCALE, bold=True)
    font_day = get_font(13 * SCALE, bold=False)
    font_legend = get_font(13 * SCALE, bold=False)

    days = data.get("days", [])

    # Group days into weeks (Sunday=0 to Saturday=6)
    weeks: List[List[Dict[str, Any]]] = []
    current_week = []
    for d in days:
        dt = datetime.strptime(d["date"], "%Y-%m-%d")
        weekday = (dt.weekday() + 1) % 7
        if weekday == 0 and current_week:
            weeks.append(current_week)
            current_week = []
        current_week.append(d)
    if current_week:
        weeks.append(current_week)

    # Keep exactly the last 26 weeks (~6 months)
    TARGET_WEEKS = 26
    if len(weeks) > TARGET_WEEKS:
        weeks = weeks[-TARGET_WEEKS:]

    num_weeks = len(weeks)

    # Geometry at 2x:
    # 1x dimensions: cell = 29px, gap = 7px, pitch = 36px.
    # 26 cols * 36px - 7px = 929px width.
    cell_size = 29 * SCALE
    gap = 7 * SCALE
    col_pitch = cell_size + gap
    corner_radius = 6 * SCALE

    grid_total_w = num_weeks * col_pitch - gap
    
    # Left margin: day labels (Mon, Wed, Fri) need ~45px
    day_label_w = 42 * SCALE
    grid_start_x = (w_2x - (grid_total_w + day_label_w)) // 2 + day_label_w
    
    # Vertical placement:
    # 7 rows * 36px - 7px = 245px.
    # Top margin: 54px for month headers.
    grid_start_y = 54 * SCALE

    # Day labels on the left (Mon=1, Wed=3, Fri=5)
    day_labels = [("Mon", 1), ("Wed", 3), ("Fri", 5)]
    for label, row_idx in day_labels:
        y_pos = grid_start_y + row_idx * col_pitch + (6 * SCALE)
        draw.text((grid_start_x - (36 * SCALE), y_pos), label, font=font_day, fill=TEXT_MUTED)

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
                draw.text((col_x, grid_start_y - (32 * SCALE)), m_label, font=font_month, fill=TEXT_MUTED)
                break

    # Draw cells
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

            # Bold tactile rounded cell
            draw.rounded_rectangle(
                [col_x, row_y, col_x + cell_size, row_y + cell_size],
                radius=corner_radius,
                fill=color,
                outline=(255, 255, 255, 8) if level == 0 else None,
                width=SCALE
            )

    # Minimalist Legend under the grid at the bottom-right
    legend_y = grid_start_y + 7 * col_pitch + (14 * SCALE)
    legend_cell_size = 14 * SCALE
    legend_gap = 5 * SCALE
    
    legend_total_w = 5 * (legend_cell_size + legend_gap) + (85 * SCALE)
    legend_start_x = grid_start_x + grid_total_w - legend_total_w

    # Left label "Recent 6 Months"
    draw.text((grid_start_x, legend_y), "Last 6 Months", font=font_legend, fill=TEXT_SUBTLE)

    # Right legend: "Less [][][][][] More"
    draw.text((legend_start_x, legend_y), "Less", font=font_legend, fill=TEXT_MUTED)
    squares_start_x = legend_start_x + (38 * SCALE)

    for i, c in enumerate(LEVEL_COLORS):
        sx = squares_start_x + i * (legend_cell_size + legend_gap)
        draw.rounded_rectangle(
            [sx, legend_y + (1 * SCALE), sx + legend_cell_size, legend_y + (1 * SCALE) + legend_cell_size],
            radius=3 * SCALE,
            fill=c
        )
    draw.text((squares_start_x + 5 * (legend_cell_size + legend_gap) + (8 * SCALE), legend_y), "More", font=font_legend, fill=TEXT_MUTED)

    # Downsample from 2160x720 to 1080x360 with Lanczos
    final_img = img_2x.resize((1080, 360), resample=Image.Resampling.LANCZOS)

    if output_path:
        final_img.save(output_path, "PNG")

    buf = io.BytesIO()
    final_img.save(buf, format="PNG", optimize=True)
    b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_data}"

if __name__ == "__main__":
    from fetch_github import fetch_contributions
    data = fetch_contributions("weegeeday")
    uri = generate_banner_image(data, "preview_card.png")
    print(f"Generated 6-month banner! Saved to preview_card.png ({len(uri)} chars)")
