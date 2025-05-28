import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django_mediafiles.models import File, ImageFile, VideoFile


@pytest.mark.django_db
def test_file_creation(temp_media):
    file = File(file=SimpleUploadedFile('test.txt', b'content'))
    file.save()

    assert file.file.name.startswith('file/')
    assert file.processing_status == 'pending'


@pytest.mark.django_db
def test_image_file_creation(test_image, temp_media):
    img = ImageFile.objects.create(
        file=SimpleUploadedFile("test.jpg", test_image),
        compression_quality=85,
        thumbnail_size=[300, 300]
    )
    assert img.allowed_types == ["image/*"]
    assert img.processing_status == 'pending'
