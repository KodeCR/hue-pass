#!/bin/bash
if [ ! -f 'hue_certificate.pem' ]; then
	bridgeid=$1
	dec_bridgeid=`python3 -c "print(int(\"$bridgeid\", 16))"`
	openssl req -new -config hue_openssl.conf -nodes -x509 -days 4017 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -pkeyopt ec_param_enc:named_curve -subj "/C=NL/O=Philips Hue/CN=$bridgeid" -keyout hue_private.key -out hue_public.crt -set_serial $dec_bridgeid
	if [ $? -ne 0 ] ; then
		echo -e "\033[31m ERROR!! Local certificate generation failed!\033[0m"
	else
		cat hue_private.key hue_public.crt > hue_certificate.pem
		rm hue_private.key hue_public.crt
	fi
else
	echo "Certificate already exists"
fi
