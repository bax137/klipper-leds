#!/bin/bash
systemctl stop ibax.voron-leds
cat pass | sudo -S shutdown -h now