import os
import torch
import librosa


from moviepy import VideoFileClip
from transformers import WhisperForConditionalGeneration, WhisperProcessor, pipeline


DIR = os.path.dirname(os.path.abspath(__file__))
FILE_VIDEO = os.path.join(DIR, "dir_video", "vid.mp4")
FILE_AUDIO = os.path.join(DIR, "dir_audio", "extracted_audio.wav")


class Subtitles:
    def extract_audio(self, video_path: str, audio_path: str) -> str:
        with VideoFileClip(video_path) as video:
            if video.audio is None:
                raise ValueError("В видео нет аудиодорожки")
            video.audio.write_audiofile(audio_path)
            return audio_path

    def transcribe_audio(self, audio_path: str) -> str:
        torch_dtype = torch.float16
        model_name = "antony66/whisper-large-v3-russian"
        device = "cuda" if torch.cuda.is_available() else "cpu"
        processor = WhisperProcessor.from_pretrained(model_name)
        model = WhisperForConditionalGeneration.from_pretrained(model_name, dtype=torch_dtype).to(device)
        asr_pipeline = pipeline(
            "automatic-speech-recognition",
            model = model,
            tokenizer = processor.tokenizer,
            feature_extractor = processor.feature_extractor,
            max_new_tokens = 256,
            chunk_length_s = 30,
            batch_size = 16,
            return_timestamps = True,
            torch_dtype = torch_dtype,
            device = device,
        )

        # Загружаем аудио
        audio_input, sr = librosa.load(audio_path)

        result = asr_pipeline(
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