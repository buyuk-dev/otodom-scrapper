#!/bin/bash

# Loop over all files matching the pattern *.json.ai
for file in *.json.ai; do
  # Check if the file exists to avoid errors
  if [ -e "$file" ]; then
    # Extract the base name without the .json.ai extension
    base="${file%.json.ai}"
    # Rename the file to the new pattern
    mv "$file" "${base}.ai.json"
  fi
done