#!/bin/bash
wget http://192.168.1.63:8888/command?shutdown=true
systemctl stop ibax.voron-leds
cat pass | sudo -S shutdown -h now