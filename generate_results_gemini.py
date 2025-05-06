from google.generativeai import GenerativeModel, configure
import os
import json

# Configure API key
with open("config.json", "r") as f:
    config = json.load(f)
token = config.get("google_token")
configure(api_key=os.environ.get(token))

# Initialize the Gemini 2.0 Flash-Lite model
model = GenerativeModel("gemini-2.0-flash-lite")

# Define the classification categories
categories = ["Corrective", "Adaptive", "Perfective", "Preventive", "Development"]

def classify_commit(survey_result, commit_message):
    """Classifies a commit message based on a survey result."""
    prompt = f"""You are an expert at classifying software development commits based on a survey result and the commit message.
    Classify the following commit message into one of these categories: {', '.join(categories)}.
    Provide your answer as a single word representing the category.

    Survey Result:
    {survey_result}

    Commit Message:
    {commit_message}

    Classification:
    """
    try:
        response = model.generate_content([prompt])
        if response.text:
            # Extract the first word as the classification
            classification = response.text.strip().split()[0]
            if classification in categories:
                return classification
            else:
                return "Unknown"
        else:
            return "No response"
    except Exception as e:
        print(f"Error during classification: {e}")
        return "Error"

def classify_multiple_commits(commits_data, sample_survey_result):
    """Classifies a list of commits."""
    results = {}
    for commit_message in commits_data:
        classification = classify_commit(sample_survey_result, commit_message)
        results[commit_message] = classification
    return results

if __name__ == "__main__":
    # Example usage:
    sample_survey = """
    Our frontend team needs the old React app converted into a Next.js app, keeping all the business logic intact, but improving SEO and performance.
    *
    Corrective
    Adaptive
    Perfective
    Preventive
    Development
    """
    list_of_commits = [
        "Fix: User login button not working on Safari.",
        "Refactor: Improve data fetching efficiency in the user profile page.",
        "Feat: Implement email notification for new sign-ups.",
        "Docs: Update API documentation for the authentication endpoints.",
        "Security: Harden against potential CSRF attacks.",
        "Chore: Upgrade react-router-dom dependency to the latest version."
    ]

    classified_commits = classify_multiple_commits(list_of_commits, sample_survey)

    for commit, classification in classified_commits.items():
        print(f"Commit: '{commit}' -> Classification: {classification}")