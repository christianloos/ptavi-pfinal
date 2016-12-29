#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" UA Server para sesión SIP """

import socketserver
import sys
import os
from xml.sax import make_parser
from xml.sax.handler import ContentHandler
from uaclient import XmlHandler

""" Clase manejadora de SIP y RTP en el servidor """

class SIP_ServerHandler(socketserver.DatagramRequestHandler):
    dest_ip = []
    dest_port = []

    def handle(self):

        # Leyendo línea a línea lo que nos envía el cliente
        line = self.rfile.read()
        data = line.decode('utf-8')
        chops = data.split(' ')
        METHOD = chops[0]

        sip_str = ' SIP/2.0\r\n' #OJO CON EL ESPACIO SI HAY ERRORES
        trying_str = 'SIP/2.0 100 Trying\r\n\r\n'
        ring_str = 'SIP/2.0 180 Ringing\r\n\r\n'
        
        # Detección de método SIP
        if METHOD == 'INVITE':
            self.dest_ip.append(chops[7])
            self.dest_port.append(chops[11])
            print("Received: " + data)
            
            sdp_body = 'Content-Type: application/sdp\r\n\r\n' + 'v=0\r\n' + \
                       'o=' + config_info['account']['username'] + ' ' + \
                       config_info['uaserver']['ip'] + '\r\n' + 's=practica_final\r\n' \
                       + 't=0\r\n' + 'm=audio ' + config_info['rtpaudio']['puerto'] + \
                       ' RTP\r\n'
            sent_line = trying_str + ring_str + sip_str + sdp_body
            self.wfile.write(bytes(sent_line, 'utf-8') + b'\r\n')
            print("Enviando...")
            print(sent_line)

        elif METHOD == 'ACK':
            print("Received: " + data)
            aEjecutar = 'mp32rtp -i ' + self.dest_ip[0] + ' -p ' + self.dest_port[0] + \
                        ' < ' + config_info['audio']['path']
            print("Executing...", aEjecutar)
            print()
            os.system(aEjecutar)
            self.dest_ip = []
            self.dest_port = []
            print("Enviado con éxito")
            

        elif METHOD == 'BYE':
            print("Received: " + data)
            self.wfile.write(b"SIP/2.0 200 OK\r\n\r\n")

        elif METHOD not in ['INVITE', 'ACK', 'BYE']:
            self.wfile.write(b"SIP/2.0 405 Method Not Allowed\r\n\r\n")
        else:
            self.wfile.write(b"SIP/2.0 400 Bad Request\r\n\r\n")


if __name__ == "__main__":
    # Creamos servidor de eco y escuchamos
    try:
        CONFIG = sys.argv[1]
    except:
        sys.exit("Usage: python3 uaserver.py config")
        
    # Instanciación del manejador del programa cliente
    parser = make_parser()
    cHandler = XmlHandler()
    parser.setContentHandler(cHandler)
    parser.parse(open(CONFIG))
    
    config_info = cHandler.get_tags()

    serv = socketserver.UDPServer(('', int(config_info['uaserver']['puerto'])),
                                  SIP_ServerHandler)
    print("Listening...")

    try:
        serv.serve_forever()
    except KeyboardInterrupt:
        print()
        print("Finalizado servidor")
