# src/tools/schedule_scraper.py

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime


def scrape_versailles_schedule(date_str: str) -> str:
    """
    Scrapes the Château de Versailles agenda page for a given date to get opening hours and events.

    Args:
        date_str (str): The date to scrape in 'YYYY-MM-DD' format.

    Returns:
        str: A JSON string containing the schedule information for different
             locations, or an error message if scraping fails.
    """
    # Validate the date format
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        error_msg = {"error": "Invalid date format. Please use YYYY-MM-DD."}
        return json.dumps(error_msg, indent=4, ensure_ascii=False)

    # Construct the URL based on the provided date
    url = f"https://www.chateauversailles.fr/actualites/agenda-chateau-versailles/fr-{date_str}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        # Send a GET request to the URL
        response = requests.get(url, headers=headers, timeout=10)
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        error_msg = {"error": f"Failed to retrieve the webpage: {e}"}
        return json.dumps(error_msg, indent=4, ensure_ascii=False)

    # Parse the HTML content of the page
    soup = BeautifulSoup(response.content, "html.parser")

    # Find the main content container
    content_container = soup.find("div", class_="view-content")
    if not content_container:
        error_msg = {
            "error": "Could not find the main content container on the page. The page structure may have changed."
        }
        return json.dumps(error_msg, indent=4, ensure_ascii=False)

    schedule_data = []
    # Find all the individual location blocks
    locations = content_container.find_all("div", class_="outer")

    if not locations:
        # Check for a specific "closed" message if available.
        closed_message = soup.find("div", class_="view-empty")
        if closed_message:
            return json.dumps(
                {"status": closed_message.get_text(strip=True)},
                indent=4,
                ensure_ascii=False,
            )
        return json.dumps(
            {"status": "No schedule information found for this date."},
            indent=4,
            ensure_ascii=False,
        )

    # Iterate over each location block to extract information
    for location in locations:
        location_info = {}

        # Extract the name of the location
        title_tag = location.find("h4", class_="title")
        if title_tag and title_tag.a:
            location_info["name"] = title_tag.a.get_text(strip=True)
        else:
            continue

        # Find the div containing hours and attendance
        info_div = location.find("div", class_="info")
        if not info_div:
            location_info["hours"] = "Not specified"
            location_info["details"] = "Not specified"
            schedule_data.append(location_info)
            continue

        # Extract opening hours
        hours_tag = info_div.find("span", class_="hours")
        location_info["hours"] = (
            hours_tag.get_text(strip=True) if hours_tag else "Not specified"
        )

        # Extract attendance or special event details
        details_tag = info_div.find("span", class_=lambda c: c and c != "hours")
        if details_tag:
            if details_tag.has_attr("title") and details_tag["title"]:
                location_info["details"] = details_tag["title"]
            else:
                location_info["details"] = details_tag.get_text(strip=True)
        else:
            location_info["details"] = "Not specified"

        schedule_data.append(location_info)

    return json.dumps(schedule_data, indent=4, ensure_ascii=False)
