import logging
from celery_hchecker import CeleryHealthChecker
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from .tasks import process_file_task, _local_file_process
from .models import File

logger = logging.getLogger(__name__)


@receiver(post_save)
def enqueue_processing(sender, instance: File, created, **kwargs):
    """
    Запуск обработки файла после сохранения с проверкой изменений
    """
    if not issubclass(sender, File):
        return

    if not instance.file or instance.processing_status != 'pending':
        return

    try:
        # Блокируем запись для обновления статуса
        with transaction.atomic():
            File.objects.filter(pk=instance.pk).select_for_update().update(
                processing_status='processing'
            )

        # Получаем параметры процессора
        processor_kwargs = instance.get_processor_kwargs()

        celery_checker = CeleryHealthChecker.get_instance()
        if not celery_checker or not celery_checker.is_healthy():
            transaction.on_commit(
                lambda: _local_file_process(instance, **processor_kwargs)
            )
        else:
            transaction.on_commit(
                lambda: process_file_task.delay(
                    file_pk=instance.pk,
                    **processor_kwargs
                )
            )

    except Exception as e:
        logger.error(f"Failed to enqueue processing: {str(e)}", exc_info=True)
