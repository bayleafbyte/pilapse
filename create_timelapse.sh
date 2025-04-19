#!/bin/bash

# Name of the output timelapse video
OUTPUT="timelapse.mp4"

# Step 1: Delete the old timelapse if it exists
if [ -f "$OUTPUT" ]; then
    echo "Deleting old timelapse video: $OUTPUT"
    rm "$OUTPUT"
fi

# Step 2: Create new timelapse from images
echo "Creating new timelapse..."
ffmpeg -framerate 10 -pattern_type glob -i '*.jpg' -c:v libx264 -pix_fmt yuv420p "$OUTPUT"

echo "Done! New timelapse saved as $OUTPUT"
