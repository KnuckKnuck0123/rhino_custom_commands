# Rhino Geometry Arsenal NK ⚔️

**Rhino Geometry Arsenal NK** is a curated collection of high-performance Python scripts for Rhino 8, designed for generative architecture, detailing, and complex greeble generation.

> [!NOTE]  
> 🎓 **Workshop Participants**: If you are taking the SCI-Arc Python workshop, please switch to the `workshop-template` branch! That branch contains an empty repository shell and setup instructions designed specifically for the class.

## 🧰 The Arsenal

### **2D Generators**

| Command | Description |
| :--- | :--- |
| **`VariableGrille`** | Generates vertical variable grilles with random height variations inside curves or on surfaces. |
| **`GridCurtainWall`** | Parametric 2D grid generation for glass panels, mullions, and frames. Supports custom surface boundaries, grid rotation, jitter, and automated 3D curvature mapping. |
| **`ContinuousCurtainWall`** | Generates continuous curtain walls along guided paths and frames. |
| **`CurtainWall`** | Parametric curtain wall generator working on surfaces or closed curves (extruded to height). |
| **`Storefront`** | Auto-generates storefront mullion systems on planar boundaries. |
| **`Pill`** | Auto-drafting command to quickly draw a parametrically controlled 2D Pill shape. |
| **`WavyGrid`** | Creates chaotic, fabric-like grids using interpolated curves and random jitter. |
| **`DiagGrid`** | A hybrid grid generator for Diamond, Rectangular, or Union Jack patterns. |
| **`StandardGrid`** | Standard orthogonal grid utility. |

### **3D Generators**

| Command | Description |
| :--- | :--- |
| **`WildArray`** | **(MASH-style)** Powerful 3D array tool with linear/random modes for translation, rotation, and scale. |
| **`CyberPanels`** | Recursive subdivision tool for sci-fi panels, extracting pipes and extrusions on any surface. |
| **`SurfaceSubdivider`** | Recursive Mondrian-style subdivision mapping to organic shapes. |
| **`RandomBrickPile`** | Generates a chaotic, conical pile of bricks using Gaussian distribution. |
| **`RigidBrickPile`** | Physically simulates stacking bricks by raycasting to prevent overlaps (slower, more realistic). |
| **`RigidStickPile`** | Rigid body simulation for dropping structural sticks/beams into a realistic pile. |
| **`StairGenerator`** | Parametric IBC-compliant stair generator (Straight, L-Shape, U-Shape, Spiral). |
| **`PolygonalPipe`** | Sweeps custom profiles (Round, Triangle, Rect) along curves. |
| **`VariableOffset`** | Advanced offset tool to vary offset distances (Curve/Surface) with sine, noise, or linear interpolation. |
| **`RandomExtrusion`** | Randomly extrudes curves/surfaces to different heights (City generator). |
| **`SurfaceGridArray`** | Maps objects onto a surface grid (UV based). |

## 🚀 Usage

This arsenal is optimized for **VS Code + Rhino 8**.

1. **Open** this folder in VS Code.
2. **Open** any script in `src/`.
3. **Execute the script** instantly in your running Rhino instance:
   - **Windows**: Press `Ctrl + Shift + B`
   - **Mac**: Press `Cmd + Shift + B`
4. **Debug**: Press `F5` to attach the debugger (requires `EditPythonScript` -> Options -> Debugger enabled in Rhino).

## ⚙️ Path Configuration (Optional)

Adding `rhinocode` to your system PATH allows you to run Rhino scripts from any terminal window without typing the full path to the executable.

**Mac:**
Run this in your terminal to append it to your zsh profile:
```bash
echo 'export PATH="$PATH:/Applications/Rhino 8.app/Contents/Resources/bin"' >> ~/.zshrc
source ~/.zshrc
```

**Windows:**
Run this in an **Administrator PowerShell**:
```powershell
[System.Environment]::SetEnvironmentVariable('Path', $env:Path + ';C:\Program Files\Rhino 8\System', [System.EnvironmentVariableTarget]::Machine)
```

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
