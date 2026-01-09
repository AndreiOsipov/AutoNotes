import os
import torch
import librosa
import cv2

from PIL import Image

from moviepy import VideoFileClip
from transformers import pipeline
from utils.utils import IMAGES_DIR

DIR = os.path.dirname(os.path.abspath(__file__))
FILE_VIDEO = os.path.join(DIR, "dir_video", "vid.mp4")
FILE_AUDIO = os.path.join(DIR, "dir_audio", "extracted_audio.wav")


def extract_frames(video_path: str, video_id: int, frame_distance=150):
    video_imges_temp_dir = IMAGES_DIR / str(video_id)
    if not (video_imges_temp_dir.exists()):
        os.makedirs(str(video_imges_temp_dir))

    capture = cv2.VideoCapture(video_path)
    totalFrames = capture.get(cv2.CAP_PROP_FRAME_COUNT)
    timestamps: list[float] = []
    frames_paths: list[str] = []

    frame_number = 0
    while frame_number >= 0 and frame_number < totalFrames:
        if capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number):
            ret, frame = capture.read()
            if ret:
                timestamp = capture.get(cv2.CAP_PROP_POS_MSEC)
                frame_path = (
                    video_imges_temp_dir / f"{frame_number}_{timestamp}.png"
                )
                cv2.imwrite(frame_path, frame)

                timestamps.append(timestamp)
                frames_paths.append(frame_path)

        frame_number += frame_distance
    capture.release()
    return frames_paths, timestamps


def extract_audio(video_path: str, audio_path: str) -> str:
    with VideoFileClip(video_path) as video:
        if video.audio is None:
            raise ValueError("В видео нет аудиодорожки")
        video.audio.write_audiofile(audio_path)
        return audio_path


class SingleProcessor:
    _instances = {}

    def __new__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[cls] = instance
            instance._initialized = False
        return cls._instances[cls]

    def __init__(self, model_name, task, **pipeline_specific_kwargs):
        # Проверка в базовом классе - наследникам не нужно проверять
        if hasattr(self, "_initialized") and self._initialized:
            return

        self.torch_dtype = torch.float16
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.model_name = model_name
        self.task = task

        self.pipeline = pipeline(
            task=self.task,
            model=self.model_name,
            torch_dtype=self.torch_dtype,
            device=self.device,
            **pipeline_specific_kwargs,
        )

        self._initialized = True


class ImageCaption(SingleProcessor):
    def __init__(self):
        super().__init__(
            model_name="Salesforce/blip-image-captioning-large",
            task="image-to-text",
        )

    def caption_image(self, image_path: str):
        image = Image.open(image_path)
        result = self.pipeline(image)
        return result[0]["generated_text"]


class Subtitles(SingleProcessor):
    def __init__(self):
        super().__init__(
            model_name="antony66/whisper-large-v3-russian",
            task="automatic-speech-recognition",
            max_new_tokens=256,
            chunk_length_s=30,
            batch_size=16,
            return_timestamps=True,
        )

    def transcribe_audio(self, audio_path: str) -> str:
        audio_input, sr = librosa.load(audio_path)
        result = self.pipeline(
            audio_input, generate_kwargs={"language": "russian"}
        )
        return result["text"]

    def transcribe_audio_with_timestamps(self, audio_path: str) -> dict:
        audio_input, sr = librosa.load(audio_path)
        result = self.pipeline(
            audio_input, generate_kwargs={"language": "russian"}
        )
        chunks = []
        if "chunks" in result:
            for chunk in result["chunks"]:
                chunks.append(
                    {"text": chunk["text"], "timestamp": chunk["timestamp"]}
                )

        return {"text": result["text"], "chunks": chunks}


class TextSummarizer(SingleProcessor):
    def __init__(self, model_name: str = "IlyaGusev/rut5_base_sum_gazeta"):
        super().__init__(
            model_name="IlyaGusev/rut5_base_sum_gazeta",
            task="summarization",
            min_length=30,
            do_sample=False,
        )

    def summarize(self, text: str, max_length: int = 150) -> str:
        """Суммаризирует текст."""
        if not text.strip():
            return ""

        if len(text) > 1000:
            chunks = self._split_text(text, chunk_size=800)
            summaries = []
            for chunk in chunks:
                result = self.pipeline(chunk, max_length=max_length)
                summaries.append(result[0]["summary_text"])
            return " ".join(summaries)
        else:
            result = self.pipeline(text, max_length=max_length)
            return result[0]["summary_text"]

    def _split_text(self, text: str, chunk_size: int = 800) -> list[str]:
        """Разбивает текст на чанки."""
        sentences = text.split(". ")
        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence)
            if current_length + sentence_length > chunk_size and current_chunk:
                chunks.append(". ".join(current_chunk) + ".")
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length

        if current_chunk:
            chunks.append(". ".join(current_chunk) + ".")

        return chunks
