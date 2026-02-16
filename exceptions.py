class AlertOrchestratorError(Exception):
    """Base exception for the Alert Orchestrator."""
    pass

class RetryableError(AlertOrchestratorError):
    """
    Error that suggests the operation might succeed if retried.
    Examples: Network timeout, DB temporarily unavailable, SMTP connection dropped.
    """
    pass

class NonRetryableError(AlertOrchestratorError):
    """
    Error that will likely not succeed if retried without changes.
    Examples: Validations errors, 404 Not Found, Unparseable data.
    """
    pass

# SMTP / Email Errors
class SMTPConnectError(RetryableError):
    pass

class SMTPDeliveryError(RetryableError):
    pass

class TemplateRenderError(NonRetryableError):
    pass

# HTTP / Adapter Errors
class DatabaseError(RetryableError):
    pass

class ProjectResolutionError(AlertOrchestratorError):
    pass

class ProjectResolutionRetryableError(ProjectResolutionError, RetryableError):
    pass

class ProjectResolutionNonRetryableError(ProjectResolutionError, NonRetryableError):
    pass
