# Rhino 3D Python Development Rules

This project is a Rhino 3D package developed using Python for Rhino. All development within this workspace must adhere to the following standards and architectural patterns.

## Core Mandates

### 1. Language & Library Selection
- **Primary Language:** Python (IronPython 2.7 or CPython 3 depending on the Rhino version, assume Rhino 8+ CPython unless specified).
- **Primary Library:** Use `Rhino` and `Rhino.Geometry` (RhinoCommon) along with `scriptcontext` as the primary API for this project. It provides better performance, robustness, and direct control over Rhino objects.
- **Secondary Library:** Use `rhinoscriptsyntax` (`import rhinoscriptsyntax as rs`) only for rapid prototyping or simple document interactions where RhinoCommon is excessively verbose.
- **Documentation:** Reference the [RhinoCommon API Reference](https://developer.rhino3d.com/api/RhinoCommon/html/N_Rhino_Geometry.htm) and [RhinoScriptSyntax Web Help](https://developer.rhino3d.com/api/rhinoscript/).

### 2. Geometry & Document Standards
- **Unit Awareness:** Always check and respect the document units (e.g., `scriptcontext.doc.ModelUnitSystem`).
- **Object Management:** Disable redraw during complex operations using `scriptcontext.doc.Views.RedrawEnabled = False` and re-enable it (`True`) at the end to improve performance and UI stability.
- **Layering:** Organize generated geometry into logical layers. Create or access layers via `scriptcontext.doc.Layers`.
- **Cleanup:** Ensure that any temporary geometry used for calculations is properly disposed of, or simply not added to the active document until final output.

### 3. Coding Style
- **Naming Conventions:** Use `PascalCase` for classes and `snake_case` for functions and variables, following Python PEP 8 where it doesn't conflict with Rhino-specific patterns.
- **Modularization:** Keep commands focused. Abstract reusable geometric logic into helper functions or classes within the `src/` directory.
- **Error Handling:** Use `try...except` blocks to catch Rhino-specific errors and provide clear feedback to the user via `rs.Print()` or `rs.MessageBox()`.

### 4. Rhino Command Structure
- Most scripts in `src/` are intended to be run as Rhino commands. 
- Ensure scripts are structured to be compatible with the Rhino Script Editor and the `.rhproj` project structure.
- Use `if __name__ == "__main__":` blocks to allow scripts to be run directly or imported.
- **Interactive UI with Live Previews:** Scripts should strive to use interactive property lists or command-line prompts combined with a real-time live preview of the generated geometry. Update the preview as the user changes parameters.
- **Select Last Convenience:** ALWAYS design scripts so that the final geometry objects created get selected at the end of the script (similar to Rhino's native `SelLast` functionality). This improves the user's workflow tremendously.

## Reference Resources
- [RhinoScriptSyntax API Reference](https://developer.rhino3d.com/api/rhinoscript/)
- [RhinoCommon API Reference](https://developer.rhino3d.com/api/RhinoCommon/html/N_Rhino_Geometry.htm)
- [Rhino Python Guides](https://developer.rhino3d.com/guides/rhinopython/)
