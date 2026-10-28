OUTPUT_DIR ="Models\student_text_classifier" 
from transformers import pipeline



classifier = pipeline(
    "text-classification",
    model=OUTPUT_DIR,
    tokenizer=OUTPUT_DIR
)

result = classifier("أنا جربت أعوض بـ x باربعة وطلع الطرفين متساويين.") #answer
print(result)


# ---- functions used by ai_service.py ----
def classify(text):
    """One text -> {"label": "...", "score": 0.97}"""
    return classifier(text, truncation=True)[0]


def classify_batch(texts):
    """List of texts -> [{"label": ..., "score": ...}, ...]"""
    return classifier(texts, truncation=True)


# ---- Quran recitation speech-to-text (Whisper) ----
import torch
 
asr_pipe = pipeline(
    task="automatic-speech-recognition",
    model="tarteel-ai/whisper-base-ar-quran",
    device="cuda" if torch.cuda.is_available() else "cpu",
    chunk_length_s=30,  # lets it handle recordings longer than 30 seconds
)
 
 
def transcribe(audio_path):
    """Path to an audio file -> transcribed text"""
    return asr_pipe(audio_path)["text"]
