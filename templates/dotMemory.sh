#!/bin/sh

Yellow='\033[1;33m'
NC='\033[0m'
echo "${Yellow}dotMemory.sh is deprecated and will soon be removed: Use the dotmemory command instead.${NC}"

set -e -u

root=$(dirname "$0")
runtime=$root/runtime-dotnet.sh
exec "$runtime" "$root/dotMemory.exe" "$@"