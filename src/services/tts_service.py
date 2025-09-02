import logging
import threading
import pyttsx3
from typing import Optional, Callable
import time

logger = logging.getLogger(__name__)


class TTSService:
    "Service for text-to-speech functionality"

    def __init__(self):
        self.engine = None
        self.lock = threading.Lock()  # Thread lock for preventing race conditions
        self.is_speaking = False
        self.speak_queue = []
        self.currently_speaking = False
        self._initialize_engine()

    def _initialize_engine(self):
        "Initialize the TTS engine"
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", 150)
            self.engine.setProperty("volume", 0.9)
            voices = self.engine.getProperty("voices")
            for voice in voices:
                if "english" in voice.name.lower():
                    self.engine.setProperty("voice", voice.id)
                    break

            # Connect event handlers
            self.engine.connect("started-utterance", self._on_start)
            self.engine.connect("finished-utterance", self._on_finish)

            # Start queue processing thread
            self.queue_thread = threading.Thread(
                target=self._process_queue, daemon=True
            )
            self.queue_thread.start()

        except Exception as e:
            logger.error(f"Error initializing TTS engine: {e}")
            self.engine = None

    def _on_start(self, name):
        """Called when speech starts"""
        self.is_speaking = True
        self.currently_speaking = True
        logger.debug("Speech started")

    def _on_finish(self, name, completed):
        """Called when speech finishes"""
        self.is_speaking = False
        self.currently_speaking = False
        logger.debug("Speech finished")

        # If there's a callback for this utterance, call it
        if hasattr(self, "_current_callback") and self._current_callback:
            callback = self._current_callback
            self._current_callback = None
            callback()

    def _process_queue(self):
        """Process the speech queue in a separate thread"""
        while True:
            if self.speak_queue and not self.currently_speaking:
                text, callback = self.speak_queue.pop(0)
                self._current_callback = callback
                self._speak_text(text)
            time.sleep(0.1)

    def _speak_text(self, text):
        """Internal method to speak text"""
        try:
            with self.lock:  # Acquire lock before using the engine
                logger.debug(f"Speaking: {text[:50]}...")
                self.engine.say(text)
                self.engine.runAndWait()
                logger.debug("Finished speaking")
        except Exception as e:
            logger.error(f"Error in TTS thread: {e}")
            self.is_speaking = False
            self.currently_speaking = False
            if hasattr(self, "_current_callback") and self._current_callback:
                self._current_callback()
                self._current_callback = None

    def text_to_speech(
        self, text: str, blocking: bool = True, callback: Optional[Callable] = None
    ) -> bool:
        "Convert text to speech with thread safety"
        if not self.engine:
            logger.error("TTS engine not initialized")
            if callback:
                callback()
            return False

        try:
            if blocking:
                self._speak_text(text)
                if callback:
                    callback()
            else:
                # Add to queue for non-blocking speech
                self.speak_queue.append((text, callback))

            return True
        except Exception as e:
            logger.error(f"Error in text-to-speech: {e}")
            if callback:
                callback()
            return False

    def is_busy(self) -> bool:
        """Check if TTS is currently speaking"""
        return self.is_speaking or len(self.speak_queue) > 0

    def clear_queue(self):
        """Clear the speech queue"""
        self.speak_queue = []
