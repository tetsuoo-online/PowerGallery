# Power Gallery

A desktop application for visually comparing and evaluating AI-generated images, built with Python and PyQt6.

![alt text](assets/2026-03-27_09_52_07-PowerGallery_V9.webp)

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![PyQt6](https://img.shields.io/badge/PyQt6-6.x-green) ![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

---

## What it does

Power Gallery lets you load batches of images into a grid, compare them side by side, and evaluate them using structured criteria. At first it was designed for AI image generation workflows — particularly for comparing outputs from different Stable Diffusion checkpoints; now you can also use the grid as a DATASET EDITOR (for LoRA training).

**Key features:**

- **Multi-tab grid view** — organize images across up to 26 labeled tabs (A–Z)
- **Drag & drop** — load images or JSON session files directly into the app
- **Fullscreen comparison** — view any image full screen; drag a split handle to compare two images from different tabs side by side
- **Modules** — switch between evaluation modes:
  - *Checkpoint Manager* — rate images against named criteria (beauty, errors, LoRAs, prompts…), score each criterion manually as positive, neutral, or negative
  - *Dataset Manager* — view and edit the `.txt` caption file associated with each image; batch add or replace tags. Is not TXT is present, it will be created automatically as you fill up the text field, or deleted if you remove the text.
- **Resizable grid** — use the slider or Ctrl+scroll to zoom cards in/out
- **Session save/load** — export your grid to JSON and reload it later, including all ratings
- **Style editor** — customize the app's color theme with a visual editor, duplicate or delete custom themes
- **Multi-language** — UI available in English, French, German, Spanish but also Arabic, Chinese, Japanese and Brazilian Portuguese. Because why not ! haha

---

## Installation

```
INSTALL.BAT
```

Then launch with:

```
START.BAT
```

---

## Usage

1. Launch the app
2. Drag images (`.png`, `.jpg`, `.jpeg`, `.webp`) or a saved `.json` session onto the drop zone
3. Drag & drop between cards to change their order (a “push”, not a swap).
4. Click any image to open the fullscreen viewer; right-click for details
5. Use **Options** to choose a module, language, and import behavior
6. Use **Export** to save your grid as a JSON file for later

---

## Keyboard shortcuts

| Key | Action |
|---|---|
| `Space` / `F11` | Toggle controls & drop zone visibility |
| `Ctrl+Space` / `Ctrl+F11` | Toggle tab bar visibility |
| `F5` | Refresh all cards |
| `←` / `→` | Navigate images in fullscreen |
| `Esc` | Close fullscreen viewer |
| `Ctrl+Scroll` | Resize cards |

---

## Screenshots
 *- So many languages ! ^^ -*</br>
![alt text](assets/Options.webp)</br> 

 *- Checkpoint compare mode -*</br>
![alt text](assets/2026-03-27_08_56_34-PowerGallery_V9.webp)</br>

 *- Fun with style editor -*</br>
![alt text](assets/style_editor.webp)</br>

 *- Comparing images -*</br>
![alt text](assets/FullscreenView_1.webp)</br>


## 💡 Notes

✅ Duplicate images are automatically ignored</br>
🔄 Checkpoint names update automatically</br>
⏱️ Long press to drag, quick tap for fullscreen</br>
🔒 The first tab cannot be deleted</br>

## Project structure

```
v9/
├── config/          # Settings, styles, language files, style editor
│   └── custom_styles/   # User-created color themes
├── modules/         # Checkpoint Manager & Dataset Manager
├── widgets/         # Card detail dialog
└── power_gallery.py # Main entry point
```

## TODO

- add metadata reading
- export the grid in a single image, all customizable

---

## License : See `LICENSE`.

## 👤 Author : *Tetsuoo*

## 🙏 Credits : - **Claude AI ❤** - AI assistant extraordinaire