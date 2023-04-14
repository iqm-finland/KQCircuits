#!/bin/bash
#
# Check if strings, defined in the input file, exist in files or filenames in
# this directory. Some directories are excluded as defined in this file.
#
# There should be one string per line in the input file.
# Returns 0 if no instances of the strings are found, returns 1 otherwise.
#
# usage: ci/check_files_for_strings.sh strings_to_find.txt master 123-feature-branch

file="$1"
target_branch="$2"
source_branch="$3"

excluded_paths=( \
"*.pip-cache*" \
"*.git*" \
"*.png" \
"*.gif" \
"*.svg" \
"*tmp" \
"*pycache*" \
"./grain.xml" \
"*/.tox*"
)
for path in "${excluded_paths[@]}"; do
  # arguments for "find" to exclude paths
  path_arguments+=(-path "$path" -prune -o)
done

echo "Checking files for strings given in $file..."

found_string=false

echo "Filenames or folder names containing given strings:"
if find . -path "*refs/remotes*" -prune -o -print | grep -if "$file"; then
  found_string=true
fi

echo "Files containing given strings:"
if find . "${path_arguments[@]}" -type f -exec grep -ilf "$file" {} +; then
  found_string=true
fi

echo "Git diff or commit message history containing given strings:"
while IFS="" read -r p || [ -n "$p" ]; do

  # Check git diffs
  log_patch=$(git log -i --oneline -G "$p" "$target_branch..$source_branch")
  if [[ -n $log_patch ]]; then
    found_string=true
    echo "$p" "$log_patch"
  fi

  # Check commit messages
  log_grep=$(git log -i --oneline --grep "$p" "$target_branch..$source_branch")
  if [[ -n $log_grep ]]; then
    found_string=true
    echo "$p" "$log_grep"
  fi

  # Check names of files that might have been removed
  log_files=$(git log --oneline --name-only "$target_branch..$source_branch")
  if [[ $log_files =~ $p ]]; then
    found_string=true
    echo "$p" "$log_files"
  fi

done < "$file"

if [ "$found_string" = true ]; then
  echo "Found instances of given strings."
  exit 1
else
  echo "No instances of given strings found."
  exit 0
fi
