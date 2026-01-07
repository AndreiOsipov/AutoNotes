import json
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import torch

# Импортируем существующие классы
from Subtitles.subtitles import Subtitles, ImageCaption, extract_frames
from utils.utils import AUDIO_DIR, IMAGES_DIR


@dataclass
class TimestampedNote:
    """Структура для хранения синхронизированной заметки с временной меткой."""
    timestamp_ms: int  # Время в миллисекундах от начала видео
    audio_text: str    # Транскрибированный текст с аудио
    image_description: str  # Описание кадра
    combined_text: str      # Объединенный текст для суммаризации
    summary: Optional[str] = None  # Краткое резюме сегмента


class NotesSynchronizer:

    def __init__(self, subtitles_model: Optional[Subtitles] = None, 
                 image_caption_model: Optional[ImageCaption] = None):
        self.subtitles = subtitles_model or Subtitles()
        self.image_caption = image_caption_model or ImageCaption()
        
    def process_video(self, video_path: str, video_id: int) -> List[TimestampedNote]:
        # 1. Извлечение аудио и транскрибация
        audio_path = AUDIO_DIR / f"{video_id}.wav"
        audio_path = self.subtitles.extract_audio(video_path, str(audio_path))
        
        # Получаем транскрипт с временными метками (нужно модифицировать Subtitles)
        transcription_result = self.subtitles.transcribe_audio_with_timestamps(audio_path)
        
        # 2. Извлечение и описание кадров
        frames_paths, timestamps = extract_frames(video_path, video_id)
        descriptions = [self.image_caption.caption_image(str(path)) for path in frames_paths]
        
        # 3. Синхронизация по времени
        synchronized_notes = self._synchronize_by_timestamp(
            transcription_result, 
            list(zip(timestamps, descriptions))
        )
        
        return synchronized_notes
    
    def _synchronize_by_timestamp(self, transcription_result: Dict, frame_data: List[Tuple[int, str]]) -> List[TimestampedNote]:
       
        notes = []
        
        # Если нет временных меток в транскрипте, используем простую стратегию
        if "chunks" not in transcription_result:
            return self._fallback_synchronization(transcription_result["text"], frame_data)
        
        # Синхронизация по временным меткам
        for chunk in transcription_result["chunks"]:
            chunk_text = chunk["text"]
            chunk_start, chunk_end = chunk["timestamp"]  # в секундах
            chunk_start_ms = chunk_start * 1000
            chunk_end_ms = chunk_end * 1000
            
            # Находим кадры, попадающие в этот временной интервал
            relevant_frames = []
            for frame_ts, frame_desc in frame_data:
                if chunk_start_ms <= frame_ts <= chunk_end_ms:
                    relevant_frames.append(frame_desc)
            
            # Объединяем описания кадров
            combined_descriptions = " ".join(relevant_frames) if relevant_frames else ""
            
            # Создаем комбинированный текст
            combined_text = f"{chunk_text}. {combined_descriptions}"
            
            note = TimestampedNote(
                timestamp_ms=int(chunk_start_ms),
                audio_text=chunk_text,
                image_description=combined_descriptions,
                combined_text=combined_text
            )
            notes.append(note)
        
        return notes
    
    def _fallback_synchronization(self,  transcription_text: str, frame_data: List[Tuple[int, str]]) -> List[TimestampedNote]:
    
        notes = []
        
        # Разбиваем текст на предложения
        sentences = transcription_text.split('. ')
        frames_per_segment = max(1, len(frame_data) // max(1, len(sentences)))
        
        for i, sentence in enumerate(sentences):
            if not sentence.strip():
                continue
                
            # Выбираем соответствующие кадры
            start_idx = i * frames_per_segment
            end_idx = min((i + 1) * frames_per_segment, len(frame_data))
            
            relevant_frames = []
            relevant_timestamps = []
            
            for j in range(start_idx, end_idx):
                if j < len(frame_data):
                    ts, desc = frame_data[j]
                    relevant_frames.append(desc)
                    relevant_timestamps.append(ts)
            
            # Используем среднюю временную метку
            avg_timestamp = sum(relevant_timestamps) // len(relevant_timestamps) if relevant_timestamps else i * 10000
            
            combined_descriptions = " ".join(relevant_frames)
            combined_text = f"{sentence}. {combined_descriptions}"
            
            note = TimestampedNote(
                timestamp_ms=avg_timestamp,
                audio_text=sentence,
                image_description=combined_descriptions,
                combined_text=combined_text
            )
            notes.append(note)
        
        return notes
    
    def generate_summary(self,  notes: List[TimestampedNote],  summary_type: str = "concise") -> Dict:

        # Объединяем весь текст для суммаризации
        full_text = " ".join([note.combined_text for note in notes])
        
        # Используем суммаризатор (нужно будет реализовать или интегрировать)
        summarizer = TextSummarizer()
        
        summaries = {
            "concise": summarizer.summarize(full_text, max_length=150),
            "detailed": summarizer.summarize(full_text, max_length=300),
            "key_points": self._extract_key_points(notes),
            "timestamped_summary": self._create_timestamped_summary(notes)
        }
        
        return summaries
    
    def _extract_key_points(self, notes: List[TimestampedNote]) -> List[str]:
        """Извлекает ключевые моменты из заметок."""
        # Простая эвристика: выбираем предложения с ключевыми словами
        keywords = ["важно", "ключевой", "основной", "запомните", "следовательно", "итак"]
        key_points = []
        
        for note in notes:
            sentences = note.combined_text.split('. ')
            for sentence in sentences:
                if any(keyword in sentence.lower() for keyword in keywords):
                    key_points.append(sentence)
        
        return list(set(key_points))[:10]  # Ограничиваем 10 ключевыми пунктами
    
    def _create_timestamped_summary(self, notes: List[TimestampedNote]) -> List[Dict]:
        """Создает суммаризацию с привязкой ко времени."""
        timestamped_summary = []
        
        for note in notes:
            # Конвертируем время в читаемый формат
            time_str = self._ms_to_timestamp(note.timestamp_ms)
            
            # Краткое описание сегмента (первые 100 символов)
            segment_summary = note.combined_text[:100] + "..." if len(note.combined_text) > 100 else note.combined_text
            
            timestamped_summary.append({
                "time": time_str,
                "summary": segment_summary,
                "has_visual": bool(note.image_description.strip())
            })
        
        return timestamped_summary
    
    def _ms_to_timestamp(self, milliseconds: int) -> str:
        """Конвертирует миллисекунды в формат MM:SS."""
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def save_notes(self, notes: List[TimestampedNote], output_path: str):
        """Сохраняет синхронизированные заметки в файл."""
        notes_dict = {
            "generated_at": datetime.now().isoformat(),
            "total_segments": len(notes),
            "notes": [
                {
                    "timestamp_ms": note.timestamp_ms,
                    "timestamp": self._ms_to_timestamp(note.timestamp_ms),
                    "audio_text": note.audio_text,
                    "image_description": note.image_description,
                    "combined_text": note.combined_text,
                    "summary": note.summary
                }
                for note in notes
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(notes_dict, f, ensure_ascii=False, indent=2)


class TextSummarizer:
    def __init__(self, model_name: str = "IlyaGusev/rut5_base_sum_gazeta"):
        try:
            from transformers import pipeline
            self.summarizer = pipeline(
                "summarization",
                model=model_name,
                device=0 if torch.cuda.is_available() else -1
            )
            self.model_loaded = True
        except ImportError:
            print("Transformers не установлен. Используется простой суммаризатор.")
            self.summarizer = None
            self.model_loaded = False
    
    def summarize(self, text: str, max_length: int = 150) -> str:
        """Суммаризирует текст."""
        if not text.strip():
            return ""
            
        if self.model_loaded and self.summarizer:
            try:
                # Разбиваем текст на части, если он слишком длинный
                if len(text) > 1000:
                    chunks = self._split_text(text, chunk_size=800)
                    summaries = []
                    for chunk in chunks:
                        result = self.summarizer(chunk, max_length=max_length, min_length=30, do_sample=False)
                        summaries.append(result[0]['summary_text'])
                    return " ".join(summaries)
                else:
                    result = self.summarizer(text, max_length=max_length, min_length=30, do_sample=False)
                    return result[0]['summary_text']
            except Exception as e:
                print(f"Ошибка при суммаризации: {e}")
                # Используем простую суммаризацию в случае ошибки
                return self._simple_summarize(text, max_length)
        else:
            return self._simple_summarize(text, max_length)
    
    def _split_text(self, text: str, chunk_size: int = 800) -> List[str]:
        """Разбивает текст на чанки."""
        sentences = text.split('. ')
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            if current_length + sentence_length > chunk_size and current_chunk:
                chunks.append('. '.join(current_chunk) + '.')
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        if current_chunk:
            chunks.append('. '.join(current_chunk) + '.')
        
        return chunks
    
    def _simple_summarize(self, text: str, max_length: int = 150) -> str:
        """Простая суммаризация на основе эвристик."""
        sentences = text.split('. ')
        
        if len(sentences) <= 3:
            return text
        
        # Выбираем первые, последние и самые длинные предложения
        important_sentences = []
        
        # Первое предложение
        if sentences:
            important_sentences.append(sentences[0])
        
        # Последнее предложение
        if len(sentences) > 1:
            important_sentences.append(sentences[-1])
        
        # Самые длинные предложения (кроме первого и последнего)
        middle_sentences = sentences[1:-1] if len(sentences) > 2 else []
        if middle_sentences:
            middle_sentences.sort(key=len, reverse=True)
            for i in range(min(2, len(middle_sentences))):
                important_sentences.append(middle_sentences[i])
        
        summary = '. '.join(sorted(set(important_sentences), key=sentences.index))
        
        # Обрезаем если нужно
        if len(summary) > max_length:
            summary = summary[:max_length-3] + "..."
        
        return summary