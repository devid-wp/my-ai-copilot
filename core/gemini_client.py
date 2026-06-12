# core/gemini_client.py
"""Google Gemini API client — same interface as NVIDIAClient.

Drop-in replacement that uses google-generativeai under the hood.
Function calling is translated from OpenAI JSON Schema format to
Gemini's ``Tool`` / ``FunctionDeclaration`` format automatically.

Usage:
    client = GeminiClient(
        api_key="...",
        system_prompt="You are...",
        model_chat="gemini-2.0-flash",
        model_code="gemini-2.5-pro",
    )
    for token in client.ask_stream(prompt, messages=memory.get_history()):
        print(token, end="", flush=True)
"""

from __future__ import annotations

import json
from typing import Any, Dict, Generator, List, Optional

from core.functions import FUNCTION_DEFINITIONS
from core.router import classify_prompt


# ---------------------------------------------------------------------------
# Schema conversion: OpenAI JSON Schema → Gemini FunctionDeclaration
# ---------------------------------------------------------------------------

_TYPE_MAP = {
    "string": "STRING",
    "integer": "INTEGER",
    "number": "NUMBER",
    "boolean": "BOOLEAN",
    "array": "ARRAY",
    "object": "OBJECT",
}


def _convert_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively convert an OpenAI-style JSON Schema to Gemini schema dict."""
    result: Dict[str, Any] = {}

    raw_type = schema.get("type", "string")
    result["type"] = _TYPE_MAP.get(raw_type, "STRING")

    if "description" in schema:
        result["description"] = schema["description"]

    if "properties" in schema:
        result["properties"] = {
            k: _convert_schema(v) for k, v in schema["properties"].items()
        }

    if "required" in schema:
        result["required"] = schema["required"]

    if "items" in schema:
        result["items"] = _convert_schema(schema["items"])

    return result


def _build_gemini_tools() -> List[Any]:
    """Convert FUNCTION_DEFINITIONS to a list of Gemini Tool objects."""
    import google.generativeai as genai

    declarations = []
    for fn in FUNCTION_DEFINITIONS:
        declarations.append(
            genai.protos.FunctionDeclaration(
                name=fn["name"],
                description=fn["description"],
                parameters=_convert_schema(fn["parameters"]),
            )
        )
    return [genai.protos.Tool(function_declarations=declarations)]


# ---------------------------------------------------------------------------
# Role mapping: OpenAI roles → Gemini roles
# ---------------------------------------------------------------------------

def _openai_messages_to_gemini(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert a list of OpenAI-format messages to Gemini ``contents`` format.

    System messages are skipped here — they are injected via
    ``generation_config`` / ``system_instruction`` at the model level.
    Tool messages (role='tool') are converted to Gemini function-response parts.
    """
    contents = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content") or ""

        if role == "system":
            # System prompt handled separately via model init
            continue

        if role == "tool":
            # Gemini expects function responses as model-turn parts
            func_name = msg.get("name", "tool")
            try:
                response_data = json.loads(content) if content else {}
            except json.JSONDecodeError:
                response_data = {"result": content}

            contents.append({
                "role": "function",
                "parts": [{
                    "function_response": {
                        "name": func_name,
                        "response": response_data,
                    }
                }]
            })
            continue

        if role == "assistant":
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                # Convert tool_calls to Gemini function_call parts
                parts = []
                for tc in tool_calls:
                    fn_name = tc.get("function", {}).get("name", "")
                    raw_args = tc.get("function", {}).get("arguments", "{}")
                    try:
                        args = json.loads(raw_args)
                    except json.JSONDecodeError:
                        args = {}
                    parts.append({"function_call": {"name": fn_name, "args": args}})
                if content:
                    parts.append({"text": content})
                contents.append({"role": "model", "parts": parts})
            else:
                contents.append({"role": "model", "parts": [{"text": content}]})
            continue

        # "user" role
        gemini_role = "user"
        contents.append({"role": gemini_role, "parts": [{"text": content}]})

    return contents


# ---------------------------------------------------------------------------
# GeminiClient
# ---------------------------------------------------------------------------

class GeminiClient:
    """Google Gemini client with the same interface as NVIDIAClient.

    Key differences from NVIDIAClient:
    - Uses google-generativeai SDK (not openai).
    - Streaming is done via ``generate_content(..., stream=True)``.
    - Function calling uses Gemini's native Tool format.
    - History is maintained externally via AgentMemory (same as NVIDIA path).
    """

    def __init__(
        self,
        api_key: str,
        system_prompt: str,
        model_chat: str = "gemini-2.0-flash",
        model_code: str = "gemini-2.5-pro",
    ) -> None:
        import google.generativeai as genai
        genai.configure(api_key=api_key)

        self._genai = genai
        self.system_prompt = system_prompt
        self.model_chat = model_chat
        self.model_code = model_code
        self.history: List[Dict[str, Any]] = []
        self._last_tool_calls: List[Dict[str, Any]] = []
        self._tools = _build_gemini_tools()

    # ------------------------------------------------------------------
    # Public interface (same as NVIDIAClient)
    # ------------------------------------------------------------------

    def select_model(self, prompt: str) -> str:
        """Return model_code for coding tasks, model_chat otherwise."""
        return self.model_code if classify_prompt(prompt) == "code" else self.model_chat

    def ask_stream(
        self,
        prompt: str,
        context: str = "",
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> Generator[str, None, None]:
        """Yield response tokens one by one, accumulating tool_calls internally.

        Mirrors NVIDIAClient.ask_stream signature exactly so main.py needs
        zero changes when switching providers.
        """
        import google.generativeai as genai

        self._last_tool_calls = []

        # ── Build the content list ─────────────────────────────────────
        if messages is not None:
            # Extract system prompt from the first message if present
            system_text = self.system_prompt
            for m in messages:
                if m.get("role") == "system":
                    system_text = m.get("content", self.system_prompt)
                    break
            contents = _openai_messages_to_gemini(messages)
        else:
            system_text = self.system_prompt
            contents = _openai_messages_to_gemini(self.history)
            if prompt:
                contents.append({"role": "user", "parts": [{"text": prompt}]})

        # Determine which model to use based on last user message
        model_prompt = prompt
        if not model_prompt and messages:
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    model_prompt = msg.get("content", "")
                    break

        selected_model_name = self.select_model(model_prompt)

        # ── Instantiate generative model with system instruction ───────
        model = genai.GenerativeModel(
            model_name=selected_model_name,
            system_instruction=system_text,
            tools=self._tools,
        )

        # ── Call the API with streaming ────────────────────────────────
        try:
            response = model.generate_content(
                contents,
                stream=True,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.5,
                    max_output_tokens=8192,
                ),
            )
        except Exception as e:
            yield f"\n[Gemini API error: {e}]"
            return

        # ── Stream text tokens and collect function calls ──────────────
        for chunk in response:
            # Text token
            try:
                text = chunk.text
                if text:
                    yield text
            except Exception:
                pass  # chunk has no text (e.g. function_call only)

            # Function call parts
            try:
                for part in chunk.candidates[0].content.parts:
                    if hasattr(part, "function_call") and part.function_call.name:
                        fc = part.function_call
                        args_dict = dict(fc.args) if fc.args else {}
                        self._last_tool_calls.append({
                            "id": f"call_{fc.name}",
                            "type": "function",
                            "function": {
                                "name": fc.name,
                                "arguments": json.dumps(args_dict, ensure_ascii=False),
                            },
                        })
            except Exception:
                pass

        # Update internal history if called without external messages
        if messages is None:
            if prompt:
                self.history.append({"role": "user", "content": prompt})
            assistant_msg: Dict[str, Any] = {
                "role": "assistant",
                "content": "",  # text already yielded
            }
            if self._last_tool_calls:
                assistant_msg["tool_calls"] = self._last_tool_calls
            self.history.append(assistant_msg)
            if len(self.history) > 20:
                self.history = self.history[-20:]

    def get_last_tool_calls(self) -> List[Dict[str, Any]]:
        """Return tool calls from the most recent assistant turn."""
        return self._last_tool_calls

    def reset_history(self) -> None:
        """Clear internal conversation history."""
        self.history.clear()

    def ask(self, prompt: str, context: str = "") -> str:
        """Non-streaming convenience wrapper (backward compatibility)."""
        return "".join(self.ask_stream(prompt, context))
