import os
import sys
import requests
import logging
from dotenv import load_dotenv

log_format = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=log_format)
logger = logging.getLogger(__name__)

load_dotenv()


def get_jira_session():
    """Create an authenticated Jira session."""
    jira_url = os.getenv("JIRA_URL")
    username = os.getenv("JIRA_USERNAME")
    api_token = os.getenv("JIRA_API_TOKEN")
    if not all([jira_url, username, api_token]):
        logger.error("Jira credentials are missing in .env file")
        sys.exit(1)
    session = requests.Session()
    session.auth = (username, api_token)
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    })
    try:
        response = session.get(f"{jira_url}/rest/api/2/myself")
        response.raise_for_status()
        logger.info(f"Successfully authenticated as {username}")
        return session
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to authenticate with Jira: {e}")
        sys.exit(1)

def get_jira_html_url(issue_key):
    """Generate the URL for exporting an issue as HTML."""
    jira_url = os.getenv("JIRA_URL")
    return f"{jira_url}/si/jira.issueviews:issue-html/{issue_key}/{issue_key}.html"

def fetch_html_content(session, issue_key):
    """Fetch the HTML content of a Jira issue."""
    url = get_jira_html_url(issue_key)
    logger.info(f"Fetching HTML for {issue_key} from {url}")
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        logger.info(f"Successfully fetched HTML for {issue_key}")
        return response.text, url
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch HTML for {issue_key}: {e}")
        return None, None 