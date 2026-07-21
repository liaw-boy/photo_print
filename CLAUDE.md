# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

No code exists yet. This repository currently contains only the project brief:
- `Photo_Border_Automation_Init.md` (Traditional Chinese, canonical version)
- `Photo_Border_Automation_Init_EN.md` (English translation, same content)

Both files describe the same initial request and should be kept in sync if edited — treat the Traditional Chinese version as canonical per its closing instruction.

## Project Intent

An automation script that replicates Adobe Lightroom for iPad's "add border and export" feature: read photos, calculate and apply borders based on configured ratios, and export high-quality images.

Core requirements from the brief:
1. **Border/padding logic** — add borders by percentage of the image's long/short edge, and pad to target aspect ratios (e.g. 1:1, 4:5 for social media) without altering the original image's aspect ratio.
2. **Quality & metadata preservation** — exported images must keep original resolution and lossless visual quality, fully preserve EXIF (camera model, aperture, shutter speed, ISO, etc.), and correctly handle color space (sRGB / Adobe RGB).
3. **Batch processing** — process all photos in an input directory to an output directory via a CLI.
4. **Architecture preference** — open-source/free stack (e.g. Python + Pillow/ImageMagick), modular design so future modules (watermarking, LUT filters) can be added without reworking the core.

## Working Language

Per the project brief, conduct technical discussion and development guidance in Traditional Chinese (繁體中文).
