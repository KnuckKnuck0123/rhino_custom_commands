# Rhino Toolbelt01

A custom collection of Python scripts for Rhino 8, focused on generative grids and cyberpunk detailing.

## Tools Included

### 1. Grid

A simple utility to generate a perfect orthogonal grid.
- **Usage**: `Grid` command
- **Inputs**: X/Y Cells, Spacing

### 2. WavyGrid

Generates a chaotic, fabric-like grid using interpolated curves and random jitter.
- **Usage**: `WavyGrid` command
- **Inputs**: X/Y Cells, spacing, and a Chaos Factor

### 3. DiagGrid

A hybrid grid generator that can mix Diagonal (Diamond), Rectangular, or Hybrid cells.
- **Usage**: `DiagGrid`
- **Modes**:
  - Mode 0: Diagonal Only
  - Mode 1: Hybrid (Union Jack)
  - Mode 2: Random Mix

### 4. CyberPanels

A recursive subdivision tool (greebler) for surfaces.
- **Usage**: `CyberPanels`
- **Features**:
  - Recursively splits surface into panels
  - Adds random extrusions (solid blocks)
  - Adds random "Pipe Frames" for structural variety
  - Works on **Curved Surfaces** (Spheres, Toroids) using Geodesic paths

### 5. WildArray

A powerful MASH-style array tool that supports both ordered (linear) and chaotic (random) distributions.
- **Usage**: `WildArray`
- **Features**:
  - **3D Grid Support**: Array objects in X, Y, and Z axes simultaneously
  - **Dual Modes**: Interpolate transforms (Linear) or randomize them (Wild)
  - **Full Control**: Customize translation, rotation, and scaling variations
  - **Interactive Loop**: Preview and edit parameters instantly without restarting

### 6. PolygonalPipe

Creates a pipe along a curve with options for custom profiles.
- **Usage**: `PolygonalPipe2`
- **Profiles**: Round, Triangle, or Rectangle/Box

### 7. RandomExtrusion

Randomly extrudes selected curves, surfaces, or SubD objects.
- **Usage**: `RandomExtrusion`
- **Features**:
  - Assigns unique random heights to each object within a Min/Max range
  - Great for creating cities or greeble landscapes quickly

### 8. RandomBrickPile

Generates a chaotic, conical pile of bricks using a Gaussian distribution.
- **Usage**: `RandomBrickPile`
- **Inputs**: Number of bricks, Center point

### 9. RigidBrickPile

Simulates physically stacking bricks by "dropping" them one by one.
- **Usage**: `RigidBrickPile`
- **Features**:
  - Raycasts against previously placed bricks to prevent overlaps
  - Creates a more realistic, stacked appearance than the random pile
  - **Warning**: Slower than RandomBrickPile for large numbers of bricks due to collision checks



This project is set up for VS Code.
- **Run**: Open any script in `src/` and press `Cmd + Shift + B` to execute it in running Rhino instance.
