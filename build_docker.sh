#!/bin/bash
set -e

# Build the image for linux/amd64
echo "Building Docker image for linux/amd64..."
docker build --platform linux/amd64 -t gemini-project:v10.4 .

# Save the image to a tar file
echo "Saving image to gemini-project-v10.4-amd64.tar..."
docker save -o gemini-project-v10.4-amd64.tar gemini-project:v10.4

echo "Done! Image saved to gemini-project-v10.4-amd64.tar"
