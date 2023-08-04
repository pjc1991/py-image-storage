#!/bin/bash
# The process name
processName="observer.py"

# Search the process
process=$(ps aux | grep "$processName" | grep -v "grep" | awk '{print $2}')

# Check if the process exists
if [ -z "$process" ]; then
    echo "No such process found"
    exit 1
fi

# Kill the process
kill -9 $process
echo "Process $processName has been killed"

