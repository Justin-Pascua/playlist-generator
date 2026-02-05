
class AuthenticationError(Exception):
    """Corresponds to 401 response (i.e. user not logged in)"""

class AuthorizationError(Exception):
    """Corresponds to 403 response (i.e. user doesn't have access to resource)"""

class NotFoundError(Exception):
    """Corresponds to 404 response (i.e. resource not found)"""

class ConflictError(Exception):
    """Corresponds to 409 response (i.e. resource already exists)"""

class VideoLinkParserError(Exception):
    """Raised when `utils.extract_video_id` cannot identify video id from a link"""
class PartialOperationWarning(UserWarning):
    """Raised when a requested side effect is not performed"""

