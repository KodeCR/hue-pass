#!/usr/bin/python3
import logging
import os
import sys
import struct
import random
import threading
import socket
import json
import requests
import ssl
import re
from functools import partial
from threading import Thread
from time import sleep
from subprocess import check_output
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

# setup
def getIP():
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.connect(('8.8.8.8', 80))
	return s.getsockname()[0]

def getConfig():
	config = defaultdict(lambda:defaultdict(str))
	try:
		with open('./HuePass.json', 'r') as fp:
			config = json.load(fp)
			logging.info("Config loaded")
	except Exception:
		print("Error: could not load config file")
		sys.exit(1)
	return config

def getBridgeIDs(config):
	r = requests.get('http://' + config['ipaddress'] + ':' + config['port'] + '/api/nouser/config')
	bridgeid = json.loads(r.text).get('bridgeid')
	logging.debug("bridge-id: " + str(bridgeid))
	r = requests.get('http://' + config['ipaddress'] + ':' + config['port'] + '/description.xml')
	uuid = re.search(r'<UDN>uuid:([0-9a-fA-F\-]*)</UDN>', r.text).group(1)
	logging.debug("uuid: " + str(uuid))
	if bridgeid == None or uuid == None:
		print("Error: could not retrieve bridgeid/uuid from " + config['ipaddress'] + ":" + config['port'])
		sys.exit(1)
	return (bridgeid, uuid)

def generateCertificate(bridgeid):
	try:
		os.system('./hue_certificate.sh ' + bridgeid)
	except:
		print("Error: couldn't generate certificate")
		sys.exit(1)

# ssdp
def serverSSDPNotify(ip, port, bridgeid, uuid, stop):
	print("Starting SSDP NOTIFY...")
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 1))
	sock.settimeout(2.5)
	message =  'NOTIFY * HTTP/1.1\r\n'
	message += 'HOST: 239.255.255.250:1900\r\n'
	message += 'CACHE-CONTROL: max-age=100\r\n'
	message += 'LOCATION: http://' + ip + ':' + str(port) + '/description.xml\r\n'
	message += 'SERVER: Linux/3.14.0 UPnP/1.0 IpBridge/1.26.0\r\n'
	message += 'NTS: ssdp:alive\r\n'
	message += 'hue-bridgeid: ' + bridgeid.upper() + '\r\n'
	messageNT = ['NT: upnp:rootdevice\r\nUSN: uuid:' + uuid + '::upnp:rootdevice\r\n',
				 'NT: uuid:' + uuid + '\r\nUSN: uuid:' + uuid + '\r\n',
				 'NT: urn:schemas-upnp-org:device:basic:1\r\nUSN: uuid:' + uuid + '::urn:schemas-upnp-org:device:basic:1\r\n']
	i = 0
	while not stop():
		if i >= 12:
			i = 0
			sock.sendto(bytes(message + messageNT[0] + '\r\n', 'utf8'), ('239.255.255.250', 1900))
			sock.sendto(bytes(message + messageNT[1] + '\r\n', 'utf8'), ('239.255.255.250', 1900))
			sock.sendto(bytes(message + messageNT[2] + '\r\n', 'utf8'), ('239.255.255.250', 1900))
		else:
			i += 1
		sleep(5)

def serverSSDPResponse(ip, port, bridgeid, uuid, stop):
	print("Starting SSDP response...")
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, struct.pack('4sL', socket.inet_aton('239.255.255.250'), socket.INADDR_ANY))
	sock.bind(('', 1900))
	message =  'HTTP/1.1 200 OK\r\n'
	message += 'CACHE-CONTROL: max-age=100\r\n'
	message += 'EXT:\r\n'
	message += 'LOCATION: http://' + ip + ':' + str(port) + '/description.xml\r\n'
	message += 'SERVER: Linux/3.14.0 UPnP/1.0 IpBridge/1.26.0\r\n'
	message += 'hue-bridgeid: ' + bridgeid + '\r\n'
	messageST = ['ST: upnp:rootdevice\r\nUSN: uuid:' + uuid + '::upnp:rootdevice\r\n',
				 'ST: uuid:' + uuid + '\r\nUSN: uuid:' + uuid + '\r\n',
				 'ST: urn:schemas-upnp-org:device:basic:1\r\nUSN: uuid:' + uuid + 'urn:schemas-upnp-org:device:basic:1\r\n']
	while not stop():
		(data, address) = sock.recvfrom(1024)
		data = data.decode('utf-8')
		if data[0:19]== 'M-SEARCH * HTTP/1.1' and data.find('ssdp:discover') != -1:
			logging.debug("Sending M-Search response to " + address[0])
			if data.find('ST: ssdp:all\r\n') or data.find('ST: upnp:rootdevice\r\n'):
				sock.sendto(bytes(message + messageST[0] + '\r\n', 'utf8'), address)
			if data.find('ST: ssdp:all\r\n') or data.find('ST: uuid:' + uuid + '\r\n'):
				sock.sendto(bytes(message + messageST[1] + '\r\n', 'utf8'), address)
			if data.find('ST: ssdp:all\r\n') or data.find('ST: urn:schemas-upnp-org:device:basic:1\r\n'):
				sock.sendto(bytes(message + messageST[2] + '\r\n', 'utf8'), address)
		sleep(1)

# http
class Handler(BaseHTTPRequestHandler):
	protocol_version = 'HTTP/1.1'
	server_version = 'nginx'
	sys_version = ''

	def __init__(self, ip, config, *args, **kwargs):
		self.ip = ip
		self.config = config
		super().__init__(*args, **kwargs)

	def _send(self, status_code, headers, content):
		self.send_response(status_code)
		for key, value in headers.items():
			self.send_header(key, value)
		self.end_headers()
		if int(headers['Content-Length']) != 0:
			self.wfile.write(content)

	def _respond(self, r):
		self._send(r.status_code, r.headers, r.content)

	def _update(self, r, content):
		r.headers['Content-Length'] = len(content)
		self._send(r.status_code, r.headers, content)

	def do_OPTIONS(self):
		logging.debug("OPTIONS: " + self.path)
		r = requests.options('http://' + self.config['ipaddress'] + ':' + self.config['port'] + self.path)
		self._respond(r)

	def do_HEAD(self):
		logging.debug("HEAD: " + self.path)
		r = requests.head('http://' + self.config['ipaddress'] + ':' + self.config['port'] + self.path)
		self._respond(r)

	def do_GET(self):
		logging.debug("GET: " + self.path)
		r = requests.get('http://' + self.config['ipaddress'] + ':' + self.config['port'] + self.path)
		if self.path == '/description.xml':
			content = bytes(re.sub(r'<URLBase>http://[0-9\.]+(:[0-9]+)?/?</URLBase>', '<URLBase>http://' + self.ip + ':80/</URLBase>', r.text), 'utf8')
			self._update(r, content)
		else:
			self._respond(r)

	def do_PUT(self):
		length = int(self.headers['Content-Length'])
		content = self.rfile.read(length)
		logging.debug("PUT: " + self.path + ' - ' + str(content))
		r = requests.put('http://' + self.config['ipaddress'] + ':' + self.config['port'] + self.path, data = content)
		self._respond(r)

	def do_POST(self):
		length = int(self.headers['Content-Length'])
		content = self.rfile.read(length)
		logging.debug("POST: " + self.path + ' - ' + str(content))
		r = requests.post('http://' + self.config['ipaddress'] + ':' + self.config['port'] + self.path, data = content)
		self._respond(r)

	def do_DELETE(self):
		logging.debug("DELETE: " + self.path)
		r = requests.delete('http://' + self.config['ipaddress'] + ':' + self.config['port'] + self.path)
		self._respond(r)

class HueHTTPServer(ThreadingMixIn, HTTPServer):
	def run(self):
		print ('Starting HTTP server...')
		self.serve_forever()
		self.server_close()

class HueHTTPSServer(ThreadingMixIn, HTTPServer):
	def run(self):
		print ('Starting HTTPS server...')
		ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
		ctx.load_cert_chain(certfile='./hue_certificate.pem')
		ctx.options |= ssl.OP_NO_TLSv1
		ctx.options |= ssl.OP_NO_TLSv1_1
		ctx.options |= ssl.OP_CIPHER_SERVER_PREFERENCE
		ctx.set_ciphers('ECDHE-ECDSA-AES128-GCM-SHA256')
		ctx.set_ecdh_curve('prime256v1')
		self.socket = ctx.wrap_socket(self.socket, server_side=True)
		self.serve_forever()
		self.server_close()

# main
def main():
	print("HuePass")
	logging.basicConfig(level=logging.INFO)
	stop = False
	startedHTTP = False
	startedHTTPS = False
	config = getConfig()
	ip = getIP()
	(bridgeid, uuid) = getBridgeIDs(config)

	if not os.path.isfile('./hue_certificate.pem'):
		generateCertificate(bridgeid)
	try:
		handler = partial(Handler, ip, config)
		serverHTTP = HueHTTPServer(('', 80), handler)
		serverHTTPS = HueHTTPSServer(('', 443), handler)
		threadHTTP = Thread(target=serverHTTP.run)
		threadHTTPS = Thread(target=serverHTTPS.run)
		threadSSDPNotify = Thread(target=serverSSDPNotify, args=[ip, 80, bridgeid.upper(), uuid, lambda: stop])
		threadSSDPResponse = Thread(target=serverSSDPResponse, args=[ip, 80, bridgeid.upper(), uuid, lambda: stop])
		threadHTTP.start()
		startedHTTP = True
		threadHTTPS.start()
		startedHTTPS = True
		threadSSDPNotify.start()
		threadSSDPResponse.start()
		while True:
			sleep(10)
	except KeyboardInterrupt:
		pass
	except Exception as e:
		print("Error: " + str(e))
	finally:
		stop = True
		print("Shutting down...")
		if startedHTTP:
			print("Stopping HTTP server...")
			serverHTTP.socket.shutdown(socket.SHUT_RDWR)
			serverHTTP.shutdown()
		if startedHTTPS:
			print("Stopping HTTPS server...")
			serverHTTPS.socket.shutdown(socket.SHUT_RDWR)
			serverHTTPS.shutdown()
		try:
			threadSSDPNotify.join()
			threadSSDPResponse.join()
		except:
			pass

if __name__ == '__main__':
	main()
