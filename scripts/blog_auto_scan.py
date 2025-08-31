import argparse
import json
from datetime import datetime
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup


def parse_post_date(text: str) -> Optional[datetime]:
    """Attempt to parse a date string into a datetime object.

    Returns None if parsing fails.
    """
    for fmt in (
        "%Y-%m-%d",
        "%d %B %Y",
        "%B %d, %Y",
        "%d %b %Y",
        "%b %d, %Y",
    ):
        try:
            return datetime.strptime(text.strip(), fmt)
        except ValueError:
            continue
    return None


def extract_posts(url: str) -> List[Dict[str, Optional[str]]]:
    """Fetch a blog URL and extract posts.

    Attempts to scan ``<article>`` elements first; if none found, falls back
    to scanning ``<h2>`` headings. Each post includes a title, publication
    date (if found) and permalink.
    """
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    posts: List[Dict[str, Optional[str]]] = []

    def add_post(title_tag):
        if not title_tag:
            return
        link_tag = title_tag.find("a")
        title = link_tag.get_text(strip=True) if link_tag else title_tag.get_text(strip=True)
        permalink = link_tag["href"] if link_tag and link_tag.has_attr("href") else None

        parent = title_tag if title_tag.name == "article" else title_tag.parent
        time_tag = parent.find("time") if parent else None
        date_text = (
            time_tag.get("datetime")
            if time_tag and time_tag.has_attr("datetime")
            else (time_tag.get_text(strip=True) if time_tag else None)
        )

        posts.append({"title": title, "date": date_text, "url": permalink})

    articles = soup.find_all("article")
    for article in articles:
        heading = article.find(["h1", "h2", "h3", "h4", "h5", "h6"])
        add_post(heading)

    if not posts:
        for h2 in soup.find_all("h2"):
            add_post(h2)

    return posts


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan blogs for recent posts")
    parser.add_argument("urls", nargs="+", help="One or more blog URLs")
    args = parser.parse_args()

    all_posts: List[Dict[str, Optional[str]]] = []
    for url in args.urls:
        all_posts.extend(extract_posts(url))

    data_path = "data/blog_posts.json"
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, ensure_ascii=False, indent=2)

    latest_title = "None"
    latest_date: Optional[datetime] = None
    for post in all_posts:
        if not post["title"]:
            continue
        parsed = parse_post_date(post["date"]) if post["date"] else None
        if parsed and (latest_date is None or parsed > latest_date):
            latest_title = post["title"]
            latest_date = parsed
        elif latest_date is None and latest_title == "None":
            latest_title = post["title"]

    print(f"{len(all_posts)} posts found. Latest: {latest_title}")


if __name__ == "__main__":
    main()
