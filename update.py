# -*- coding: utf-8 -*-
import os
import sys
import datetime
import requests

# =========================================================
# 仅使用这两个环境变量（GitHub Actions Secrets）
# =========================================================
USERNAME = os.getenv("MY_GITHUB_USERNAME")
TOKEN = os.getenv("MY_GITHUB_PAT")

TOP_REPO_NUM = int(os.getenv("TOP_REPO_NUM", "10"))
RECENT_REPO_NUM = int(os.getenv("RECENT_REPO_NUM", "10"))

SHOW_TOP_LANGS = (
    os.getenv("SHOW_TOP_LANGS", "false").strip().lower()
    in ("1", "true", "yes", "y")
)

# 你已经确认的自部署卡片地址
STATS_BASE = "https://github-readme-stats-phi-rouge.vercel.app"
STREAK_BASE = "https://github-readme-streak-stats-delta-green.vercel.app"

STATIC_SKILL_ICONS = os.getenv(
    "SKILL_ICONS_STATIC",
    "https://skillicons.dev/icons?i="
    "c,cpp,go,py,html,css,js,nodejs,java,md,"
    "pytorch,tensorflow,flask,fastapi,express,qt,react,"
    "cmake,docker,git,linux,nginx,mysql,redis,sqlite,"
    "githubactions,vercel,visualstudio,vscode"
)


def log(*args):
    print("[UPDATE_PROFILE]", *args, flush=True)


def headers():
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    return h


def get_json(url, tag):
    log(f"GET {tag}: {url}")
    r = requests.get(url, headers=headers(), timeout=30)
    log(f" -> status={r.status_code}")
    if r.status_code != 200:
        log(r.text[:300])
        r.raise_for_status()
    return r.json()


# =========================================================
# 拉取仓库
# =========================================================
def fetch_all_repos(username: str):
    repos, page = [], 1
    base = "https://api.github.com/user/repos"
    extra = "&visibility=all&affiliation=owner,collaborator,organization_member&sort=updated"

    while True:
        url = f"{base}?per_page=100&page={page}{extra}"
        data = get_json(url, f"repos_page_{page}")
        if not data:
            break
        repos.extend(data)
        page += 1

    log(f"total repos fetched = {len(repos)}")
    return repos


def parse_iso(s: str) -> datetime.datetime:
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def fmt_dt(dt: datetime.datetime):
    human = dt.strftime("%Y-%m-%d %H:%M:%S")
    slug = human.replace("-", "--").replace(" ", "-").replace(":", "%3A")
    return human, slug


# =========================================================
# 渲染 README
# =========================================================
def render(username: str, repos: list) -> str:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cache_bust = now.replace("-", "").replace(":", "").replace(" ", "")

    processed = []
    for r in repos:
        pushed = r.get("pushed_at") or r.get("updated_at") or r.get("created_at")
        dt = parse_iso(pushed)
        human, slug = fmt_dt(dt)

        processed.append({
            "name": r["name"],
            "url": r["html_url"],
            "desc": (r.get("description") or "").replace("|", "\\|"),
            "stars": r["stargazers_count"],
            "dt": dt,
            "human": human,
            "slug": slug,
            "private": r["private"],
            "fork": r["fork"],
        })

    public = [r for r in processed if not r["private"]]
    top = sorted(public, key=lambda x: x["stars"], reverse=True)[:TOP_REPO_NUM]
    recent = sorted(public, key=lambda x: x["dt"], reverse=True)[:RECENT_REPO_NUM]

    stats_url = (
        f"{STATS_BASE}/api"
        f"?username={username}"
        f"&show_icons=true"
        f"&include_all_commits=true"
        f"&count_private=true"
        f"&hide_border=true"
        f"&theme=github_dark"
        f"&v={cache_bust}"
    )

    streak_url = (
        f"{STREAK_BASE}/"
        f"?user={username}"
        f"&theme=github-dark"
        f"&hide_border=true"
        f"&v={cache_bust}"
    )

    top_langs_url = (
        f"{STATS_BASE}/api/top-langs/"
        f"?username={username}"
        f"&layout=compact"
        f"&langs_count=10"
        f"&hide_border=true"
        f"&theme=github_dark"
        f"&v={cache_bust}"
    )

    md = f"""## Abstract
<p>
  <img src="{stats_url}" width="58%" />
  <img src="{streak_url}" width="40%" />
</p>
"""

    if SHOW_TOP_LANGS:
        md += f"""
<p>
  <img src="{top_langs_url}" width="45%" />
</p>
"""

    md += f"""
<p>
  <img src="https://github-readme-activity-graph.vercel.app/graph?username={username}&theme=github&v={cache_bust}" width="100%" />
</p>

<p>
  <img src="https://github-profile-trophy.vercel.app/?username={username}&theme=gruvbox&row=1&column=7&v={cache_bust}" width="100%" />
</p>

![skills]({STATIC_SKILL_ICONS})

## Top Projects
| Project | Description | Stars |
|:--|:--|:--|
"""

    for r in top:
        name = f"{r['name']}{' (fork)' if r['fork'] else ''}"
        md += f"|[{name}]({r['url']})|{r['desc']}|`{r['stars']}⭐`|\n"

    md += """
## Recent Updates
| Project | Description | Last Update |
|:--|:--|:--|
"""

    for r in recent:
        name = f"{r['name']}{' (fork)' if r['fork'] else ''}"
        md += f"|[{name}]({r['url']})|{r['desc']}|![{r['human']}](https://img.shields.io/badge/{r['slug']}-brightgreen?style=flat-square)|\n"

    md += f"\n*Last updated on: {now}*\n"
    return md


def main():
    if not USERNAME or not TOKEN:
        print(
            "ERROR: Please set MY_GITHUB_USERNAME and MY_GITHUB_PAT in repository secrets.",
            file=sys.stderr,
        )
        sys.exit(2)

    repos = fetch_all_repos(USERNAME)
    md = render(USERNAME, repos)

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(md)

    log("WRITE README.md -> OK")


if __name__ == "__main__":
    main()