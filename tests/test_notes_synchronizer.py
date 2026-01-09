from unittest.mock import patch
from NotesSynchronizer.notes_synchronizer import (
    NotesSynchronizer,
    TimestampedNote,
    TimestampedSummary,
    VideoSummary,
)
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class MockSubtitles:
    def transcribe_audio_with_timestamps(self, audio_path: str):
        return {
            "text": "Тестовый текст транскрипции",
            "chunks": [
                {"text": "Первая часть текста", "timestamp": (0.0, 5.0)},
                {"text": "Вторая часть текста", "timestamp": (5.0, 10.0)},
            ],
        }


class MockImageCaption:
    def caption_image(self, image_path: str):
        return "Тестовое описание изображения"


class MockTextSummarizer:
    def summarize(self, text: str, max_length: int = 150):
        return "Тестовое резюме"


class TestTimestampedNote:
    """Тесты для класса TimestampedNote"""

    def test_timestamp_mmss_conversion(self):
        """Тест конвертации миллисекунд в формат MM:SS"""
        note = TimestampedNote(
            timestamp_ms=65000,
            audio_text="test audio",
            image_description="test image",
            combined_text="test combined",
        )
        assert note.timestamp_mmss == "01:05"

    def test_timestamp_mmss_less_than_minute(self):
        """Тест конвертации для времени меньше минуты"""
        note = TimestampedNote(
            timestamp_ms=30000,
            audio_text="test audio",
            image_description="test image",
            combined_text="test combined",
        )
        assert note.timestamp_mmss == "00:30"


class TestTimestampedSummary:
    """Тесты для класса TimestampedSummary"""

    def test_segment_summary_dict(self):
        """Тест конвертации в словарь"""
        summary = TimestampedSummary(
            time="01:30", summary="Test summary", has_visual=True
        )

        expected_dict = {
            "time": "01:30",
            "summary": "Test summary",
            "has_visual": True,
        }
        assert summary.segment_summary_dict == expected_dict


class TestVideoSummary:
    """Тесты для класса VideoSummary"""

    def test_summary_dict(self):
        """Тест конвертации VideoSummary в словарь"""
        timestamped_summaries = [
            TimestampedSummary(
                time="01:30", summary="Summary 1", has_visual=True
            ),
            TimestampedSummary(
                time="02:45", summary="Summary 2", has_visual=False
            ),
        ]

        video_summary = VideoSummary(
            concise="Краткое содержание",
            detailed="Подробное содержание",
            key_points=["Ключевой момент 1", "Ключевой момент 2"],
            timestamped_summaries=timestamped_summaries,
        )
        result = video_summary.summary_dict
        assert result["concise"] == "Краткое содержание"
        assert result["detailed"] == "Подробное содержание"
        assert result["key_points"] == [
            "Ключевой момент 1",
            "Ключевой момент 2",
        ]
        assert len(result["timestamped_summaries"]) == 2


class TestNotesSynchronizer:
    """Тесты для класса NotesSynchronizer"""

    @pytest.fixture
    def mock_models(self):
        """Фикстура для мок-моделей"""
        return MockSubtitles(), MockImageCaption(), MockTextSummarizer()

    @pytest.fixture
    def synchronizer(self, mock_models):
        """Фикстура для NotesSynchronizer"""
        subtitles_mock, image_caption_mock, summarizer_mock = mock_models
        return NotesSynchronizer(
            subtitles_mock, image_caption_mock, summarizer_mock
        )

    @patch("NotesSynchronizer.notes_synchronizer.extract_audio")
    @patch("NotesSynchronizer.notes_synchronizer.extract_frames")
    def test_synchronize_success(
        self, mock_extract_frames, mock_extract_audio, synchronizer
    ):
        """Тест успешной синхронизации заметок"""

        mock_extract_audio.return_value = "/tmp/test_audio.wav"
        mock_extract_frames.return_value = (
            ["/tmp/frame1.png", "/tmp/frame2.png"],
            [1000.0, 6000.0],
        )
        video_path = "/tmp/test_video.mp4"
        video_id = 123
        result = synchronizer.synchronize(video_path, video_id)
        mock_extract_audio.assert_called_once()
        mock_extract_frames.assert_called_once_with(video_path, video_id)
        assert len(result) == 2
        assert isinstance(result[0], TimestampedNote)
        assert result[0].audio_text == "Первая часть текста"

    def test_generate_summary(self, synchronizer):
        """Тест генерации сводки"""

        notes = [
            TimestampedNote(
                timestamp_ms=0,
                audio_text="Первая часть аудио",
                image_description="Первое изображение",
                combined_text="Комбинированный текст 1",
            ),
            TimestampedNote(
                timestamp_ms=30000,
                audio_text="Вторая часть аудио",
                image_description="Второе изображение",
                combined_text="Комбинированный текст 2",
            ),
        ]

        result = synchronizer.generate_summary(notes)
        assert isinstance(result, VideoSummary)
        assert result.concise == "Тестовое резюме"
        assert result.detailed == "Тестовое резюме"
        assert len(result.timestamped_summaries) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
