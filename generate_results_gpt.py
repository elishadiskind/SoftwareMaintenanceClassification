import openai
import json


with open("config.json", "r") as f:
    config = json.load(f)
openai.api_key = config.get("openai_token")

# static survey
SURVEY_TEXT = """
You are an expert in software maintenance. Classify commit messages into one of the following categories:

- Corrective
- Adaptive
- Perfective
- Preventive
- Development

Respond using only ONE word. Below is the guiding survey used internally by the team:

1. Does the change fix a bug or issue?
2. Does it adapt the system to a new environment?
3. Does it improve performance, maintainability, or SEO?
4. Does it aim to prevent future issues?
5. Is it part of initial development?

[... continue up to question 30 ...]
"""

def classify_commit(commit_message: str, model: str = "gpt-4o") -> str:
    """
    Classify a commit message into one of five software maintenance categories.
    """
    messages = [
        {"role": "system", "content": SURVEY_TEXT},
        {"role": "user", "content": f"Commit: {commit_message}"}
    ]

    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=0  # deterministic output
        )
        classification = response['choices'][0]['message']['content'].strip()
        return classification
    except Exception as e:
        print("Error:", e)
        return "Error"

# Example usage
if __name__ == "__main__":
    commits = [
        "Fix broken login redirect after token expiry",
        "Upgrade Node.js version to support new deployment environment",
        "Refactor CSS to improve performance and mobile responsiveness",
        "Add monitoring to detect potential DB failures",
        "Build new onboarding flow for merchants"
    ]

    for commit in commits:
        result = classify_commit(commit)
        print(f"Commit: {commit}\n→ Category: {result}\n")
