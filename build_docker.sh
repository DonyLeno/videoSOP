#!/bin/bash
set -e

# Build the image for linux/amd64
echo "Building Docker image for linux/amd64..."
docker build --platform linux/amd64 -t gemini-project:latest .

# Save the image to a tar file
echo "Saving image to gemini-project-amd64.tar..."
docker save -o gemini-project-amd64.tar gemini-project:latest

echo "Done! Image saved to gemini-project-amd64.tar"
