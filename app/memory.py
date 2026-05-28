user_history = {}


def get_user_history(user_id):
    if user_id not in user_history:
        user_history[user_id] = []

    if len(user_history[user_id]) > 10:
        user_history[user_id] = user_history[user_id][-10:]

    return user_history[user_id]


def add_to_history(user_id, user_question, bot_response):
    if user_id not in user_history:
        user_history[user_id] = []

    user_history[user_id].append(
        {"role": "user", "content": user_question}
    )
    user_history[user_id].append(
        {"role": "assistant", "content": bot_response}
    )


def clear_history(user_id):
    user_history[user_id] = []