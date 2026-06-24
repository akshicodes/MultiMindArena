from backend.tts_service import EdgeTTSProvider, ElevenLabsProvider, TTSService


def test_edge_provider_uses_expected_voice_mapping():
    provider = EdgeTTSProvider()
    assert provider.get_voice("GPT") == "en-US-AriaNeural"
    assert provider.get_voice("Gemini") == "en-US-JennyNeural"
    assert provider.get_voice("Llama") == "en-GB-SoniaNeural"
    assert provider.get_voice("Step") == "en-US-GuyNeural"


def test_elevenlabs_provider_uses_expected_voice_mapping():
    provider = ElevenLabsProvider()
    assert provider.get_voice("GPT") == "JBFqnCBsd6RMkjVDRZzb"
    assert provider.get_voice("Gemini") == "EXAVITQu4vr4xnSDxMaL"
    assert provider.get_voice("Llama") == "IKne3meq5aSn9XLyUdCD"
    assert provider.get_voice("Step") == "GBv7mTt0atIp3Br8iCZE"


def test_tts_service_selects_edge_by_default():
    service = TTSService()
    assert isinstance(service.get_provider("edge"), EdgeTTSProvider)
    assert isinstance(service.get_provider("elevenlabs"), ElevenLabsProvider)
    assert isinstance(service.get_provider(None), EdgeTTSProvider)
