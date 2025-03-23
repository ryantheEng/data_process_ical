from icalendar import Calendar, Event
from datetime import datetime, date, timedelta
import json

import logging

class IcalParser:
    def __init__(self,  ical_path="BI.ics", 
                        client_list_path="src/client_data/client_list_and_info.json",
                        month=None,
                        logger=None,
                        logger_level=logging.DEBUG
                        ):
        self.ical_path = ical_path
        self.client_list_path = client_list_path

        # datetime objects
        self.year = date.today().year

        if not month:
            self.month = date.today().month - 1
            if self.month == 0:
                self.month = 12
                self.year = date.today().year - 1
        else:
            self.month = month

        self.inv_date = date(self.year, self.month,1)

        # load object data
        self.cal = self.load_ical()
        self.client_data = self.load_client_dict()
        self.cal = self.filter_master_calendar()

        if logger is None:
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(logger_level)
            if not self.logger.handlers:  # Avoid adding duplicate handlers
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
            self.logger.propagate = False  # Disable propagation to the root logger
        else:
            self.logger = logger

        return

    def load_ical(self):
        event_cal = Calendar()

        with open(self.ical_path, 'rb') as f:
            cal = Calendar.from_ical(f.read())

            for component in cal.walk():
                if component.name == "VEVENT":
                    event_cal.add_component(component)

        return event_cal

    def load_client_dict(self):
        with open(self.client_list_path, 'r') as f:
            client_list = json.load(f)

        return client_list

    def filter_master_calendar(self):
        filtered_master_cal = Calendar()

        # datetime
        exp_date = date(self.year, self.month+1, 1)

        for component in self.cal.walk():
            if component.name == "VEVENT":
                # # parse and simplify date objects
                # start_date = component.get('dtstart').dt
                # if isinstance(start_date, datetime):
                #     start_date = start_date.date()
                # if start_date >= exp_date:
                    # continue
                # parse client name and title of event
                event_summary = str(component.get('summary'))
                for client_id, client_info in self.client_data.items():
                    client_id_str = client_id
                    if event_summary.startswith(client_id_str):
                        filtered_master_cal.add_component(component)
                        break
        

        return filtered_master_cal
    
    def filter_client_calendar(self,client_id):
        # create client_id string
        client_id_str = client_id

        client_id_cal = Calendar()

        for component in self.cal.walk():
            if str(component.get('summary')).startswith(client_id_str):
                # check if client_id has a space directly after it, otherwise could be part of another name
                if len(str(component.get('summary'))) > len(client_id_str) and str(component.get('summary'))[len(client_id_str)] != ' ':
                    continue
                client_id_cal.add_component(component)

        # separate into types
        client_id_cal_recurring = Calendar()
        client_id_cal_non_recurring = Calendar()

        for component in client_id_cal.walk():
            if component.get('RRULE'):
                client_id_cal_recurring.add_component(component)
            else:
                client_id_cal_non_recurring.add_component(component)

        client_id_cal_non_recurring_filtered = self.filter_non_recurring(client_id_cal_non_recurring)
        client_id_cal_recurring_filtered = self.filter_recurring(client_id_cal_recurring)

        return client_id_cal_non_recurring_filtered,client_id_cal_recurring_filtered

    def filter_recurring(self,non_filtered_cal):
        client_id_cal_recurring_filtered = Calendar()
        for component in non_filtered_cal.walk():
            if component.get('RRULE'):
                if 'UNTIL' in component['RRULE']:
                    if component['RRULE']['UNTIL'][0].date() >= self.inv_date.date():
                        client_id_cal_recurring_filtered.add_component(component)
                        self.logger.debug(f'Found:Recurring: {component.get('Summary')}')
                else:
                    client_id_cal_recurring_filtered.add_component(component)
                    self.logger.debug(f'Found:Recurring: {component.get('Summary')}')
        return client_id_cal_recurring_filtered

    def filter_non_recurring(self,non_filtered_cal):
        # go through non-recurring events and filter so that it happened in the datetime we want
        client_id_cal_non_recurring_filtered = Calendar()
        for component in non_filtered_cal.walk():
            if component.get('dtstart'):

                start_date = component.get('dtstart').dt
            else:
                continue
            if isinstance(start_date, datetime):
                start_date = start_date.date()
            if start_date.month == self.month and start_date.year == self.year:
                client_id_cal_non_recurring_filtered.add_component(component)
                self.logger.debug(f'Found:NonRecurring: {component.get('Summary')}')
        return client_id_cal_non_recurring_filtered

    def get_recur_info(self,recur_cal):

        recur_data = []
        data_empty = {
            'date': None,
            'hours': None,
            'parking': False
        }

        for event in recur_cal.events:
            # get the days of the week that the event takes place on
            if event.get('dtstart').dt > self.inv_date.astimezone()+timedelta(weeks=4):
                continue
            if 'RRULE' in event:
                # Get day of week from start date
                start_date = event.get('dtstart').dt
                if isinstance(start_date, datetime):
                    start_date = start_date.date()
                weekday = start_date.weekday()  # Gets day number (0-6, where 0 is Monday)
                # Get duration/hours from event
                duration = event.get('duration')

                # check frequency rule
                interval = 1
                if 'FREQ' in event['RRULE']:
                    if event['RRULE']['FREQ'][0] != 'WEEKLY':
                        self.logger.warning(f'Only Weekly Recurring Events Supported: {event.get('Summary')}')
                        continue
                    if 'INTERVAL' in event['RRULE']:
                        interval = event['RRULE']['INTERVAL'][0]
                
                # get first event of month based on interval
                # Find how many weeks since the first event to this month's first day
                weeks_diff = ((date(self.inv_date.year, self.inv_date.month, 1) - start_date).days // 7)
                # Adjust for the interval by finding how many complete intervals have passed
                intervals_passed = weeks_diff // interval
                # Calculate the first event of this month by adding the complete intervals
                first_event = start_date + timedelta(weeks=intervals_passed * interval)
                # If first_event is before the month starts, add one more interval
                if first_event < (date(self.inv_date.year, self.inv_date.month, 1)):
                    first_event = start_date + timedelta(weeks=(intervals_passed + 1) * interval)

                # Get all occurrences in the month
                current_date = first_event

                while current_date.month == self.month:
                    if current_date in [item['date'] for item in recur_data]:
                        pass
                    else:
                        recur_data.append(data_empty.copy())
                        recur_data[-1]['date'] = current_date   
                        self.logger.debug(f'Added Recurring: {current_date}')
                        if not isinstance(duration, timedelta):
                            start_time = event.get('dtstart').dt
                            end_time = event.get('dtend').dt
                            duration = end_time - start_time
                        recur_data[-1]['hours'] = (duration.seconds / 3600)  # Convert seconds to hours
                        if self.check_parking(event):
                            recur_data[-1]['parking'] = True
                    current_date += timedelta(weeks=interval)

                # check the exdates
                if 'EXDATE' in event:
                    dates = [item['date'] for item in recur_data]
                    exdates = event['EXDATE']
                    if not hasattr(exdates, '__iter__'):
                        exdates = [exdates]
                    # check exdates against dates
                    for exdate in exdates:
                        if exdate.dts[0].dt.date() in dates:
                            index = dates.index(exdate.dts[0].dt.date())
                            self.logger.debug(f'Removed:Recurring:{exdate.dts[0].dt.date()}')
                            recur_data.pop(index)
                            dates.pop(index)

        return recur_data

    def get_non_recur_info(self,non_recur_cal,recur_data_dates):
        recur_data = []
        data_empty = {
            'date': None,
            'hours': None,
            'parking': False
        }
        if not isinstance(recur_data_dates, list):
            recur_data_dates = [recur_data_dates]
        recur_data_dates_ = [item['date'] for item in recur_data_dates]
        all_dates = []

        for event in non_recur_cal.events:
            # get the days of the week that the event takes place on
            if 'DTSTART' in event:
                # Get day of week from start date
                start_date = event.get('dtstart').dt
                if isinstance(start_date, datetime):
                    start_date = start_date.date()
                # see if exists in recur_data_dates
                if start_date in recur_data_dates_:
                    pass
                elif start_date in all_dates:
                    pass
                else:
                    all_dates.append(start_date)
                    recur_data.append(data_empty.copy())
                    self.logger.debug(f'Added NonRecurring: {start_date}')
                    recur_data[-1]['date'] = start_date
                    if 'DTEND' in event:
                        end_date = event.get('dtend').dt
                        duration = end_date - event.get('dtstart').dt
                        recur_data[-1]['hours'] = (duration.seconds / 3600)

                    if self.check_parking(event):
                        recur_data[-1]['parking'] = True
                        continue
                    
                if self.check_parking(event):
                    date_to_match = start_date
                    for item in recur_data_dates:
                        if item['date'] == date_to_match:
                            item['parking'] = True
                            break

        return recur_data
    
    def check_parking(self,component):
        if component.get('Summary') and 'park' in component.get('Summary').lower():
            self.logger.debug(f'Parking Found: {component.get('Summary')}')
            return True
        return False
    
    def sort_data(self,data):
        # sort data by date
        return sorted(data, key=lambda x: x['date'])
    
    def calculate_hours_and_dates(self,client_name):
        self.logger.info(f'Parsing Data for {client_name}')
        non_recur,recur = self.filter_client_calendar(client_name)

        recur_data = self.get_recur_info(recur)
        non_recur_data = self.get_non_recur_info(non_recur,recur_data)

        all_data = recur_data + non_recur_data
        all_data = self.sort_data(all_data)

        return all_data


    
# testing
if __name__ == '__main__':
    ical_parser = IcalParser(month=2)
    ical_parser.calculate_hours_and_dates('AA')
    quit