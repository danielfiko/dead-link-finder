import asyncio
import httpx
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

load_dotenv()

# Maksimalt antall samtidige forespørsler
MAX_CONCURRENT_REQUESTS = 10  # Set the maximum number of concurrent requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

BASE_URL = os.environ["BASE_URL"]
ARTICLES_URL = os.environ["ARTICLES_URL"]


# Asynkron funksjon for HTTP-forespørsler
async def fetch(url, semaphore):
    async with semaphore:
        async with httpx.AsyncClient(headers=HEADERS) as client:
            response = await client.get(url)
            return response


# Asynkron funksjon for å skrape elementer fra nettsiden
async def scrape_items(url, item_tag, item_class, link_tag):
    # Opprett en Semaphore for å kontrollere antall samtidige HTTP-forespørsler
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    html_content = await fetch(url, semaphore)
    soup = BeautifulSoup(html_content, 'html.parser')

    # Finn elementer basert på tag og klasse
    if item_class:
        item_elements = soup.find_all(item_tag, class_=item_class)
    else:
        item_elements = soup.find_all(item_tag)

    not_found_counter = 0
    tasks = []

    # Gå gjennom hvert element og lag oppgaver for asynkrone skraping av lenker
    for item_element in item_elements:
        link_elements = item_element.find_all(link_tag)
        number_of_link_elements = len(link_elements)

        for index, link_element in enumerate(link_elements, start=1):
            article_url = BASE_URL + link_element['href']
            h3_text = item_element.find('h3').get_text(separator=' ', strip=True)
            h3_text += f" {index}" if number_of_link_elements > 1 else ""
            tasks.append((h3_text, article_url))
            print(f"Fant {h3_text}")

    # Asynkrone skraping av lenker
    responses = await asyncio.gather(*(fetch(url, semaphore) for _, url in tasks))

    # Gå gjennom resultatene og sjekk statuskoder, skriv ut manglende artikler
    for (h3_text, url), response in zip(tasks, responses):
        if response.status_code != 200:
            print(h3_text, end=" ")
            print(f"({url})")
            not_found_counter += 1

    print(f"Fant ikke {not_found_counter} av {len(item_elements)} artikler.")


def main():
    print("Sjekker artikler:")
    asyncio.run(scrape_items(ARTICLES_URL, 'app-article-item', None, 'a'))


if __name__ == "__main__":
    main()
