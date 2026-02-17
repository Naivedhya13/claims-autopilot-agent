from __future__ import annotations
import json
from typing import Type
from openai import OpenAI
from .config import SETTINGS

client = OpenAI(api_key=SETTINGS.openai_api_key)

def call_json(system: str, user: str, output_model: Type):
    model = SETTINGS.model

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    content = resp.choices[0].message.content or "{}"
    data = json.loads(content)
    return output_model.model_validate(data)