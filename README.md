# Jira2PDF

## Context
We needed a quick and effective way to pull all Jira issues/tasks/bugs/etc from Jira in PDF, in a format that was easy to read and that included images in the description and comments sections. 

After trying the tools in the Marketplace and no success with the idea of 'Bulk export' into independent PDFs, I ended up creating this script to accomplish the objective.

By the time we ran this, total was: 1,219. It took around 30-45 minutes. 

We have very specific customizations and we needed that information in the PDF as well.

At the end, I used Cursor + Claude Sonnet to accomplish the objective.


## Features
- Fetches Jira issues as HTML with all styling and images embedded
- Converts HTML files to PDF using either pdfkit or WeasyPrint (preferably pdfkit)
- Parallel processing for improved performance
- Smart filename generation including Jira key, title, sprint, and service ticket number
- Resource caching for faster repeated exports
- Detailed logging and failure tracking
- Modular, maintainable codebase

## Prerequisites
- Python 3.6 or higher
- For pdfkit: wkhtmltopdf must be installed on your system (added to Environment Variables as well)
- For WeasyPrint: GTK+ 3 must be installed on Windows

## Setup
1. **Clone or copy this repository:**
   ```bash
   git clone <repository-url>
   cd Jira2PDF
   ```

2. **Create and activate a virtual environment (recommended):**
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On Unix/MacOS:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install PDF engine (choose one):**
   ```bash
   # For pdfkit:
   pip install pdfkit
   # For WeasyPrint:
   pip install weasyprint
   ```

5. **Create a `.env` file** in the project root with your Jira credentials:
   ```env
   JIRA_URL=https://yourcompany.atlassian.net
   JIRA_USERNAME=your-email@example.com
   JIRA_API_TOKEN=your-api-token
   ```

6. **Add your Jira issue keys** (one per line) to `keys.txt`.

## Usage
Run the main program:
```bash
python main.py [options]
```

### Command Line Options
- `--skip-html` : Skip HTML generation and convert existing HTML files to PDF
- `--skip-pdf` : Skip PDF generation and only create HTML files
- `--keep-instructions` : Keep the instruction box and navigation elements in the output
- `--threads N` : Number of parallel processing threads (default: 4)
- `--pdf-engine pdfkit|weasyprint` : PDF conversion engine to use (default: pdfkit)

### Examples
Basic usage:
```bash
python main.py
```

Only generate HTML files:
```bash
python main.py --skip-pdf
```

Convert existing HTML files to PDF:
```bash
python main.py --skip-html
```

## Output
- HTML files are saved in the `exports/` directory
- PDF files are saved in the `exports/pdf/` directory
- Filenames follow the format: `ISSUEKEY - Title - Sprint - ServiceTicket.html/pdf`
- Failed exports are logged in `export_failures.csv`
- Detailed logs are written to `jira2pdf.log`

## Project Structure
```
├── main.py              # Entry point, argument parsing, orchestration
├── jira_api.py          # Jira API session, authentication, fetching
├── html_exporter.py     # HTML extraction, resource embedding, filename logic
├── pdf_converter.py     # PDF conversion logic
├── requirements.txt     # Python dependencies
├── .env                 # Jira credentials (not included in repo)
├── keys.txt            # List of Jira issue keys to export
├── exports/            # Output directory
│   └── pdf/           # PDF output directory
└── jira2pdf.log       # Log file
```

## Troubleshooting

### Common Issues

1. **PDF Generation Fails**
   - For pdfkit: Ensure wkhtmltopdf is installed and in your system PATH
   - For WeasyPrint: Install GTK+ 3 on Windows
   - Check `export_failures.csv` for specific error details

2. **Authentication Errors**
   - Verify your Jira credentials in `.env`
   - Ensure your API token is valid and has necessary permissions

3. **Resource Loading Issues**
   - Check your internet connection
   - Verify Jira URL is correct and accessible
   - Check `jira2pdf.log` for specific error messages

### Logging
- Detailed logs are written to `jira2pdf.log`
- Failed exports are tracked in `export_failures.csv`
- Use `--keep-instructions` to debug HTML generation issues


---
## What could be improved?

### Performance Optimizations
- **Resource Handling**
  - Replace base64 encoding with direct file references to improve HTML loading speed
  - Implement a more efficient caching system for images and files to prevent redundant downloads
  - Consider using a local file system cache with proper invalidation strategies

### Code Structure
- **Code Organization**
  - Create a `utils.py` module to centralize common functionality
  - Implement proper separation of concerns between modules
  - Add type hints and improve code documentation

### Jira Integration
- **API Optimization**
  - Refactor to use Jira's REST API endpoints directly instead of relying on PDF preview links
  - Add support for Jira's GraphQL API for more efficient data fetching