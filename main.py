import os
import sys
import csv
import argparse
import logging
from html_exporter import read_issue_keys, extract_issue_details, create_safe_filename, get_resource_cache, download_and_embed_resource, embed_css_resources, embed_external_resources, save_html_to_file
from jira_api import get_jira_session, fetch_html_content
from pdf_converter import convert_html_to_pdf, convert_html_to_pdf_alternative, convert_pdfs_in_parallel

def main():
    parser = argparse.ArgumentParser(description='Export Jira issues directly to PDF.')
    parser.add_argument('--skip-html', action='store_true', help='Skip HTML generation and convert existing HTML files to PDF')
    parser.add_argument('--skip-pdf', action='store_true', help='Skip PDF generation and only create HTML files')
    parser.add_argument('--keep-instructions', action='store_true', help='Keep the instruction box and navigation elements in the output')
    parser.add_argument('--threads', type=int, default=4, help='Number of parallel processing threads (default: 4)')
    parser.add_argument('--pdf-engine', choices=['pdfkit', 'weasyprint'], default='pdfkit', help='PDF conversion engine to use (default: pdfkit)')
    args = parser.parse_args()

    html_dir = "exports"
    os.makedirs(html_dir, exist_ok=True)
    pdf_dir = os.path.join(html_dir, "pdf")
    os.makedirs(pdf_dir, exist_ok=True)

    html_success_count = 0
    html_failure_count = 0
    pdf_success_count = 0
    pdf_failure_count = 0

    failures_file = "export_failures.csv"
    with open(failures_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Issue Key", "Issue Title", "HTML Status", "PDF Status", "Failure Reason"])

    html_results = []

    if not args.skip_html:
        issue_keys = read_issue_keys()
        if not issue_keys:
            logging.warning("No issue keys found in keys.txt")
            return
        logging.info(f"Found {len(issue_keys)} issue(s) to process")
        session = get_jira_session()
        remove_instructions = not args.keep_instructions
        resource_cache = get_resource_cache()
        for issue_key in issue_keys:
            html_content, base_url = fetch_html_content(session, issue_key)
            if not html_content or not base_url:
                html_results.append((False, f"Failed to fetch HTML content for {issue_key}", issue_key, None))
                continue
            title, sprint, service_ticket = extract_issue_details(html_content, issue_key)
            base_filename = create_safe_filename(issue_key, title, sprint, service_ticket)
            html_path = os.path.join(html_dir, f"{base_filename}.html")
            processed_html = embed_external_resources(html_content, base_url, session, remove_instructions, resource_cache)
            html_success, html_error = save_html_to_file(processed_html, html_path)
            if html_success:
                html_results.append((True, None, title, html_path))
                html_success_count += 1
            else:
                html_results.append((False, html_error, title, None))
                html_failure_count += 1

    if not args.skip_pdf:
        html_paths_to_convert = []
        if html_results:
            for success, _, _, html_path in html_results:
                if success and html_path:
                    html_paths_to_convert.append(html_path)
        else:
            html_paths_to_convert = [os.path.join(html_dir, f) for f in os.listdir(html_dir) if f.endswith('.html')]
        if not html_paths_to_convert:
            logging.warning("No HTML files found to convert to PDF")
        else:
            logging.info(f"Converting {len(html_paths_to_convert)} HTML files to PDF")
            global convert_html_to_pdf
            if args.pdf_engine == 'weasyprint':
                try:
                    import weasyprint
                    logging.info("Using WeasyPrint for PDF conversion")
                    convert_html_to_pdf = convert_html_to_pdf_alternative
                except ImportError:
                    logging.error("WeasyPrint not installed. Install with: pip install weasyprint")
                    sys.exit(1)
            else:
                try:
                    import pdfkit
                    logging.info("Using pdfkit for PDF conversion")
                except ImportError:
                    logging.error("pdfkit not installed. Install with: pip install pdfkit")
                    sys.exit(1)
            pdf_results = convert_pdfs_in_parallel(
                html_paths_to_convert, 
                pdf_dir,
                max_workers=args.threads,
                pdf_engine=args.pdf_engine
            )
            for success, html_path, _ in pdf_results:
                if success:
                    pdf_success_count += 1
                else:
                    pdf_failure_count += 1
                    basename = os.path.basename(html_path)
                    base_name = os.path.splitext(basename)[0]
                    issue_key = base_name.split(" - ")[0] if " - " in base_name else base_name
                    with open(failures_file, 'a', newline='') as file:
                        writer = csv.writer(file)
                        pdf_status = "Success" if success else "Failed"
                        writer.writerow([issue_key, base_name, "Success", pdf_status, "" if success else "PDF conversion failed"])

    logging.info("=" * 60)
    logging.info("Export Summary:")
    if not args.skip_html:
        logging.info(f"HTML Export: {html_success_count} succeeded, {html_failure_count} failed")
    if not args.skip_pdf:
        logging.info(f"PDF Conversion: {pdf_success_count} succeeded, {pdf_failure_count} failed")
    logging.info(f"HTML files are in the '{html_dir}' directory")
    logging.info(f"PDF files are in the '{pdf_dir}' directory")
    if html_failure_count > 0 or pdf_failure_count > 0:
        logging.info(f"See {failures_file} for details on failures")

if __name__ == "__main__":
    main() 