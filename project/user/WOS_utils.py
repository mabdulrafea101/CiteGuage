# project/user/WOS_utils.py
import requests
import json
import os
import logging
import datetime
from django.conf import settings

# API Config
API_KEY = getattr(settings, "WOS_API_KEY", None)
BASE_URL = "https://api.clarivate.com/api/wos"

# Logging setup
logging.basicConfig(format="%(message)s", level=logging.INFO)


# --------------------------
# Helper Functions
# --------------------------

def build_usr_query(field, query):
    """Builds the Web of Science query string."""
    return f'{field}=("{query}")'


def build_params(field, query, count):
    """Builds API request parameters."""
    return {
        "databaseId": "WOS",
        "lang": "en",
        "usrQuery": build_usr_query(field, query),
        "count": count,
        "firstRecord": 1,
        "sortField": "TC+D",  # Latest date descending
        "optionView": "FR"
    }


def call_wos_api(params):
    """Performs GET request to the WOS API and returns parsed JSON."""
    if not API_KEY or API_KEY == "YOUR_WOS_API_KEY":
        raise ValueError("WOS_API_KEY not set or is a placeholder.")

    headers = {"X-ApiKey": API_KEY}
    try:
        response = requests.get(BASE_URL, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"WOS API request failed: {e}")
        return {}
    except ValueError:
        logging.error("WOS API did not return valid JSON")
        return {}


def normalize_records(data):
    """
    Extracts and normalizes records into a list from WOS API response.
    Returns [] if structure is unexpected.
    """
    records_data = data.get("Data", {}).get("Records", {}).get("records", {})
    records = []

    if isinstance(records_data, list):
        records = records_data
    elif isinstance(records_data, dict):
        records = records_data.get("REC", [])
    elif isinstance(records_data, str):
        records_data = records_data.strip()
        if records_data:
            try:
                parsed = json.loads(records_data)
                if isinstance(parsed, list):
                    records = parsed
                elif isinstance(parsed, dict):
                    records = parsed.get("REC", [])
            except json.JSONDecodeError as e:
                logging.error(f"Failed to decode JSON string for records: {e}")
    else:
        logging.warning(f"Unexpected records_data type: {type(records_data)}")

    return records


def save_records(records):
    """Saves raw records to a timestamped JSON file in json_data/<date>/."""
    date_dir = datetime.datetime.now().strftime("%Y%m%d")
    raw_dir = os.path.join(os.getcwd(), "json_data", date_dir)
    os.makedirs(raw_dir, exist_ok=True)

    file_path = os.path.join(raw_dir, f"records_{datetime.datetime.now().strftime('%H%M%S')}.json")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=4, ensure_ascii=False)
        logging.info(f"Successfully saved records to: {file_path}")
    except Exception as e:
        logging.error(f"Error saving records to JSON: {e}")


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

    if isinstance(titles, list):
        for t in titles:
            if isinstance(t, dict) and t.get("type") == "item":
                return t.get("content", "Untitled")
    return "Untitled"


def parse_papers(records):
    """Parses list of WOS records into structured paper dictionaries."""
    papers = []
    for rec in records:
        if not isinstance(rec, dict):
            continue
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
    return papers


# --------------------------
# Main Orchestrator Function
# --------------------------

def search_papers_wos(query, count, field):
    """Main function to search WOS and return parsed papers."""
    params = build_params(field, query, count)
    raw_data = call_wos_api(params)

    if not raw_data:
        return []

    records = normalize_records(raw_data)
    logging.info(f"Extracted {len(records)} records from API.")

    save_records(records)

    papers = parse_papers(records)
    logging.info(f"Parsed {len(papers)} papers.")

    return papers
