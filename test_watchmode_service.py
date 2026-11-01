
from app.services.watchmode_service import get_streaming_sources

# Interstellar ka Watchmode ID.
TITLE_ID = 1184713


def main():
    try:
        sources = get_streaming_sources(TITLE_ID, region="IN")

        print(f"Unique streaming sources: {len(sources)}")

        for source in sources:
            print(
    source["platform"],
    "|",
    source["availability_label"],
    "|",
    source["url"] or "Link unavailable",
)

    except Exception as error:
        print("Streaming source test failed:", error)


if __name__ == "__main__":
    main()
