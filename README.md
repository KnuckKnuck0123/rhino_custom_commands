# Rhino Geometry Arsenal NK ⚔️

**Rhino Geometry Arsenal NK** is a curated collection of high-performance Python scripts for Rhino 8, designed for generative architecture, detailing, and complex greeble generation.

## 🧰 The Arsenal

### **2D Generators**

| Command | Description |
| :--- | :--- |
| **`VariableGrille`** | Generates vertical variable grilles with random height variations inside curves or on surfaces. |
| **`GridCurtainWall`** | Parametric 2D grid generation for glass panels, mullions, and frames. Supports custom surface boundaries, grid rotation, jitter, and automated 3D curvature mapping. |
| **`WavyGrid`** | Creates chaotic, fabric-like grids using interpolated curves and random jitter. |
| **`DiagGrid`** | A hybrid grid generator for Diamond, Rectangular, or Union Jack patterns. |
| **`StandardGrid`** | Standard orthogonal grid utility. |

### **3D Generators**

| Command | Description |
| :--- | :--- |
| **`WildArray`** | **(MASH-style)** Powerful 3D array tool with linear/random modes for translation, rotation, and scale. |
| **`CyberPanels`** | Recursive subdivision tool for sci-fi panels, extracting pipes and extrusions on any surface. |
| **`RandomBrickPile`** | Generates a chaotic, conical pile of bricks using Gaussian distribution. |
| **`RigidBrickPile`** | Physically simulates stacking bricks by raycasting to prevent overlaps (slower, more realistic). |
| **`PolygonalPipe`** | Sweeps custom profiles (Round, Triangle, Rect) along curves. |
| **`RandomExtrusion`** | Randomly extrudes curves/surfaces to different heights (City generator). |
| **`SurfaceGridArray`** | Maps objects onto a surface grid (UV based). |

## 🚀 Usage

This arsenal is optimized for **VS Code + Rhino 8**.

1. **Open** this folder in VS Code.
2. **Open** any script in `src/`.
3. **Press `Cmd + Shift + B`** to execute the script instantly in your running Rhino instance.
4. **Debug**: Press `F5` to attach the debugger (requires `EditPythonScript` -> Options -> Debugger enabled in Rhino).

## 🛠️ Installation & Plugin Creation

### 🚀 Drag & Drop Installation (Rhino 8)
The fastest way to install all the scripts as custom commands without compiling:

**For Windows & Mac:**
1. Open a new or existing document in Rhino 8.
2. Drag and drop the `Rhino_Geometry_Arsenal_NK.rhproj` file directly from your file browser onto the open Rhino workspace.
3. Rhino will parse the project and automatically register each python script within the `src/` folder as a native Rhino command.

### Running as Scripts
Clone this repository into your Rhino scripts folder or use the VS Code workspace directly.

### Baking as a Rhino Plugin (.rhp)
To compile this project into a standalone Rhino plugin:
1. Open Rhino 8 and run the `ScriptEditor` command.
2. Open the `Rhino_Geometry_Arsenal_NK.rhproj` project file within the Script Editor.
3. Click the **Publish** button in the Script Editor toolbar.
4. Follow the prompts to build the `.rhp` plugin or `.yak` package, which can then be installed via the Rhino Plugin Manager or Package Manager.

## 📄 License

MIT License.
