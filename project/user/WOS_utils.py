# project/user/WOS_utils.py
import requests
import json
import logging
from django.conf import settings

API_KEY = getattr(settings, "WOS_API_KEY", None)
BASE_URL = "https://api.clarivate.com/api/wos"

def search_paper_and_citations(title):
    """
    Search a paper in Web of Science Expanded via POST request.
    Falls back to Topic Search (TS) if Title Search (TI) fails.
    Returns (citation_count, UID) or (None, None) if not found.
    """
    if not API_KEY:
        raise ValueError("WOS_API_KEY not set in Django settings.")

    headers = {
        "X-ApiKey": API_KEY,
        "Content-Type": "application/json"
    }

    for query_type in ["TI", "TS"]:  # Try exact title, then topic search
        payload = {
            "databaseId": "WOS",
            "usrQuery": f"{query_type}=({title})",
            "count": 5,
            "firstRecord": 1,
            "sortField": "LD+D",
            "viewField": "UID,citation_related",
            "optionView": "FULL"
        }

        try:
            response = requests.post(BASE_URL, headers=headers, json=payload)
            response.raise_for_status()
        except requests.HTTPError as e:
            return None, None

        data = response.json()

        # Safely extract records
        records = data.get("Data", {}).get("Records", {}).get("records", [])
        if isinstance(records, list):  # Sometimes WOS returns {} instead of []
            records = []

        if len(records) > 0:
            record = records[0]
            ut = record.get("UID")

            citation_count = (
                record.get("dynamic_data", {})
                      .get("citation_related", {})
                      .get("tc_list", {})
                      .get("silo_tc", [{}])[0]
                      .get("local_count", 0)
            )
            return citation_count, ut

    return None, None


def list_papers_from_wos(query, count=5):
    """
    Search Web of Science Expanded via POST and return a list of papers.
    Each paper dict contains title, UID, and citation count.
    """
    if not API_KEY:
        raise ValueError("WOS_API_KEY not set in Django settings.")

    headers = {
        "X-ApiKey": API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "databaseId": "WOS",
        "usrQuery": f"TS=({query})",  # Topic Search for broader match
        "count": count,
        "firstRecord": 1,
        "sortField": "LD+D",
        "viewField": "UID,summary,citation_related",
        "optionView": "FULL"
    }

    try:
        response = requests.post(BASE_URL, headers=headers, json=payload)
        response.raise_for_status()
    except requests.HTTPError:
        return []

    data = response.json()
    records = data.get("Data", {}).get("Records", {}).get("records", [])
    if isinstance(records, dict):
        records = []

    papers = []
    for rec in records:
        title = ""
        try:
            title = rec["title"]["title"][0]["value"]
        except (KeyError, IndexError, TypeError):
            title = "Untitled"

        citation_count = (
            rec.get("dynamic_data", {})
               .get("citation_related", {})
               .get("tc_list", {})
               .get("silo_tc", [{}])[0]
               .get("local_count", 0)
        )

        papers.append({
            "title": title,
            "uid": rec.get("UID"),
            "citations": citation_count
        })

    return papers




# Set up logging for better error messages
logging.basicConfig(level=logging.INFO, format='%(message)s')


def search_papers_wos(query, count=10, field="TS"):
    """
    Searches for papers on the Web of Science API and returns a list of dictionaries.
    """
    if not API_KEY or API_KEY == "YOUR_WOS_API_KEY":
        raise ValueError("WOS_API_KEY not set or is a placeholder.")

    headers = {"X-ApiKey": API_KEY}
    usr_query = f'{field}=("{query}")'

    params = {
        "databaseId": "WOS",
        "lang": "en",
        "usrQuery": usr_query,
        "count": count,
        "firstRecord": 1,
        "sortField": "LD+D",
        "optionView": "FR"
    }

    try:
        response = requests.get(BASE_URL, headers=headers, params=params)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred: {e}")
        return []

    data = response.json()

    records = data.get("Data", {}).get("Records", {}).get("records", [])

    logging.info("\n-------- RAW records from WOS ---------\n")
    # For demonstration, we'll use the provided snippet as a single record
    # In a real scenario, this would be a list of dicts from the API
    if isinstance(records, dict):
        logging.info(json.dumps(records, indent=2))

    # The issue was here. The original code incorrectly checked for a dict.
    # The API response is structured as a list of records.
    if not isinstance(records, list):
        logging.error("Expected a list of records from the API, but got a different type.")
        return []
    
    papers = []
    for rec in records:
        title = extract_title(rec)
        citations = (
            rec.get("dynamic_data", {})
               .get("citation_related", {})
               .get("tc_list", {})
               .get("silo_tc", [{}])[0]
               .get("local_count", 0)
        )
        papers.append({
            "title": title,
            "uid": rec.get("UID"),
            "citations": citations
        })

    logging.info("\n-------- Parsed Paper (First Record Only) ---------\n")
    if papers:
        logging.info(json.dumps(papers[0], indent=2))
    else:
        logging.info("No papers were found or parsed.")

    return papers

def extract_title(rec):
    """Safely extract the main title from a WOS record."""
    if not isinstance(rec, dict):
        return "Untitled"

    titles = (
        rec.get("static_data", {})
           .get("summary", {})
           .get("titles", {})
           .get("title", [])
    )
    print(titles)

    if isinstance(titles, list):
        for t in titles:
            if isinstance(t, dict) and t.get("type") == "item":
                return t.get("content", "Untitled")
        if titles and isinstance(titles[0], dict):
            return titles[0].get("content", "Untitled")

    return "Untitled"

# Mocking a call to the function with a single record for demonstration
# In a real scenario, this part would be replaced by an actual API call.
# The following code simulates the issue in the original code
# by feeding it the provided JSON snippet.
mock_data = {
    "Data": {
        "Records": {
            "records": [
                {
                    "static_data": {
                        "summary": {
                            "titles": {
                                "title": [
                                    {
                                        "type": "item",
                                        "content": "Explainable machine learning (XML) imaging: A radiomics pipeline for visualizing and explaining complex prediction models"
                                    }
                                ]
                            }
                        }
                    },
                    "dynamic_data": {
                        "citation_related": {
                            "tc_list": {
                                "silo_tc": [
                                    { "local_count": 30 },
                                    { "local_count": 0 }
                                ]
                            }
                        }
                    },
                    "UID": "WOS:000827219900001"
                }
            ]
        }
    }
}

# Simulating the function call with the mock data to show the corrected logic in action.
# This part is just for demonstration and not part of the function itself.
print("--- Simulating the corrected function's output ---")
try:
    # A simplified version of the function that uses the mock data
    class MockResponse:
        def json(self):
            return mock_data
        def raise_for_status(self):
            pass
    
    class MockRequests:
        def get(self, url, headers, params):
            return MockResponse()

    # Temporarily replace the requests module with our mock
    original_requests = requests
    requests = MockRequests()
    
    search_papers_wos(query="explainable machine learning imaging")
    
    # Restore the original requests module
    requests = original_requests
    
except ValueError as e:
    print(f"Error: {e}")