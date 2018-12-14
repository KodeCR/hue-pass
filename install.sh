#!/bin/bash
apt install -y python3 python3-requests
if [ -f '/lib/systemd/system/deconz.service' ]; then
	sed -i 's/ --http-port=80$/ --http-port=80 --ws-port=8088 --allow-local=0 --lan-bridgeid=1/' /lib/systemd/system/deconz.service
fi
if [ -f '/lib/systemd/system/deconz-gui.service' ]; then
	sed -i 's/ --http-port=80$/ --http-port=80 --ws-port=8088 --allow-local=0 --lan-bridgeid=1/' /lib/systemd/system/deconz-gui.service
fi
cp hue-pass.service /lib/systemd/system/
systemctl daemon-reload
systemctl enable hue-pass.service
systemctl start hue-pass.service
