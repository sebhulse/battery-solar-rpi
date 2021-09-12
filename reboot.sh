#!/bin/bash
# chronjob on reboot:
# @reboot bash /home/pi/battery-solar-rpi/reboot.sh >> /home/pi/battery-solar-rpi/logs/reboot_cron.log 2>&1

timestamp() {
  date +"%Y-%m-%d_%H-%M-%S"
  }

echo
echo -----------------------
echo "$(timestamp)"

# ping github.com every second until a 200 response is recieved
until $(curl --output /dev/null --silent --head --fail https://github.com);
do
    printf '. '
    sleep 1
done

echo

# pull from github repo to update
git --git-dir=/home/pi/battery-solar-rpi/.git/ --work-tree=/home/pi/battery-solar-rpi/ pull

# wait until influxdb database has booted up
until curl -s -o /dev/null -w "%{http_code}" http://localhost:8086/health
do
  sleep 15
done

echo
echo "Connection to influxdb established"
echo

# start the infinite main.py script
python3 /home/pi/battery-solar-rpi/main.py
