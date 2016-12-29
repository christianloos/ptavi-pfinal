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

""" Clase manejadora del XML de configuración para el proxy """
class Proxy_XmlHandler(ContentHandler):

    def __init__(self):
        self.tags = {}

    # Definición de la lista de atributos
    def startElement(self, name, attrs):
        data_xml = {}
        att_1 = ['name', 'ip', 'puerto']
        att_2 = ['path', 'passwdpath']
        att_3 = ['path']
        tag_list = {'server': att_1, 'database': att_2,
                    'log': att_3}

        if tag in tag_list:
            for atribute in tag_list[tag]:
                if tag == 'server' and atribute == 'ip':
                    if attrs.get(atribute, "127.0.0.1") != "":
                        data_xml[atribute] = attrs.get(atribute, "127.0.0.1")
                    elif attrs.get(atribute, "") != "":
                        data_xml[atribute] = attrs.get(atribute, "")
                    self.tag_list[tag] = data_xml

    def get_tags(self):
        return self.tag_list

""" Clase manejadora del servidor SIP """
class SIPRegisterHandler(socketserver.DatagramRequestHandler):

    user_list = []
    nonce = '898989898798989898989'
    resend_address = []
    resend_port = []
    
    # Manejador que administra las peticiones Register
    def handle(self):
        self.json2registered()
        self.expiration()
        line = self.rfile.read()
        data = line.decode('utf-8')
        chops = data.split()
        method = chops[0]
        print('Received:')
        print(line.decode('utf-8'))
        
        if method == 'REGISTER' and len(chops) >= 6:
            auto = chops[5]
            fich = open(config_info['database']['passwdpath'], 'r')
            
            for linea in fich.readlines():
                if chops[1][4:-5] == linea.split()[0][:-5]:
                    passwd = linea.split()[0][-4:]
                    
                    authenticate = hashlib.sha1()
                    authenticate.update(bytes(passwd, 'utf-8'))
                    authenticate.update(bytes(self.nonce,'utf-8'))
                    authenticate = authenticate.hexdigest()
                    
                    if authenticate == chops[7][10:-1]:
                        self.wfile.write(b"SIP/2.0 200 OK\r\n\r\n")
                        expires = int(chops[4].split('/')[0])
                        gm = time.strftime('%Y-%m-%d %H:%M:%S',
                                           time.gmtime(time.time()+expires))
                        client = [chops[1][4:-5],
                                  {"address": self.client_address[0],
                                   "port": chops[1][-4],
                                   "expires": gm}]
                        
                        if chops[4].split('/')[0] == '0':
                            for user in self.user_list:
                                if user[0] == chops[1][4:-5]:
                                    self.user_list.remove(user)
                        elif chops[0] == 'REGISTER':
                            self.user_list.append(client)
                            if chops [3][:-1] == 'Expires':
                                if chops[4].split('/')[0] == '0':
                                    self.data_list.remove(client)
                            print('Client successfully registered')

                        self.register2json()
                    else:
                        print('Incorrect password for user: ' + chops[1][4:-5])
                        self.wfile.write(b"SIP/2.0 400 Bad Request\r\n\r\n")

        elif method == 'REGISTER' and len(chops) < 6:
            self.wfile.write(bytes('SIP/2.0 401 Unauthorized\r\n' +
                                   'WW Authenticate: Digest nonce="' + self.nonce +
                                   '"\r\n\r\n'))
            print('Client not successfully registered, authentication required')
            print()
            
        elif method == 'INVITE':
            dest = chops[1][4:]
            resend = False
            for client in self.user_list:
                if client[0] == dest:
                    resend = True
                    with socket.socket(socket.AF_INET, 
                                       socket.SOCK_DGRAM) as my_socket:
                        my_socket.connect((client[1]["address"], 
                                           int(client[1]["port"])))
                        self.resend_address.append(client[1]["address"])
                        self.resend_port.append(int(client[1]["port"]))
                        my_socket.send(bytes(lines.decode('utf-8'),'utf-8' + b'\r\n'))
                        print("Reenviando: (" + client[1]["address"] + "," +
                              client[1]["port"] + ")")
                        print(data)
                        
                        reply = my_socket.recv(1024).decode('utf-8')
                        print('Recibido --', reply)
                        
                        self.wfile.write(bytes(reply, 'utf-8'))
                        
            if not resend:
                self.wfile.write(b"SIP/2.0 404 User Not Found\r\n\r\n")
                
        elif method == 'ACK':
            ack_chops = data.split()
            print("Reenviando: (" + self.resend_adress[0] + str(self.resend_port[0]) +
                  ")")
            print(data)
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as my_socket:
                my_socket.connect((self.resend_address[0], self.resend_port[0]))
                my_socket.send(bytes(lines.decode('utf-8'), 'utf-8'))
                self.resend_address = []
                self.resend_port = []
                
        def register2json(self):
            json.dump(self.user_list, open('registered.json', 'w'), indent='\t')
            
        def json2registered(self):
            try:
                with open('registered.json') as client_list:
                    self.user_list = json.load(client_list)
            except:
                self.register2json()
                
        def expiration(self):
            for user in self.user_list:
                if user[1]["expires"] <= time.strftime('%Y-%m-%d %H:%M:%S',
                                                       time.gmtime(time.time())):
                    self.user_list.remove(user)
                    json.dump(self.user_list, open('registered.json', 'w'), indent='\t')


if __name__ == "__main__":

    try:
        CONFIG = sys.argv[1]
    except:
        sys.exit("Usage: python3 proxy_registrar.py config")

    parser = make_parser()
    cHandler = Proxy_XmlHandler()
    parser.setContentHandler(cHandler)
    parser.parse(open(CONFIG))
    
    config_info = cHandler.get_tags()
    
    serv = socketserver.UDPServer(('', int(config_info['server']['puerto'])),
                                  SIPRegisterHandler)
    print("Server Sheldon_Proxy listening at port " +
          config_info['server']['puerto'] + " ..." + b'\r\n')

    try:
        serv.serve_forever()
    except KeyboardInterrupt:
        json = open('registered.json', 'w')
        json.close()
        print("Finalizado servidor")
