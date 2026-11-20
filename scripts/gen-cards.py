#!/usr/bin/env python3
"""生成 GitHub 个人主页统计卡片 SVG

数据全部来自 GitHub API，输出静态 SVG 并提交到本仓库，
因此不再依赖任何第三方 Vercel 实例，页面不会再因为公共实例下线而挂图

用法:
    GITHUB_TOKEN=<pat> python3 scripts/gen-cards.py
可选环境变量:
    GH_LOGIN    目标用户名，默认 LanRhyme
    CARDS_OUT   输出目录，默认 assets
"""

import datetime
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
LOGIN = os.environ.get("GH_LOGIN", "LanRhyme")
OUT_DIR = pathlib.Path(os.environ.get("CARDS_OUT", "assets"))

BG = "#0d1117"
TITLE = "#8a9a70"
TEXT = "#e8f0d8"
ICON = "#6b7e4f"
RING = "#4a5a35"

FONT = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,"
        "sans-serif,'Apple Color Emoji','Segoe UI Emoji'")

CARD_W = 467
CARD_H = 195
PAD = 25
RADIUS = 12

ICONS = {
    "star": ("M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279"
             "l-3.046 2.97.719 4.192a.75.75 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1"
             "-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"),
    "commit": ("M11.93 8.5a4.002 4.002 0 0 1-7.86 0H.75a.75.75 0 0 1 0-1.5h3.32a4.002 4.002 0 0 1"
               " 7.86 0h3.32a.75.75 0 0 1 0 1.5h-3.32Z"),
    "pr": ("M1.5 3.25a2.25 2.25 0 1 1 3 2.122v5.256a2.251 2.251 0 1 1-1.5 0V5.372A2.25 2.25 0 0 1 1.5 3.25Z"
           "m2.25 -.75a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm-.75 9a.75.75 0 1 0 1.5 0 .75.75 0 0 0-1.5 0Z"
           "M11 2.5H9.573l1 1H11a1 1 0 0 1 1 1v5.628a2.251 2.251 0 1 0 1.5 0V4.5A2.5 2.5 0 0 0 11 2.5Z"
           "m1 9.5a.75.75 0 1 0 1.5 0 .75.75 0 0 0-1.5 0Z"),
    "issue": ("M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3ZM8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0ZM1.5 8"
              "a6.5 6.5 0 1 1 13 0 6.5 6.5 0 0 1-13 0Z"),
    "repo": ("M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5"
             "a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Z"
             "m10.5-1V9h-8c-.856 0-1.654.288-2.289.772a1 1 0 0 0-.211.228V2.5a1 1 0 0 1 1-1h9.5Z"),
}

LANG_QUERY = """
query ($login: String!) {
  user(login: $login) {
    login
    name
    createdAt
    repositoriesContributedTo(first: 1, includeUserRepositories: true) { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes {
        name
        stargazerCount
        isFork
        languages(first: 12, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

REPOS_QUERY = """
query ($login: String!, $cursor: String) {
  user(login: $login) {
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        name
        stargazerCount
        languages(first: 12, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

CONTRIB_QUERY = """
query ($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def _http(url, data=None):
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "lanrhyme-readme-cards",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode()
    req = urllib.request.Request(url, data=data, headers=headers)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")[:300]
            if exc.code in (403, 429) and attempt < 3:
                import time
                time.sleep(5 * (attempt + 1))
                continue
            raise SystemExit(f"GitHub API {exc.code} {url}: {body}")
    raise SystemExit(f"GitHub API 请求失败: {url}")


def gql(query, variables):
    payload = _http(f"{API}/graphql", {"query": query, "variables": variables})
    if "errors" in payload:
        raise SystemExit(f"GraphQL 错误: {payload['errors']}")
    return payload["data"]


def search_total(query):
    url = f"{API}/search/issues?per_page=1&q={urllib.parse.quote(query)}"
    return _http(url).get("total_count", 0)


def streak_stats(day_counts, created, today):
    """按贡献日历算总贡献、当前连续天数与历史最长连续天数"""
    days = {datetime.date.fromisoformat(k): v for k, v in day_counts.items()}
    one_day = datetime.timedelta(days=1)

    total = sum(days.values())

    end = today if days.get(today, 0) > 0 else today - one_day
    start = end
    while days.get(start, 0) > 0:
        start -= one_day
    current_start = start + one_day
    current = {
        "length": max((end - current_start).days + 1, 0),
        "start": current_start.isoformat(),
        "end": end.isoformat(),
    }

    longest = {"length": 0, "start": today.isoformat(), "end": today.isoformat()}
    run_start = None
    previous = None
    for day in sorted(days):
        if days[day] <= 0:
            run_start = None
            previous = None
            continue
        if run_start is None or previous is None or day - previous > one_day:
            run_start = day
        run_length = (day - run_start).days + 1
        if run_length > longest["length"]:
            longest = {"length": run_length, "start": run_start.isoformat(), "end": day.isoformat()}
        previous = day
    if current["length"] > longest["length"] and current["length"] > 0:
        longest = dict(current)

    return {"total": total, "since": created.isoformat(),
            "current": current, "longest": longest}


def fmt_range(start_iso, end_iso, none_text="—"):
    if not start_iso or not end_iso:
        return none_text
    start = datetime.date.fromisoformat(start_iso)
    end = datetime.date.fromisoformat(end_iso)
    if start > end:
        return none_text
    if start.year == end.year:
        return f"{start.strftime('%b')} {start.day} - {end.strftime('%b')} {end.day}"
    return f"{start.strftime('%b')} {start.day}, {start.year} - {end.strftime('%b')} {end.day}, {end.year}"


def collect():
    profile = gql(LANG_QUERY, {"login": LOGIN})["user"]
    repos = list(profile["repositories"]["nodes"])
    cursor = profile["repositories"]["pageInfo"]["endCursor"]
    has_next = profile["repositories"]["pageInfo"]["hasNextPage"]
    while has_next:
        page = gql(REPOS_QUERY, {"login": LOGIN, "cursor": cursor})["user"]["repositories"]
        repos.extend(page["nodes"])
        cursor = page["pageInfo"]["endCursor"]
        has_next = page["pageInfo"]["hasNextPage"]

    stars = 0
    languages = {}
    for repo in repos:
        stars += repo["stargazerCount"]
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            bucket = languages.setdefault(name, {"size": 0, "color": edge["node"]["color"] or ICON})
            bucket["size"] += edge["size"]
            if edge["node"]["color"]:
                bucket["color"] = edge["node"]["color"]

    created = datetime.datetime.fromisoformat(profile["createdAt"].replace("Z", "+00:00"))
    now = datetime.datetime.now(datetime.timezone.utc)
    commits = 0
    day_counts = {}
    for year in range(created.year, now.year + 1):
        start = datetime.datetime(year, 1, 1, tzinfo=datetime.timezone.utc)
        end = min(datetime.datetime(year, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc), now)
        if end <= start:
            continue
        collection = gql(CONTRIB_QUERY, {
            "login": LOGIN,
            "from": start.isoformat().replace("+00:00", "Z"),
            "to": end.isoformat().replace("+00:00", "Z"),
        })["user"]["contributionsCollection"]
        commits += collection["totalCommitContributions"] + collection["restrictedContributionsCount"]
        for week in collection["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                day_counts[day["date"]] = day["contributionCount"]

    prs = search_total(f"author:{LOGIN} type:pr")
    issues = search_total(f"author:{LOGIN} type:issue")

    return {
        "login": profile["login"],
        "name": profile["name"] or profile["login"],
        "repos": len(repos),
        "stars": stars,
        "commits": commits,
        "prs": prs,
        "issues": issues,
        "contributed": profile["repositoriesContributedTo"]["totalCount"],
        "languages": sorted(languages.items(), key=lambda kv: (-kv[1]["size"], kv[0].lower())),
        "streak": streak_stats(day_counts, created.date(), now.date()),
    }


def esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def svg_open(title_text, height):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{height}" \
viewBox="0 0 {CARD_W} {height}" fill="none" role="img" aria-label="{esc(title_text)}">
  <title>{esc(title_text)}</title>
  <rect x="0.5" y="0.5" width="{CARD_W - 1}" height="{height - 1}" rx="{RADIUS}" ry="{RADIUS}" \
fill="{BG}" stroke="{RING}" stroke-opacity="0.35"/>
"""


def text(x, y, value, size=14, weight=400, fill=TEXT, anchor="start", opacity=1.0):
    extra = f' text-anchor="{anchor}"' if anchor != "start" else ""
    op = f' fill-opacity="{opacity}"' if opacity != 1.0 else ""
    return (f'  <text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}"{op}{extra}>{esc(value)}</text>\n')


def icon(name, x, y, size=15, color=ICON, opacity=1.0):
    path = ICONS[name]
    op = f' fill-opacity="{opacity}"' if opacity != 1.0 else ""
    return (f'  <g transform="translate({x},{y}) scale({size / 16})">'
            f'<path d="{path}" fill="{color}"{op}/></g>\n')


def render_stats(data):
    rows = [
        ("star", "Total Stars", data["stars"]),
        ("commit", "Total Commits", data["commits"]),
        ("pr", "Total Pull Requests", data["prs"]),
        ("issue", "Total Issues", data["issues"]),
        ("repo", "Contributed to", data["contributed"]),
    ]
    title = f"{data['name']}'s GitHub Stats"
    out = [svg_open(title, CARD_H)]
    out.append(text(PAD, 35, title, size=18, weight=600, fill=TITLE))
    out.append(f'  <line x1="{PAD}" y1="48" x2="{CARD_W - PAD}" y2="48" stroke="{RING}" '
               f'stroke-opacity="0.5" stroke-width="1"/>\n')
    y = 72
    for key, label, value in rows:
        out.append(icon(key, PAD, y - 12, size=15))
        out.append(text(PAD + 22, y, label, size=13, fill=TEXT, opacity=0.92))
        out.append(text(CARD_W - PAD, y, f"{value:,}", size=13, weight=600, anchor="end"))
        y += 27
    out.append("</svg>\n")
    return "".join(out)


def render_langs(data, limit=6):
    langs = data["languages"][:limit]
    total = sum(item["size"] for _, item in data["languages"]) or 1
    title = "Most Used Languages"
    out = [svg_open(title, CARD_H)]
    out.append(text(PAD, 35, title, size=18, weight=600, fill=TITLE))
    out.append(f'  <line x1="{PAD}" y1="48" x2="{CARD_W - PAD}" y2="48" stroke="{RING}" '
               f'stroke-opacity="0.5" stroke-width="1"/>\n')
    y = 72
    for name, meta in langs:
        pct = meta["size"] / total * 100
        out.append(f'  <circle cx="{PAD + 5}" cy="{y - 4}" r="5" fill="{esc(meta["color"])}"/>\n')
        out.append(text(PAD + 20, y, name, size=13, fill=TEXT, opacity=0.92))
        out.append(text(CARD_W - PAD, y, f"{pct:.2f}%", size=13, weight=600, anchor="end"))
        y += 23
    out.append("</svg>\n")
    return "".join(out)


def render_streak(data):
    streak = data["streak"]
    since = datetime.date.fromisoformat(streak["since"])
    columns = [
        ("Total Contributions", f'{streak["total"]:,}',
         f"Since {since.strftime('%b')} {since.day}, {since.year}"),
        ("Current Streak", f'{streak["current"]["length"]:,}',
         fmt_range(streak["current"]["start"], streak["current"]["end"])),
        ("Longest Streak", f'{streak["longest"]["length"]:,}',
         fmt_range(streak["longest"]["start"], streak["longest"]["end"])),
    ]
    title = "Contribution Streak"
    out = [svg_open(title, CARD_H)]
    out.append(text(PAD, 35, title, size=18, weight=600, fill=TITLE))
    out.append(f'  <line x1="{PAD}" y1="48" x2="{CARD_W - PAD}" y2="48" stroke="{RING}" '
               f'stroke-opacity="0.5" stroke-width="1"/>\n')
    span = (CARD_W - 2 * PAD) / len(columns)
    for index, (label, value, dates) in enumerate(columns):
        center = PAD + span * index + span / 2
        if index:
            x = PAD + span * index
            out.append(f'  <line x1="{x:.1f}" y1="62" x2="{x:.1f}" y2="152" stroke="{RING}" '
                       f'stroke-opacity="0.5" stroke-width="1"/>\n')
        out.append(text(center, 108, value, size=28, weight=700, fill=TITLE, anchor="middle"))
        out.append(text(center, 132, label, size=13, weight=600, anchor="middle"))
        out.append(text(center, 152, dates, size=10.5, anchor="middle", opacity=0.65))
    out.append("</svg>\n")
    return "".join(out)


def main():
    if not TOKEN:
        raise SystemExit("缺少 GITHUB_TOKEN")
    data = collect()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "stats.svg").write_text(render_stats(data), encoding="utf-8")
    (OUT_DIR / "top-langs.svg").write_text(render_langs(data), encoding="utf-8")
    (OUT_DIR / "streak.svg").write_text(render_streak(data), encoding="utf-8")
    summary = {k: v for k, v in data.items() if k != "languages"}
    summary["languages"] = [(n, m["size"]) for n, m in data["languages"][:6]]
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
