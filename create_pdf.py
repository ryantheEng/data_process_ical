# Convert markdown to HTML using markdown library
import markdown
from weasyprint import HTML
from markdown.extensions.tables import TableExtension
from datetime import datetime, date, timedelta
import os
class create_pdf:
    def __init__(self):
        self.last_month = datetime.now().replace(day=1) - timedelta(days=1)
        self.markdown_path = f"{self.last_month.strftime('%b').lower()}/markdowns"
        self.pdf_path = f"{self.last_month.strftime('%b').lower()}/pdfs"

    def create_pdfs(self):
        # loop through all markdown files in the markdown_path
        for file in os.listdir(self.markdown_path):
            if file.endswith(".md"):
                # read the markdown file
                with open(os.path.join(self.markdown_path, file), "r") as f:
                    markdown_text = f.read()
                # convert markdown to HTML
                html_text = markdown.markdown(markdown_text, extensions=[TableExtension()])

                # Create HTML string with styles
                html_string = f"""
                    <html>
                    <head>
                        <style>
                            table {{width: 100%; border-collapse: collapse;}}
                            th, td {{border: 1px solid black; padding: 1px; text-align: left;}}
                            th {{background-color: #f2f2f2;}}
                        </style>
                    </head>
                    <body>
                        {html_text}
                    </body>
                    </html>"""
                # create PDF
                HTML(string=html_string).write_pdf(os.path.join(self.pdf_path, file.replace(".md", ".pdf")))
                print(f"Created PDF for {file}")

if __name__ == "__main__":
    my_pdf = create_pdf()
    my_pdf.create_pdfs()