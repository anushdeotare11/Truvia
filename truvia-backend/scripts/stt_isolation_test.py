"""Isolation test for local STT via faster-whisper."""
import sys
import time

def main():
    from faster_whisper import WhisperModel
    t0 = time.time()
    # 'base' balances accuracy/speed; CPU int8 for portability. Model downloads once.
    model = WhisperModel("base", device="cpu", compute_type="int8")
    print(f"model loaded in {time.time()-t0:.1f}s")
    segments, info = model.transcribe("storage/test_scam_call.wav", beam_size=1)
    texts = []
    logprobs = []
    for seg in segments:
        texts.append(seg.text)
        logprobs.append(seg.avg_logprob)
    joined = " ".join(t.strip() for t in texts).strip()
    import math
    # Convert avg logprob to a rough 0..1 confidence
    conf = math.exp(sum(logprobs) / len(logprobs)) if logprobs else 0.0
    print("LANG:", info.language, "lang_prob:", round(info.language_probability, 3))
    print("TRANSCRIPT:", joined)
    print("CONF:", round(conf, 3))

if __name__ == "__main__":
    main()
