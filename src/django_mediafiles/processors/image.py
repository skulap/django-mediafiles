from io import BytesIO
from PIL import Image
from .file import FileProcessor


class ImageProcessor(FileProcessor):
    def __init__(self, media_file, max_size=None, quality=85, thumbnail_size=(300, 300)):
        self._max_size = self._validate_max_size(max_size)
        self._compression_quality = self._validate_quality(quality)
        self._thumbnail_size = self._validate_thumbnail_size(thumbnail_size)

        super().__init__(media_file)

    def _validate_max_size(self, max_size):
        if max_size and max_size < 1:
            raise ValueError('max_size must be greater than 0')

        return max_size

    def _validate_quality(self, quality):
        if quality > 100 or quality < 1:
            raise ValueError('quality must be between 1 and 100')

        return quality

    def _validate_thumbnail_size(self, thumbnail_size):
        if not isinstance(thumbnail_size, (tuple, list)):
            raise ValueError('thumbnail_size must be a tuple, list')

        if len(thumbnail_size) == 1:
            thumbnail_size = (thumbnail_size[0], thumbnail_size[0])
        elif len(thumbnail_size) > 2:
            raise ValueError('thumbnail size must be 1 or 2')

        return thumbnail_size

    def _resize_image(self, img: Image.Image):
        """Изменение размера изображения"""
        original_max = max(img.size)
        if original_max > self._max_size:
            aspect_ratio = float(img.size[0]) / float(img.size[1])
            if aspect_ratio > 1:
                aspect_ratio = 1.0 / aspect_ratio
                width = self._max_size
                height = int(width * aspect_ratio)
            else:
                height = self._max_size
                width = int(height * aspect_ratio)

            _format = img.format
            img = img.resize((width, height), Image.Resampling.LANCZOS)
            img.format = _format

            self._logger.info(f"Resized to {(width, height)}")

        return img

    def _compress_image(self, img: Image.Image):
        """Сжатие изображения"""
        output = BytesIO()
        img.save(output, format=img.format, quality=self._compression_quality, optimize=True)
        self._save_to_field('file', output.getvalue(), self._media_file.file.name)
        self._logger.info(f"Compressed with quality {self._compression_quality}%")

    def _generate_thumbnail(self, img):
        """Генерация миниатюры"""
        thumb_output = BytesIO()
        img.thumbnail(self._thumbnail_size)
        img.save(thumb_output, format=img.format)
        self._save_to_field('thumbnail', thumb_output.getvalue(), f"thumb_{self._media_file.file.name}")
        self._logger.info(f"Generated thumbnail {self._thumbnail_size}")

    def process(self):
        super().process()

        content = self._load_file_content()
        try:
            with Image.open(content) as img:

                self._logger.info(f'Start image file compressing...')
                # Изменение размера
                if self._max_size:
                    img = self._resize_image(img)

                # Сохранение размеров
                self._changes.update({
                    'width': img.width,
                    'height': img.height,
                })

                # Сжатие и сохранение
                self._compress_image(img)

                # Генерация миниатюры
                self._generate_thumbnail(img)
        except Exception as e:
            self._logger.error(f"Image processing error: {str(e)}")
            raise e
