import os
import torch
import librosa
import cv2

from PIL import Image

from moviepy import VideoFileClip
from transformers import WhisperForConditionalGeneration, WhisperProcessor, BlipProcessor, BlipForConditionalGeneration, pipeline
from utils.utils import IMAGES_DIR

DIR = os.path.dirname(os.path.abspath(__file__))
FILE_VIDEO = os.path.join(DIR, "dir_video", "vid.mp4")
FILE_AUDIO = os.path.join(DIR, "dir_audio", "extracted_audio.wav")


def extract_frames(video_path: str, video_id: int, frame_distance = 150):
    video_imges_temp_dir = IMAGES_DIR / str(video_id)
    if not(video_imges_temp_dir.exists()):
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
                frame_path = video_imges_temp_dir / f"{frame_number}_{timestamp}.png"
                cv2.imwrite(frame_path, frame)

                timestamps.append(timestamp)
                frames_paths.append(frame_path)
                
        frame_number += frame_distance
    capture.release()
    return frames_paths, timestamps


class ImageCaption:
    def __init__(self):
        self.model_name = "Salesforce/blip-image-captioning-large"
        self.processor = BlipProcessor.from_pretrained(self.model_name)
        self.model = BlipForConditionalGeneration.from_pretrained(self.model_name, torch_dtype=torch.float16)
        self.model.to("cuda:0")

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(ImageCaption, cls).__new__(cls)
        return cls.instance
    

    def caption_image(self, image_path: str):
        image = Image.open(image_path)
        inputs = self.processor(images=image, text="describe the image", return_tensors="pt").to("cuda:0", torch.float16)
        output = self.model.generate(**inputs, max_length=128)
        return str(self.processor.decode(output[0], skip_special_tokens=True))

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
        audio_input, sr = librosa.load(audio_path)
        result = self.asr_pipeline(
            audio_input,
            generate_kwargs={"language": "russian"}
        )
        return result["text"]


if __name__ == '__main__':
    # ImageCaption()
    frames_paths, timestamps = extract_frames("/home/andrei/AutoNotes/Subtitles/dir_video/1_2025-11-06 19-32-19.mp4", 1)
    for p, ts in zip(frames_paths, timestamps):
        print(f"{p} --- {ts}")
    # video = FILE_VIDEO
    # print(video)
    # audio = FILE_AUDIO
    # print(audio)
    # sub = Subtitles()
    # print('Начинаем извлечение аудио из видео')
    # sub.extract_audio(video, audio)
    # print('Извлекли аудио из видео')
    # text = sub.transcribe_audio(audio)
    # print('Извлекли текст из аудио')
    # with open(os.path.join(DIR, "dir_txt", "конспект.txt"), "w", encoding="utf-8") as f:
    #         f.write(text)
    # print("Конспект сохранен в конспект.txt")

