import numpy as np
import scipy.io.wavfile as wav
import librosa
import librosa.display
import soundfile as sf
from typing import Dict, Any, Optional, Tuple
import logging
from models.mock_interview import AudioAnalysis, EmotionType
from core.settings import Settings

logger = logging.getLogger(__name__)


class AudioAnalysisService:
    def __init__(self):
        self.sample_rate = getattr(Settings, "SAMPLE_RATE", 16000)

    def analyze_audio_features(self, audio_file_path: str) -> AudioAnalysis:
        """Analyze audio features for emotion and fluency with optimized performance"""
        try:
            # Load audio file with librosa for faster processing
            y, sr = librosa.load(audio_file_path, sr=self.sample_rate)

            # Calculate basic audio features
            audio_analysis = AudioAnalysis()

            # Pitch analysis using librosa
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
            pitch_values = []
            for i in range(pitches.shape[1]):
                index = magnitudes[:, i].argmax()
                pitch = pitches[index, i]
                if pitch > 0:
                    pitch_values.append(pitch)

            if pitch_values:
                audio_analysis.pitch = np.mean(pitch_values)

            # Speech rate estimation
            audio_analysis.speech_rate = len(y) / sr

            # Pause detection using librosa
            non_silent_intervals = librosa.effects.split(y, top_db=30)
            audio_analysis.pauses_count = (
                len(non_silent_intervals) - 1 if len(non_silent_intervals) > 0 else 0
            )

            # Fluency score based on pauses and speech rate
            pause_ratio = audio_analysis.pauses_count / max(
                audio_analysis.speech_rate, 1
            )
            audio_analysis.fluency_score = max(0, 1 - min(pause_ratio, 1))

            # Clarity score using spectral centroid
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            audio_analysis.clarity_score = np.mean(spectral_centroids) / 5000

            # Pace score using tempo estimation
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            audio_analysis.pace_score = min(tempo / 200, 1.0)

            # Emotion scores using a lightweight model
            audio_analysis.emotion_scores = self._analyze_emotions_fast(y, sr)

            return audio_analysis

        except Exception as e:
            logger.error(f"Audio analysis error: {e}")
            return AudioAnalysis()

    def _analyze_emotions_fast(self, y: np.ndarray, sr: int) -> Dict[str, float]:
        """Fast emotion analysis using basic audio features"""
        try:
            # Extract basic features
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            chroma = librosa.feature.chroma_stft(y=y, sr=sr)
            mel = librosa.feature.melspectrogram(y=y, sr=sr)

            # Calculate statistics
            mfccs_mean = np.mean(mfccs, axis=1)
            chroma_mean = np.mean(chroma, axis=1)
            mel_mean = np.mean(mel, axis=1)

            # Simple heuristic for emotion detection
            energy = np.sum(y**2) / len(y)
            zero_crossing_rate = np.mean(librosa.feature.zero_crossing_rate(y))

            # Emotion scoring based on heuristics
            emotions = {
                EmotionType.CONFIDENT: min(energy * 0.8, 1.0),
                EmotionType.NERVOUS: min(zero_crossing_rate * 10, 1.0),
                EmotionType.NEUTRAL: 0.5,
                EmotionType.ENTHUSIASTIC: min(np.mean(mel_mean) * 0.01, 1.0),
                EmotionType.UNCERTAIN: min(zero_crossing_rate * 5, 1.0),
            }

            # Normalize scores
            total = sum(emotions.values())
            if total > 0:
                emotions = {k: v / total for k, v in emotions.items()}

            return emotions

        except Exception as e:
            logger.error(f"Emotion analysis error: {e}")
            return {
                EmotionType.CONFIDENT: 0.2,
                EmotionType.NERVOUS: 0.2,
                EmotionType.NEUTRAL: 0.6,
                EmotionType.ENTHUSIASTIC: 0.0,
                EmotionType.UNCERTAIN: 0.0,
            }

    def get_audio_duration(self, audio_file_path: str) -> float:
        """Get audio duration in seconds"""
        try:
            y, sr = librosa.load(audio_file_path, sr=None)
            return len(y) / sr
        except:
            return 0.0
