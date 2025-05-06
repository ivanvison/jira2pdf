import os
import logging
from functools import partial
import concurrent.futures

def convert_html_to_pdf(html_path, output_path=None):
    """Convert a single HTML file to PDF using pdfkit."""
    try:
        import pdfkit
        if output_path is None:
            output_path = os.path.splitext(html_path)[0] + '.pdf'
        logging.info(f"Converting {html_path} to {output_path}")
        wkhtmltopdf_path = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
        config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
        options = {
            '--load-error-handling': 'ignore',
            '--load-media-error-handling': 'ignore',
            '--enable-local-file-access': True
        }
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        pdfkit.from_string(html_content, output_path, 
                          configuration=config, 
                          options=options,
                          css=None,
                          cover=None,
                          toc=None,
                          cover_first=False)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logging.info(f"Successfully converted to PDF: {output_path}")
            return True, output_path
        else:
            logging.error(f"PDF file was not created or is empty: {output_path}")
            return False, None
    except Exception as e:
        # If an error occurs, check if the PDF was still created
        if output_path and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logging.warning(f"PDF conversion raised an error, but PDF was created: {output_path}. Error: {str(e)}")
            return True, output_path
        else:
            logging.error(f"Failed to convert {html_path} to PDF: {str(e)}")
            return False, None

def convert_html_to_pdf_alternative(html_path, output_path=None):
    """Convert HTML to PDF using WeasyPrint."""
    try:
        from weasyprint import HTML, CSS
        if output_path is None:
            output_path = os.path.splitext(html_path)[0] + '.pdf'
        logging.info(f"Converting {html_path} to {output_path} using WeasyPrint")
        css = CSS(string="""
            @page {
                size: A4;
                margin: 1cm;
            }
            body {
                font-family: Arial, sans-serif;
                font-size: 11pt;
                line-height: 1.3;
                margin: 0;
                padding: 0;
            }
            table {
                border-collapse: collapse;
                width: 100%;
                margin-bottom: 1em;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 4px;
            }
            img {
                max-width: 100%;
                height: auto;
            }
            a {
                text-decoration: underline;
                color: #000;
            }
        """)
        HTML(html_path).write_pdf(
            output_path,
            stylesheets=[css],
            optimize_size=('fonts', 'images'),
            presentational_hints=True,
            zoom=1.0,
            attachments=None,
            pdf_version='1.7',
            font_config=None
        )
        logging.info(f"Successfully converted to PDF: {output_path}")
        return True, output_path
    except Exception as e:
        logging.error(f"Failed to convert {html_path} to PDF: {str(e)}")
        return False, None

def convert_pdfs_in_parallel(html_paths, pdf_dir, max_workers=None, pdf_engine='pdfkit'):
    """Convert multiple HTML files to PDF in parallel."""
    results = []
    if max_workers is None:
        import multiprocessing
        max_workers = max(1, multiprocessing.cpu_count() - 1)
    logging.info(f"Using {max_workers} workers for parallel PDF conversion")
    if pdf_engine == 'weasyprint':
        convert_func = partial(convert_single_pdf, pdf_dir=pdf_dir, engine='weasyprint')
    else:
        convert_func = partial(convert_single_pdf, pdf_dir=pdf_dir, engine='pdfkit')
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {executor.submit(convert_func, html_path): html_path for html_path in html_paths}
        for future in concurrent.futures.as_completed(future_to_path):
            html_path = future_to_path[future]
            try:
                results.append(future.result())
                logging.info(f"Completed PDF conversion for {os.path.basename(html_path)}")
            except Exception as e:
                logging.error(f"Error converting {html_path} to PDF: {str(e)}")
                results.append((False, html_path, None))
    return results

def convert_single_pdf(html_path, pdf_dir, engine='pdfkit'):
    """Convert a single HTML file to PDF for parallel processing."""
    base_name = os.path.splitext(os.path.basename(html_path))[0]
    pdf_path = os.path.join(pdf_dir, base_name + '.pdf')
    if engine == 'weasyprint':
        success, path = convert_html_to_pdf_alternative(html_path, pdf_path)
    else:
        success, path = convert_html_to_pdf(html_path, pdf_path)
    return success, html_path, path 