import httpx
from datetime import datetime

class Crawler:
    user_agent_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    async def fetch_data(self, url, headers=None):
        async with httpx.AsyncClient() as client:
            try:
                if not headers:
                    headers = self.user_agent_headers

                response = await client.get(url, headers=headers)
                response.raise_for_status()

                print(f"Status Code: {response.status_code}")

                if response.status_code == 200:
                    return response.text
                elif response.status_code == 202:
                    return None

            except httpx.HTTPError as error:
                return {"error": f"An HTTP Error Occurred: {error}"}

            except Exception as error:
                return {"error": f"An Error Occurred: {error}"}

    def get_news_links():
        try:
            with open("uscis_news/news.txt", "r") as file:
                links = file.readlines()
                links = [link.strip() for link in links]

                return links
        except Exception as exp:
            return {"Error": f"An Error Occurred: {exp}"}

    def get_scraped_news():
        try:
            with open("uscis_news/scraped.txt", "r") as file:
                news = file.readlines()
                news = [scraped.strip() for scraped in news]
                return news
        except Exception as exp:
            return {"Error": f"An Error Occurred: {exp}"}
