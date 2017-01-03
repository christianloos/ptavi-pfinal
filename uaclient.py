#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" UA Client para una sesión SIP """

import sys
import os
import socket
import hashlib
from xml.sax import make_parser
from xml.sax import ContentHandler

""" Clase manejadora del XML de configuración"""
class XmlHandler(ContentHandler):

    def __init__(self):

        # Definición de la lista de atributos
        self.data_xml = []
        self.tag_dicc = {"account": ['username', 'passwd'],
                         "uaserver": ['ip', 'puerto'], 
                         "rtpaudio": ['puerto'], 
                         "regproxy": ['ip', 'puerto'],
                         "log": ['path'],
                         "audio": ['path']}

    def startElement(self, tag, atts):

        if tag in self.tag_dicc:
            tag_dicc = {}
            for att in self.tag_dicc[tag]:
                tag_dicc[att] = atts.get(att, "")
            element = {tag: tag_dicc}
            self.data_xml.append(element)        

    def get_tags(self):
        return self.data_xml


if __name__ == "__main__":

    # Archivo de configuración XML y método pasados por comandos.
    try:
        XML = str(sys.argv[1])
        REQUEST = str(sys.argv[2])
        if REQUEST == 'REGISTER':
            EXPTIME = int(sys.argv[3])
        elif REQUEST in ['INVITE', 'BYE']:
            USER = sys.argv[3]
    except:
        sys.exit("Usage: python3 uaclient.py config method option")
    
    # Instanciación del manejador del archivo de configuración
    parser = make_parser()
    cHandler = XmlHandler()
    parser.setContentHandler(cHandler)
    parser.parse(open(XML))
    config_info = cHandler.get_tags()


    # Declaración de variables usadas al extraer los datos del XML
    user_address = config_info[0]['account']['username']
    user_passwd = config_info[0]['account']['passwd']
    server_ip = config_info[1]['uaserver']['ip']
    server_port = int(config_info[1]['uaserver']['puerto'])
    rtp_port = int(config_info[2]['rtpaudio']['puerto'])
    proxy_ip = config_info[3]['regproxy']['ip']
    proxy_port = int(config_info[3]['regproxy']['puerto'])
    log = config_info[4]['log']['path']
    audio = config_info[5]['audio']['path']

    # Creamos el socket, lo configuramos y lo atamos a un servidor/puerto
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as my_socket:
        my_socket.connect((proxy_ip, proxy_port))

        sip_str = ' SIP/2.0\r\n'

        # Petición REGISTER
        if REQUEST == 'REGISTER':
        
            # Envío de datos
            expires_str = 'Expires: ' + str(EXPTIME) + '\r\n'
            line = REQUEST + " sip:" + user_address + ':' + str(server_port) +\
                   sip_str
            sent_line = line + expires_str + '\r\n'
            my_socket.send(bytes(sent_line, 'utf-8') + b'\r\n')
            print("Sending... " + '\r\n' + sent_line)
            
            # Recepción de datos
            data = my_socket.recv(1024)
            response = data.decode('utf-8')
            chops = response.split()
            
            if chops[1] == '401':
                print('Received from server:', data.decode('utf-8'))

        # Petición INVITE
        if REQUEST == 'INVITE':
        
            # Envío de datos/ Descripción de sesión
            header = 'Content-Type: application/sdp\r\n\r\n'

            v = 'v=0\r\n'
            o = 'o=' + user_address + ' ' + server_ip + '\r\n'
            s = 's=RobarPlanos\r\n'
            t = 't=0\r\n'
            m = 'm=audio ' + str(rtp_port) + ' RTP\r\n'
            body = v + o + s + t + m
            line = REQUEST + " sip:" + USER + sip_str
            sent_line = line + header + body
            
            my_socket.send(bytes(sent_line, 'utf-8') + b'\r\n')
            print("Sending..." + '\r\n' + sent_line)

            # Recepción de datos
            data = my_socket.recv(1024)
            response = data.decode('utf-8')
            chops = response.split()

            if chops[1] == '404':
                print('Received from server:', data.decode('utf-8'))
            elif chops[7] == '200':
                print('Received from server:', data.decode('utf-8'))
                
                # Envío del ACK
                ack_line = 'ACK sip:' + user_address + sip_str

                my_socket.send(bytes(ack_line, 'utf-8') + b'\r\n')
                print("Sending..." + '\r\n' + ack_line)
                
                # Envío RTP
                aEjecutar = 'mp32rtp -i ' + server_ip + ' -p ' + \
                str(rtp_port) + ' < ' + str(audio)
                print("Executing... ", aEjecutar)
                os.system(aEjecutar)
                print("Successfully sent")

        # Petición BYE
        elif REQUEST == 'BYE':

            bye_line = 'BYE sip:' + user_address + sip_str
            
            my_socket.send(bytes(bye_line, 'utf-8') + b'\r\n')
            print("Sending..." + '\r\n' + bye_line)
            data = my_socket.recv(1024)
            response = data.decode('utf-8')
            chops = response.split()
            
            # Finalización del socket al recibir el OK por parte del server
            if chops[1] == '200':
                print('Received from server:', data.decode('utf-8'))
                print("Finishing socket...")
                # Cerramos todo
                my_socket.close()
                print("Socket ended")
