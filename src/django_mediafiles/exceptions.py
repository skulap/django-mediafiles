from django.core.exceptions import ValidationError


class FileValidationError(ValidationError):
    pass
