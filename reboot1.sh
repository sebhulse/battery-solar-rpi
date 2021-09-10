#!/bin/bash
# chronjob on reboot:
# @reboot bash /home/pi/battery-solar-rpi/reboot1.sh >> /home/pi/raspberrydata/logs/reboot1_cron.log 2>&1

timestamp() {
  date +"%Y-%m-%d_%H-%M-%S"
  }

echo
echo -----------------------
echo "$(timestamp)"

# mount the google drive directory
rclone mount gdrive: $HOME/mnt/gdrive
