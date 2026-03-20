# Rhino Custom Commands Workshop Template

Welcome to the Rhino Custom Commands Workshop! This repository is designed as a blank slate for participants to draft, run, and compile their own Python scripts within Rhino 8.

## 📁 Repository Structure

- `src/2D/`: Directory for drafting your 2D generative and automation scripts.
- `src/3D/`: Directory for drafting your 3D generative and solid manipulation scripts.
- `README.md`: This file! Instructions for configuring your environment.
- `Gemini.md`: The agent instruction file. This ensures your AI pair-programmer is customized specifically to act as an expert in Rhino.Common and Rhino.Python geometry manipulation.

## 🚀 Execution & Hotkeys

This setup is optimized for **VS Code, Antigravity + Rhino 8**. You can write your script and instantly execute it without switching context!

1. **Launch Rhino 8** and leave it running.
2. **Open this folder** in VS Code.
3. Open or draft any `.py` script in the `src/` directory.
4. **Execute the script instantly** inside Rhino using the built-in system task:
   - **Mac**: Press `Cmd + Shift + B`
   - **Windows**: Press `Ctrl + Shift + B`
5. **Debug**: Press `F5` to attach the debugger (requires `EditPythonScript` -> Options -> Debugger to be enabled in Rhino; alternatively, use RhinoCode's debugging interface).

## 🧰 Prerequisites & Extensions

Make sure you have installed the required extensions in your IDE (such as the official **Rhino** or **RhinoPython** extensions for VS Code) to get autocompletion and linting for `rhinoscriptsyntax` and `Rhino` modules.

### Path Configuration (Optional)

Adding the modern `rhinocode` CLI to your system's PATH variable allows you to run Rhino scripts from any terminal.

**Mac:**
Run this command in your terminal to append the bin path to your `~/.zshrc`:
```bash
echo 'export PATH="$PATH:/Applications/Rhino 8.app/Contents/Resources/bin"' >> ~/.zshrc
source ~/.zshrc
```

**Windows:**
Run this command in an **Administrator PowerShell** window:
```powershell
[System.Environment]::SetEnvironmentVariable('Path', $env:Path + ';C:\Program Files\Rhino 8\System', [System.EnvironmentVariableTarget]::Machine)
```

## 🛠 Building a Rhino Plugin
When you are ready to wrap all of your scripts into a proper Rhino Plugin (`.rhp`), open the `ScriptEditor` inside Rhino 8, build a new Project, and point it to the scripts you developed here in the `src/` directory!
