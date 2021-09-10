#!/bin/bash
# chronjob for midnight every day:
# 0 0 * * * bash /home/pi/battery-solar-rpi/midnight.sh >> /home/pi/battery-solar-rpi/logs/midnight_cron.log 2>&1
timestamp() {
  date +"%Y-%m-%d_%H-%M-%S"
  }

newfilename="influxdb_backup_$(timestamp)"

echo -----------------------
echo "$(timestamp)"
echo

# make a new directory and make a backup of the whole database
mkdir /home/pi/mnt/gdrive/InfluxDB-Backup/$newfilename
influxd backup -portable /home/pi/mnt/gdrive/InfluxDB-Backup/$newfilename
cd /home/pi/mnt/gdrive/InfluxDB-Backup/
pwd
echo "Amount of directories in above directory:"
no_folders=$(ls | wc -l)
echo "$no_folders"

# if there are more than 2 backups in the google drive directory, delete the oldest one
if (( no_folders > 2 ))
then
  echo "Directory to be deleted:"
  ls -lt | awk '{print $9}' | tail -1
  ls -lt | awk '{print $9}' | tail -1 | xargs rm -r
  echo "Deleted"
else
  echo "Nothing deleted, no. of directories <= 2"
fi

echo "Commiting logs to git"

# commit the logs to git 
git --git-dir=/home/pi/battery-solar-rpi/.git/ --work-tree=/home/pi/battery-solar-rpi/ add -A
git --git-dir=/home/pi/battery-solar-rpi/.git/ --work-tree=/home/pi/battery-solar-rpi/ commit -am "cron commit battery-solar-rpi @ $(timestamp)"
git --git-dir=/home/pi/battery-solar-rpi/.git/ --work-tree=/home/pi/battery-solar-rpi/ push
