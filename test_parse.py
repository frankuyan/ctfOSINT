import json
import re

def _parse_llm_response(raw: str):
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```\w*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[^{}]+\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"error": "failed"}

print(_parse_llm_response("Here is the JSON:\n```json\n{\"verdict\": \"real\", \"reason\": \"has {nested} braces\"}\n```"))
