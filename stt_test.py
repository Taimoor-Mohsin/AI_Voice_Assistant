import sounddevice as sd
import queue
import sys
from vosk import Model, KaldiRecognizer

# Path to the unzipped model folder
MODEL_PATH = "vosk-model-small-en-us-0.15"

# Create a queue to hold audio data
q = queue.Queue()

def callback(indata, frames, time, status):
    q.put(bytes(indata))

try:
    model = Model(MODEL_PATH)
except Exception as e:
    print("Could not find the model. Please check MODEL_PATH.")
    sys.exit(1)

rec = KaldiRecognizer(model, 16000)

print("Say something! (Press Ctrl+C to stop)")
with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                       channels=1, callback=callback):
    while True:
        data = q.get()
        if rec.AcceptWaveform(data):
            result = rec.Result()
            print(result)  # This prints JSON, text is in the "text" field!
        else:
            # Partial result can be used for live feedback
            pass
