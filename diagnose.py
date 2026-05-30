"""
Quick diagnostic: tests mic capture, VAD speech detection, and TTS.
Run this standalone - no GUI needed.
"""
import sys, time, queue, threading
sys.path.insert(0, '.')

print("=" * 50)
print("JARVIS Diagnostic Tool")
print("=" * 50)

# ── 1. TTS test ──────────────────────────────────────────────────────────────
print("\n[1] Testing TTS...")
try:
    import pyttsx3
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    print(f"    Found {len(voices)} voice(s)")
    for i, v in enumerate(voices[:3]):
        print(f"    [{i}] {v.name}")
    engine.setProperty('rate', 175)
    engine.say("TTS test successful. JARVIS can speak.")
    engine.runAndWait()
    print("    TTS: OK")
except Exception as e:
    print(f"    TTS FAILED: {e}")

# ── 2. Mic test ──────────────────────────────────────────────────────────────
print("\n[2] Testing microphone (speak now for 5 seconds)...")
try:
    import sounddevice as sd
    import numpy as np

    devices = sd.query_devices()
    default_in = sd.query_devices(kind='input')
    print(f"    Default mic: {default_in['name']}")

    audio_q = queue.Queue()
    max_level = [0.0]

    def callback(indata, frames, time, status):
        level = float(np.abs(indata).max())
        max_level[0] = max(max_level[0], level)
        audio_q.put(indata.copy())

    with sd.InputStream(samplerate=16000, channels=1, dtype='float32',
                        blocksize=480, callback=callback):
        print("    Recording 5 seconds... SPEAK NOW")
        time.sleep(5)

    print(f"    Peak audio level: {max_level[0]:.4f}")
    if max_level[0] < 0.001:
        print("    WARNING: Very low audio level - mic may not be working or is muted")
    elif max_level[0] < 0.01:
        print("    WARNING: Low audio level - speak closer to mic or check mic volume")
    else:
        print("    Mic: OK")
except Exception as e:
    print(f"    Mic FAILED: {e}")

# ── 3. VAD test ──────────────────────────────────────────────────────────────
print("\n[3] Testing VAD speech detection (speak for 5 seconds)...")
try:
    import webrtcvad
    import sounddevice as sd
    import numpy as np

    vad = webrtcvad.Vad(2)
    speech_frames = [0]
    total_frames = [0]
    audio_q2 = queue.Queue()

    def cb2(indata, frames, time, status):
        pcm = (indata[:, 0] * 32767).astype('int16').tobytes()
        audio_q2.put(pcm)

    def vad_worker():
        while True:
            try:
                frame = audio_q2.get(timeout=6)
                total_frames[0] += 1
                if vad.is_speech(frame, 16000):
                    speech_frames[0] += 1
            except queue.Empty:
                break

    t = threading.Thread(target=vad_worker, daemon=True)
    t.start()

    with sd.InputStream(samplerate=16000, channels=1, dtype='int16',
                        blocksize=480, callback=cb2):
        print("    Listening for 5 seconds... SPEAK NOW")
        time.sleep(5)

    t.join(timeout=2)
    pct = (speech_frames[0] / max(total_frames[0], 1)) * 100
    print(f"    Speech frames: {speech_frames[0]}/{total_frames[0]} ({pct:.1f}%)")
    if pct < 5:
        print("    WARNING: VAD detected very little speech. Check mic or speak louder.")
    else:
        print("    VAD: OK - speech detected")
except Exception as e:
    print(f"    VAD FAILED: {e}")

print("\n" + "=" * 50)
print("Diagnostic complete.")
print("=" * 50)
