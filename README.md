# Rhino Array Tools

Development branch for a future Rhino 8 array tools package for Windows and macOS.
The only workflow carried over from the original collection is the editor test hotkey.
No existing array tools or package definitions are included yet.

## Test from the editor

1. Open **this folder** (`array-tools`) in VS Code or a compatible editor so its workspace task is loaded.
2. Open Rhino 8.11 or newer with a document, then run `StartScriptServer` in Rhino. You can add this to Rhino startup commands.
3. Open and save `src/TestConnection.py` to check the connection, or your own Python command script in `src/`.
4. Press **Cmd+Shift+B** on macOS or **Ctrl+Shift+B** on Windows.
5. Respond to any command prompts in Rhino. The connection check only prints a message; it does not modify geometry.

The default build task, `Run Rhino 8 Script`, sends the active saved file to the running Rhino instance with `rhinocode script`. No plugin installation or manual `RunPythonScript` invocation is needed. This executes source code inside Rhino; it does not register or test an installed plugin command.

The task uses the standard Rhino 8 locations on each OS; no PATH setup is required:

- macOS: `/Applications/Rhino 8.app/Contents/Resources/bin/rhinocode`
- Windows: `C:\Program Files\Rhino 8\System\rhinocode.exe`

For a custom Rhino installation, update the corresponding command in `.vscode/tasks.json`. Keep a single Rhino instance open for straightforward targeting.

[McNeel RhinoCode CLI documentation](https://developer.rhino3d.com/en/guides/scripting/advanced-cli/)

## Array tool development

Add Python 3 command scripts under `src/` with a `main()` entry point guarded by `if __name__ == "__main__":`. Prefer RhinoCommon and platform-independent paths. Verify interactive behavior on both Windows and macOS before packaging.

When the command set is ready, create a new project in Rhino 8's Script Editor and publish the array commands as a plugin/package. Package identity, versioning, and build artifacts are intentionally deferred until then.

[McNeel script plugin publishing guide](https://developer.rhino3d.com/guides/scripting/projects-publish/)
