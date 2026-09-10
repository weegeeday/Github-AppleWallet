"""
Module for fetching and parsing public GitHub contribution data.
"""
import re
import urllib.request
from datetime import datetime, date
from typing import Dict, List, Any, Optional

def fetch_contributions(username: str) -> Dict[str, Any]:
    url = f"https://github.com/users/{username}/contributions"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    )
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8")

    # Parse TD elements: each represents a day
    # Example: <td ... data-date="2026-03-01" id="contribution-day-component-25-0" data-level="2" ...>
    # And tool-tip: <tool-tip for="contribution-day-component-25-0">3 contributions on March 1st.</tool-tip>
    
    # 1. Map component ID to contribution count from tooltips
    tooltip_matches = re.findall(
        r'<tool-tip[^>]*for=["\'](contribution-day-component-[^"\']+)["\'][^>]*>(.*?)</tool-tip>',
        html,
        re.DOTALL
    )
    
    count_by_id = {}
    for comp_id, text in tooltip_matches:
        text = text.strip()
        # Text formats:
        # "No contributions on Sunday, March 1, 2026"
        # "1 contribution on Monday, March 2, 2026"
        # "5 contributions on Tuesday, March 3, 2026"
        count_match = re.search(r'(\d+)\s+contribution', text)
        if count_match:
            count_by_id[comp_id] = int(count_match.group(1))
        else:
            count_by_id[comp_id] = 0

    # 2. Extract day cells
    # We want data-date, data-level, and id
    td_pattern = re.compile(
        r'<td[^>]*class="[^"]*ContributionCalendar-day[^"]*"[^>]*>',
        re.DOTALL
    )
    
    days = []
    for td in td_pattern.finditer(html):
        tag = td.group(0)
        date_m = re.search(r'data-date=["\'](\d{4}-\d{2}-\d{2})["\']', tag)
        level_m = re.search(r'data-level=["\'](\d+)["\']', tag)
        id_m = re.search(r'id=["\']([^"\']+)["\']', tag)
        
        if date_m:
            day_date = date_m.group(1)
            level = int(level_m.group(1)) if level_m else 0
            comp_id = id_m.group(1) if id_m else None
            count = count_by_id.get(comp_id, 0)
            
            days.append({
                "date": day_date,
                "level": level,
                "count": count
            })

    # Sort days by date ascending
    days.sort(key=lambda x: x["date"])

    # Extract total contributions in the last year from heading if available
    # e.g., <h2 ...>\n 543 contributions\n in the last year\n </h2>
    total_match = re.search(r'([\d,]+)\s+contributions?\s+in\s+the\s+last\s+year', html, re.IGNORECASE)
    if total_match:
        total_last_year = int(total_match.group(1).replace(",", ""))
    else:
        total_last_year = sum(d["count"] for d in days)

    # Calculate streaks
    today_str = date.today().isoformat()
    current_year_str = str(date.today().year)
    
    today_commits = 0
    year_commits = 0
    for d in days:
        if d["date"] == today_str:
            today_commits = d["count"]
        if d["date"].startswith(current_year_str):
            year_commits += d["count"]

    # Current streak calculation:
    # Walk backwards from most recent day. If today has 0 commits, streak can still be alive from yesterday!
    current_streak = 0
    longest_streak = 0
    temp_streak = 0

    # For longest streak
    for d in days:
        if d["count"] > 0:
            temp_streak += 1
            if temp_streak > longest_streak:
                longest_streak = temp_streak
        else:
            temp_streak = 0

    # For current streak
    # Find index of today or the latest day
    rev_days = list(reversed(days))
    if rev_days:
        idx = 0
        # If today is the latest day and has 0 commits, check if yesterday had commits
        if rev_days[0]["date"] == today_str and rev_days[0]["count"] == 0:
            idx = 1
        
        while idx < len(rev_days) and rev_days[idx]["count"] > 0:
            current_streak += 1
            idx += 1

    return {
        "username": username,
        "avatar_url": f"https://github.com/{username}.png",
        "profile_url": f"https://github.com/{username}",
        "total_last_year": total_last_year,
        "year_commits": year_commits,
        "today_commits": today_commits,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "days": days
    }

if __name__ == "__main__":
    import sys, os
    user = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GH_USERNAME", "octocat")
    data = fetch_contributions(user)
    print(f"User: {data['username']}")
    print(f"Total last year: {data['total_last_year']}")
    print(f"Year to date ({date.today().year}): {data['year_commits']}")
    print(f"Today's commits: {data['today_commits']}")
    print(f"Current streak: {data['current_streak']} days")
    print(f"Longest streak: {data['longest_streak']} days")
    print(f"Days parsed: {len(data['days'])}")
    if data['days']:
        print("Last 3 days:", data['days'][-3:])
