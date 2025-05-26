from .base import BaseProcessor
import magic


class FileProcessor(BaseProcessor):
    def _detect_mime_type(self):
        """Определение MIME-типа с использованием загруженного контента"""
        self._logger.info(f'Start detecting mime-type...')

        self._reset_buffer()
        try:
            header = self._file_content.read(2048)
            mime_type = magic.from_buffer(header, mime=True)
            self._changes['mime_type'] = mime_type
            self._logger.info(f"Detected MIME type: {mime_type}")
            return mime_type
        except Exception as e:
            self._logger.error(f"MIME detection failed: {str(e)}")
            raise e
        finally:
            self._reset_buffer()

    def process(self):
        self._logger.info(f'Processing file {self._media_file}...')

        self._load_file_content()
        self._detect_mime_type()
