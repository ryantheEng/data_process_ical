from ical_parser import IcalParser
from markdown_creator import MarkdownCreator
import logging

class InvoiceApp(IcalParser, MarkdownCreator):
    def __init__(self, ical_path="BI.ics", client_list_path="src/client_data/client_list_and_info.json", month=None, logger=None, logger_level=logging.DEBUG,
                 mydatafp="src/my_info/my_info.json"):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logger_level)
        if not self.logger.handlers:  # Avoid adding duplicate handlers
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.propagate = False  # Disable propagation to the root logger

        # Pass self.logger to IcalParser
        IcalParser.__init__(self, ical_path, client_list_path, month, self.logger, logger_level)
        MarkdownCreator.__init__(self, mydatafp, month, self.logger, logger_level)

    def main_loop(self):
        for key,value in self.client_data.items():
            #debug 
            if key == 'MLS':
                pass
            # get hours and dates
            data_dict = self.calculate_hours_and_dates(key)

            self.create_invoice(value,data_dict)

if __name__ == '__main__':
    myapp = InvoiceApp(month=3)
    myapp.main_loop()