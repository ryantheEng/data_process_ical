# Convert markdown to HTML using markdown library
import markdown
from weasyprint import HTML
from markdown.extensions.tables import TableExtension
from datetime import datetime,date
# json
import json
import os
import logging

class MarkdownCreator():
    def __init__(self,my_data_fp='src/my_info/my_info.json',month=None,logger=None,logger_level=logging.INFO):

        if logger is None:
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(logger_level)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        else:
            self.logger = logger

        # read json
        with open(my_data_fp, 'r') as f:
            self.my_data = json.load(f)

        if not month:
            self.month = date.today().month - 1
            if self.month == 0:
                self.month = 12
                self.year = date.today().year - 1
        else:
            self.month = month
            self.year = date.today().year

        self.inv_date = datetime(self.year, self.month, 1)

        # Create folder for month if it doesn't exist
        if not os.path.exists(f'output/{self.inv_date.strftime('%B').lower()}'):
            os.makedirs(f'output/{self.inv_date.strftime('%B').lower()}')
        
        # create folder for markdowns
        if not os.path.exists(f'output/{self.inv_date.strftime('%B').lower()}/markdowns'):
            os.makedirs(f'output/{self.inv_date.strftime('%B').lower()}/markdowns')
        
        # create folder for pdfs
        if not os.path.exists(f'output/{self.inv_date.strftime('%B').lower()}/pdfs'):
            os.makedirs(f'output/{self.inv_date.strftime('%B').lower()}/pdfs')

        self.invoice_entry = {
            'Service': 'Behavour Intervention',
            'Date': None, # datetime strf
            'Hours': None, # string
            'Rate': None,   # string dollar amount
            'Travel Fee': '$3.00', # string dollar amount
            'Parking': None,
            'Total Fee': None, # string dollar amount,
            'Hours float': None,
            'Rate float': None,
            'Total Fee float': None,
            'Parking float': None

        }
        self.header = None

    def create_table_header(self,invoices):
        # don't include parking in header if no parking
        if all(invoice['Parking float'] == 0 for invoice in invoices):
            self.logger.info('No Parking Found .. Removing Parking Column')
            for i in invoices:
                i.pop('Parking')
            # self.invoice_entry.pop('Parking')
            self.table_header = f"| {' | '.join(key for key in self.invoice_entry.keys() if 'float' not in key and key != 'Parking')} | \n"
            # Add separator line
            self.table_header += f"|{'|'.join([' ---------- ' for _ in range(6)])}| \n"
            return False
        else:
            self.table_header = f"| {' | '.join(key for key in self.invoice_entry.keys() if 'float' not in key)} | \n"
            # Add separator line
            self.table_header += f"|{'|'.join([' ---------- ' for _ in range(7)])}| \n"
            return True # parking found

    def create_invoice_header(self,client_object):
        # create info header
        return f"Invoice Date: {datetime.now().strftime('%B %d,%Y')}\n### Service Provider: {self.my_data['name']} \n### Mailing Address: {self.my_data['mailing_address']} \n### Phone Number: {self.my_data['phone_number']} \n### Client Name: {client_object['name']} \n### Invoice Period: {self.inv_date.strftime('%B %Y')}"

    def create_table(self,objlist,parking=False):
        table = ''
        if parking:
            for line in objlist:
                # Add values
                table += f"| {' | '.join(str(line[key]) for key in line.keys() if 'float' not in key)} | \n"

        else:
            for line in objlist:
                # Add values
                table += f"| {' | '.join(str(line[key]) for key in line.keys() if 'float' not in key and 'Parking' not in key)} | \n"

        return table
    
    def fill_table(self,invoice_dict,client_dict):
        objlist = []
        for i in range(len(invoice_dict)):
            entry = self.invoice_entry.copy()
            entry['Date'] = invoice_dict[i]['date'].strftime('%B %d, %Y')
            entry['Hours float'] = invoice_dict[i]['hours']
            entry['Rate float'] = client_dict['rate']
            entry['Hours'] = f"{invoice_dict[i]['hours']:.2f}"
            entry['Rate'] = f"${client_dict['rate']:.2f}"

            if invoice_dict[i]['parking']:
                entry['Parking'] = f"${client_dict['parking rate']:.2f}"
                entry['Parking float'] = client_dict['parking rate']
            else:
                entry['Parking'] = f"-"
                entry['Parking float'] = 0
            entry['Total Fee float'] = entry['Hours float'] * entry['Rate float'] + 3 + entry['Parking float']
            entry['Total Fee'] = f"${entry['Total Fee float']:.2f}"
            objlist.append(entry)

        return objlist
    
    def create_invoice(self,client_object,inv_object):
        # Invoice Header
        header = self.create_invoice_header(client_object)
        # Invoice Table
        invoice_object_list = self.fill_table(inv_object,client_object)
        parking_ret = self.create_table_header(invoice_object_list)
        table = self.create_table(invoice_object_list,parking_ret)
        table = self.table_header+table
        # totals
        total_hours = f"Total Hours: {sum(float(invoice['Hours float']) for invoice in invoice_object_list)} hours"
        total_amount = f"Final Invoice Amount: ${sum(float(invoice['Total Fee float']) for invoice in invoice_object_list):.2f}"
        
        # Convert markdown to HTML
        html = markdown.markdown(table,extensions=[TableExtension()])

        # add header
        header_html = markdown.markdown(header)
        hours_html = markdown.markdown(total_hours)
        amount_html = markdown.markdown(total_amount)

        # put it all together
        myhtml = header_html + html + hours_html + amount_html
        full_html_string = self.create_html(myhtml)

        # markdown file
        markdown_file = header + "\n\n" + table + "\n\n" + total_hours + "\n\n" + total_amount
        # create md file with month and year in filename
        with open(f"output/{self.inv_date.strftime('%B').lower()}/markdowns/{client_object['name']}_{self.inv_date.strftime('%m_%Y')}.md", "w") as file:
            file.write(markdown_file)

        # Convert HTML to PDF using WeasyPrint
        pdf_file = f"output/{self.inv_date.strftime('%B').lower()}/pdfs/{client_object['name']}_{self.inv_date.strftime('%m_%Y')}.pdf"
        HTML(string=full_html_string).write_pdf(pdf_file)

        logging.info(f'Finished Invoice for {client_object['name']}')

    def create_html(self,my_data_html_string):
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
            {my_data_html_string}
        </body>
        </html>"""

        return html_string
    

if __name__ == '__main__':
    markdowns = MarkdownCreator(month=2)