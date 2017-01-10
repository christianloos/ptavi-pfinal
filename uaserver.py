#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" UA Server para una sesión SIP """

import sys
import os
import socketserver
from xml.sax import make_parser
from xml.sax.handler import ContentHandler
from uaclient import XmlHandler
import time

"""
Clase manejadora de SIP y RTP en el servidor
"""


class SIP_ServerHandler(socketserver.DatagramRequestHandler):

    dest_ip = []
    dest_port = []

    def handle(self):

        # Leyendo línea a línea lo que envía el cliente
        line = self.rfile.read()
        data = line.decode('utf-8')

        chops = data.split()
        REQUEST = chops[0]

        sip_str = ' SIP/2.0\r\n'
        trying_str = 'SIP/2.0 100 Trying\r\n\r\n'
        ring_str = 'SIP/2.0 180 Ring\r\n\r\n'
        ok_str = 'SIP/2.0 200 OK\r\n'

        # Detección del método SIP
        # Petición INVITE
        if REQUEST == 'INVITE':

            self.dest_ip.append(chops[7])
            self.dest_port.append(chops[11])
            print("Received: " + data)

            # Apertura del log
            log_info = 'Received from ' + proxy_ip + ':' + \
                       str(proxy_port) + ': ' + \
                       data.replace('\r\n', ' ')
            log_reg(config_info, log_info)

            # Respuesta al cliente
            header = 'Content-Type: application/sdp\r\n\r\n'
            v = 'v=0\r\n'
            o = 'o=' + user_address + ' ' + server_ip + '\r\n'
            s = 's=RobarPlanos\r\n'
            t = 't=0\r\n'
            m = 'm=audio ' + str(rtp_port) + ' RTP\r\n'
            body = v + o + s + t + m
            sent_line = trying_str + ring_str + ok_str + header + body
            self.wfile.write(bytes(sent_line, 'utf-8') + b'\r\n')
            print("Sending..." + '\r\n' + sent_line)

            log_info = 'Sent to ' + proxy_ip + ':' + str(proxy_port) + \
                       ': ' + sent_line.replace('\r\n', ' ')
            log_reg(config_info, log_info)

        # Petición ACK/ Envío RTP
        elif REQUEST == 'ACK':

            # Envío RTP
            print("Received: " + data)

            log_info = 'Received from ' + proxy_ip + ':' + \
                       str(proxy_port) + ': ' + \
                       data.replace('\r\n', ' ')
            log_reg(config_info, log_info)

            aEjecutar = 'mp32rtp -i ' + server_ip + ' -p ' + \
                        str(rtp_port) + ' < ' + str(audio)
            print("Executing... ", aEjecutar)
            os.system(aEjecutar)
            print("Successfully sent")

            log_info = 'Sent to ' + server_ip + ':' + str(rtp_port) + \
                       ': ' + 'RTP MEDIA'
            log_reg(config_info, log_info)

        elif REQUEST == 'BYE':

            print("Received: " + data)

            log_info = 'Received from ' + proxy_ip + ':' + \
                       str(proxy_port) + ': ' + \
                       data.replace('\r\n', ' ')
            log_reg(config_info, log_info)

            self.wfile.write(bytes(ok_str, 'utf-8') + b'\r\n')
            print("Sending..." + '\r\n' + ok_str)

            log_info = 'Sent to ' + proxy_ip + ':' + str(proxy_port) + \
                       ': ' + ok_str.replace('\r\n', ' ')
            log_reg(config_info, log_info)

        elif REQUEST not in ['INVITE', 'ACK', 'BYE']:
            self.wfile.write(b"SIP/2.0 405 Method Not Allowed\r\n\r\n")

            log_info = 'Error: SIP/2.0 405 Method Not Allowed.'
            log_reg(config_info, log_info)

        else:
            self.wfile.write(b"SIP/2.0 400 Bad Request\r\n\r\n")

            log_info = 'Error: SIP/2.0 400 Bad Request.'
            log_reg(config_info, log_info)


# Función de registro de operaciones en un log
def log_reg(config_info, info):

    with open(log, 'a') as log_file:
        hora = time.strftime('%Y%m%d%H%M%S', time.gmtime(time.time()))
        info = hora + ' ' + info + '\r\n'
        log_file.write(info)


if __name__ == "__main__":

    # Archivo de configuración XML y método pasados por comandos.
    try:
        XML = str(sys.argv[1])
    except:
        sys.exit("Usage: python3 uaserver.py config")

    # Instanciación del manejador del archivo de configuración
    parser = make_parser()
    cHandler = XmlHandler()
    parser.setContentHandler(cHandler)
    parser.parse(open(XML))
    config_info = cHandler.get_tags()

    print()

    # Declaración de variables usadas al extraer los datos del XML
    user_address = config_info[0]['account']['username']
    server_ip = config_info[1]['uaserver']['ip']
    server_port = int(config_info[1]['uaserver']['puerto'])
    proxy_ip = config_info[3]['regproxy']['ip']
    proxy_port = int(config_info[3]['regproxy']['puerto'])
    rtp_port = int(config_info[2]['rtpaudio']['puerto'])
    log = config_info[4]['log']['path']
    audio = config_info[5]['audio']['path']

    # Creación del socket con la IP y puerto al que conectarse
    serv = socketserver.UDPServer((server_ip,
                                   server_port),
                                  SIP_ServerHandler)
    print("Listening..." + '\r\n')

    log_info = 'Starting...'
    log_reg(config_info, log_info)

    try:
        serv.serve_forever()
    except KeyboardInterrupt:
        print()
        log_info = 'Finishing...'
        log_reg(config_info, log_info)
        print("Server offline")
