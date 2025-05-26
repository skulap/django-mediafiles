import datetime
import tempfile
from src.django_mediafiles.processors.file import FileProcessor
import ffmpeg


class VideoProcessor(FileProcessor):
    def __init__(self, preview_size=(854, 480), crf=28, preset='fast', **kwargs):
        self.preview_size = preview_size
        self.crf = crf  # 0-51, где меньше - лучше качество
        self.preset = preset
        self._validate_params()

        super().__init__(**kwargs)

    def _validate_params(self):
        """Проверка параметров обработки видео"""
        if not isinstance(self.preview_size, (tuple, list)) or len(self.preview_size) != 2:
            raise ValueError("Preview size must be a tuple/list with 2 elements")

        if not (0 <= self.crf <= 51):
            raise ValueError("CRF must be between 0 and 51")

        valid_presets = ['ultrafast', 'superfast', 'veryfast', 'faster',
                         'fast', 'medium', 'slow', 'slower', 'veryslow']
        if self.preset not in valid_presets:
            raise ValueError(f"Invalid preset. Valid values: {valid_presets}")

    def _extract_metadata(self):
        """Извлечение метаданных видео с помощью ffmpeg"""
        try:
            # Создание временного файла для анализа
            with tempfile.NamedTemporaryFile(suffix='.video') as temp_in:
                temp_in.write(self._file_content.getvalue())
                temp_in.flush()

                probe = ffmpeg.probe(temp_in.name)
                video_stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')

                return {
                    'duration': float(probe['format']['duration']),
                    'width': int(video_stream['width']),
                    'height': int(video_stream['height']),
                    'codec': video_stream.get('codec_name', 'unknown')
                }

        except ffmpeg.Error as e:
            self._logger.error(f"FFmpeg metadata extraction failed: {e.stderr.decode()}")
            raise

    def _generate_preview(self, metadata):
        try:
            duration = metadata['duration']

            with tempfile.NamedTemporaryFile(suffix='.preview.mp4') as temp_out:
                # Создание временного входного файла
                with tempfile.NamedTemporaryFile(suffix='.source.mp4') as temp_in:
                    temp_in.write(self._file_content.getvalue())
                    temp_in.flush()

                    input_stream = ffmpeg.input(temp_in.name)
                    segments = []

                    # Логика выбора сегментов
                    if duration <= 10:
                        # Просто обрезаем до длительности
                        video = input_stream.video.trim(end=duration)
                        segments.append(video)
                    else:
                        # Генерация 5 сегментов
                        interval = (duration - 2) / 4  # Интервал между началами отрезков
                        for i in range(5):
                            start = i * interval
                            # Видео сегмент
                            v = input_stream.video.trim(start=start, end=start + 2).setpts('PTS-STARTPTS')
                            segments.append(v)

                    # Склейка сегментов
                    if len(segments) > 1:
                        video_streams = [s[0] for s in segments]
                        video = ffmpeg.concat(*video_streams, v=1, a=0)
                    else:
                        video = segments[0]

                    # Масштабирование и кодирование
                    video = video.filter('scale', *self.preview_size)
                    output_args = {
                        'c:v': 'libx264',
                        'crf': self.crf,
                        'preset': self.preset,
                        'movflags': 'faststart'
                    }

                    output = ffmpeg.output(video, temp_out.name, **output_args)
                    output.run(overwrite_output=True)

                # Чтение результата
                with open(temp_out.name, 'rb') as f:
                    return f.read()

        except ffmpeg.Error as e:
            self._logger.error(f"FFmpeg processing failed: {e.stderr.decode()}")
            raise e

    def process(self):
        super().process()

        # Шаг 1: Загрузка файла
        self._load_file_content()

        # Шаг 2: Извлечение метаданных
        metadata = self._extract_metadata()

        # Шаг 3: Генерация превью
        preview_content = self._generate_preview(metadata)

        # Обновление метаданных
        self._changes.update({
            'duration': datetime.timedelta(metadata['duration']),
            'width': metadata['width'],
            'height': metadata['height']
        })
        # Сохранение превью
        if preview_content:
            preview_name = f"preview_{self._media_file.file.name}"
            self._save_to_field('preview', preview_content, preview_name)
