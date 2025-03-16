from ical_parser import IcalParser
from markdown_creator import MarkdownCreator
import logging

class InvoiceApp(IcalParser, MarkdownCreator):
    def __init__(self, ical_path="BI.ics", client_list_path="src/client_data/client_list_and_info.json", month=None, logger=None, logger_level=logging.DEBUG,
                 mydatafp="src/my_info/my_info.json"):
        IcalParser.__init__(self, ical_path, client_list_path, month, logger, logger_level)
        MarkdownCreator.__init__(self, mydatafp, month,logger,logger_level)

    def main_loop(self):
        for key,value in self.client_data.items():
            # get hours and dates
            dates,hours = self.calculate_hours_and_dates(key)

            self.create_invoice(value,dates,hours)


if __name__ == '__main__':
    myapp = InvoiceApp()
    myapp.main_loop()