# Windows EXE Build

Install dev tools with uv:

```powershell
uv sync --group dev
```

Use the script from project root:

```powershell
.\scripts\build_exe.ps1
```

Output:
- `dist\Warships\Warships.exe`

## Debug Build (console traceback)

```powershell
.\scripts\build_exe.ps1 -DebugConsole
```

Output:
- `dist\WarshipsDbg\WarshipsDbg.exe`

## Notes

- This build path is intentionally CLI-based (not `Warships.spec`) because it reliably bundles `pygfx`, `wgpu`, and `rendercanvas` resources.
- The script also bundles `glfw3.dll` from:
  - `.venv\Lib\site-packages\glfw\glfw3.dll`
- Preset data is **not** bundled into the EXE package; presets are created/managed at runtime.
