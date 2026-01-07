import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock
import json

from NotesSynchronizer.notes_synchronizer import NotesSynchronizer, TimestampedNote, TextSummarizer


class TestNotesSynchronizer(unittest.TestCase):
    
    def setUp(self):
        """Подготовка тестовых данных."""
        # Моки для зависимостей
        self.mock_subtitles = Mock()
        self.mock_image_caption = Mock()
        
        # Настраиваем мок для транскрибации
        self.mock_subtitles.transcribe_audio_with_timestamps.return_value = {
            "text": "Это пример транскрипта. Он содержит несколько предложений.",
            "chunks": [
                {"text": "Это пример транскрипта.", "timestamp": (0.0, 2.5)},
                {"text": "Он содержит несколько предложений.", "timestamp": (2.5, 5.0)}
            ]
        }
        
        # Мок для extract_frames (импортируем из существующего модуля или мокаем)
        self.mock_subtitles.extract_audio = Mock(return_value="/fake/audio.wav")
        
        # Инициализируем синхронизатор
        self.synchronizer = NotesSynchronizer(
            subtitles_model=self.mock_subtitles,
            image_caption_model=self.mock_image_caption
        )
    
    def test_timestamped_note_creation(self):
        """Тест создания заметки с временной меткой."""
        note = TimestampedNote(
            timestamp_ms=1500,
            audio_text="Пример текста",
            image_description="Описание кадра",
            combined_text="Пример текста. Описание кадра"
        )
        
        self.assertEqual(note.timestamp_ms, 1500)
        self.assertEqual(note.audio_text, "Пример текста")
        self.assertIn("кадра", note.image_description)
    
    def test_fallback_synchronization(self):
        """Тест резервной стратегии синхронизации."""
        transcription_text = "Первое предложение. Второе предложение. Третье предложение."
        frame_data = [
            (1000, "Описание кадра 1"),
            (2000, "Описание кадра 2"),
            (3000, "Описание кадра 3")
        ]
        
        notes = self.synchronizer._fallback_synchronization(transcription_text, frame_data)
        
        self.assertEqual(len(notes), 3)  # 3 предложения
        self.assertIn("Первое", notes[0].audio_text)
        self.assertIn("кадра", notes[0].image_description)
    
    def test_ms_to_timestamp(self):
        """Тест конвертации миллисекунд в временную метку."""
        result = self.synchronizer._ms_to_timestamp(125000)  # 2 минуты 5 секунд
        self.assertEqual(result, "02:05")
        
        result = self.synchronizer._ms_to_timestamp(5000)  # 5 секунд
        self.assertEqual(result, "00:05")
    
    def test_extract_key_points(self):
        """Тест извлечения ключевых моментов."""
        notes = [
            TimestampedNote(
                timestamp_ms=1000,
                audio_text="Это важный момент, запомните его.",
                image_description="",
                combined_text="Это важный момент, запомните его."
            ),
            TimestampedNote(
                timestamp_ms=2000,
                audio_text="Обычное предложение без ключевых слов.",
                image_description="",
                combined_text="Обычное предложение без ключевых слов."
            )
        ]
        
        key_points = self.synchronizer._extract_key_points(notes)
        self.assertEqual(len(key_points), 1)
        self.assertIn("важный момент", key_points[0])


class TestTextSummarizer(unittest.TestCase):
    
    def setUp(self):
        self.summarizer = TextSummarizer()
    
    def test_simple_summarize_short_text(self):
        """Тест простой суммаризации короткого текста."""
        text = "Короткий текст."
        result = self.summarizer._simple_summarize(text, max_length=50)
        self.assertEqual(result, text)
    
    def test_simple_summarize_long_text(self):
        """Тест простой суммаризации длинного текста."""
        text = "Первое предложение. " * 10
        result = self.summarizer._simple_summarize(text, max_length=100)
        self.assertLess(len(result), len(text))
        self.assertIn("Первое", result)
    
    def test_text_splitting(self):
        """Тест разбиения текста на чанки."""
        text = ". ".join([f"Предложение {i}" for i in range(20)])
        chunks = self.summarizer._split_text(text, chunk_size=100)
        
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLess(len(chunk), 150)


if __name__ == '__main__':
    unittest.main()