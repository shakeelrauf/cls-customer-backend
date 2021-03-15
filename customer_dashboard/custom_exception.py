class EmailNotMatchedException(Exception):
    """Raised when email and confirm email not matched"""
    pass


class PasswordException(Exception):
    """Raised when password is smaller than 8 character and not using one upper, one lower and one special character"""
    pass


class NotFoundError(Exception):
    """Raised when object is not found in ESC database"""
    pass


class ConnectionError(Exception):
    """Raised when database connection error"""
    pass


class ESCDataNotFetchingError(Exception):
    """Raised when data not fetching from ESC database"""
    pass


class OldPasswordNotMatched(Exception):
    """Raised when old password not matched while user chaning his password"""
    pass
