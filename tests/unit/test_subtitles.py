import pytest
from unittest.mock import patch
from Subtitles import Subtitles


def test_extract_audio_no_audio(sub, mock_video_no_audio):
    """Проверяем, что выбрасывается ValueError, если в видео нет аудио"""
    with patch("subtitles.VideoFileClip", return_value=mock_video_no_audio):
        with pytest.raises(ValueError):
            sub.extract_audio("dummy_video.mp4", "dummy_audio.wav")


def test_extract_audio_calls_write_audiofile(sub, mock_video):
    """Проверяем, что write_audiofile вызывается, если аудио есть"""
    with patch("subtitles.VideoFileClip", return_value=mock_video):
        result = sub.extract_audio("dummy_video.mp4", "dummy_audio.wav")
        mock_video.audio.write_audiofile.assert_called_once_with("dummy_audio.wav")
        assert result == "dummy_audio.wav"


def test_transcribe_audio_returns_text(sub, mock_pipeline_result):
    """Проверяем, что метод возвращает текст"""
    with patch("subtitles.pipeline", return_value=lambda audio_input, **kwargs: mock_pipeline_result):
        text = Subtitles().transcribe_audio("dummy_audio.wav")
        assert text == "Привет мир"
        assert isinstance(text, str)
