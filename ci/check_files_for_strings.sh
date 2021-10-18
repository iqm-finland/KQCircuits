#!/bin/bash
#
# Check if strings, defined in the input file, exist in files or filenames in
# this directory. Some directories are excluded as defined in this file.
#
# There should be one string per line in the input file.
# Returns 0 if no instances of the strings are found, returns 1 otherwise.
#
# usage: ci/check_files_for_strings.sh strings_to_find.txt

file="$1"

excluded_paths=( \
"*.pip-cache*" \
"*.git*" \
"*.png" \
"*.gif" \
"*tmp" \
"*pycache*" \
"./grain.xml" \
)
for path in "${excluded_paths[@]}"; do
  # arguments for "find" to exclude paths
  path_arguments+=(-path "$path" -prune -o)
done

echo "Checking files for strings given in $file..."

found_string=false

echo "Filenames or folder names containing given strings:"
if find . | grep -if "$file"; then
  found_string=true
fi

echo "Files containing given strings:"
if find . "${path_arguments[@]}" -type f -exec grep -ilf "$file" {} +;
then
  found_string=true
fi

if [ "$found_string" = true ]; then
  echo "Found instances of given strings."
  exit 1
else
  echo "No instances of given strings found."
  exit 0
fi
