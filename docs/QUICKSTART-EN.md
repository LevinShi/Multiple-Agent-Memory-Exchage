# Getting started

Use macOS or Linux with Python 3.10+. Native Windows is not supported. Your coding clients must be able to run local commands. The core uses Python's standard library and does not require a separate model API key; your AI clients retain their own account and billing requirements.

## Run the offline demo

From the extracted source directory:

```sh
python3 demo.py
```

`synthetic_cli_relay: passed` confirms the CLI handoff works on synthetic data in a temporary directory. It does not launch AI clients or prove that a model follows its rules.

## Connect two clients

```sh
python3 init_vault.py "$HOME/local-agent-memory-demo" --demo
```

This creates a new vault with read/write access for the four supported actors on the synthetic `demo` project only. Export remains disabled. Existing directories are never overwritten.

Copy the appropriate generated `ENTRY-*.md` instructions into each client's supported default or project rules. Preserve existing rules, then start new conversations. Templates are provided for Codex, Cursor, ZCode, and MiniMax Code; exact rule locations vary by client version. See [client notes (Chinese)](CLIENTS.md).

Ask the first client to plan a small task in the `demo` project, then ask the second to continue it. Inspect the actual tool calls: the first vault operation should be `gateway.py begin`, saving should return a record ID, and the second client should read the new record. A verbal claim to have remembered something is not evidence.

## Authorize real projects separately

```sh
python3 init_vault.py "$HOME/local-agent-memory-vault"
```

This vault starts with no project access. Have the maintainer configure `permissions.json` according to your explicit choices: which project, which actors, and whether each may read, write, or export. The [policy examples](PERMISSIONS.md) show the format. Client identity is self-reported; this is not OS-level isolation.

Keep the vault outside the public code repository. Do not upload personal records, policies, raw chats, or private capture data. The project stores files locally, but cloud-based AI clients may send the context they read to their model providers.

## Storage and optional capture

Shared notes have no vault-wide hard storage cap. Save concise updates rather than complete transcripts. Optional private capture deduplicates content and pauses at a default 50 MiB limit; backups and Git history take additional space. Soft deletion retains original data.

Gemini capture is experimental and not needed for the core workflow. Live testing is paused; long histories, complex replies, and real account switching remain unverified. Do not send repeated test messages just to exercise the capture feature.

## Developer checks

```sh
python3 -m unittest discover -v
python3 demo_capture.py
```

Both use synthetic data. Client actions go through `gateway.py begin`; subsequent search/show/save/evidence calls use the returned run ID with the same actor and project. See [ENTRY.template.md](../ENTRY.template.md) and the [import format](IMPORT-FORMAT.md).
