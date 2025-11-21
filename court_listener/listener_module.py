from bs4 import BeautifulSoup
from urllib.parse import urljoin
from post_crawler.crawler_module import Crawler
import asyncio
import httpx
import os
import re

crawler = Crawler()


class CourtListener:
    court_listener_token = os.getenv("COURTLISTENER_TOKEN")
    court_listener_headers = {
        "Authorization": f"Token {court_listener_token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    }

    async def crawl_court_listener(self, court_listener_url):
        acquired_links = []
        nest_count = 0
        next_results = ""

        async def crawl_opinions(url=court_listener_url):
            nonlocal acquired_links, nest_count, next_results
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(url, headers=self.court_listener_headers)
                    response.raise_for_status()
                    if response.status_code == 200:
                        opinions_object = response.json()
                        opinions_urls = [
                            url["absolute_url"] for url in opinions_object["results"]
                        ]
                        acquired_links.extend(opinions_urls)
                        self.store_opinions_links(opinions_urls)

                        next_results = opinions_object.get("next")
                        if opinions_object and next_results:
                            print(
                                f"Current Page Nest Count: {nest_count}. \nLast Link In Page: {opinions_urls[-1]}"
                            )
                            nest_count += 1
                            await asyncio.sleep(1)
                            print(f"Next URL: {next_results}")
                            await crawl_opinions(next_results)

                        if not next_results:
                            return {
                                "Status Code": response.status_code,
                                "Message": "The Crawl Is Complete. Check Opinions File With: (/view_opinions/)",
                            }

                    to_return = (
                        "You're Getting This Because The Response Isn't The Expected."
                        if response.status_code != 200
                        else acquired_links
                    )
                    return {"Status Code": response.status_code, "Message": to_return}

                except httpx.HTTPError as error:
                    if next_results:
                        self.store_opinions_links(next=next_results)
                    error_response = {
                        "error": f"An HTTP Error Occurred: {error}",
                        "message": (
                            f"Next Page Link Stored For Continuation."
                            if next_results
                            else None
                        ),
                    }
                    print(error_response)
                    return error_response

                except Exception as error:
                    print({"error": f"An Error Occurred: {error}"})
                    return {"error": f"An Error Occurred: {error}"}

        return await crawl_opinions()

    async def scrape_consumed_opinions(self, opinion):
        url = "https://www.courtlistener.com"
        complete_url = urljoin(url, opinion)

        print(f"\n>>> Scraping: {complete_url}")
        page = await crawler.fetch_data(complete_url, self.court_listener_headers)
        await asyncio.sleep(5)
        print(f">>>>>>> Scraping Complete <<<<<<<\n")

        if isinstance(page, str):
            await self.process_opinions_download(page)
        else:
            self.store_opinions_pages(opinion, page)
            return "Page Not Retrieved."

    def store_opinions_links(self, links=None, next=None):
        if links and not next:
            with open("opinions/opinions.txt", "a") as file:
                if isinstance(links, list):
                    for link in links:
                        file.write(link + "\n")
                else:
                    return "Links Input is not a List."
        else:
            with open("opinions/next.txt", "w") as file:
                file.write(next)

    def get_saved_opinions(self):
        try:
            with open("opinions/opinions.txt", "r") as file:
                opinions = file.readlines()
                opinions = [opinion.strip() for opinion in opinions]
                return {"opinions": list(set(opinions))}
        except FileNotFoundError:
            return {"message": "Opinions Currently Unavailable."}

    def modify_opinion_filename(self, name):
        return re.sub(r'[<>:"/\\|?*]', "_", name)

    def store_opinions_pages(self, name, page):
        directories = "opinions/pages/"
        os.makedirs(directories, exist_ok=True)

        if isinstance(page, str):
            with open(
                f"opinions/pages/{self.modify_opinion_filename(name)}.txt", "w"
            ) as file:
                file.write(page)
        else:
            with open("opinions/error.txt", "a") as file:
                file.write(name + "\n")

    async def process_opinions_download(self, page):
        directories = "opinions/downloads/"
        os.makedirs(directories, exist_ok=True)
        pdf_links = []

        try:
            parsed_page = BeautifulSoup(page, "html.parser")
            page_links = parsed_page.find_all("a")
            for link in page_links:
                href = link.get("href")
                if (
                    href
                    and href.startswith("https://storage.courtlistener.com/")
                    and href.endswith(".pdf")
                ):
                    pdf_links.append(href)
        except Exception as exp:
            print(f"There was an Exception With The Download Process: {exp}")

        await self.download_opinions(pdf_links)

        print("Process Complete, Check Logs For More Information.")
        return

    async def download_opinions(self, links):
        if links:
            async with httpx.AsyncClient() as client:
                try:
                    for link in links:
                        response = await client.get(
                            link, headers=self.court_listener_headers
                        )
                        response.raise_for_status()
                        filename = link.split("/")[-1]
                        if self.check_existence("downloaded", filename):
                            print(f"File //{filename}// Already Downloaded.")
                            return
                        
                        with open(f"opinions/downloads/{filename}", "wb") as file:
                            file.write(response.content)

                        with open(f"opinions/downloaded.txt", "a") as file:
                            file.write(filename + "\n")

                        print(f"File //{filename}// Downloaded.")

                except httpx.HTTPError as error:
                    print(f"An HTML Error Occurred: {error}")

                except Exception as exp:
                    print(f"An Exception Occurred: {exp}")

    def check_existence(self, filename, opinion):
        try:
            with open(f"opinions/{filename}.txt", "r") as file:
                opinions = file.readlines()
                opinions = [opinion.strip() for opinion in opinions]
                if opinion in opinions:
                    return True
                return False
        except FileNotFoundError:
            print(f"{filename} File Currently Unavailable.")
            return False
