"""Definitions for the tools shipped with Citadex."""

from core.tools.models import ToolDefinition, ToolRisk

BUILTIN_TOOL_DEFINITIONS = (
    ToolDefinition(
        name="create_file",
        description="Create a new file or overwrite an existing one with the given content.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path from the project root, for example 'src/main.py'.",
                },
                "content": {"type": "string", "description": "Full content of the file."},
            },
            "required": ["path", "content"],
        },
        risk=ToolRisk.PROJECT_WRITE,
    ),
    ToolDefinition(
        name="edit_file",
        description=(
            "Apply one or more line-range patches to an existing file. "
            "Each patch replaces lines [start_line, end_line) with new_content."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path to the file to edit."},
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
                                "description": "Exclusive end line number.",
                            },
                            "new_content": {
                                "type": "string",
                                "description": "Replacement text.",
                            },
                        },
                        "required": ["start_line", "end_line", "new_content"],
                    },
                },
            },
            "required": ["path", "patches"],
        },
        risk=ToolRisk.PROJECT_WRITE,
    ),
    ToolDefinition(
        name="delete_file",
        description="Permanently delete a file or directory inside the project root.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path to delete."},
            },
            "required": ["path"],
        },
        risk=ToolRisk.PROJECT_DELETE,
    ),
    ToolDefinition(
        name="make_directory",
        description="Create a directory and intermediate parents inside the project root.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative directory path."},
            },
            "required": ["path"],
        },
        risk=ToolRisk.PROJECT_WRITE,
    ),
    ToolDefinition(
        name="execute_cmd",
        description=(
            "Execute one allowlisted command inside the project root. Shell operators, redirects "
            "and inline interpreter code are forbidden."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "A single development command."},
            },
            "required": ["command"],
        },
        risk=ToolRisk.COMMAND_WRITE,
    ),
    ToolDefinition(
        name="list_directory",
        description="List files and directories inside the project root.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to list; empty means project root.",
                },
            },
            "required": [],
        },
        risk=ToolRisk.READ_ONLY,
    ),
    ToolDefinition(
        name="read_file",
        description="Read a file inside the project root.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path to the file."},
            },
            "required": ["path"],
        },
        risk=ToolRisk.READ_ONLY,
    ),
    ToolDefinition(
        name="search_in_files",
        description="Search for text across project source files before editing.",
        input_schema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Case-insensitive text to find."},
                "path": {
                    "type": "string",
                    "description": "Optional subdirectory; empty means the entire project.",
                },
            },
            "required": ["pattern"],
        },
        risk=ToolRisk.READ_ONLY,
    ),
)

BUILTIN_TOOL_DEFINITIONS += tuple(
    ToolDefinition(
        name=name,
        description=description,
        input_schema={
            "type": "object",
            "properties": properties,
            "required": required,
        },
        risk=risk,
    )
    for name, description, properties, required, risk in (
        (
            "move_file",
            "Move a file to another path inside the project.",
            {"source": {"type": "string"}, "destination": {"type": "string"}},
            ["source", "destination"],
            ToolRisk.PROJECT_WRITE,
        ),
        (
            "copy_file",
            "Copy a file to another path inside the project.",
            {"source": {"type": "string"}, "destination": {"type": "string"}},
            ["source", "destination"],
            ToolRisk.PROJECT_WRITE,
        ),
        (
            "file_exists",
            "Check whether a path exists inside the project.",
            {"path": {"type": "string"}},
            ["path"],
            ToolRisk.READ_ONLY,
        ),
        (
            "get_file_info",
            "Return safe metadata for a file or directory.",
            {"path": {"type": "string"}},
            ["path"],
            ToolRisk.READ_ONLY,
        ),
    )
)

BUILTIN_TOOL_DEFINITIONS += (
    ToolDefinition(
        name="git_status",
        description="Show the concise Git branch and working-tree status.",
        input_schema={"type": "object", "properties": {}, "required": []},
        risk=ToolRisk.READ_ONLY,
    ),
    ToolDefinition(
        name="git_diff",
        description="Show a bounded Git diff for the working tree or one path.",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Optional project-relative path."}},
            "required": [],
        },
        risk=ToolRisk.READ_ONLY,
    ),
)

BUILTIN_TOOL_DEFINITIONS += (
    ToolDefinition(
        name="run_tests",
        description="Run the project's detected test command, optionally scoped to one path.",
        input_schema={
            "type": "object", "properties": {"path": {"type": "string"}}, "required": [],
        },
        risk=ToolRisk.COMMAND_WRITE,
    ),
    ToolDefinition(
        name="format_code",
        description="Run the project's standard formatter on one project-relative path.",
        input_schema={
            "type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"],
        },
        risk=ToolRisk.COMMAND_WRITE,
    ),
)

__all__ = ["BUILTIN_TOOL_DEFINITIONS"]
