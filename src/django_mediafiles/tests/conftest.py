import pytest
import django
from django.conf import settings
from django.db import connections


def pytest_configure():
    settings.configure(
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'django_mediafiles',
        ],
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
                'OPTIONS': {
                    'timeout': 30  # Увеличиваем таймаут блокировки
                }
            }
        },
        DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
        MEDIA_ROOT='/tmp/media_test',
    )
    django.setup()

    # Закрываем все соединения с БД после настройки
    for conn in connections.all():
        conn.close()


@pytest.fixture
def temp_media(monkeypatch):
    import tempfile
    media_root = tempfile.mkdtemp()
    monkeypatch.setattr(settings, 'MEDIA_ROOT', media_root)
    return media_root


@pytest.fixture
def test_image():
    from PIL import Image
    from io import BytesIO
    image = Image.new('RGB', (800, 600), color='red')
    buffer = BytesIO()
    image.save(buffer, format='JPEG', ext='jpg')  # Явно указываем формат
    buffer.seek(0)
    return buffer.getvalue()
