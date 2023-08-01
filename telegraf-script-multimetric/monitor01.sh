#!/bin/bash
# This script returns current CPU and memory usage values

cpuUsage=$(top -bn1 | awk '/Cpu/ { print $2}')
memUsage=$(free -m | awk '/Mem/{print $3}')

# echo "CPU Usage: $cpuUsage%"
# echo "Memory Usage: $memUsage MB"

n1=$cpuUsage
n2=$memUsage

# Calculate the sum using bc
sum=$(echo "($n1*10*10^0)+($n2*10^4)" | bc)

# Print the result
# echo "Sum: $sum"

output=${sum%.*}
echo $output
