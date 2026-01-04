import os
import torch
import librosa


from moviepy import VideoFileClip
from transformers import WhisperForConditionalGeneration, WhisperProcessor, pipeline

DIR = os.path.dirname(os.path.abspath(__file__))
FILE_VIDEO = os.path.join(DIR, "dir_video", "vid.mp4")
FILE_AUDIO = os.path.join(DIR, "dir_audio", "extracted_audio.wav")


class Subtitles:
    def __init__(self):
        self.torch_dtype = torch.float16
        self.model_name = "antony66/whisper-large-v3-russian"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.processor = WhisperProcessor.from_pretrained(self.model_name)
        self.model = WhisperForConditionalGeneration.from_pretrained(self.model_name, dtype=self.torch_dtype).to(self.device)
        
        self.asr_pipeline = pipeline(
            "automatic-speech-recognition",
            model = self.model,
            tokenizer = self.processor.tokenizer,
            feature_extractor = self.processor.feature_extractor,
            max_new_tokens = 256,
            chunk_length_s = 30,
            batch_size = 16,
            return_timestamps = True,
            torch_dtype = self.torch_dtype,
            device = self.device,
        )
        
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Subtitles, cls).__new__(cls)
        return cls.instance

    def extract_audio(self, video_path: str, audio_path: str) -> str:
        with VideoFileClip(video_path) as video:
            if video.audio is None:
                raise ValueError("В видео нет аудиодорожки")
            video.audio.write_audiofile(audio_path)
            return audio_path

    def transcribe_audio(self, audio_path: str) -> str:

        # Загружаем аудио
        audio_input, sr = librosa.load(audio_path)

        result = self.asr_pipeline(
            audio_input,
            generate_kwargs={"language": "russian"}
        )

        return result["text"]


if __name__ == '__main__':
    video = FILE_VIDEO
    print(video)
    audio = FILE_AUDIO
    print(audio)
    sub = Subtitles()
    print('Начинаем извлечение аудио из видео')
    sub.extract_audio(video, audio)
    print('Извлекли аудио из видео')
    text = sub.transcribe_audio(audio)
    print('Извлекли текст из аудио')
    with open(os.path.join(DIR, "dir_txt", "конспект.txt"), "w", encoding="utf-8") as f:
            f.write(text)
    print("Конспект сохранен в конспект.txt")