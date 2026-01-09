from dataclasses import dataclass
from typing import List, Dict, Tuple

from subtitles.subtitles import (
    Subtitles,
    ImageCaption,
    TextSummarizer,
    extract_frames,
    extract_audio,
)
from utils.utils import AUDIO_DIR


@dataclass
class TimestampedNote:
    """Структура для хранения синхронизированной заметки с временной меткой."""

    timestamp_ms: int
    audio_text: str
    image_description: str
    combined_text: str

    @property
    def timestamp_mmss(self) -> str:
        """Конвертирует миллисекунды в формат MM:SS."""
        seconds = self.timestamp_ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"


@dataclass
class TimestampedSummary:
    time: str
    summary: str
    has_visual: bool

    @property
    def segment_summary_dict(self):
        return {
            "time": self.time,
            "summary": self.summary,
            "has_visual": self.has_visual,
        }


@dataclass
class VideoSummary:
    concise: str
    detailed: str
    key_points: list[str]
    timestamped_summaries: list[TimestampedSummary]

    @property
    def summary_dict(self):
        return {
            "concise": self.concise,
            "detailed": self.detailed,
            "key_points": self.key_points,
            "timestamped_summaries": [
                timestamped_summary.segment_summary_dict
                for timestamped_summary in self.timestamped_summaries
            ],
        }


class NotesSynchronizer:
    def __init__(
        self,
        subtitles_model: Subtitles,
        image_caption_model: ImageCaption,
        summarizer: TextSummarizer,
    ):
        self.subtitles = subtitles_model
        self.image_caption = image_caption_model
        self.summarizer = summarizer

    def synchronize(self, video_path: str, video_id: int) -> List[TimestampedNote]:
        """синхронизирует кадры видео с отрезками звука"""
        audio_path = AUDIO_DIR / f"{video_id}.wav"
        audio_path = extract_audio(video_path, str(audio_path))
        transcription_result = self.subtitles.transcribe_audio_with_timestamps(
            audio_path
        )

        frames_paths, timestamps = extract_frames(video_path, video_id)
        descriptions = [
            self.image_caption.caption_image(str(path)) for path in frames_paths
        ]

        synchronized_notes = self._synchronize_by_timestamp(
            transcription_result, list(zip(timestamps, descriptions))
        )

        return synchronized_notes

    def _synchronize_by_timestamp(
        self, transcription_result: Dict, frame_data: List[Tuple[int, str]]
    ) -> List[TimestampedNote]:
        notes = []

        # Если нет временных меток в транскрипте, используем простую стратегию
        if "chunks" not in transcription_result:
            return self._fallback_synchronization(
                transcription_result["text"], frame_data
            )

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
                combined_text=combined_text,
            )
            notes.append(note)

        return notes

    def _fallback_synchronization(
        self, transcription_text: str, frame_data: List[Tuple[int, str]]
    ) -> List[TimestampedNote]:
        notes = []

        # Разбиваем текст на предложения
        sentences = transcription_text.split(". ")
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
            avg_timestamp = (
                sum(relevant_timestamps) // len(relevant_timestamps)
                if relevant_timestamps
                else i * 10000
            )

            combined_descriptions = " ".join(relevant_frames)
            combined_text = f"{sentence}. {combined_descriptions}"

            note = TimestampedNote(
                timestamp_ms=avg_timestamp,
                audio_text=sentence,
                image_description=combined_descriptions,
                combined_text=combined_text,
            )
            notes.append(note)

        return notes

    def generate_summary(self, notes: List[TimestampedNote]):
        """генерирует саммари по уже синхронизированным частям видео"""
        full_text = " ".join([note.combined_text for note in notes])

        return VideoSummary(
            self.summarizer.summarize(full_text, max_length=150),
            self.summarizer.summarize(full_text, max_length=300),
            self._extract_key_points(notes),
            self._create_timestamped_summary(notes),
        )

    def _extract_key_points(self, notes: List[TimestampedNote]) -> List[str]:
        """Извлекает ключевые моменты из заметок."""
        # Простая эвристика: выбираем предложения с ключевыми словами
        keywords = [
            "важно",
            "ключевой",
            "основной",
            "запомните",
            "следовательно",
            "итак",
        ]
        key_points = []

        for note in notes:
            sentences = note.combined_text.split(". ")
            for sentence in sentences:
                if any(keyword in sentence.lower() for keyword in keywords):
                    key_points.append(sentence)

        return list(set(key_points))[:10]  # Ограничиваем 10 ключевыми пунктами

    def _create_timestamped_summary(self, notes: List[TimestampedNote]):
        """Создает суммаризацию с привязкой ко времени."""
        return [
            TimestampedSummary(
                note.timestamp_mmss,
                (
                    note.combined_text[:100] + "..."
                    if len(note.combined_text) > 100
                    else note.combined_text
                ),
                bool(note.image_description.strip()),
            )
            for note in notes
        ]
