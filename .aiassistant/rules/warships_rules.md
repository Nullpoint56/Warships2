---
apply: always
---

# AI Assistant Rules

## PowerShell Constraint

Only use .NET (System.IO) APIs for filesystem access.

The following are PROHIBITED:
- Get-ChildItem
- gci
- dir (alias)
- Select-Object
- Where-Object for filesystem filtering

Recursive traversal MUST use:
[System.IO.Directory]::EnumerateFiles
[System.IO.Directory]::EnumerateDirectories
[System.IO.Directory]::EnumerateFileSystemEntries

This rule has no exceptions.

