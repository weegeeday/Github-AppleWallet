"""
High-resolution supersampled renderer for GitHub contribution heatmap.
Optimized for Apple Wallet 1080x360 strip banner:
- Generous safe margins (140px+) so iOS pass corner radius never clips the newest days.
- Full 7-day columns (future days rendered with subtle placeholders so the column isn't cut off).
- Today's cell highlighted with a crisp accent ring.
- 2x supersampling (2160x720) downscaled with Lanczos for retina sharpness.
"""
import io
import base64
import os
from datetime import datetime, date
from typing import Dict, List, Any, Optional
from PIL import Image, ImageDraw, ImageFont

# Canonical GitHub Dark Mode Colors
BG_COLOR = (13, 17, 23, 255)          # #0d1117 (seamless pass background)
TEXT_MUTED = (139, 148, 158, 255)      # #8b949e
TEXT_SUBTLE = (110, 118, 129, 255)     # #6e7681
TODAY_RING = (240, 246, 252, 220)      # Bright crisp ring for today

LEVEL_COLORS = [
    (22, 27, 34, 255),        # Level 0: #161b22
    (14, 68, 41, 255),        # Level 1: #0e4429
    (0, 109, 50, 255),        # Level 2: #006d32
    (38, 166, 65, 255),       # Level 3: #26a641
    (57, 211, 83, 255),       # Level 4: #39d353
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
    Renders 1080x360 px image showing the last 20 weeks (~5 months) of contributions.
    Guarantees wide safe margins on both left and right edges so iOS Apple Wallet
    corner radius and card borders NEVER cut off the latest days.
    """
    SCALE = 2
    w_2x = 1080 * SCALE
    h_2x = 360 * SCALE

    img_2x = Image.new("RGBA", (w_2x, h_2x), BG_COLOR)
    draw = ImageDraw.Draw(img_2x)

    font_month = get_font(14 * SCALE, bold=True)
    font_day = get_font(12 * SCALE, bold=False)
    font_legend = get_font(12 * SCALE, bold=False)

    days = data.get("days", [])
    today_str = date.today().isoformat()

    # Create a lookup map of date -> day dict
    day_map = {d["date"]: d for d in days}

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

    # Fill future days of the current week with placeholder objects
    if weeks:
        last_week = weeks[-1]
        last_day_dt = datetime.strptime(last_week[-1]["date"], "%Y-%m-%d")
        last_weekday = (last_day_dt.weekday() + 1) % 7  # 0 to 6
        for w in range(last_weekday + 1, 7):
            last_week.append({
                "date": f"future-{w}",
                "level": -1,  # -1 denotes future placeholder
                "count": 0
            })

    # Keep exactly 20 weeks (~5 months) to ensure wide 140px safe margins
    TARGET_WEEKS = 20
    if len(weeks) > TARGET_WEEKS:
        weeks = weeks[-TARGET_WEEKS:]

    num_weeks = len(weeks)

    # 1x dimensions:
    # Cell size = 28px, Gap = 8px, Pitch = 36px.
    # 20 cols * 36px - 8px = 712px total grid width.
    # Total canvas = 1080px.
    # Left day labels take ~40px.
    # Total content width = 712px + 45px = 757px.
    # Left margin: (1080 - 757) // 2 + 45 = ~206px.
    # Right margin: 1080 - (206 + 712) = ~162px safe margin from the right edge!
    # No iPhone screen or card bezel can EVER crop 162px!

    cell_size = 28 * SCALE
    gap = 8 * SCALE
    col_pitch = cell_size + gap
    corner_radius = 6 * SCALE

    grid_total_w = num_weeks * col_pitch - gap
    day_label_w = 46 * SCALE
    
    # Perfectly centered horizontally
    grid_start_x = (w_2x - (grid_total_w + day_label_w)) // 2 + day_label_w
    
    # 7 rows * 36px - 8px = 244px.
    # Canvas = 360px.
    # Top margin: 54px (for month labels at 26px).
    grid_start_y = 54 * SCALE

    # Day labels on the left (Mon=1, Wed=3, Fri=5)
    day_labels = [("Mon", 1), ("Wed", 3), ("Fri", 5)]
    for label, row_idx in day_labels:
        y_pos = grid_start_y + row_idx * col_pitch + (6 * SCALE)
        draw.text((grid_start_x - (38 * SCALE), y_pos), label, font=font_day, fill=TEXT_MUTED)

    # Month labels along the top
    months_drawn = set()
    for col_idx, week in enumerate(weeks):
        for d in week:
            if d.get("level", 0) == -1:
                continue
            dt = datetime.strptime(d["date"], "%Y-%m-%d")
            m_key = dt.strftime("%Y-%m")
            if dt.day <= 7 and m_key not in months_drawn:
                months_drawn.add(m_key)
                m_label = dt.strftime("%b")
                col_x = grid_start_x + col_idx * col_pitch
                draw.text((col_x, grid_start_y - (30 * SCALE)), m_label, font=font_month, fill=TEXT_MUTED)
                break

    # Draw cells
    for col_idx, week in enumerate(weeks):
        col_x = grid_start_x + col_idx * col_pitch
        for row_idx, d in enumerate(week):
            row_y = grid_start_y + row_idx * col_pitch
            level = d.get("level", 0)
            is_today = (d.get("date") == today_str)

            if level == -1:
                # Future day: faint dashed/subtle placeholder
                draw.rounded_rectangle(
                    [col_x, row_y, col_x + cell_size, row_y + cell_size],
                    radius=corner_radius,
                    fill=(18, 22, 28, 160),
                    outline=(255, 255, 255, 15),
                    width=SCALE
                )
            else:
                if level < 0: level = 0
                if level > 4: level = 4
                color = LEVEL_COLORS[level]

                draw.rounded_rectangle(
                    [col_x, row_y, col_x + cell_size, row_y + cell_size],
                    radius=corner_radius,
                    fill=color,
                    outline=(255, 255, 255, 12) if level == 0 else None,
                    width=SCALE
                )

                # If this is today, add a glowing highlight ring
                if is_today:
                    draw.rounded_rectangle(
                        [col_x - 1*SCALE, row_y - 1*SCALE, col_x + cell_size + 1*SCALE, row_y + cell_size + 1*SCALE],
                        radius=corner_radius + 1*SCALE,
                        outline=TODAY_RING,
                        width=2 * SCALE
                    )

    # Footer under the grid:
    legend_y = grid_start_y + 7 * col_pitch + (14 * SCALE)
    legend_cell_size = 13 * SCALE
    legend_gap = 4 * SCALE
    
    legend_total_w = 5 * (legend_cell_size + legend_gap) + (80 * SCALE)
    legend_start_x = grid_start_x + grid_total_w - legend_total_w

    # Left label: "Recent Contributions"
    draw.text((grid_start_x, legend_y), "Recent Activity", font=font_legend, fill=TEXT_SUBTLE)

    # Right legend: "Less [][][][][] More"
    draw.text((legend_start_x, legend_y), "Less", font=font_legend, fill=TEXT_MUTED)
    squares_start_x = legend_start_x + (34 * SCALE)

    for i, c in enumerate(LEVEL_COLORS):
        sx = squares_start_x + i * (legend_cell_size + legend_gap)
        draw.rounded_rectangle(
            [sx, legend_y + (1 * SCALE), sx + legend_cell_size, legend_y + (1 * SCALE) + legend_cell_size],
            radius=2.5 * SCALE,
            fill=c
        )
    draw.text((squares_start_x + 5 * (legend_cell_size + legend_gap) + (6 * SCALE), legend_y), "More", font=font_legend, fill=TEXT_MUTED)

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
    user = os.environ.get("GH_USERNAME", "octocat")
    data = fetch_contributions(user)
    uri = generate_banner_image(data, "preview_card.png")
    print(f"Generated safe-margin banner for @{user}! Saved to preview_card.png ({len(uri)} chars)")
