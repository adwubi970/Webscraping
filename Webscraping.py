from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import csv
import json
import re

URL = "https://www.bbc.com/news/articles/crmddnge9yro"

def clean(s):
    if s is None:
        return None
    s = re.sub(r"\s+", " ", s).strip()
    return s if s else None

def first_text(soup, selectors):

    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            return clean(el.get_text(" ", strip=True))
    return None

def meta_content(soup, *, name=None, prop=None):
    """Return content from <meta name=...> or <meta property=...>."""
    if name:
        tag = soup.find("meta", attrs={"name": name})
    else:
        tag = soup.find("meta", attrs={"property": prop})
    if tag and tag.get("content"):
        return clean(tag.get("content"))
    return None

def extract_article_body(soup):
    container_selectors = [
        "article",
        '[data-testid="article-body"]',
        ".article-body",
        ".article-content",
        ".content-body",
        ".entry-content",
        "#article-body",
        "#main-content article",
        "main article",
    ]

    container = None
    for sel in container_selectors:
        container = soup.select_one(sel)
        if container:
            break

    if not container:
        return None

    paragraphs = container.select("p")
    texts = []
    for p in paragraphs:
        t = clean(p.get_text(" ", strip=True))
        if not t:
            continue
        
        if t.lower() in {"advertisement", "related resources"}:
            continue
        texts.append(t)

    if not texts:
       
        return clean(container.get_text(" ", strip=True))

    return "\n\n".join(texts)


def save_json(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_csv(data, filename):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=data.keys())
        w.writeheader()
        w.writerow(data)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            locale="en-US"
        )
        page = context.new_page()

        page.route(
            "**/*",
            lambda route: route.abort()
            if route.request.resource_type in ("image", "font", "media")
            else route.continue_()
        )

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)

        try:
            page.wait_for_selector("h1", timeout=30000)
        except Exception:
            pass 

        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    
    title = first_text(soup, ["h1"]) or meta_content(soup, prop="og:title") or meta_content(soup, name="title")

    author = (
        meta_content(soup, name="author")
        or meta_content(soup, prop="article:author")
        or first_text(soup, [
            ".author-name",
            ".byline .name",
            ".byline",
            "[data-testid='author-name']",
            "span[itemprop='name']",
        ])
    )

    published = (
        meta_content(soup, prop="article:published_time")
        or meta_content(soup, name="pubdate")
        or meta_content(soup, name="date")
        or first_text(soup, [
            "time[datetime]",
            "time",
            ".date",
            ".published-date",
            "[data-testid='publish-date']",
        ])
    )

    description = meta_content(soup, name="description") or meta_content(soup, prop="og:description")

    
    body = extract_article_body(soup)

    data = {
        "url": URL,
        "headline": title,
        "author": author,
        "published_date": published,
        "description": description,
        "body": body,
    }

    
    print("\n--- EXTRACTED ---")
    for k, v in data.items():
        if k == "body" and v:
            print(f"{k}: {v[:400]}{'...' if len(v) > 400 else ''}")
        else:
            print(f"{k}: {v}")

    save_json(data, "techtarget_article.json")
    save_csv(data, "techtarget_article.csv")
    print("\nSaved -> techtarget_article.json and techtarget_article.csv")

if __name__ == "__main__":
    main()
