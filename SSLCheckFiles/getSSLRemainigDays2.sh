#!/bin/bash

#A simple script to calcualate the remaining days until a SSL certificate will expire

display_usage() {
  echo "This script must be run with ...."
  echo -e "\nUsage:\n$0 FQDN \n"
  exit 1
}

# Check if an argument is provided
if [ $# -ne 1 ]; then
    usage
fi

datediff() {
  date1_epoch=$1
  date2_epoch=$2

  if(echo $(( (date1_epoch - date2_epoch) / 86400 )) > 0); then
    echo $(( (date1_epoch - date2_epoch) / 86400 ))
    exit 0
  else
    exit 1
  fi
}

cert_date=$(echo | openssl s_client -servername $1 -connect $1:443 2>/dev/null | openssl x509 -noout -dates | grep notAfter | cut -d= -f2)
now_date=$(date)
cert_date_epoch=$(date -d "$cert_date" "+%s")
now_date_epoch=$(date -d "$now_date" "+%s")
datediff $cert_date_epoch $now_date_epoch
