from pydantic import BaseModel
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import asyncio
import time
import re
from fastapi import APIRouter
from .crawler_module import Crawler
from database import Functions

app = APIRouter()
crawler = Crawler()
db_func = Functions()

# Crawler Test Route
@app.get("/crawler/check")
async def crawl_checker():
    crawled = [
        {
            "title": "USCIS Issues New Guidance on EB-1 Eligibility Criteria for Individuals with Extraordinary Ability",
            "release_date": "10/02/2024",
            "content": "U.S. Citizenship and Immigration Services is issuing policy guidance in our Policy Manual to further clarify the types of evidence that we may evaluate to determine eligibility for extraordinary ability (E11) EB-1 immigrant visa classifications.This policy guidance:Confirms that we consider a person’s receipt of team awards under the criterion for lesser nationally or internationally recognized prizes or awards for excellence in the field of endeavor;Clarifies that we consider past memberships under the membership criterion;Removes language suggesting published material must demonstrate the value of the person’s work and contributions to satisfy the published material criterion; andExplains that while the dictionary defines an “exhibition” as a public showing not limited to art, the relevant regulation expressly modifies that term with “artistic,” such that we will only consider non-artistic exhibitions as part of a properly supported claim of comparable evidence.This new guidance builds on a previous EB-1 policy update, providing more clarity and transparency to assist petitioners in submitting appropriate evidence that may establish the beneficiary’s eligibility.This policy update is effective immediately and is controlling and supersedes any related prior guidance on the topic. For more information, see the Policy Manual, Volume 6, Part F, Chapter 2.",
            "last_updated": "10/02/2024",
            "link": "https://www.uscis.gov/newsroom/alerts/uscis-issues-new-guidance-on-eb-1-eligibility-criteria-for-individuals-with-extraordinary-ability",
        }
    ]
    print(f"Crawled Data: {crawled}")
    return "Information: Crawler Routes Are Active."


@app.get("/crawler/crawl-uscis")
async def crawl_uscis():
    uscis_url = "https://www.uscis.gov/newsroom/all-news"
    try:
        uscis_page = await crawler.fetch_data(uscis_url)
        parsed_page = BeautifulSoup(uscis_page, "html.parser")
        parsed_urls = parsed_page.find_all("a")

        recent_posts_links, recent_posts = [], []

        for anchor in parsed_urls:
            href = anchor.get("href")
            if href and (
                href.startswith("/newsroom/alerts")
                or href.startswith("/newsroom/news-releases")
            ):
                href = urljoin(uscis_url, href)
                recent_posts_links.append(href)

        for post_link in recent_posts_links:
            print(f">>>Saving Post From: {post_link}")

            blog_page = await crawler.fetch_data(post_link)
            blog_parse = BeautifulSoup(blog_page, "html.parser")
            blog_post = blog_parse.find("article").text

            data = blog_post.strip()
            re_data = re.split(r"\n+", data)
            title = re_data[0]
            release_date = re_data[2].strip()
            content = re_data[3]
            last_updated = re_data[5].strip()

            recent_posts.append(
                {
                    "title": title,
                    "release_date": release_date,
                    "content": content,
                    "last_updated": last_updated,
                    "link": post_link,
                }
            )

            time.sleep(1)

        return db_func.save_crawler_data(recent_posts)

    # Handle Errors/Exceptions
    except Exception as error:
        return {"error": f"An Error Occurred: {error}"}


@app.get("/crawler/data/get-crawled")
async def get_crawled_data():
    crawled_data = db_func.retrieve_crawler_data()
    return crawled_data


@app.get("/crawler/data/get-prompted")
async def get_prompted_crawled_data():
    prompted_crawled_data = db_func.get_prompted_crawled_data()
    return prompted_crawled_data


@app.get("/crawler/data/get-unprompted")
async def get_unprompted_crawled_data():
    unprompted_crawled_data = db_func.get_unprompted_crawled_data()
    return unprompted_crawled_data


class CrawlPostUpdate(BaseModel):
    id: str
    prompted: bool


@app.put("/crawler/post/update-status")
async def change_crawled_post_status(
    payload: CrawlPostUpdate,
):
    post = db_func.update_prompted_status(data_id=payload.id, prompted=payload.prompted)
    if not post:
        return {"status_code": 404, "error": "Post Not Found"}

    return post

@app.get("/crawler/uscis-news/crawl")
async def crawl_uscis_news_links():
    uscis_url = "https://www.uscis.gov/newsroom/all-news"
    news_links = []

    try:
        async def crawl_news_links(url=uscis_url):
            page = await crawler.fetch_data(url)
            content = BeautifulSoup(page, "html.parser")
            if isinstance(content, dict):
                print(f"Page Fetch Error.")
            next = content.find("a", {"aria-label": "Next page"})
            parsed_urls = content.find_all("a")

            for anchor in parsed_urls:
                href = anchor.get("href")

                if href and (
                    href.startswith("/newsroom/alerts")
                    or href.startswith("/newsroom/news-releases")
                ):
                    href = urljoin(uscis_url, href)
                    if isinstance(href, str):
                        news_links.append(href)
                    print(f"HREF: {href}")

                    with open("uscis_news/news.txt", "a") as file:
                        file.write(href + "\n")

            if next:
                await asyncio.sleep(3)
                print(f"Now Crawling: {urljoin(uscis_url, next.get('href'))}")
                await crawl_news_links(urljoin(uscis_url, next.get("href")))
            else:
                print(f"No Next For Now.")
                return {"News Links": news_links}

        return await crawl_news_links()

    except Exception as error:
        return {"error": f"An Error Occurred: {error}"}


@app.get("/crawler/uscis-news/scrape")
async def scrape_uscis_news():
    news_links = crawler.get_news_links()
    if isinstance(news_links, list):
        scraped_news = crawler.get_scraped_news()

        try:
            for news in news_links:
                news = await crawler.fetch_data(news)
                if isinstance(news, dict):
                    print({"Message": "News Page Not Retrieved.", "Link": news})
                    continue
                
                news_parse = BeautifulSoup(news, "html.parser")
                news_article: str = news_parse.find("article").text

                article = news_article.strip()

                article = re.split(r"\n+", article)
                news_title = article[0]

                modify_title = lambda title: re.sub(r'[<>:"/\\|?*]', "_", title)

                if news_title not in scraped_news:
                    print(f">>>Saving: {modify_title(news_title)}")
                    with open(
                        f"uscis_news/downloads/{modify_title(news_title)}.txt", "w"
                    ) as file:
                        file.writelines(news_article)

                    with open("uscis_news/downloaded.txt", "a") as file:
                        file.write(f"{modify_title(news_title)}.txt \n")

                else:
                    print(f">>>Skipping(Already Saved): {modify_title(news_title)}")
                await asyncio.sleep(3)

        except Exception as error:
            return {"error": f"An Error Occurred: {error}"}

    print(f"Process Complete! Check Files For Details.")
    return {"Crawled News Links": news_links}
