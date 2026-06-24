from backend.tts_service import EdgeTTSProvider, ElevenLabsProvider, TTSService


def test_edge_provider_uses_expected_voice_mapping():
    provider = EdgeTTSProvider()
    assert provider.get_voice("GPT") == "en-US-AriaNeural"
    assert provider.get_voice("Gemini") == "en-US-JennyNeural"


def test_elevenlabs_provider_uses_expected_voice_mapping():
    provider = ElevenLabsProvider()
    assert provider.get_voice("GPT") == "GPT"
    assert provider.get_voice("Step") == "Step"


def test_tts_service_selects_edge_by_default():
    service = TTSService()
    assert isinstance(service.get_provider("edge"), EdgeTTSProvider)
    assert isinstance(service.get_provider("elevenlabs"), ElevenLabsProvider)
    assert isinstance(service.get_provider(None), EdgeTTSProvider)
