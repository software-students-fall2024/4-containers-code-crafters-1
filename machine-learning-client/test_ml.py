from speech_to_text import get_google_cloud_credentials
from speech_to_text import transcribe_file
from speech_to_text import transcribe
from speech_to_text import app
import os
import json
import pytest
from unittest.mock import patch
from unittest.mock import patch, MagicMock

# test get credendtial function
def test_missing_service_account_json():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(EnvironmentError, match="Service account JSON not found in environment variables"):
            get_google_cloud_credentials()

# test transcribe function
@pytest.fixture
def mock_credentials():
    return MagicMock()

@pytest.fixture
def mock_response():
    alternative = MagicMock()
    alternative.transcript = "This is a test transcription."
    result = MagicMock()
    result.alternatives = [alternative]
    mock_response = MagicMock()
    mock_response.results = [result]
    return mock_response

@patch("speech_to_text.speech.SpeechClient")
def test_transcribe_file_success(mock_speech_client, mock_credentials, mock_response):
    mock_client_instance = mock_speech_client.return_value
    mock_client_instance.recognize.return_value = mock_response

    audio_file = "test_audio.wav"
    with open(audio_file, "wb") as f:
        f.write(b"fake audio content")

    result = transcribe_file(audio_file, mock_credentials)

    assert result.transcript == "This is a test transcription."
    mock_speech_client.assert_called_once_with(credentials=mock_credentials)
    mock_client_instance.recognize.assert_called_once()

    import os
    os.remove(audio_file)

# test communication function
@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

@patch("speech_to_text.get_google_cloud_credentials")
@patch("speech_to_text.transcribe_file")
def test_transcribe_success(mock_transcribe_file, mock_get_google_cloud_credentials, client):
    mock_get_google_cloud_credentials.return_value = MagicMock()

    mock_result = MagicMock()
    mock_result.transcript = "hello may I ask what's your name"
    mock_result.confidence = 0.9
    mock_transcribe_file.return_value = mock_result

    response = client.post("/transcribe", json={"audio_file": "path/to/test_audio.wav"})

    assert response.status_code == 200
    assert response.get_json() == {
        "transcript": "hello may I ask what's your name",
        "confidence": 0.9
    }


if __name__ == "__main__":
    pytest.main()