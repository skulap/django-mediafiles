import shutil
from pathlib import Path

import pytest
from django.core.files import File as DjangoFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django_mediafiles.models import ImageFile, VideoFile, File
from django_mediafiles.processors.image import ImageProcessor
from django_mediafiles.processors.video import VideoProcessor


@pytest.mark.django_db
def test_image_processor(test_image, temp_media):
    img = ImageFile.objects.create(
        file=SimpleUploadedFile("test.jpg", test_image),
        compression_quality=50,
        thumbnail_size=[300, 300]
    )

    processor = ImageProcessor(img, max_size=600)
    processor.process()
    processor.apply_changes()

    img.refresh_from_db()
    assert img.width == 600
    assert img.height == 450
    assert img.thumbnail.name.startswith('thumb_')
    assert img.processing_status == 'success'


def has_ffmpeg():
    return shutil.which("ffmpeg") is not None


@pytest.mark.skipif(not has_ffmpeg(), reason="Требуется установленный ffmpeg")
@pytest.mark.django_db
def test_video_processor(temp_media):
    test_video_short = Path(__file__).parent / "test_video_short.mp4"
    test_video_long = Path(__file__).parent / "test_video_long.mp4"

    def test(video_path, total_seconds):
        # Создаем объект VideoFile
        with video_path.open('rb') as f:
            _video = VideoFile.objects.create(
                file=DjangoFile(f, name=video_path.name)
            )

        processor = VideoProcessor(_video)
        processor.process()
        processor.apply_changes()

        _video.refresh_from_db()
        assert _video.duration.total_seconds() == total_seconds
        assert _video.preview.name.startswith('preview_')

    test(test_video_short, 5.0)
    test(test_video_long, 20.0)

