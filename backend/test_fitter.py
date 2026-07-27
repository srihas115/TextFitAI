import httpx


CASES = [
    {
        "name": "shorten",
        "payload": {
            "text": "I am writing to say that, in my personal opinion, this proposal is really quite useful because it gives teams a simple way to communicate priorities, reduce confusion, and make decisions without requiring several long meetings every single week.",
            "max_words": 24,
            "min_words": None,
            "min_chars": None,
            "max_chars": None,
        },
    },
    {
        "name": "lengthen",
        "payload": {
            "text": "The launch went well and users responded positively.",
            "min_words": 26,
            "max_words": 34,
            "min_chars": None,
            "max_chars": None,
        },
    },
    {
        "name": "tight character range",
        "payload": {
            "text": "TextFitAI keeps copy aligned with strict layout limits while preserving meaning.",
            "min_words": None,
            "max_words": None,
            "min_chars": 95,
            "max_chars": 110,
        },
    },
]


def main() -> None:
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=120) as client:
        for case in CASES:
            response = client.post("/fit", json=case["payload"])
            response.raise_for_status()
            data = response.json()
            print(
                f"{case['name']}: attempts={data['attempts']}, "
                f"met_target={data['met_target']}, words={data['word_count']}, chars={data['char_count']}"
            )
            print(data["result"])
            print()


if __name__ == "__main__":
    main()
