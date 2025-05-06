import os
import re
import base64
import logging
import urllib.parse
from bs4 import BeautifulSoup

def read_issue_keys(file_path='keys.txt'):
    """Read Jira issue keys from a file, ignoring comments and empty lines."""
    if not os.path.exists(file_path):
        logging.error(f"Keys file not found: {file_path}")
        with open(file_path, 'w') as f:
            f.write("# Add your Jira issue keys here (one per line)\n")
            f.write("# Lines starting with # are comments and will be ignored\n")
            f.write("# Example:\n")
            f.write("# PROJECT-123\n")
        logging.info(f"Created template {file_path} file. Please add your issue keys and run again.")
        return []
    with open(file_path, 'r') as file:
        lines = file.readlines()
    keys = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            keys.append(line)
    return keys

def extract_issue_details(html_content, issue_key):
    """Extract issue title, sprint, and service ticket from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    # Start with empty title
    title = None
    # PRIMARY METHOD: Extract from title tag, exactly as shown in browser
    title_tag = soup.find('title')
    if title_tag:
        title_text = title_tag.text.strip()
        bracket_match = re.search(r'\[\s*#?(' + re.escape(issue_key) + r')\s*\]\s*(.*?)(?:\s*-\s*Jira)?$', title_text)
        if bracket_match:
            title = bracket_match.group(2).strip()
            logging.info(f"Found title in title tag: {title}")
        elif issue_key in title_text:
            parts = title_text.split(issue_key, 1)
            if len(parts) > 1:
                title = parts[1].strip()
                if title.endswith("- Jira"):
                    title = title[:-7].strip()
                title = re.sub(r'^[\s\-:]+', '', title)
                logging.info(f"Extracted title by splitting on issue key: {title}")
    if not title or not title.strip():
        logging.info("Title tag extraction failed, trying summary field")
        summary_field = soup.find('div', {'id': 'summary-val'}) or soup.find('span', {'id': 'summary-val'})
        if summary_field:
            title = summary_field.text.strip()
            logging.info(f"Found title in summary field: {title}")
    if not title or not title.strip():
        logging.info("Summary field extraction failed, trying headers")
        for header in soup.find_all(['h1', 'h2', 'h3']):
            header_text = header.text.strip()
            if issue_key in header_text and len(header_text) > len(issue_key):
                parts = header_text.split(issue_key, 1)
                if len(parts) > 1:
                    title = parts[1].strip()
                    title = re.sub(r'^[\s\-:]+', '', title)
                    logging.info(f"Found title in header: {title}")
                    break
    if not title or not title.strip():
        logging.warning(f"Could not extract title for {issue_key}, using placeholder")
        title = "Jira Issue"
    sprint = "No Sprint"
    sprint_patterns = [
        r'Sprint:</span>.*?<span[^>]*>(.*?)<',
        r'Sprint:</span>.*?<span[^>]*>(.*?)</span>',
        r'Sprint</span>:.*?<span[^>]*>(.*?)<',
        r'Sprint</span>.*?<span[^>]*>(.*?)</span>',
        r'Sprint:.*?<span[^>]*>(.*?)<',
        r'Sprint:.*?<td[^>]*>(.*?)<'
    ]
    for pattern in sprint_patterns:
        sprint_match = re.search(pattern, html_content, re.DOTALL)
        if sprint_match:
            sprint_value = sprint_match.group(1).strip()
            if sprint_value and not sprint_value.lower() in ['none', '-']:
                sprint = sprint_value
                break
    service_ticket = None
    for row in soup.find_all('tr'):
        tds = row.find_all('td')
        if len(tds) >= 2:
            label = tds[0].get_text(strip=True)
            if label.startswith('Service Ticket #'):
                value = tds[1].get_text(strip=True)
                if value and value.isdigit():
                    service_ticket = value
                    break
    logging.info(f"Extracted details - Issue: {issue_key}, Title: {title}, Sprint: {sprint}, Service Ticket: {service_ticket}")
    return title, sprint, service_ticket

def create_safe_filename(issue_key, title, sprint, service_ticket=None):
    """Create a safe filename from issue key, title, sprint, and service ticket."""
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
    safe_sprint = re.sub(r'[\\/*?:"<>|]', "", sprint)
    safe_ticket = re.sub(r'[\\/*?:"<>|]', "", service_ticket) if service_ticket else None
    if not safe_title.strip():
        safe_title = "Jira Issue"
    if not safe_sprint.strip():
        safe_sprint = "No Sprint"
    if len(safe_title) > 150:
        safe_title = safe_title[:147] + "..."
    if len(safe_sprint) > 30:
        safe_sprint = safe_sprint[:27] + "..."
    if safe_ticket and len(safe_ticket) > 30:
        safe_ticket = safe_ticket[:27] + "..."
    if safe_title.startswith(issue_key):
        safe_title = safe_title[len(issue_key):].strip()
        safe_title = re.sub(r'^[\s\-:]+', '', safe_title)
    filename = f"{issue_key} - {safe_title} - {safe_sprint}"
    if safe_ticket:
        filename += f" - {safe_ticket}"
    if len(filename) > 240:
        filename = filename[:237] + "..."
    return filename

def get_resource_cache():
    """Create a session-wide resource cache to avoid redundant downloads."""
    return {
        'css': {},
        'images': {},
        'resources': {}
    }

def download_and_embed_resource(session, url, base_url, resource_cache):
    """Download a resource and return as a data URL with caching."""
    if url.startswith('data:'):
        return url
    if url.startswith('javascript:'):
        return url
    if not url.startswith(('http://', 'https://')):
        url = urllib.parse.urljoin(base_url, url)
    if url in resource_cache['resources']:
        logging.debug(f"Using cached resource: {url}")
        return resource_cache['resources'][url]
    try:
        logging.debug(f"Downloading resource: {url}")
        response = session.get(url, timeout=30)
        response.raise_for_status()
        content_type = response.headers.get('Content-Type', 'application/octet-stream')
        if 'text/css' in content_type:
            content_type = 'text/css'
        elif any(img_type in content_type for img_type in ['image/png', 'image/jpeg', 'image/gif', 'image/svg+xml']):
            pass
        else:
            content_type = 'application/octet-stream'
        data = base64.b64encode(response.content).decode('utf-8')
        data_url = f"data:{content_type};base64,{data}"
        resource_cache['resources'][url] = data_url
        logging.debug(f"Resource embedded: {url}")
        return data_url
    except Exception as e:
        logging.warning(f"Failed to download resource {url}: {str(e)}")
        return url

def embed_css_resources(css_content, session, base_url, resource_cache):
    """Embed all resources referenced in CSS with caching."""
    def replace_url_in_css(match):
        url = match.group(1).strip("'\"")
        return f"url({download_and_embed_resource(session, url, base_url, resource_cache)})"
    return re.sub(r'url\([\'\"]?([^\'")]+)[\'\"]?\)', replace_url_in_css, css_content)

def embed_external_resources(html_content, base_url, session, remove_instructions=True, resource_cache=None):
    """Embed all external resources into the HTML with resource caching."""
    if resource_cache is None:
        resource_cache = get_resource_cache()
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        for link in soup.find_all('link', rel='stylesheet'):
            if 'href' in link.attrs:
                css_url = link['href']
                try:
                    if not css_url.startswith(('http://', 'https://')):
                        css_url = urllib.parse.urljoin(base_url, css_url)
                    if css_url in resource_cache['css']:
                        logging.info(f"Using cached CSS: {css_url}")
                        css_content = resource_cache['css'][css_url]
                    else:
                        logging.info(f"Processing CSS: {css_url}")
                        css_response = session.get(css_url, timeout=30)
                        css_response.raise_for_status()
                        css_content = css_response.text
                        css_content = embed_css_resources(css_content, session, css_url, resource_cache)
                        resource_cache['css'][css_url] = css_content
                    style_tag = soup.new_tag('style')
                    style_tag.string = css_content
                    link.replace_with(style_tag)
                    logging.info(f"Embedded CSS from {css_url}")
                except Exception as e:
                    logging.warning(f"Failed to process CSS {css_url}: {str(e)}")
        for style in soup.find_all('style'):
            if style.string:
                style.string = embed_css_resources(style.string, session, base_url, resource_cache)
        for img in soup.find_all('img'):
            if 'src' in img.attrs:
                img_url = img['src']
                logging.info(f"Processing image: {img_url}")
                img['src'] = download_and_embed_resource(session, img_url, base_url, resource_cache)
        for element in soup.find_all(style=True):
            element['style'] = embed_css_resources(element['style'], session, base_url, resource_cache)
        print_style = soup.new_tag('style')
        print_style['media'] = 'print'
        print_style.string = """
            @page {
                size: A4;
                margin: 1cm;
            }
            body {
                font-family: Arial, sans-serif;
                font-size: 11pt;
                line-height: 1.3;
            }
            a {
                text-decoration: underline;
                color: #000;
            }
            .no-print, #previous-view, header, nav {
                display: none !important;
            }
            table {
                page-break-inside: auto;
                border-collapse: collapse;
            }
            tr {
                page-break-inside: avoid;
                page-break-after: auto;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 4px;
            }
            img {
                max-width: 100% !important;
                height: auto !important;
            }
        """
        soup.head.append(print_style)
        if remove_instructions:
            for element in soup.find_all(class_="no-print"):
                element.decompose()
                logging.info("Removed instruction box element")
            previous_view = soup.find(id="previous-view")
            if previous_view:
                previous_view.decompose()
                logging.info("Removed previous-view element")
        return str(soup)
    except Exception as e:
        logging.error(f"Error embedding resources: {str(e)}")
        return html_content

def save_html_to_file(html_content, output_path):
    """Save HTML content to a file."""
    try:
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(html_content)
        logging.info(f"HTML saved successfully: {output_path}")
        return True, None
    except Exception as e:
        error_msg = f"Failed to save HTML: {str(e)}"
        logging.error(error_msg)
        return False, error_msg 