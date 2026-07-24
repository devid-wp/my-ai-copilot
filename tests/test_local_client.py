from core.local_client import LocalClient
from core.local_runtime import LOCAL_MODEL_ID


def test_local_client_uses_one_bundled_model():
    client = LocalClient("system")

    assert client.provider_name == "LOCAL QWEN"
    assert client.model_chat == LOCAL_MODEL_ID
    assert client.model_code == LOCAL_MODEL_ID
    assert str(client.client.base_url).startswith("http://127.0.0.1:11435/v1/")
