#!/usr/bin/python3
# -*- coding: utf-8 -*-

import http.server
import socketserver
from urllib.parse import urlparse
from urllib.parse import parse_qs
import json
import xmltodict
import upnpclient

class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        # Extract query param
        action = ''
        query_components = parse_qs(urlparse(self.path).query)
        if 'action' in query_components:
            action = query_components["action"][0]
            content_type = "application/json"
            
            self.send_response(200)
            self.send_header("Content-type", content_type)
            self.end_headers()

            if action == "getdata":
                obj = dev.AVTransport.GetMediaInfo(InstanceID='0')
                meta = obj['CurrentURIMetaData']
                items = xmltodict.parse(meta)["DIDL-Lite"]["item"]
                try:
                    print(obj["TrackSource"])
                    items["TrackSource"] = obj["TrackSource"]
                except:
                    print("Error adding TrackSource")
                    pass

                self.wfile.write(str.encode(json.dumps(items)))
                return

            elif action == "status":
                obj = dev.AVTransport.GetTransportInfo(InstanceID='0')
                self.wfile.write(str.encode(json.dumps(obj)))
                return  
            elif action == "play":
                dev.AVTransport.Play(InstanceID='0',Speed='1')
                return
            elif action == "pause":
                dev.AVTransport.Pause(InstanceID='0')
                return
            elif action == "next":
                dev.AVTransport.Next(InstanceID='0')
                return
            elif action == "prev":
                dev.AVTransport.Previous(InstanceID='0')
                return
        else:
            if self.path == "" or self.path == "/":
                self.path = 'wiim.html'

            return http.server.SimpleHTTPRequestHandler.do_GET(self)


####################################################################
#### Change the ip address to that of your WiiM Mini
dev = upnpclient.Device("http://192.168.68.112:49152/description.xml")
####################################################################

# Create an object of the above class
handler_object = MyHttpRequestHandler

PORT = 8080
my_server = socketserver.TCPServer(("", PORT), handler_object)

# Start the server
my_server.serve_forever()
