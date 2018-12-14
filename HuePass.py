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
def getBridgeIDs():
	r = requests.get('http://127.0.0.1:80/api/nouser/config')
	bridgeid = json.loads(r.text).get('bridgeid')
	logging.debug("bridge-id: " + str(bridgeid))
	r = requests.get('http://127.0.0.1:80/description.xml')
	uuid = re.search(r'<UDN>uuid:([0-9a-fA-F\-]*)</UDN>', r.text).group(1)
	logging.debug("uuid: " + str(uuid))
	if bridgeid == None or uuid == None:
		print("Error: could not retrieve bridgeid/uuid from 127.0.0.1:80")
		sys.exit(1)
	return (bridgeid, uuid)

def generateCertificate(bridgeid):
	try:
		os.system('./hue_certificate.sh ' + bridgeid)
	except:
		print("Error: couldn't generate certificate")
		sys.exit(1)

# http
class Handler(BaseHTTPRequestHandler):
	protocol_version = 'HTTP/1.1'
	server_version = 'nginx'
	sys_version = ''

	def __init__(self, *args, **kwargs):
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
		r = requests.options('http://127.0.0.1:80' + self.path)
		self._respond(r)

	def do_HEAD(self):
		logging.debug("HEAD: " + self.path)
		r = requests.head('http://127.0.0.1:80' + self.path)
		self._respond(r)

	def do_GET(self):
		logging.debug("GET: " + self.path)
		r = requests.get('http://127.0.0.1:80' + self.path)
		self._respond(r)

	def do_PUT(self):
		length = int(self.headers['Content-Length'])
		content = self.rfile.read(length)
		logging.debug("PUT: " + self.path + ' - ' + str(content))
		r = requests.put('http://127.0.0.1:80' + self.path, data = content)
		self._respond(r)

	def do_POST(self):
		length = int(self.headers['Content-Length'])
		content = self.rfile.read(length)
		logging.debug("POST: " + self.path + ' - ' + str(content))
		r = requests.post('http://127.0.0.1:80' + self.path, data = content)
		self._respond(r)

	def do_DELETE(self):
		logging.debug("DELETE: " + self.path)
		r = requests.delete('http://127.0.0.1:80' + self.path)
		self._respond(r)

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
	startedHTTPS = False
	(bridgeid, uuid) = getBridgeIDs()

	if not os.path.isfile('./hue_certificate.pem'):
		generateCertificate(bridgeid)
	try:
		serverHTTPS = HueHTTPSServer(('', 443), Handler)
		threadHTTPS = Thread(target=serverHTTPS.run)
		threadHTTPS.start()
		startedHTTPS = True
		while True:
			sleep(10)
	except KeyboardInterrupt:
		pass
	except Exception as e:
		print("Error: " + str(e))
	finally:
		print("Shutting down...")
		if startedHTTPS:
			print("Stopping HTTPS server...")
			serverHTTPS.socket.shutdown(socket.SHUT_RDWR)
			serverHTTPS.shutdown()

if __name__ == '__main__':
	main()
