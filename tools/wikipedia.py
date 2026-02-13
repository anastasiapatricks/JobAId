
import requests
from utils import debug


def get_company_summary(company_name: str) -> str:
    """
    Fetch the Wikipedia summary for a company using the REST API, with disambiguation and organization fallback.
    Returns the summary text, or a fallback message.
    """
    def fetch_summary(query):
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query}"
        headers = {"User-Agent": "CompanyInfoFetcher/1.0 (https://example.com)"}
        debug(f"Wikipedia tool: Fetching API URL: {url}")
        r = requests.get(url, headers=headers, timeout=5)
        debug(f"Wikipedia tool: API status code: {r.status_code}")
        if r.status_code == 200:
            return r.json()
        return None

    if not company_name:
        debug("Wikipedia tool: No company provided.")
        return ""

    formatted_name = company_name.strip().replace(" ", "_")
    debug(f"Wikipedia tool: Formatted company name: {formatted_name}")

    # Try direct lookup
    data = fetch_summary(formatted_name)

    # If it's a disambiguation, retry with "(company)"
    if data and data.get("type") == "disambiguation":
        debug("Wikipedia tool: Disambiguation page found, retrying with (company)")
        data = fetch_summary(f"{formatted_name}_(company)")

    # If still nothing, try "(organisation)" or "(organization)"
    if (not data or "extract" not in data or not data["extract"]) and not (data and data.get("type") != "disambiguation"):
        debug("Wikipedia tool: No extract found, trying (organisation) and (organization)")
        data = fetch_summary(f"{formatted_name}_(organisation)")
        if not data or "extract" not in data or not data["extract"]:
            data = fetch_summary(f"{formatted_name}_(organization)")

    # Return the final text if available
    if data and data.get("extract"):
        debug("Wikipedia tool: Successfully retrieved summary extract.")
        return data["extract"]
    else:
        debug("Wikipedia tool: Could not find a Wikipedia introduction for that name.")
        return f"No Wikipedia introduction found for '{company_name}'."