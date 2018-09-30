# HuePass
This is a Hue REST API wrapper that sets up a Hue app compatible HTTPS server in addition to an HTTP and SSDP service. The intent is to enable deCONZ (which doesn't support SSL at the moment) to work with the official Hue app (which requires an SSL connection), but theoratically it should work with any Hue compatible rest API.

## Install
```
cd /opt
sudo git clone https://github.com/KodeCR/hue-pass
sudo ./install.sh
```

## Configure
By default hue-pass will pass through to the localhost (127.0.0.1) at port 8080. To configure deCONZ for this please edit `/lib/systemd/system/deconz.service` or `deconz-gui.service` to replace `--http-port=80` with `--http-port=8080 --ws-port=8081 --upnp=0 --allow-local=0`:
```
sed -i 's/ --http-port=80$/ --http-port=8080 --ws-port=8081 --upnp=0 --allow-local=0/' /lib/systemd/system/deconz.service
sed -i 's/ --http-port=80$/ --http-port=8080 --ws-port=8081 --upnp=0 --allow-local=0/' /lib/systemd/system/deconz-gui.service
```

The `install.sh` script does the above for you, and installs hue-pass as a (systemd) service.

The ip-address and port can be changed in 'HuePass.json'.

The code is based on https://github.com/mariusmotea/diyHue but heavily modified.
