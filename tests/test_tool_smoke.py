from core.tool_smoke import test_native_tool_calling


class FakeClient:
    def ask_stream(self, _prompt, messages=None):
        assert messages[-1]["role"] == "user"
        return iter(())

    def get_last_tool_calls(self):
        return [
            {
                "id": "call_1",
                "function": {
                    "name": "file_exists",
                    "arguments": '{"path":"pyproject.toml"}',
                },
            }
        ]


def test_smoke_accepts_expected_native_call():
    assert test_native_tool_calling(FakeClient()) == "file_exists"
