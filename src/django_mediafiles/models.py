import os
import uuid
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.text import get_valid_filename
from django_basemodels.managers import PolymorphicBaseModelQuerySet
from django_basemodels.models import BaseModel
from polymorphic.managers import PolymorphicManager
from polymorphic.models import PolymorphicModel
from .processors.file import FileProcessor
from .processors.image import ImageProcessor
from .processors.video import VideoProcessor
from .validators import FileMimeTypeValidator


def _upload_save_path(instance, filename):
    safe_filename = get_valid_filename(filename)
    filename, ext = os.path.splitext(os.path.basename(safe_filename))
    path = f'{instance._meta.model_name.lower()}/{uuid.uuid4()}{ext.lower()}'
    return path


class File(BaseModel, PolymorphicModel):
    processor_class = FileProcessor

    mime_type = models.CharField(null=True, max_length=120, editable=False, verbose_name=_("MIME"))
    file = models.FileField(
        null=False, blank=False,
        validators=[FileMimeTypeValidator()],
        upload_to=_upload_save_path,
        verbose_name=_("Файл")
    )
    processing_status = models.CharField(
        max_length=20,
        choices=(
            ('pending', _("В обработке")),
            ('processing', _("Обрабатывается")),
            ('success', _("Успешно")),
            ('failed', _("Ошибка")),
        ),
        default='pending',
        null=False, blank=False,
        editable=False
    )

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    objects = PolymorphicManager.from_queryset(PolymorphicBaseModelQuerySet)()

    class Meta:
        verbose_name = _("Файл")
        verbose_name_plural = _("Файлы")
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_file_name = self.file.name if self.file else None

    def get_processor_kwargs(self):
        return {}

    def get_processor(self):
        if self.processor_class:
            return self.processor_class(self, **self.get_processor_kwargs())

    def save(self, *args, **kwargs):
        """Переопределение сохранения для обработки изменений файла"""
        if not self.pk or (self.file and self.file.name != self.__original_file_name):
            self.processing_status = 'pending'

        super().save(*args, **kwargs)
        self.__original_file_name = self.file.name if self.file else None

    @property
    def original_file_name(self):
        return self.__original_file_name


class ImageFile(File):
    allowed_types = ["image/*"]
    processor_class = ImageProcessor

    width = models.PositiveIntegerField(null=True, editable=False, verbose_name=_("Ширина"))
    height = models.PositiveIntegerField(null=True, editable=False, verbose_name=_("Высота"))
    thumbnail = models.ImageField(null=True, blank=True, editable=False, verbose_name=_("Миниатюра"))

    compression_quality = models.PositiveIntegerField(
        default=85,
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    thumbnail_size = models.JSONField(
        default=[300, 300],
        verbose_name=_("Размер миниатюры")
    )

    class Meta:
        verbose_name = _('Изображение')
        verbose_name_plural = _('Изображения')

    def __init__(self, *args, **kwargs):
        self.__max_size: int | None = kwargs.pop('max_size', None)
        if self.__max_size and self.__max_size < 1:
            raise ValueError('max_size must be greater than 0')

        super().__init__(*args, **kwargs)

    def get_processor_kwargs(self):
        return {
            "max_size": self.__max_size,
            "quality": self.compression_quality,
            "thumbnail_size": self.thumbnail_size,
        }

    @property
    def max_size(self) -> int:
        return self.__max_size


class VideoFile(File):
    allowed_types = ["video/*"]
    processor_class = VideoProcessor

    duration = models.DurationField(null=True, blank=True, verbose_name=_('Длительность'), editable=False)
    preview = models.FileField(
        null=True, blank=True,
        editable=False,
        verbose_name=_("Превью")
    )

    width = models.IntegerField(null=True, verbose_name=_('Ширина'), editable=False)
    height = models.IntegerField(null=True, verbose_name=_('Высота'), editable=False)

    class Meta:
        verbose_name = _('Видео')
        verbose_name_plural = _('Видео')


class DocumentFile(File):
    allowed_types = ["application/pdf", "text/plain"]

    class Meta:
        verbose_name = _('Документ')
        verbose_name_plural = _('Документы')
