import json

import openai
from jsoncomment import JsonComment

json = JsonComment(json)


def generate_summary(text, prompt):
    """Use OpenAI GPT API to process scrapped ad data."""
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": text},
    ]

    completion = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.2,
        max_tokens=1000,
        stop=None,
        response_format={"type": "json_object"},
    )

    summary = completion.choices[0].message.content.strip()
    return json.loads(summary)
