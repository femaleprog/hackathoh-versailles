import os
import requests

# Replace with your API key
API_KEY = os.getenv("GOOGLE_API_KEY")


def search_places_in_versailles(
    query,
    fields: list[str] = ["places.displayName", "places.formattedAddress", "places.id"],
):
    if "Versailles" not in query:
        query += ", Versailles"

    url = "https://places.googleapis.com/v1/places:searchText"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": ",".join(fields),
    }

    payload = {"textQuery": query}

    response = requests.post(url, json=payload, headers=headers)
    return response.json()["places"][0]


def get_best_route_between_places(
    places: list[str], starting_place: str = None, finishing_place: str = None
):
    if starting_place is None:
        starting_place = places[0]
    if finishing_place is None:
        finishing_place = str(starting_place)

    interim_places = [
        place for place in places if place not in (starting_place, finishing_place)
    ]

    # Prepare the request to the Routes API
    routes_url = "https://routes.googleapis.com/directions/v2:computeRoutes"

    routes_headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline,routes.legs.steps",
    }

    routes_payload = {
        "origin": {"placeId": starting_place},
        "destination": {"placeId": finishing_place},
        "intermediates": [{"placeId": place} for place in interim_places],
        "travelMode": "WALK",
    }

    routes_response = requests.post(
        routes_url, json=routes_payload, headers=routes_headers
    )
    return routes_response.json()


if __name__ == "__main__":

    ALL_PLACES = [
        "Les Jardins",
        "Le Domaine de Trianon",
        "La Grande Écurie",
        "La Petite Écurie",
        "La galerie des Carrosses",
        "La galerie des Sculptures et des Moulages",
        "La Salle du Jeu de Paume",
        "Le Grand Trianon",
        "Le Petit Trianon",
        "Le hameau de la Reine",
    ]

    a = search_places_in_versailles(
        "Pavillon des Matelots",
    )

    all_places_with_info = [search_places_in_versailles(place) for place in ALL_PLACES]

    test = [place["id"] for place in all_places_with_info]
    route = get_best_route_between_places(test)
    print(1)
