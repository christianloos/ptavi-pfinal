#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" Servidor proxy para una sesión SIP """

import socket
import sys
import socketserver
import time
import json
from xml.sax import make_parser
from xml.sax.handler import ContentHandler
import hashlib


"""
Clase manejadora del XML de configuración para el proxy
"""


class Proxy_XmlHandler(ContentHandler):

    def __init__(self):

        # Definición de la lista de atributos
        self.data_xml = []
        self.tag_dicc = {"server": ['name', 'ip', 'puerto'],
                         "database": ['path', 'passwdpath'],
                         "log": ['path']}

    def startElement(self, tag, atts):

        if tag in self.tag_dicc:
            tag_dicc = {}
            for att in self.tag_dicc[tag]:
                tag_dicc[att] = atts.get(att, "")
            element = {tag: tag_dicc}
            self.data_xml.append(element)

    def get_tags(self):
        return self.data_xml


# Función de registro de operaciones en un log
def log_reg(config_info, info):

    with open(log, 'a') as log_file:
        hora = time.strftime('%Y%m%d%H%M%S', time.gmtime(time.time()))
        info = hora + ' ' + info + '\r\n'
        log_file.write(info)


"""
Clase manejadora del registrar
"""


class SIPRegisterHandler(socketserver.DatagramRequestHandler):

    nonce = '898989898798989898989"\r\n\r\n'
    bad_str = 'SIP/2.0 400 Bad Request\r\n\r\n'
    client_list = []
    hora = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time()))
    resend_address = []
    resend_port = []

    # Manejador que administra las peticiones SIP
    def handle(self):

        self.json2registered()

        # Leyendo línea a línea lo que manda el cliente
        line = self.rfile.read()
        data = line.decode('utf-8')
        chops = data.split()

        print("Received from the client: " + '\r\n' + data)

        REQUEST = chops[0]

        # Petición REGISTER
        if REQUEST == 'REGISTER':

            # Con el cliente sin autorizar
            if len(chops) < 6:

                # Apertura del log
                log_info = 'Received from ' + self.client_address[0] + ':' + \
                            str(chops[1].split(':')[2]) + ': ' + \
                            data.replace('\r\n', ' ')
                log_reg(config_info, log_info)

                auto = 'SIP/2.0 401 Unauthorized\r\n' + \
                       'WWW Authenticate: Digest nonce="' + self.nonce
                print("Sending... " + '\r\n' + auto)
                self.wfile.write(bytes(auto, 'utf-8'))

                log_info = 'Sent to ' + self.client_address[0] + ':' + \
                           str(chops[1].split(':')[2]) + \
                           ': ' + auto.replace('\r\n', ' ')
                log_reg(config_info, log_info)

            # Autenticación del cliente
            elif len(chops) >= 6:

                log_info = 'Received from ' + self.client_address[0] + ':' + \
                            str(chops[1].split(':')[2]) + ': ' + \
                            data.replace('\r\n', ' ')
                log_reg(config_info, log_info)

                user = chops[1].split(':')[1]
                passwords = open(passwd_file, 'r')

                for lines in passwords.readlines():

                    # Se comprueba la contraseña
                    if user == lines.split(':')[0]:

                        password = lines.split(':')[1]

                        authenticate = hashlib.sha1()
                        authenticate.update(bytes(password, 'utf-8'))
                        authenticate.update(bytes(self.nonce, 'utf-8'))
                        authenticate = authenticate.hexdigest()

                        # Cliente autorizado
                        exp_time = int(chops[4])

                        client = [user,
                                  {"address": self.client_address[0],
                                   "port": chops[1].split(':')[2],
                                   "exp_time": str(self.hora) + ' + ' +
                                   str(exp_time)}]

                        if exp_time == 0:
                            for cli in self.client_list:
                                if cli[0] == user:
                                    self.client_list.remove(cli)

                        if exp_time > 0:
                            for cli in self.client_list:
                                if cli[0] == user:
                                    self.client_list.remove(cli)
                            self.client_list.append(client)
                            print('Client successfully registered\r\n')
                            ok_str = 'SIP/2.0 200 OK\r\n'
                            print("Sending... " + '\r\n' + ok_str)
                            self.wfile.write(bytes(ok_str, 'utf-8'))

                            log_info = 'Sent to ' + self.client_address[0] + \
                                       ':' + str(chops[1].split(':')[2]) + \
                                       ': ' + ok_str.replace('\r\n', ' ')
                            log_reg(config_info, log_info)

                        self.register2json()

        # Petición INVITE
        elif REQUEST == 'INVITE':

            destination = chops[1][4:]
            resend = False

            for cli in self.client_list:
                if cli[0] == destination:
                    log_info = 'Received from ' + cli[1]["address"] + \
                               ':' + str(cli[1]["port"]) + ': ' + \
                                data.replace('\r\n', ' ')
                    log_reg(config_info, log_info)

                    resend = True
                    with socket.socket(socket.AF_INET,
                                       socket.SOCK_DGRAM) as my_socket:
                        my_socket.connect((cli[1]["address"],
                                           int(cli[1]["port"])))
                        self.resend_address.append(cli[1]["address"])
                        self.resend_port.append(int(cli[1]["port"]))
                        my_socket.send(bytes(data, 'utf-8'))
                        print()
                        print("Resending: (" + cli[1]["address"] + "," +
                              cli[1]["port"] + ")\r\n" + data)

                        log_info = 'Resending to ' + cli[1]["address"] + \
                                   ':' + str(cli[1]["port"]) + \
                                   ': ' + data.replace('\r\n', ' ')
                        log_reg(config_info, log_info)

                        response = my_socket.recv(1024).decode('utf-8')
                        print('Received from the server', response)
                        self.wfile.write(bytes(response, 'utf-8'))

                        log_info = 'Received from ' + cli[1]["address"] + \
                                   ':' + str(cli[1]["port"]) + ': ' + \
                                   response.replace('\r\n', ' ')
                        log_reg(config_info, log_info)

                        resend_address = []
                        resend_port = []

            if not resend:
                not_found = "SIP/2.0 404 User Not Found\r\n\r\n"
                self.wfile.write(bytes(not_found, 'utf-8'))
                print('Sending...', not_found)

                log_info = 'Sent to ' + cli[1]["address"] + \
                           ':' + str(cli[1]["port"]) + \
                           ': ' + 'Error: ' + not_found.replace('\r\n', ' ')
                log_reg(config_info, log_info)

                resend_address = []
                resend_port = []

        # Petición ACK
        elif REQUEST == 'ACK':

            destination = chops[1][4:]

            for cli in self.client_list:
                if cli[0] != destination:

                    with socket.socket(socket.AF_INET,
                                       socket.SOCK_DGRAM) as my_socket:
                        my_socket.connect((cli[1]["address"],
                                           int(cli[1]["port"])))
                        my_socket.send(bytes(data, 'utf-8'))
                        print("Resending: (" + self.resend_address[0] + "," +
                              str(self.resend_port[0]) + ")\r\n" + data)

                        log_info = 'Resending to ' + cli[1]["address"] + \
                                   ':' + str(cli[1]["port"]) + ': ' + \
                                   data.replace('\r\n', ' ')
                        log_reg(config_info, log_info)

                        resend_address = []
                        resend_port = []

        elif REQUEST == 'BYE':

            destination = chops[1][4:]

            for cli in self.client_list:
                if cli[0] != destination:

                    with socket.socket(socket.AF_INET,
                                       socket.SOCK_DGRAM) as my_socket:
                        my_socket.connect((cli[1]["address"],
                                           int(cli[1]["port"])))
                        my_socket.send(bytes(data, 'utf-8'))
                        print("Resending: (" + self.resend_address[0] + "," +
                              str(self.resend_port[0]) + ")\r\n" + data)

                        log_info = 'Resending to ' + cli[1]["address"] + \
                                   ':' + str(cli[1]["port"]) + ': ' + \
                                   data.replace('\r\n', ' ')
                        log_reg(config_info, log_info)

                        response = my_socket.recv(1024).decode('utf-8')
                        print('Received from the server:', response)

                        self.wfile.write(bytes(response, 'utf-8'))

                        log_info = 'Resending to' + cli[1]["address"] + \
                                   ':' + str(cli[1]["port"]) + ': ' + \
                                   response.replace('\r\n', ' ')
                        log_reg(config_info, log_info)

                        resend_address = []
                        resend_port = []

    def register2json(self):

        json_file = open('registered.json', 'w')
        json.dump(self.client_list, json_file, indent='\t')

    def json2registered(self):

        try:
            with open('registered.json') as client_file:
                self.client_list = json.load(client_file)
        except:
            self.register2json()

if __name__ == "__main__":

    # Archivo de configuración XML y método pasados por comandos.
    try:
        XML = str(sys.argv[1])
    except:
        sys.exit("Usage: python3 proxy_registrar.py config")

    # Instanciación del manejador del archivo de configuración
    parser = make_parser()
    cHandler = Proxy_XmlHandler()
    parser.setContentHandler(cHandler)
    parser.parse(open(XML))
    config_info = cHandler.get_tags()

    print()

    # Declaración de variables usadas al extraer los datos del XML
    proxy_name = config_info[0]['server']['name']
    proxy_ip = config_info[0]['server']['ip']
    proxy_port = config_info[0]['server']['puerto']
    user_file = config_info[1]['database']['path']
    passwd_file = config_info[1]['database']['passwdpath']
    log = config_info[2]['log']['path']

    # Creación del servidor
    serv = socketserver.UDPServer((proxy_ip,
                                   int(proxy_port)),
                                  SIPRegisterHandler)
    print("Server " + proxy_name + " listening at port " + proxy_port +
          "..." + '\r\n')
    log_info = 'Starting...'
    log_reg(config_info, log_info)

    try:
        serv.serve_forever()
    except KeyboardInterrupt:
        print()
        log_info = 'Finishing...'
        log_reg(config_info, log_info)
        print("Server offline")
