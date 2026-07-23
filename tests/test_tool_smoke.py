import json

from core.tool_smoke import E2E_CONTENT, E2E_PATH, check_native_tool_calling, run_live_tool_smoke


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
    assert check_native_tool_calling(FakeClient()) == "file_exists"


class FakeE2EClient:
    def __init__(self):
        self.calls = iter(
            [
                ("create_file", {"path": E2E_PATH, "content": E2E_CONTENT}),
                ("read_file", {"path": E2E_PATH}),
                ("delete_file", {"path": E2E_PATH}),
            ]
        )
        self.last = None

    def ask_stream(self, _prompt, messages=None):
        assert messages[-1]["role"] == "user"
        self.last = next(self.calls)
        return iter(())

    def get_last_tool_calls(self):
        name, arguments = self.last
        return [
            {
                "id": f"call_{name}",
                "function": {"name": name, "arguments": json.dumps(arguments)},
            }
        ]


def test_live_smoke_executes_create_read_delete_in_temporary_project():
    assert run_live_tool_smoke(FakeE2EClient()) == [
        "create_file",
        "read_file",
        "delete_file",
    ]
