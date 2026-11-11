from fastapi.testclient import TestClient
from app.main import app
from app.tts import get_wpm, synthesize_speech

client = TestClient(app)


def test_get_wpm_mapping():
    assert get_wpm("slow") == 100
    assert get_wpm(0.6) == 100
    assert get_wpm("normal") == 175
    assert get_wpm(1.0) == 175
    assert get_wpm("fast") == 245
    assert get_wpm(1.3) == 245


def test_synthesize_speech_and_caching(tmp_path, monkeypatch):
    monkeypatch.setattr("app.tts.TTS_CACHE_DIR", tmp_path)
    
    # Generate slow speech
    p1 = synthesize_speech("Hello world", speed="slow")
    assert p1.exists()
    assert p1.stat().st_size > 0

    # Cache hit check
    p2 = synthesize_speech("Hello world", speed="slow")
    assert p1 == p2


def test_tts_api_endpoint(tmp_path, monkeypatch):
    monkeypatch.setattr("app.tts.TTS_CACHE_DIR", tmp_path)

    res = client.get("/api/tts?text=Welcome+to+the+lesson&speed=normal")
    assert res.status_code == 200
    assert res.headers["content-type"] == "audio/mp4"
    assert len(res.content) > 0

    # Test speed differences
    res_slow = client.get("/api/tts?text=Welcome+to+the+lesson&speed=slow")
    assert res_slow.status_code == 200

    res_fast = client.get("/api/tts?text=Welcome+to+the+lesson&speed=fast")
    assert res_fast.status_code == 200

    # Empty text error
    res_err = client.get("/api/tts?text=")
    assert res_err.status_code == 400
