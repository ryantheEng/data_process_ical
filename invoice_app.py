import icalendar
from datetime import datetime, date, timedelta
import os
# Convert markdown to HTML using markdown library
import markdown
from weasyprint import HTML
from markdown.extensions.tables import TableExtension
# json
import json

"""
@brief: Class App for calculating hours for clients

@details:
    - Loads the calendar from the given path
    - Loops through the client list and calcualtes the hours for each client
    - Calculates the hours for each client
    - Returns the total hours for each client
"""
class InvoiceApp:
    def __init__(self,cal_path,client_list):
        self.cal_path = cal_path
        self.last_month = datetime.now().replace(day=1) - timedelta(days=1)
        self.year = (datetime.now().replace(day=1) - timedelta(days=1)).year
        self.last_month_naive = self.last_month.replace(tzinfo=None)
        self.client_list = client_list

        with open(self.cal_path, 'rb') as file:
            cal = icalendar.Calendar.from_ical(file.read())

        self.cal = icalendar.Calendar()
        # remove all non-event components
        for component in cal.walk():
            if component.name == "VEVENT":
                self.cal.add_component(component)

    def load_calendar(self,client_name):
        
        # Filter events to only include current month
        filtered_cal = icalendar.Calendar()
        for component in self.cal.walk():
            if component.name == "VEVENT":
                if component.get('Summary').startswith(client_name) and not any(c.isupper() for c in component.get('Summary')[len(client_name):len(client_name)+1]):
                    print(component.get('Summary') + " " + str(component.get('dtstart').dt))
                    if 'RRULE' in component:
                        if 'UNTIL' not in component['RRULE']:
                            filtered_cal.add_component(component)
                        elif component['RRULE']['UNTIL'][0].month >= self.last_month.month and component['RRULE']['UNTIL'][0].year >= self.last_month.year:
                            filtered_cal.add_component(component)
                    elif not 'RRULE' in component and component.get('dtstart').dt.month == self.last_month.month:
                        filtered_cal.add_component(component)
        
        # Sort calendar components by UID
        sorted_components = sorted(filtered_cal.walk(), key=lambda x: x.get('UID', '') if x.name == "VEVENT" else '')

        # Create dictionary to store highest sequence number for each UID
        uid_sequences = {}
        filtered_components = []
        
        # Go through components and keep only highest sequence for each UID
        for component in sorted_components:
            if component.name == "VEVENT":
                uid = component.get('UID', '')
                seq = component.get('SEQUENCE', 0)
                
                if uid not in uid_sequences or seq > uid_sequences[uid][0]:
                    uid_sequences[uid] = (seq, component)
        
        # Rebuild calendar with deduplicated components
        filtered_cal = icalendar.Calendar()
        for seq, component in uid_sequences.values():
            filtered_cal.add_component(component)
        cal = filtered_cal

        return cal


    def days_in_month(self,event_weekday):
        # return days in the month that match the event weekday
        days_in_month = 0
        dates_in_month = []
        for day in range(1, self.last_month.day + 1):
            if datetime(self.last_month.year, self.last_month.month, day).weekday() == event_weekday:
                days_in_month += 1
                dates_in_month.append(datetime(self.last_month.year, self.last_month.month, day))
        return days_in_month,dates_in_month
    
    def calculate_hours(self,cal):
        total_hours = 0
        all_days = []
        dates_to_remove = []
        for component in cal.walk():
            if component.name == "VEVENT":
                event_start = component.get('dtstart').dt
                event_start_naive = event_start.replace(tzinfo=None)
                event_end = component.get('dtend').dt
                event_duration = event_end - event_start
                event_weekday = event_start.weekday()
                days_in_month,dates_in_month = self.days_in_month(event_weekday)

                # intervals
                if 'RRULE' in component:
                    # Get interval from RRULE
                    if 'INTERVAL' in component['RRULE']:
                        interval = int(component['RRULE']['INTERVAL'][0])
                    else:
                        interval = 1
                    # Only keep dates that match the interval pattern
                    filtered_dates = []

                    # find the first date in the month that matches the interval
                    first_date = component.get('dtstart').dt
                    while first_date.month != self.last_month.month and first_date.year <= self.last_month.year:
                        if component['RRULE']['FREQ'][0] == 'WEEKLY':
                            first_date += timedelta(weeks=interval)
                        elif component['RRULE']['FREQ'][0] == 'MONTHLY':
                            first_date += timedelta(months=interval)
                        elif component['RRULE']['FREQ'][0] == 'DAILY':
                            first_date += timedelta(days=interval)
                    # go through freq 
                    # filtered_dates.append(first_date)

                    first_date_temp = first_date
                    
                    while first_date.month == self.last_month.month and first_date.year == self.last_month.year:
                        if first_date.month == self.last_month.month and first_date.year == self.last_month.year:
                            first_date_temp = first_date
                            filtered_dates.append(first_date_temp)
                        if component['RRULE']['FREQ'][0] == 'WEEKLY':
                            first_date += timedelta(weeks=interval)
                        elif component['RRULE']['FREQ'][0] == 'MONTHLY':
                            first_date += timedelta(months=interval)
                        elif component['RRULE']['FREQ'][0] == 'DAILY':
                            first_date += timedelta(days=interval)

                        if 'UNTIL' in component['RRULE']:
                            if first_date >= component['RRULE']['UNTIL'][0]:
                                break
                        if first_date.month != self.last_month.month:
                            break

                    dates_in_month = filtered_dates
                    days_in_month = len(filtered_dates)
                
                # non-recursive
                else:
                    if event_start_naive.month != self.last_month_naive.month or event_start_naive.year != self.last_month_naive.year:
                        continue
                    filtered_dates = [event_start]
                    dates_in_month = filtered_dates
                    days_in_month = len(filtered_dates)
                    
                for date in dates_in_month:
                    # if date not in all_days:
                    #     # Check for overlapping times with existing dates
                    #     overlapping = False
                    #     for existing_date in all_days:
                    #         # if (date <= (existing_date + timedelta(hours=3)) and 
                    #         #     (date + timedelta(hours=3)) >= existing_date):
                    #         if date.day == existing_date.day and date.month == existing_date.month and date.year == existing_date.year:
                    #             overlapping = True
                    #             days_in_month -= 1
                    #             dates_in_month.remove(date)
                    #             break
                    #     if not overlapping:
                    all_days.append(date)

                # all_days.append(dates_in_month)

                hours_per_day = event_duration.total_seconds() / 60 / 60
                total_hours += hours_per_day*days_in_month
                
                # remove the EXDATE hours from the total
                if 'EXDATE' in component:
                    exdate_array = component.get('EXDATE')
                    if isinstance(exdate_array, icalendar.prop.vDDDLists):
                        if exdate_array.dts[0].dt.month == self.last_month.month and exdate_array.dts[0].dt.year == self.last_month.year:
                            total_hours -= hours_per_day
                            dates_to_remove.append(exdate_array.dts[0].dt)
                        # print(exdate_array.dts[0].dt.month)
                    else:
                        for exdate in exdate_array:
                            if exdate.dts[0].dt.month == self.last_month.month and exdate.dts[0].dt.year == self.last_month.year:
                                total_hours -= hours_per_day
                                dates_to_remove.append(exdate.dts[0].dt)
        
        # remove dates from all_days
        all_days.sort()

        dates_to_remove.sort()

        print(f'Sorting...')
        all_days = [day for day in all_days if not any(day.day == remove_date.day and day.month == remove_date.month and day.year == remove_date.year for remove_date in dates_to_remove)]

        if not cal.is_empty():
            return total_hours,all_days,hours_per_day
        else:
            return None,None,None
        
    def create_invoice(self,client_name,dates,hours,client_info,my_info,hours_all):
        invoice_entries = []
        # order dates
        dates.sort()
        for date in dates:
            invoice = {}
            invoice['Service'] = 'Behaviour Intervention'
            invoice['Date'] = date.strftime('%B %d, %Y')
            invoice['Hours'] = hours
            invoice['Rate'] = '$'+str(client_info['rate'])+'.00'
            invoice['Travel Fee'] = '$3.00'
            invoice['Total'] = '$'+str(hours*client_info['rate'] + 3)+"0"
            invoice_entries.append(invoice)
        

        # create markdown table
        table = ""
        # Add headers
        table += f"| {' | '.join(invoice_entries[0].keys())} | \n"
        # Add separator line
        table += f"|{'|'.join([' ---------- ' for _ in range(len(invoice_entries[0]))])}| \n"
        for invoice in invoice_entries:
            # Add values
            table += f"| {' | '.join(str(value) for value in invoice.values())} | \n"

        # header
        header = f"Invoice Date: {datetime.now().strftime('%B %d,%Y')}\n### Service Provider: {my_info['name']} \n### Mailing Address: {my_info['mailing_address']} \n### Phone Number: {my_info['phone_number']} \n### Client Name: {client_info['name']} \n### Invoice Period: {self.last_month.strftime('%m-%Y')}"
        
        # add total hours
        total_hours = f"Total Hours: {sum(float(invoice['Hours']) for invoice in invoice_entries)} hours"
        total_amount = f"Final Invoice Amount: ${sum(float(invoice['Total'].replace('$','')) for invoice in invoice_entries)}"

        # Convert markdown to HTML
        html = markdown.markdown(table,extensions=[TableExtension()])

        # add header
        header_html = markdown.markdown(header)
        hours_html = markdown.markdown(total_hours)
        amount_html = markdown.markdown(total_amount)

        myhtml = header_html + html + hours_html + amount_html
        
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
                {myhtml}
            </body>
            </html>"""

        # Create folder for month if it doesn't exist
        if not os.path.exists(self.last_month.strftime('%b').lower()):
            os.makedirs(self.last_month.strftime('%b').lower())
        
        # create folder for markdowns
        if not os.path.exists(f"{self.last_month.strftime('%b').lower()}/markdowns"):
            os.makedirs(f"{self.last_month.strftime('%b').lower()}/markdowns")
        
        # create folder for pdfs
        if not os.path.exists(f"{self.last_month.strftime('%b').lower()}/pdfs"):
            os.makedirs(f"{self.last_month.strftime('%b').lower()}/pdfs")

        # markdown file
        markdown_file = header + "\n\n" + table + "\n\n" + total_hours + "\n\n" + total_amount
        
        # create md file with month and year in filename
        with open(f"{self.last_month.strftime('%b').lower()}/markdowns/{client_name}_{self.last_month.strftime('%m_%Y')}.md", "w") as file:
            file.write(markdown_file)
        # Convert HTML to PDF using WeasyPrint
        pdf_file = f"{self.last_month.strftime('%b').lower()}/pdfs/{client_name}_{self.last_month.strftime('%m_%Y')}.pdf"
        HTML(string=html_string).write_pdf(pdf_file)

        return table

if __name__ == "__main__":
    cal_path = "BI.ics"
    client_list_path = "client_list_and_info.json"
    my_info_path = "my_info.json"   
    with open(client_list_path, 'r') as file:
        client_list = json.load(file)
    with open(my_info_path, 'r') as file:
        my_info = json.load(file)
    app = InvoiceApp(cal_path,client_list)
    for client in client_list:
        cal = app.load_calendar(client)
        if client == "LQF":
            for component in cal.walk():
                print(component.get('UID'))    
        hours_all,dates,hours = app.calculate_hours(cal)
        if hours_all is not None:
            invoice = app.create_invoice(client,dates,hours,client_list[client],my_info,hours_all)
            print(f"Invoice created for {client} in {app.last_month.strftime('%m_%Y')}")
        else:
            print(f"No events found for {client} in {app.last_month.strftime('%m_%Y')}")