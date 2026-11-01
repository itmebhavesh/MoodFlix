
import os
import requests
from dotenv import load_dotenv

# .env file se API key load karo
load_dotenv()

# OMDb API key read karo
api_key = os.getenv("OMDB_API_KEY")

# API key available hai ya nahi, check karo
if not api_key:
    print("OMDb API key nahi mili. .env file check karo.")
else:
    # Interstellar ki movie details maango
    url = "https://www.omdbapi.com/"

    params = {
        "apikey": api_key,
        "t": "Interstellar",
        "plot": "short",
    }

    try:
        # OMDb server ko request bhejo
        response = requests.get(url, params=params, timeout=15)

        # HTTP response check karo
        response.raise_for_status()

        # JSON response ko Python dictionary mein badlo
        data = response.json()

        if data.get("Response") == "True":
            print("OMDb API connected successfully!")
            print("Title:", data.get("Title"))
            print("Year:", data.get("Year"))
            print("IMDb Rating:", data.get("imdbRating"))
            print("Actors:", data.get("Actors"))
            print("Rotten Tomatoes:", [
                rating["Value"]
                for rating in data.get("Ratings", [])
                if rating.get("Source") == "Rotten Tomatoes"
            ])
        else:
            print("OMDb API error:", data.get("Error"))

    except requests.RequestException as error:
        print("Connection error:", error)
