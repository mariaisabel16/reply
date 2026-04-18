# Hero Flow: From Raw Data to Structured User Profile

This document outlines the main workflow for processing raw, scraped user data and storing it in a structured format in our S3 database.

## The Two-Agent-Process

The core of our data pipeline is a two-step process that ensures data quality and structure.

### Step 1: Data Scraping (First Agent / Webcrawler)

1.  **Action**: A webcrawler or a similar data gathering tool scrapes user information from various sources (e.g., university portals).
2.  **Output**: The raw data is saved as individual, potentially messy and unstructured JSON files.
3.  **Storage**: These files are placed in the `/TemporaryUserInfoFiles` directory, acting as a staging area.

**Example Raw File (`MockUser.json`):**
```json
{
  "userId": "tum_12345",
  "personal_info": {
    "firstName": "Max",
    "lastName": "Mustermann"
  },
  "study_details": {
    "university": "Technische Universität München",
    "program": "Informatik",
    "current_semester": 5
  },
  "grades": {
    "totalECTS": 120,
    "courses_passed": [
      {"id": "IN0001", "name": "Einführung in die Informatik"},
      {"id": "MA0001", "name": "Lineare Algebra"}
    ]
  },
  "irrelevant_data": "some_random_login_token_or_html_snippet"
}
```

---

### Step 2: Intelligent Structuring & Upload (Second Agent / `workflow.py`)

This is where the magic happens. The `workflow.py` script acts as our second, intelligent agent.

1.  **Trigger**: The workflow is initiated.
2.  **Action**: The script iterates through all JSON files in the `/TemporaryUserInfoFiles` directory.
3.  **Intelligence**: For each file, it invokes our **Bedrock Agent** with a specific prompt (`SYSTEM_PROMPT_FILTER_STATIC_USER_DATA`).
    - The agent's task is to read the messy JSON and extract **only the predefined static user fields** (like `userId`, `firstName`, `totalECTS`, `passedModules`).
    - All irrelevant or dynamic information is discarded.
4.  **Output**: The Bedrock Agent returns a clean, structured JSON object.
5.  **Storage**: This clean JSON object is then uploaded to the S3 bucket (`metadaten-tum-hackathon-reply-top90`) following a strict path convention: `users/{userId}.json`.

**Example Structured File (in S3):**
```json
{
    "userId": "tum_12345",
    "firstName": "Max",
    "lastName": "Mustermann",
    "university": "Technische Universität München",
    "studyProgram": "Informatik",
    "totalECTS": 120,
    "passedModules": [
        {
            "moduleId": "IN0001",
            "moduleName": "Einführung in die Informatik"
        },
        {
            "moduleId": "MA0001",
            "moduleName": "Lineare Algebra"
        }
    ]
}
```

This ensures that our S3 `users/` directory contains only high-quality, consistently structured data, ready for use by the main CampusPilot application.
