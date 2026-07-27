# Local runtime

Citadex Local runs `Qwen2.5-Coder-1.5B-Instruct Q4_K_M` through an embedded
llama.cpp server.

## Runtime layout

```text
Citadex Local/
├── Citadex-Local.exe
├── models/
│   └── qwen2.5-coder-1.5b-instruct-q4_k_m.gguf
└── runtime/
    ├── llama-server.exe
    └── required DLL files
```

The server binds only to `127.0.0.1:11435`, starts with Citadex, and stops when
Citadex exits. Inference is limited to two CPU threads to reduce sustained CPU
load on entry-level computers.

## Tool calling

The local client uses the same tool registry, path validation, permissions,
budgets, undo system, and post-change verification as the API edition.

Small local models sometimes return a tool call as a fenced JSON object instead
of a native protocol call. Citadex accepts exactly one structurally valid
`{"name": ..., "arguments": ...}` object. Multiple or malformed calls are
rejected instead of executed.

## Building

Create a portable bundle:

```powershell
.\build_local.bat
```

Create the lightweight web installer:

```powershell
.\build_installer.bat
```

The installer downloads the model from the official Qwen Hugging Face
repository and verifies its pinned SHA-256 checksum.

