#!/bin/bash
if [ "x$1" != "x--force" -a ! -f /lib/systemd/system/hue-pass.service ]
then
	echo "ok, hue-pass.service seems not be installed." 
	exit 0
fi

echo "Leaving installed: python3 python3-requests"
if [ -f '/lib/systemd/system/deconz.service' ]; then
	sed -i 's/ --http-port=80 --ws-port=8088 --allow-local=0 --lan-bridgeid=1$/ --http-port=80/' /lib/systemd/system/deconz.service
fi
if [ -f '/lib/systemd/system/deconz-gui.service' ]; then
	sed -i 's/ --http-port=80 --ws-port=8088 --allow-local=0 --lan-bridgeid=1$/ --http-port=80/' /lib/systemd/system/deconz-gui.service
fi
if [ -f /lib/systemd/system/hue-pass.service ]
then
	systemctl stop hue-pass.service
	systemctl disable hue-pass.service
	rm /lib/systemd/system/hue-pass.service 
	systemctl daemon-reload
fi
echo "To even remove hue-pass package data, you might now do:"
echo "	sudo rm -rf /opt/hue-pass" 
