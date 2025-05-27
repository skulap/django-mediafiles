import fnmatch
import magic
from .exceptions import FileValidationError
from django.utils.translation import gettext_lazy as _


class FileMimeTypeValidator(object):
    error_messages = {
        'mimetype': _("Файлы типа %(mimetype)s не поддерживаются."),
    }

    def __init__(self, mimetypes=None):
        self.mimetypes = mimetypes

    def __call__(self, file):
        if self.mimetypes is None and file and hasattr(file, 'allowed_types'):
            self.mimetypes = file.allowed_types

        if self.mimetypes:
            self._validate_mimetype(file.file)

    def _validate_mimetype(self, data):
        """Проверка MIME-типа файла."""
        # Получение MIME-типа файла
        mimetype = magic.from_buffer(data.read(2048), mime=True)
        data.seek(0)  # Возвращаем указатель в начало файла

        # Если MIME-типы указаны, проверяем их
        if self.mimetypes:
            if not any(fnmatch.fnmatchcase(mimetype.lower(), pattern.lower())
                       for pattern in self.mimetypes):
                params = {'mimetype': mimetype}
                raise FileValidationError(self.error_messages['mimetype'], 'mimetype', params)
        return mimetype
