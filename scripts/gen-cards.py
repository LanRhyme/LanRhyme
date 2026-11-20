#!/usr/bin/env python3
"""生成 GitHub 个人主页统计卡片 SVG

版式对齐 github-readme-stats 与 github-readme-streak-stats 的原始卡片几何
（标题位置、行距、图标、rank 环、语言进度条、连续天数三栏与火焰环）
但数据与渲染全部在本地完成，不依赖任何第三方实例

用法:
    GITHUB_TOKEN=<pat> python3 scripts/gen-cards.py
可选环境变量:
    GH_LOGIN    目标用户名，默认 LanRhyme
    CARDS_OUT   输出目录，默认 assets
"""

import datetime
import json
import math
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
BORDER = "#e4e2e2"
FIRE_ORANGE = "#FB8C00"

FAMILY = "'Segoe UI', Ubuntu, 'Helvetica Neue', Sans-Serif"
STREAK_FAMILY = "'Segoe UI', Ubuntu, sans-serif"

STATS_W, STATS_H = 467, 195
LANGS_W, LANGS_BASE_H = 300, 90
STREAK_W, STREAK_H = 495, 195

# 图标取自 Octicons，与 github-readme-stats 使用的完全一致
ICONS = {
    "star": "M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97"
            ".719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79"
            "l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"
            "m0 2.445L6.615 5.5a.75.75 0 01-.564.41l-3.097.45 2.24 2.184a.75.75 0 01.216.664"
            "l-.528 3.084 2.769-1.456a.75.75 0 01.698 0l2.77 1.456-.53-3.084a.75.75 0 01.216-.664"
            "l2.24-2.183-3.096-.45a.75.75 0 01-.564-.41L8 2.694v.001z",
    "commits": "M1.643 3.143L.427 1.927A.25.25 0 000 2.104V5.75c0 .138.112.25.25.25h3.646"
               "a.25.25 0 00.177-.427L2.715 4.215a6.5 6.5 0 11-1.18 4.458.75.75 0 10-1.493.154"
               " 8.001 8.001 0 101.6-5.684zM7.75 4a.75.75 0 01.75.75v2.992l2.028.812a.75.75 0 01"
               "-.557 1.392l-2.5-1A.75.75 0 017 8.25v-3.5A.75.75 0 017.75 4z",
    "prs": "M7.177 3.073L9.573.677A.25.25 0 0110 .854v4.792a.25.25 0 01-.427.177L7.177 3.427"
           "a.25.25 0 010-.354zM3.75 2.5a.75.75 0 100 1.5.75.75 0 000-1.5zm-2.25.75a2.25 2.25 0 11"
           "3 2.122v5.256a2.251 2.251 0 11-1.5 0V5.372A2.25 2.25 0 011.5 3.25zM11 2.5h-1V4h1a1 1 0 01"
           "1 1v5.628a2.251 2.251 0 101.5 0V5A2.5 2.5 0 0011 2.5zm1 10.25a.75.75 0 111.5 0 .75.75 0 01"
           "-1.5 0zM3.75 12a.75.75 0 100 1.5.75.75 0 000-1.5z",
    "issues": "M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8zm9 3a1 1 0 11"
              "-2 0 1 1 0 012 0zm-.25-6.25a.75.75 0 00-1.5 0v3.5a.75.75 0 001.5 0v-3.5z",
    "contribs": "M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5"
                "a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5"
                "v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8zM5 12.25v3.25a.25.25 0 00.4.2"
                "l1.45-1.087a.25.25 0 01.3 0L8.6 15.7a.25.25 0 00.4-.2v-3.25a.25.25 0 00-.25-.25h-3.5"
                "a.25.25 0 00-.25.25z",
}

FIRE_PATH = ("M 1.5 0.67 C 1.5 0.67 2.24 3.32 2.24 5.47 C 2.24 7.53 0.89 9.2 -1.17 9.2 C -3.23 9.2 -4.79 7.53 -4.79 5.47 "
             "L -4.76 5.11 C -6.78 7.51 -8 10.62 -8 13.99 C -8 18.41 -4.42 22 0 22 C 4.42 22 8 18.41 8 13.99 "
             "C 8 8.6 5.41 3.79 1.5 0.67 Z M -0.29 19 C -2.07 19 -3.51 17.6 -3.51 15.86 C -3.51 14.24 -2.46 13.1 "
             "-0.7 12.74 C 1.07 12.38 2.9 11.53 3.92 10.16 C 4.31 11.45 4.51 12.81 4.51 14.2 C 4.51 16.85 2.36 19 "
             "-0.29 19 Z")

PROFILE_QUERY = """
query ($login: String!) {
  user(login: $login) {
    login
    name
    createdAt
    followers { totalCount }
    repositoriesContributedTo(first: 1, includeUserRepositories: true) { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      totalCount
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
      totalPullRequestReviewContributions
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


def rank_of(stars, commits, prs, issues, reviews, followers, all_commits=True):
    """github-readme-stats 的 rank 算法原样移植"""
    commits_median, commits_weight = (1000, 2) if all_commits else (250, 2)
    prs_median, prs_weight = 50, 3
    issues_median, issues_weight = 25, 1
    reviews_median, reviews_weight = 2, 1
    stars_median, stars_weight = 50, 4
    followers_median, followers_weight = 10, 1
    total_weight = (commits_weight + prs_weight + issues_weight
                    + reviews_weight + stars_weight + followers_weight)

    def ecdf(x):          # 指数分布 CDF
        return 1 - 2 ** -x

    def lncdf(x):         # 对数正态 CDF 近似
        return x / (1 + x)

    rank = 1 - (
        commits_weight * ecdf(commits / commits_median)
        + prs_weight * ecdf(prs / prs_median)
        + issues_weight * ecdf(issues / issues_median)
        + reviews_weight * ecdf(reviews / reviews_median)
        + stars_weight * lncdf(stars / stars_median)
        + followers_weight * lncdf(followers / followers_median)
    ) / total_weight

    thresholds = [1, 12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100]
    levels = ["S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C"]
    percentile = rank * 100
    level = "C"
    for threshold, name in zip(thresholds, levels):
        if percentile <= threshold:
            level = name
            break
    return {"level": level, "percentile": round(percentile, 2)}


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


def collect():
    profile = gql(PROFILE_QUERY, {"login": LOGIN})["user"]
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
            bucket = languages.setdefault(name, {"size": 0, "color": edge["node"]["color"] or "#858585"})
            bucket["size"] += edge["size"]
            if edge["node"]["color"]:
                bucket["color"] = edge["node"]["color"]

    created = datetime.datetime.fromisoformat(profile["createdAt"].replace("Z", "+00:00"))
    now = datetime.datetime.now(datetime.timezone.utc)
    commits = 0
    reviews = 0
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
        reviews += collection["totalPullRequestReviewContributions"]
        for week in collection["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                day_counts[day["date"]] = day["contributionCount"]

    prs = search_total(f"author:{LOGIN} type:pr")
    issues = search_total(f"author:{LOGIN} type:issue")
    followers = profile["followers"]["totalCount"]

    return {
        "login": profile["login"],
        "name": profile["name"] or profile["login"],
        "repos": len(repos),
        "stars": stars,
        "commits": commits,
        "prs": prs,
        "issues": issues,
        "reviews": reviews,
        "followers": followers,
        "contributed": profile["repositoriesContributedTo"]["totalCount"],
        "languages": sorted(languages.items(), key=lambda kv: (-kv[1]["size"], kv[0].lower())),
        "rank": rank_of(stars, commits, prs, issues, reviews, followers),
        "streak": streak_stats(day_counts, created.date(), now.date()),
    }


def esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def k_format(num):
    """github-readme-stats 的 kFormatter：1000 以上压成 6.3k"""
    if abs(num) < 1000:
        return str(int(num))
    return f"{round(abs(num) / 1000, 1):g}k"


def svg_head(width, height, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" fill="none" role="img" aria-label="{esc(label)}">\n'
            f'  <title>{esc(label)}</title>\n')


def text_node(x, y, value, size, weight, fill, anchor=None, baseline=None, family=FAMILY):
    attrs = [f'x="{x}"', f'y="{y}"', f'font-family="{family}"', f'font-size="{size}"',
             f'font-weight="{weight}"', f'fill="{fill}"']
    if anchor:
        attrs.append(f'text-anchor="{anchor}"')
    if baseline:
        attrs.append(f'dominant-baseline="{baseline}" alignment-baseline="{baseline}"')
    return f'<text {" ".join(attrs)}>{esc(value)}</text>\n'


def card_bg(width, height):
    return (f'  <rect x="0.5" y="0.5" rx="12" width="{width - 1}" height="{height - 2}" '
            f'fill="{BG}" stroke="{BORDER}" stroke-opacity="0"/>\n')


def fmt_range(start_iso, end_iso):
    start = datetime.date.fromisoformat(start_iso)
    end = datetime.date.fromisoformat(end_iso)
    if start > end:
        return "—"
    if start.year == end.year:
        return f"{start.strftime('%b')} {start.day} - {end.strftime('%b')} {end.day}"
    return (f"{start.strftime('%b')} {start.day}, {start.year} - "
            f"{end.strftime('%b')} {end.day}, {end.year}")


def render_stats(data):
    """github-readme-stats 的 stats 卡片版式：标题 + 五行 + 右侧 rank 环"""
    rows = [
        ("star", "Total Stars Earned:", k_format(data["stars"])),
        ("commits", "Total Commits:", k_format(data["commits"])),
        ("prs", "Total PRs:", k_format(data["prs"])),
        ("issues", "Total Issues:", k_format(data["issues"])),
        ("contribs", "Contributed to:", k_format(data["contributed"])),
    ]
    title = f"{data['name']}'s GitHub Stats"
    percentile = data["rank"]["percentile"]
    circuit = 2 * math.pi * 40
    dash_offset = circuit - circuit / 100 * (100 - percentile)

    out = [svg_head(STATS_W, STATS_H, title)]
    out.append(card_bg(STATS_W, STATS_H))
    out.append('  <g transform="translate(25, 35)">\n')
    out.append("    " + text_node(0, 0, title, 18, 600, TITLE))
    out.append("  </g>\n")
    out.append('  <g transform="translate(0, 55)">\n')

    # rank 环：外圈 20% 不透明，进度弧 80% 不透明，按 percentile 走线
    out.append('    <g transform="translate(390.5, 47.5)">\n')
    out.append(f'      <circle cx="-10" cy="8" r="40" fill="none" stroke="{TITLE}" '
               f'stroke-width="6" stroke-opacity="0.2"/>\n')
    out.append(f'      <circle cx="-10" cy="8" r="40" fill="none" stroke="{TITLE}" stroke-width="6" '
               f'stroke-opacity="0.8" stroke-linecap="round" stroke-dasharray="250" '
               f'stroke-dashoffset="{dash_offset:.4f}" transform="rotate(-90 -10 8)"/>\n')
    out.append("      " + text_node(-10, 8, data["rank"]["level"], 24, 800, TEXT,
                                    anchor="middle", baseline="central"))
    out.append("    </g>\n")

    for index, (icon, label, value) in enumerate(rows):
        out.append(f'    <g transform="translate(25, {index * 25})">\n')
        out.append(f'      <svg x="0" y="0" width="16" height="16" viewBox="0 0 16 16">'
                   f'<path fill-rule="evenodd" d="{ICONS[icon]}" fill="{ICON}"/></svg>\n')
        out.append("      " + text_node(25, 12.5, label, 14, 700, TEXT))
        out.append("      " + text_node(219.01, 12.5, value, 14, 700, TEXT))
        out.append("    </g>\n")

    out.append("  </g>\n</svg>\n")
    return "".join(out)


def render_langs(data, limit=6):
    """github-readme-stats 的 top-langs compact 版式：进度条 + 两列语言"""
    langs = data["languages"][:limit]
    total = sum(meta["size"] for _, meta in langs) or 1
    count = len(langs)
    height = LANGS_BASE_H + round(count / 2) * 25
    bar_width = LANGS_W - 50
    title = "Most Used Languages"

    out = [svg_head(LANGS_W, height, title)]
    out.append(card_bg(LANGS_W, height))
    out.append('  <g transform="translate(25, 35)">\n')
    out.append("    " + text_node(0, 0, title, 18, 600, TITLE))
    out.append("  </g>\n")
    out.append('  <g transform="translate(0, 55)">\n')

    # 顶部堆叠进度条，段宽按占比 * 可用宽度，最窄 10px
    out.append(f'    <mask id="rect-mask">\n      <rect x="0" y="0" width="{bar_width}" height="8" '
               f'fill="white" rx="5"/>\n    </mask>\n')
    offset = 0.0
    for _, meta in langs:
        span = round(meta["size"] / total * bar_width, 2)
        out.append(f'    <rect mask="url(#rect-mask)" x="{offset:.2f}" y="0" width="{max(span, 10):.2f}" '
                   f'height="8" fill="{esc(meta["color"])}"/>\n')
        offset += span

    out.append('    <g transform="translate(25, 25)">\n')
    chunk = (count + 1) // 2
    columns = [langs[:chunk], langs[chunk:]]
    # 第二列偏移：按最长语言文本宽度估算，最少 150
    longest = max(langs, key=lambda kv: len(kv[0]))
    longest_text = f"{longest[0]} {longest[1]['size'] / total * 100:.2f}%"
    gap = max(150, round(20 + len(longest_text) * 0.53 * 11))
    for column_index, column in enumerate(columns):
        if not column:
            continue
        out.append(f'      <g transform="translate({column_index * gap}, 0)">\n')
        for row_index, (name, meta) in enumerate(column):
            pct = meta["size"] / total * 100
            out.append(f'        <g transform="translate(0, {row_index * 25})">\n')
            out.append(f'          <circle cx="5" cy="6" r="5" fill="{esc(meta["color"])}"/>\n')
            out.append("          " + text_node(15, 10, f"{name} {pct:.2f}%", 11, 400, TEXT))
            out.append("        </g>\n")
        out.append("      </g>\n")
    out.append("    </g>\n")
    out.append("  </g>\n</svg>\n")
    return "".join(out)


def render_streak(data):
    """github-readme-streak-stats 版式：三栏 + 中栏火焰环"""
    streak = data["streak"]
    since = datetime.date.fromisoformat(streak["since"])
    title = "Contribution Streak"
    out = [svg_head(STREAK_W, STREAK_H, title)]
    out.append("  <defs>\n")
    out.append(f'    <clipPath id="outer_rectangle">\n      <rect width="{STREAK_W}" height="{STREAK_H}" '
               'rx="12"/>\n    </clipPath>\n')
    out.append('    <mask id="mask_out_ring_behind_fire">\n'
               f'      <rect width="{STREAK_W}" height="{STREAK_H}" fill="white"/>\n'
               '      <ellipse cx="247.5" cy="32" rx="13" ry="18" fill="black"/>\n'
               "    </mask>\n")
    out.append("  </defs>\n")
    out.append('  <g clip-path="url(#outer_rectangle)">\n')
    out.append(card_bg(STREAK_W, STREAK_H))
    out.append(f'    <line x1="165" y1="28" x2="165" y2="170" stroke="{RING}" stroke-width="1"/>\n')
    out.append(f'    <line x1="330" y1="28" x2="330" y2="170" stroke="{RING}" stroke-width="1"/>\n')

    # 左栏：总贡献
    out.append("    " + text_node(82.5, 80, f'{streak["total"]:,}', 28, 700, ICON,
                                  anchor="middle", family=STREAK_FAMILY))
    out.append("    " + text_node(82.5, 116, "Total Contributions", 14, 400, TEXT,
                                  anchor="middle", family=STREAK_FAMILY))
    out.append("    " + text_node(82.5, 146, f"Since {since.strftime('%b')} {since.day}, {since.year}", 12,
                                  400, TEXT, anchor="middle", family=STREAK_FAMILY))

    # 中栏：当前连续，数字外面套火焰环
    out.append('    <g mask="url(#mask_out_ring_behind_fire)">\n')
    out.append(f'      <circle cx="247.5" cy="71" r="40" fill="none" stroke="{TITLE}" stroke-width="5"/>\n')
    out.append("    </g>\n")
    out.append(f'    <g transform="translate(247.5, 19.5)">\n      <path d="{FIRE_PATH}" fill="{TITLE}"/>\n'
               "    </g>\n")
    out.append("    " + text_node(247.5, 80, f'{streak["current"]["length"]:,}', 28, 700, TEXT,
                                  anchor="middle", family=STREAK_FAMILY))
    out.append("    " + text_node(247.5, 140, "Current Streak", 14, 700, FIRE_ORANGE,
                                  anchor="middle", family=STREAK_FAMILY))
    out.append("    " + text_node(247.5, 166, fmt_range(streak["current"]["start"], streak["current"]["end"]),
                                  12, 400, TEXT, anchor="middle", family=STREAK_FAMILY))

    # 右栏：最长连续
    out.append("    " + text_node(412.5, 80, f'{streak["longest"]["length"]:,}', 28, 700, ICON,
                                  anchor="middle", family=STREAK_FAMILY))
    out.append("    " + text_node(412.5, 116, "Longest Streak", 14, 400, TEXT,
                                  anchor="middle", family=STREAK_FAMILY))
    out.append("    " + text_node(412.5, 146, fmt_range(streak["longest"]["start"], streak["longest"]["end"]),
                                  12, 400, TEXT, anchor="middle", family=STREAK_FAMILY))
    out.append("  </g>\n</svg>\n")
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
