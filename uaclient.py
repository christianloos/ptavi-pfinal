#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" UA Client para una sesión SIP """

import socket
import sys
import os
import haslib
from xml.sax import make_parser
from xml.sax import ContentHandler

""" Clase manejadora del XML de configuración"""
class XmlHandler(ContentHandler):

    def __init__(self):
        self.tags = {}

    # Definición de la lista de atributos
    def startElement(self, name, attrs):
        data_xml = {}
        att_1 = ['username', 'passwd']
        att_2 = ['ip', 'puerto']
        att_3 = ['puerto']
        att_4 = ['ip', 'puerto']
        att_5 = ['path']
        att_6 = ['path']
        tag_list = {'account': att_1, 'uaserver': att_2,
                    'rtpaudio': att_3, 'regproxy': att_4,
                    'log': att_5, 'audio': att_6}

        if tag in tag_list:
            for atribute in tag_list[tag]:
                if tag == 'uaserver' and atribute == 'ip':
                    if attrs.get(atribute, "127.0.0.1") != "":
                        data_xml[atribute] = attrs.get(atribute, "127.0.0.1")
                    elif attrs.get(atribute, "") != "":
                        data_xml[atribute] = attrs.get(atribute, "")
                    self.tag_list[tag] = data_xml

    def get_tags(self):
        return self.tag_list

if __name__ == "__main__":

    # Instanciación del manejador
    parser = make_parser()
    cHandler = XmlHandler()
    parser.setContentHandler(cHandler)
    

    # Dirección IP y puerto del servidor pasada por comandos.
    try:
        CONFIG = str(sys.argv[1])
        METHOD = str(sys.argv[2])
        if METHOD == 'REGISTER':
            OPTION = int(sys.argv[3])
        elif METHOD in ['INVITE', 'BYE']:
            OPTION = sys.argv[3]
    except:
        sys.exit("Usage: python3 uaclient.py config method option")

    parser.parse(open(CONFIG))
    config_info = cHandler.get_tags()


    # Creamos el socket, lo configuramos y lo atamos a un servidor/puerto
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as my_socket:
        my_socket.connect((config_info['regproxy']['ip'],
                           int(config_info['regproxy']['puerto'])))

        sip_str = ' SIP/2.0\r\n'
        
        # Petición REGISTER
        if METHOD == 'REGISTER':
            # Envío de datos
            
            expires_str = 'Expires: ' + str(OPTION) + '\r\n\r\n'
            line = METHOD + " sip:" + config_info['account']['username'] +
                   ':' + config_info['uaserver']['puerto'] + sip_str
            sent_line = line + expires_str
            my_socket.send(bytes(sent_line, 'utf-8') + b'\r\n')
            print("Enviando...")
            print(sent_line)
            
            # Recepción de datos
            data = my_socket.recv(1024)
            
            if data.decode('utf-8').split()[1] == '401':
                print('Recibido --', data.decode('utf-8'))
                
                nonce = data.decode('utf-8')split()[6].split('"')[1]
                response = hashlib.sha1()
                response.update(bytes(config_info['account']['passwd'], 'utf-8'))
                response.update(bytes(nonce, 'utf-8'))
                response = response.hexdigest()
                
                # Mensaje de autorización
                auto = 'Authorization: Digest response="' + response + '\r\n\r\n'
                hash_line = line + 'Expires: ' + str(OPTION) + '\r\n' + auto
                my_socket.send(bytes(hash_line, 'utf-8') + b'\r\n')
                print("Enviando...")
                print(hash_line)
                
                data = my_socket.recv(1024)
                print('Recibido --', data.decode('utf-8'))
            else:
                print("Mensaje no reconocido")


        # Petición INVITE
        elif METHOD == 'INVITE':
            # Envío de datos
            header = 'Content-Type: application/sdp\r\n\r\n'
            body = 'v=0\r\n' + 'o=' + config_info['account']['username'] +
                   ' ' + config_info['uaserver']['ip'] + '\r\n' +
                   's=practica_final\r\n' + 't=0\r\n' + 'm=audio ' +
                   config_info['rtpaudio']['puerto'] + ' RTP\r\n'
            line = METHOD + " sip:" + OPTION + sip_str
            sent_line = line + header + body
            
            my_socket.send(bytes(sent_line, 'utf-8') + b'\r\n')
            print("Enviando...")
            print(sent_line)
            
            # Recepción de datos
            data = my_socket.recv(1024)
            
            if data.decode('utf-8').split()[1] == '404':
                print('Recibido --', data.decode('utf-8'))
            elif data.decode('utf-8').split()[7] == '200':
                print('Recibido --', data.decode('utf-8'))
                ack_line = 'ACK sip:' + config_info['account']['username'] + sip_str
                my_socket.send(bytes(ack_line, 'utf-8') + b'\r\n')
                print("Enviando...")
                print(ack_line)
                
            # Se extrae el puerto y la IP para el envío RTP
            rtp_ip = data.decode('utf-8').split()[13]
            rtp_port = data.decode('utf-8').split()[17]
            
            # Envío RTP
            aEjecutar = 'mp32rtp -i ' + config_info['regproxy']['ip'] +
                        ' -p ' + rtp_port + ' < ' + config_info['audio']['path']
            print("Ejecutando...", aEjecutar)
            os.system(aEjecutar)
            print("Enviado con éxito")

        elif METHOD == 'BYE':

            print("Terminando socket...")
            # Cerramos todo
            my_socket.close()
            print("Socket terminado")
