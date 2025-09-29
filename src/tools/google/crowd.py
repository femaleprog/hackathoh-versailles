import os
import requests
from enum import Enum
import logging

from pydantic import BaseModel, Field
from typing import Optional, List
from typing import Literal

# Replace with your API key
API_KEY = os.getenv("GOOGLE_API_KEY")


PlaceField = Literal["places.displayName", "places.formattedAddress", "places.id"]


class SearchPlaceToolParams(BaseModel):
    query: str = Field(..., description="The query to search for")
    fields: Optional[List[PlaceField]] = Field(
        default=["places.displayName", "places.formattedAddress", "places.id"],
        description="List of fields to return",
    )


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
    return final_answer


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


def get_best_route_between_places(places: list[str]):
    """
    Calculate the optimal walking route between multiple places using Google Routes API.

    Args:
        places (list[str]): List of Google Place IDs to visit.
        starting_place (str, optional): Place ID for the starting point.
            If None, uses the first place in the list.
        finishing_place (str, optional): Place ID for the destination.
            If None, returns to the starting place.

    Returns:
        dict: The route information from the API response including duration,
              distance, polyline data and detailed steps.

    Raises:
        requests.exceptions.RequestException: If the API request fails.
    """

    places_with_details = {
        place: search_places_in_versailles(place) for place in places
    }

    used_places = {k: v for k, v in places_with_details.items() if "warning" not in v}
    forgotten_places = {k: v for k, v in places_with_details.items() if "warning" in v}

    logging.warning("Some places were not found: %s", forgotten_places)

    starting_place = str(list(used_places.keys())[0])
    finishing_place = str(list(used_places.keys())[0])

    interim_places = [
        place
        for place in used_places.keys()
        if place not in (starting_place, finishing_place)
    ]

    # Prepare the request to the Routes API
    routes_url = "https://routes.googleapis.com/directions/v2:computeRoutes"

    routes_headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline,routes.legs.steps,routes.optimized_intermediate_waypoint_index",
    }

    routes_payload = {
        "origin": {"placeId": used_places[starting_place]["id"]},
        "destination": {"placeId": used_places[finishing_place]["id"]},
        "intermediates": [
            {"placeId": used_places[place]["id"]} for place in interim_places
        ],
        "travelMode": "WALK",
        "optimizeWaypointOrder": True,
    }

    routes_response = requests.post(
        routes_url, json=routes_payload, headers=routes_headers
    )

    json_response = routes_response.json()

    optimized_waypoints = json_response["routes"][0].get(
        "optimizedIntermediateWaypointIndex"
    )
    optimized_waypoints_names = [interim_places[i] for i in optimized_waypoints]
    sublegs = [(starting_place, optimized_waypoints_names[0])]
    for i in range(len(optimized_waypoints_names) - 1):
        sublegs.append((optimized_waypoints_names[i], optimized_waypoints_names[i + 1]))
    sublegs.append((optimized_waypoints_names[-1], finishing_place))

    for leg, (tmp_start, tmp_end) in zip(json_response["routes"][0]["legs"], sublegs):
        leg["startPlaceDetails"] = tmp_start
        leg["endPlaceDetails"] = tmp_end

    return json_response


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
