# Icon Files Required

Please add the following icon files to this directory before building:

- `32x32.png` - 32x32 pixels PNG icon
- `128x128.png` - 128x128 pixels PNG icon
- `128x128@2x.png` - 256x256 pixels PNG icon (for high DPI)
- `icon.icns` - macOS icon file (optional for Windows build)
- `icon.ico` - Windows icon file (recommended)

## Quick Solution

You can use the existing `frontend/public/favicon.svg` as a base and convert it to PNG/ICO formats using online tools:

1. https://cloudconvert.com/svg-to-png
2. https://cloudconvert.com/png-to-ico

Or use ImageMagick:
```bash
convert -background none -size 32x32 frontend/public/favicon.svg icons/32x32.png
convert -background none -size 128x128 frontend/public/favicon.svg icons/128x128.png
convert -background none -size 256x256 frontend/public/favicon.svg icons/128x128@2x.png
convert -background none -size 256x256 frontend/public/favicon.svg icons/icon.ico
```

## Temporary Solution

If you don't have icons ready, you can comment out the `icon` section in `src-tauri/tauri.conf.json`:

```json
"bundle": {
  "active": true,
  "targets": ["msi", "nsis"],
  // "icon": [...],
  ...
}
```

Tauri will use default icons in this case.
