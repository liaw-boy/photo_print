# Project Initialization Guide: Automated Photo Border Processing Script

## Project Overview
You are now a senior image processing and automation development expert. I need your assistance in developing an automation script whose functionality matches the "add border and export" feature of Adobe Lightroom for iPad. 
This script must be able to read photos, automatically calculate and apply borders based on configured ratios, and export high-quality images.

## Core Requirements
1. **Border Calculation & Padding Logic**:
   - Support adding borders by percentage (e.g., extending outward based on a specific percentage of the image's long or short edge).
   - Support target aspect ratio padding (e.g., padding photos of any aspect ratio to fit common social media dimensions like 1:1 or 4:5 without altering the original image's aspect ratio).
2. **Image Quality & Photography Data Preservation**:
   - The exported image must maintain the original high resolution and lossless visual quality.
   - **MUST completely preserve the original photo's EXIF metadata** (including camera model, aperture, shutter speed, ISO, etc., as this is crucial for photography works).
   - Correctly handle and preserve the original file's Color Space (e.g., sRGB / Adobe RGB).
3. **Batch Processing Automation**:
   - Support specifying an input directory to automatically process all photos within it in batches, outputting them to a designated output directory.
   - Provide a simple and user-friendly execution method (e.g., a well-designed Command Line Interface / CLI).
4. **Technical & Architectural Preferences**:
   - The project must be developed using open-source and free ecosystems/tools (e.g., Python with Pillow / ImageMagick).
   - The codebase must feature a modular design so that other image processing modules (such as adding watermarks or applying LUT filters) can be easily integrated in the future.

## Your Initial Tasks
Please carefully read the requirements above and provide the following to kick off our project:
1. Recommend the most suitable programming language and open-source image processing libraries for this requirement, and briefly explain the reasons for your choice.
2. Outline the foundational architecture and core execution workflow of this automation script.
3. Write an initial MVP (Minimum Viable Product) code example, focusing on demonstrating "how to calculate and add borders" and "how to losslessly transfer EXIF data when saving the new file."

*Note: Please use Traditional Chinese for all subsequent technical discussions and development guidance.*
