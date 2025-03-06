


# Define a custom error class
class CSVError(Exception):
    """Exception raised for errors in the CSV file."""
    def __init__(self, message="CSV file is either empty or does not exist."):
        self.message = message
        super().__init__(self.message)