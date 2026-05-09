import json
import os

FILE = "data/chat.json"

def save_chat(user, bot):
    if not os.path.exists("data"):
        os.makedirs("data")

    if not os.path.exists(FILE):
        with open(FILE, "w") as f:
            json.dump([], f)

    with open(FILE, "r") as f:
        chats = json.load(f)

    chats.append({"user": user, "bot": bot})

    with open(FILE, "w") as f:
        json.dump(chats, f, indent=2)
