import json
import logging
import os
from typing import List, Literal, Optional

import requests
from dotenv import load_dotenv
from langfuse import Langfuse, observe
from pydantic import BaseModel, Field

load_dotenv()

# Replace with your API key
API_KEY = os.getenv("GOOGLE_API_KEY")


PlaceField = Literal["places.displayName", "places.formattedAddress", "places.id"]


class SearchPlaceToolParams(BaseModel):
    query: str = Field(..., description="The query to search for")
    fields: Optional[List[PlaceField]] = Field(
        default=["places.displayName", "places.formattedAddress", "places.id"],
        description="List of fields to return",
    )


@observe(name="search_places_in_versailles")
def search_places_in_versailles(
    query: str,
    fields: list[PlaceField] = [
        "places.displayName",
        "places.formattedAddress",
        "places.id",
    ],
):
    """
    Search for places in Versailles using the Google Places API.
    This function queries Google Places API with the provided search term,
    automatically appending "Versailles" to the query if it's not already included.
    Args:
        query (str): The search query to find places in Versailles.
        fields (list[PlaceField], optional): The fields to include in the response.
            Defaults to display name, formatted address, and place ID.
    Returns:
        dict: The first place result from the API response containing the requested fields.
    Raises:
        KeyError: If the API response doesn't contain 'places' or the array is empty.
        requests.exceptions.RequestException: If the API request fails.
    """
    if "Versailles" not in query:
        query += ", Versailles"

    params = SearchPlaceToolParams(query=query, fields=fields)

    url = "https://places.googleapis.com/v1/places:searchText"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": ",".join(params.fields),
    }

    payload = {"textQuery": params.query}

    response = requests.post(url, json=payload, headers=headers)

    json_response = response.json()["places"]
    if len(json_response) == 1:
        final_answer = json_response[0]
    else:
        final_answer = json_response[0]
        final_answer["warning"] = (
            "Multiple results found, returning the first one. Handle with care"
        )
    return json.dumps(final_answer)


class RouteToolParams(BaseModel):
    places: List[str] = Field(
        ..., description="List of place IDs to include in the route"
    )
    starting_place: Optional[str] = Field(
        default=None,
        description="Place ID for the starting point. If None, first place in the list will be used",
    )
    finishing_place: Optional[str] = Field(
        default=None,
        description="Place ID for the destination. If None, same as starting place",
    )


@observe(name="get_best_route_between_places")
def get_best_route_between_places(places: list[str]):
    """
    Calculates the walking route between multiple places in the given order.

    This function does not optimize the route; it follows the order of places
    as they appear in the input list.

    Args:
        places (list[str]): An ordered list of place names to visit.

    Returns:
        dict: The route information from the API response, including duration,
              distance, polyline data, and detailed steps for each leg.

    Raises:
        requests.exceptions.RequestException: If the API request fails.
        ValueError: If fewer than two valid places are found.
    """

    print("Getting route between places in the given order:", places)
    places_with_details = {
        place: json.loads(search_places_in_versailles(place)) for place in places
    }

    # Filter out places that were not found, while preserving the original order
    ordered_valid_places = [
        p for p in places if "warning" not in places_with_details[p]
    ]

    not_found_places = [p for p in places if "warning" in places_with_details[p]]
    if not_found_places:
        logging.warning(
            "Some places were not found and will be skipped: %s", not_found_places
        )

    if len(ordered_valid_places) < 2:
        raise ValueError("At least two valid places are required to calculate a route.")

    # Define the route's origin, destination, and intermediate waypoints
    starting_place_name = ordered_valid_places[0]
    finishing_place_name = ordered_valid_places[-1]
    interim_places_names = ordered_valid_places[1:-1]

    # Prepare the request to the Routes API
    routes_url = "https://routes.googleapis.com/directions/v2:computeRoutes"

    routes_headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        # Field mask updated to remove optimization-related fields
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline,routes.legs.steps",
    }

    routes_payload = {
        "origin": {"placeId": places_with_details[starting_place_name]["id"]},
        "destination": {"placeId": places_with_details[finishing_place_name]["id"]},
        "travelMode": "WALK",
    }

    # Add intermediate waypoints to the payload if they exist
    if interim_places_names:
        routes_payload["intermediates"] = [
            {"placeId": places_with_details[place]["id"]}
            for place in interim_places_names
        ]

    # Make the API request
    routes_response = requests.post(
        routes_url, json=routes_payload, headers=routes_headers
    )
    routes_response.raise_for_status()  # Raise an exception for HTTP errors
    json_response = routes_response.json()

    if not json_response.get("routes"):
        return {"error": "No route could be calculated for the given places."}

    # Annotate the response legs with the original place names for clarity
    for i, leg in enumerate(json_response["routes"][0]["legs"]):
        leg["startPlaceDetails"] = ordered_valid_places[i]
        leg["endPlaceDetails"] = ordered_valid_places[i + 1]

    return json_response


@observe(name="get_weather_in_versailles")
def get_weather_in_versailles(n_days: int):
    # Google Weather API endpoint for Versailles
    url = "https://weather.googleapis.com/v1/forecast/days:lookup"

    # Coordinates for Versailles, France
    params = {
        "key": API_KEY,
        "location.latitude": 48.8049,
        "location.longitude": 2.1204,
        "days": n_days,
    }

    response = requests.get(url, params=params)
    return response.json()


if __name__ == "__main__":
    ALL_PLACES = [
        "La Grande Écurie",
        "La Petite Écurie",
        "La galerie des Sculptures et des Moulages",
        "La Salle du Jeu de Paume",
        "Le Petit Trianon",
        "Le hameau de la Reine",
    ]

    route = get_best_route_between_places(ALL_PLACES)

    a = search_places_in_versailles(
        "Pavillon des Matelots",
    )

    all_places_with_info = [search_places_in_versailles(place) for place in ALL_PLACES]

    test = [place["id"] for place in all_places_with_info]

    get_weather_in_versailles(1)
