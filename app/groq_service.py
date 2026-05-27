from app.bot_instance import groq_client
from app.config import GROQ_MODEL, TEMPERATURE, MAX_TOKENS


def ask_groq(messages):
    completion = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS
    )

    response = completion.choices[0].message.content
    return response.replace("**", "")