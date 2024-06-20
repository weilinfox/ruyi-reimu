
class ParseException(Exception):
    def __init__(self, message):
        self.message = message


class AssertException(Exception):
    def __init__(self, message):
        self.message = message


class NetworkException(Exception):
    def __init__(self, message):
        self.message = message
