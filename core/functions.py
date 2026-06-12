"""core/functions.py — OpenAI-compatible function definitions for the agent.

These schemas are passed as the ``functions`` parameter in the chat completion
request so the model knows which tools it can call.
"""
from typing import List, Dict, Any

FUNCTION_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "create_file",
        "description": "Create a new file (or overwrite an existing one) with the given content.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path (from project root) for the file to create, e.g. 'src/main.py'.",
                },
                "content": {
                    "type": "string",
                    "description": "Full content of the file.",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": (
            "Apply one or more line-range patches to an existing file. "
            "Each patch replaces lines [start_line, end_line) with new_content."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file to edit.",
                },
                "patches": {
                    "type": "array",
                    "description": "List of patches to apply in order.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "start_line": {
                                "type": "integer",
                                "description": "1-based line number to start replacing from.",
                            },
                            "end_line": {
                                "type": "integer",
                                "description": "Exclusive end line number (last line replaced = end_line - 1).",
                            },
                            "new_content": {
                                "type": "string",
                                "description": "Replacement text (including newline at end if needed).",
                            },
                        },
                        "required": ["start_line", "end_line", "new_content"],
                    },
                },
            },
            "required": ["path", "patches"],
        },
    },
    {
        "name": "delete_file",
        "description": "Permanently delete a file inside the project root.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file to delete.",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "make_directory",
        "description": "Create a directory (and all intermediate parents) inside the project root.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path of the directory to create, e.g. 'src/utils'.",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "execute_cmd",
        "description": (
            "Execute a shell command inside the project root directory. "
            "Only whitelisted commands are allowed: python, git, pip, npm, node, cargo, go, ls, dir, echo, cat."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The full command string to execute, e.g. 'python agent_test.py'.",
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "list_directory",
        "description": "List files and directories inside a given path within the project root.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to list (empty string = project root).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "read_file",
        "description": "Read and return the content of a file inside the project root (up to 5 KB).",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file to read.",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "search_in_files",
        "description": "Search for a text pattern across all project source files. Use this to find where a function/class/variable is defined or used before editing.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Text or pattern to search for (case-insensitive).",
                },
                "path": {
                    "type": "string",
                    "description": "Subdirectory to limit search to (optional, default: entire project).",
                },
            },
            "required": ["pattern"],
        },
    },
]

__all__ = ["FUNCTION_DEFINITIONS"]
