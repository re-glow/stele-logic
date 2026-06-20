class SteleError(Exception):
    pass


class ParseError(SteleError):
    def __init__(self, message, line=None):
        self.line = line
        super().__init__(message)


class ProofError(SteleError):
    def __init__(self, message, line=None):
        self.line = line
        super().__init__(message)
