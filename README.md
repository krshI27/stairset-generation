# Stairset Generator

A procedural stair model web app for designing stair sets with customizable geometry, materials, lighting, and perspective.

## Project overview

The Stairset Generator is a small interactive web app that produces 3D stair models based on user input. It should support both technical stair design and creative visual exploration with configurable step dimensions, landings, handrails, materials, and projection modes.

## Goals

- Let users generate a stair assembly by defining step width, depth, height, and count.
- Allow the insertion of flat landing sections and multi-run stair arrangements.
- Provide optional handrails, balustrades, stringers, and support geometry.
- Render the stairset in a browser with lighting, color, reflectance, and surface materials.
- Support perspective switching: orthographic/parallel, single vanishing point, and multi-point perspective.
- Export geometry as 3D mesh data for further use.

## Target users

- Designers and architects exploring simple stair concepts
- Generative art makers and visualization enthusiasts
- Developers prototyping model generation and perspective rendering
- Educators demonstrating geometry and perspective principles

## Core features

1. Parameter panel
   - Step height, width, depth
   - Number of steps
   - Landing insertion points and landing depth
   - Handrail presence, height, thickness, and rail style
   - Material color, reflectance, and finish
   - Lighting intensity, direction, and type
   - Projection mode: parallel, single-point perspective, two-point perspective, three-point perspective

2. Procedural geometry engine
   - Generate step geometry from input dimensions
   - Add landing geometry where requested
   - Generate rails and posts based on handrail settings
   - Automatically connect treads and risers into a single mesh

3. Interactive rendering
   - Browser preview of the stairset
   - Lighting control for shadows and highlights
   - Material shading and reflectance
   - Camera controls for perspective type and viewpoint

4. Export and sharing
   - Export mesh as OBJ, STL, or glTF
   - Save configuration presets
   - Share a stair design URL or JSON parameter file

## Architecture

### Frontend / UI

- Parameter form and controls
- Preview canvas / 3D viewer
- Material and lighting panels
- Perspective mode selector

### Geometry generator

- Stair generator module
- Landing scheduler and run manager
- Handrail & baluster generator
- Mesh builder with face normals and UV hints

### Renderer

- Simple WebGL or Plotly/pythreejs preview
- Perspective camera system
- Lighting model supporting diffuse/specular
- Material/color pipeline

### Export module

- OBJ/STL/glTF writer
- JSON save/load for design parameters

## Implementation plan

### Phase 1: MVP

- Set up a new project directory with a Streamlit app or simple web app scaffold.
- Build a parameter panel for step height, width, depth, count, and landing insertion.
- Generate a basic stair model with treads and risers.
- Render a 3D preview using an embedded plot/threejs view.
- Add export to OBJ or glTF.

### Phase 2: Structure and materials

- Add support for flat landings and multiple stair runs.
- Implement handrails, posts, and simple balustrades.
- Add color, reflectance, and material presets.
- Improve the 3D preview with lighting controls.

### Phase 3: Perspective rendering

- Add projection mode switching between orthographic and perspective.
- Implement single-point and two-point perspective camera controls.
- Experiment with vanishing points and custom camera placements.
- Add a preset for classic architectural axonometric views.

### Phase 4: polish and exports

- Refine mesh generation and fix geometry issues.
- Add a scene background and ambient lighting presets.
- Support multiple export formats and download links.
- Add example presets such as straight run, split landing, and U-shaped stairs.

## Optional advanced work

- Add curved and spiral stair forms.
- Add a second camera mode for walkthrough animation.
- Add a custom perspective drawing overlay based on the Clip Studio article.
- Add support for importing custom profile shapes for rails and steps.
- Add UI for designing rail cross-sections and materials.

## Technologies

- Python + Streamlit for the initial web app
- `numpy` / `trimesh` / `meshio` for geometry generation
- `pythreejs`, `plotly`, or `stl_renderer` for browser preview
- `three.js` / React if a richer frontend is desired later
- `pillow` or vector export utilities for simple render output

## Local startup

### Python / Streamlit app

Option A: Use the dedicated Conda environment:

1. Create the Conda environment:

   ```bash
   conda env create -f environment.yml
   ```

2. Activate it:

   ```bash
   conda activate stairset-generation
   ```

3. Run the Streamlit app:

   ```bash
   streamlit run streamlit_app.py
   ```

Option B: Use a standard Python virtual environment:

1. Create a virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the Streamlit app:

   ```bash
   streamlit run streamlit_app.py
   ```

4. Open the local URL shown by Streamlit and interact with the stair generator.

### Optional JavaScript / Vite preview

If you want to run the existing Three.js prototype instead:

```bash
npm install
npm run dev
```

Then open the local URL shown by Vite.
