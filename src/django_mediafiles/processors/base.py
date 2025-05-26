import abc
import logging
import os
import tempfile
from io import BytesIO
from typing import Any
from django.core.files import File as DjangoFile
from django.core.files.storage import default_storage


class BaseProcessor(abc.ABC):
    def __init__(self, media_file, **kwargs):
        self._logger = logging.getLogger(__file__)
        self._media_file = media_file
        self._file_content = None
        self._changes = {}
        self._temp_files = []

    def _load_file_content(self):
        """Загрузка файла в память один раз"""
        if self._file_content is None:
            try:
                with default_storage.open(self._media_file.file.name, 'rb') as f:
                    self._file_content = BytesIO(f.read())
                self._logger.debug("File content loaded to memory")
            except Exception as e:
                self._logger.error(f"Failed to load file: {str(e)}")
                raise
        return self._file_content

    def _reset_buffer(self):
        """Сброс позиции буфера в начало"""
        if self._file_content:
            self._file_content.seek(0)

    def _get_file_buffer(self) -> Any | None:
        """Безопасное получение файла из любого хранилища"""
        if hasattr(self, '_file_buffer'):
            return getattr(self, '_file_buffer')

        if default_storage.exists(self._media_file.file.name):
            with default_storage.open(self._media_file.file.name, 'rb') as f:
                self._file_buffer = f
                return self._file_buffer
        return None

    def _save_to_field(self, field_name, content, filename):
        """Сохранение контента в поле модели"""
        buffer = BytesIO(content)
        getattr(self._media_file, field_name).save(
            filename,
            DjangoFile(buffer),
            save=False
        )
        self._changes[field_name] = getattr(self._media_file, field_name).name
        self._logger.debug(f"Saved to {field_name}: {filename}")

    def _create_temp_file(self, content=None):
        """Создание временного файла с контекстным менеджером"""
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            self._temp_files.append(tf.name)
            if content:
                tf.write(content)
            return tf.name

    def _cleanup_temp_files(self):
        """Очистка временных файлов с обработкой ошибок"""
        for path in self._temp_files:
            try:
                os.unlink(path)
                self._logger.debug(f"Deleted temp file: {path}")
            except Exception as e:
                self._logger.warning(f"Failed to delete {path}: {str(e)}")
        self._temp_files.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup_temp_files()

    def apply_changes(self):
        """Применение изменений к модели с защитой от рекурсии"""
        if self._changes:
            try:
                update_fields = list(self._changes.keys())

                self._media_file.processing_status = 'success'
                update_fields.append('processing_status')
                for field, value in self._changes.items():
                    setattr(self._media_file, field, value)

                self._media_file.save(update_fields=update_fields)
                self._logger.info(f"Applied changes: {', '.join(update_fields)}")
            except Exception as e:
                self._logger.error(f"Failed to apply changes: {str(e)}")
                raise e
        self._cleanup_temp_files()

    @abc.abstractmethod
    def process(self):
        pass
