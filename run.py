# .env file se API keys aur environment variables load karne ke liye
import os
from dotenv import load_dotenv

# .env file ki values environment mein load karta hai
load_dotenv()
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Debug mode is opt-in; never expose the interactive debugger by default.
    app.run(debug=os.getenv("FLASK_DEBUG", "false").strip().lower() == "true")
