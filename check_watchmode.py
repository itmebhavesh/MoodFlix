
import os
import requests
from dotenv import load_dotenv

# .env file se API key load karo
load_dotenv()
api_key = os.getenv("WATCHMODE_API_KEY")

# Interstellar ka Watchmode ID
title_id = 1184713

if not api_key:
    print("Watchmode API key nahi mili. .env file check karo.")

else:
    # Movie ke streaming sources ka endpoint
    url = f"https://api.watchmode.com/v1/title/{title_id}/sources/"

    # India ke streaming sources request karo
    params = {
        "apiKey": api_key,
        "regions": "IN",
    }

    try:
        # API request bhejo
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()

        # JSON response ko Python data mein convert karo
        sources = response.json()

        if not sources:
            print("India ke liye koi streaming source return nahi hua.")

        else:
            print("Watchmode streaming sources fetched successfully!")
            print("Movie: Interstellar")
            print("Country: India")
            print()

            # Har streaming provider ki details dikhao
            for source in sources:
                print("Platform:", source.get("name", "Unknown"))
                print("Availability:", source.get("type", "Unknown"))
                print("Link:", source.get("web_url") or "Not provided")
                print("-" * 35)

    except requests.HTTPError as error:
        print("API HTTP error:", error)
        print("Response:", response.text[:500])

    except requests.RequestException as error:
        print("Connection error:", error)
