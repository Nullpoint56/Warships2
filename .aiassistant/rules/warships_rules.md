---
apply: always
---

# AI Assistant Rules

## 1. PowerShell File System Enumeration

For recursive filesystem operations:

- DO NOT use: `Get-ChildItem -Recurse`
- DO NOT pipe to `Select-Object FullName` for large trees
- DO NOT perform late filtering in `Where-Object`

Use .NET streaming APIs instead:

Files:
[System.IO.Directory]::EnumerateFiles(path, pattern, SearchOption)

Directories:
[System.IO.Directory]::EnumerateDirectories(path, pattern, SearchOption)

Files + Directories:
[System.IO.Directory]::EnumerateFileSystemEntries(path, pattern, SearchOption)

Always pass:
[System.IO.SearchOption]::AllDirectories

Filter using the `pattern` parameter when possible (e.g., "*.md").

Rationale:
PowerShell materializes FileInfo objects and is significantly slower for large trees.
.NET Enumerate* APIs are streaming and allocation-light.

Exception:
Use Get-ChildItem only if non-filesystem providers (registry, cert store) or rich metadata is explicitly required.
