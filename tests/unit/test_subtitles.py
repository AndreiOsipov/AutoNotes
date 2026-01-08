import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from Subtitles.subtitles import Subtitles

@pytest.fixture
def sub():
    # Сбрасываем синглтон для тестов, если нужно, 
    # но обычно достаточно просто вернуть экземпляр
    return Subtitles()

def test_extract_audio_no_audio(sub):
    """Проверяем, что выбрасывается ValueError, если в видео нет аудио"""
    mock_video_no_audio = MagicMock()
    mock_video_no_audio.audio = None
    mock_video_no_audio.__enter__.return_value = mock_video_no_audio

    # Патчим VideoFileClip там, где он импортирован — в Subtitles.subtitles
    with patch("Subtitles.subtitles.VideoFileClip", return_value=mock_video_no_audio):
        with pytest.raises(ValueError, match="В видео нет аудиодорожки"):
            sub.extract_audio("dummy_video.mp4", "dummy_audio.wav")

def test_extract_audio_calls_write_audiofile(sub):
    """Проверяем, что write_audiofile вызывается, если аудио есть"""
    mock_video = MagicMock()
    mock_video.__enter__.return_value = mock_video
    # Важно: mock_video.audio должен быть моком с методом write_audiofile
    
    with patch("Subtitles.subtitles.VideoFileClip", return_value=mock_video):
        sub.extract_audio("dummy_video.mp4", "dummy_audio.wav")
        mock_video.audio.write_audiofile.assert_called_once_with("dummy_audio.wav")

def test_transcribe_audio_returns_text(sub):
    """Проверяем, что метод возвращает именно тот текст, который пришел из нейросети"""
    fake_audio = np.zeros(16000, dtype=np.float32)
    # Текст в return_value должен совпадать с тем, что мы проверяем в assert
    mock_result = {"text": "Привет мир"}
    
    with patch("Subtitles.subtitles.librosa.load", return_value=(fake_audio, 16000)):
        # Патчим asr_pipeline внутри объекта sub
        with patch.object(sub, 'asr_pipeline', return_value=mock_result):
            text = sub.transcribe_audio("dummy_audio.wav")
            assert text == "Привет мир"