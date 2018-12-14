# HuePass
This is a Hue REST API wrapper that sets up a Hue app compatible HTTPS server and passes through requests to the HTTP instance. The intent is to enable deCONZ (which doesn't support SSL at the moment) to work with the official Hue app (which requires an SSL connection), but theoratically it should work with any Hue compatible rest API.

## Install
```
cd /opt
sudo git clone https://github.com/KodeCR/hue-pass
sudo ./install.sh
```

## Configure
Hue-pass will pass through to the localhost (127.0.0.1) at port 80, and enables a HTTPS service at port 443. This default web-socket port for deCONZ is also at port 443 and needs to be changed. Also localhost is access (like HuePass) is by default whitelisted for authorisation, this needs to be disabled. I also recommend to change deCONZ to base the bridge-id on the LAN mac-address instead of the Zigbee MAC-address so that the Hue app will work properly with HomeKit. To configure deCONZ for all this please edit `/lib/systemd/system/deconz.service` or `deconz-gui.service` to replace `--http-port=80` with `--http-port=80 --ws-port=8088 --allow-local=0 --lan-bridgeid=1`:
```
sed -i 's/ --http-port=80$/ --http-port=80 --ws-port=8088 --allow-local=0 --lan-bridgeid=1/' /lib/systemd/system/deconz.service
sed -i 's/ --http-port=80$/ --http-port=80 --ws-port=8088 --allow-local=0 --lan-bridgeid=1/' /lib/systemd/system/deconz-gui.service
```

The `install.sh` script does the above for you, and installs hue-pass as a (systemd) service.