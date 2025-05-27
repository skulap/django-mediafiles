import logging
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from .models import File

logger = logging.getLogger(__name__)


@shared_task(name='django-mediafiles.file-processing')
def process_file_task(file_pk: int, **processor_kwargs):
    try:
        obj: File = File.objects.get(pk=file_pk)
    except ObjectDoesNotExist:
        return

    return _local_file_process(obj, **processor_kwargs)


def _local_file_process(instance, **processor_kwargs):
    processor = instance.processor_class(media_file=instance, **processor_kwargs)
    try:
        processor.process()
        processor.apply_changes()

        return "success"
    except Exception:
        File.objects.filter(
            pk=instance.pk
        ).update(processing_status="failed")

        return "failed"



