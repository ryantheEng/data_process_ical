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

        if logger is None:
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(logger_level)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        else:
            self.logger = logger

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

        all_dates = []
        all_hours = []

        for event in recur_cal.events:
            # get the days of the week that the event takes place on
            if 'RRULE' in event:
                # Get day of week from start date
                start_date = event.get('dtstart').dt
                if isinstance(start_date, datetime):
                    start_date = start_date.date()
                weekday = start_date.weekday()  # Gets day number (0-6, where 0 is Monday)
                # Get duration/hours from event
                duration = event.get('duration')

                # get the dates of the weekday that corresponds with the month,year
                # Get first day of the month
                first_day = date(self.year, self.month, 1)

                # Find first occurrence of the weekday
                days_ahead = weekday - first_day.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                first_occurrence = first_day + timedelta(days=days_ahead)

                # Get all occurrences in the month
                current_date = first_occurrence

                dates = []
                hours = []

                while current_date.month == self.month:
                    dates.append(current_date)
                    if not isinstance(duration, timedelta):
                        start_time = event.get('dtstart').dt
                        end_time = event.get('dtend').dt
                        duration = end_time - start_time
                    hours.append(duration.seconds / 3600)  # Convert seconds to hours
                    current_date += timedelta(days=7)

                # check the exdates
                if 'EXDATE' in event:
                    exdates = event['EXDATE']
                    if not hasattr(exdates, '__iter__'):
                        exdates = [exdates]
                    # check exdates against dates
                    for exdate in exdates:
                        if exdate.dts[0].dt.date() in dates:
                            index = dates.index(exdate.dts[0].dt.date())
                            self.logger.debug(f'Removed:Recurring:{exdate.dts[0].dt.date()}')
                            dates.pop(index)
                            hours.pop(index)
                
                all_dates+=dates
                all_hours+=hours

        return all_dates, all_hours

    def get_non_recur_info(self,non_recur_cal,recur_data_dates):
        all_dates = []
        all_hours = []

        for event in non_recur_cal.events:
            # get the days of the week that the event takes place on
            if 'DTSTART' in event:
                # Get day of week from start date
                start_date = event.get('dtstart').dt
                if isinstance(start_date, datetime):
                    start_date = start_date.date()
                # see if exists in recur_data_dates
                if start_date in recur_data_dates:
                    continue
                elif start_date in all_dates:
                    continue
                else:
                    all_dates.append(start_date)
                    if 'DTEND' in event:
                        end_date = event.get('dtend').dt
                        duration = end_date - event.get('dtstart').dt
                        all_hours.append(duration.seconds / 3600)

        return all_dates, all_hours
    
    def check_parking(self,component):
        if component.get('Summary') and 'park' in component.get('Summary').lower():
            return True
        return False
    
    def sort_data(self,dates,hours):
        # sort data by date
        data = list(zip(dates,hours))
        data.sort(key=lambda x: x[0])
        dates,hours = zip(*data)
        return dates,hours
    
    def calculate_hours_and_dates(self,client_name):
        self.logger.info(f'Parsing Data for {client_name}')
        non_recur,recur = self.filter_client_calendar(client_name)

        recur_data = self.get_recur_info(recur)
        non_recur_data = self.get_non_recur_info(non_recur,recur_data[0])

        all_dates_data = recur_data[0] + non_recur_data[0]
        all_hours_data = recur_data[1] + non_recur_data[1]

        data = self.sort_data(all_dates_data,all_hours_data)

        return list(data[0]),list(data[1])
    
# testing
if __name__ == '__main__':
    ical_parser = IcalParser(month=2)
    ical_parser.calculate_hours_and_dates('AA')
    quit