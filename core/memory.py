import json

FILE = "data/chat_history.json"

def save_chat(user, bot):
    with open(FILE, "r") as f:
        data = json.load(f)

    data.append({"user": user, "bot": bot})

    with open(FILE, "w") as f:
        json.dump(data, f, indent=2)
