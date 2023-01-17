import http.server
import socketserver
from urllib.parse import urlparse, parse_qs
import json
import xmltodict
import string
import ifaddr
import socket
import re
import requests
import xml.etree.ElementTree as ET
import upnpclient
import threading

def getIPs():
    """
    Function to get all of the IP addresses on the system
    
    :returns a list of IP addresses
    """
    ips = []
    # Get list of all adapters on the system
    adapters = ifaddr.get_adapters()

    for iface in adapters:
        for addr in iface.ips:
            # Only return IPv4 addresses that
            #    are not 127.0.0.1, and
            #    are not in the reserved 169.254.0.0/16 range
            if (addr.is_IPv4 and (addr.ip != '127.0.0.1' and (addr.network_prefix != 16 and addr.ip[:7] != '169.254'))):
                ips.append(addr.ip)

    return ips

def findUPnPlocations():
    """
    Function to find the UPnP devices on the local network

    :returns a list of all of the UPnP URLS on the network
    """
    SSDP_MX = 2
    locations = []
    location_regex = re.compile("location:[ ]*(.+)\r\n", re.IGNORECASE)
    ssdpDiscover = ('M-SEARCH * HTTP/1.1\r\n' +
                    'ST: ssdp:all\r\n' +
                    'MX: 2\r\n' +
                    'MAN: "ssdp:discover"\r\n' +
                    'HOST: 239.255.255.250:1900\r\n' +
                    '\r\n')
    
    myIPs = getIPs()
    for ip in myIPs:
        # Open a socket for every IP address on the system, then send an SSDP discovery message and wait for UPnP servers to respond
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, SSDP_MX)
        sock.bind((ip, 0))
        sock.sendto(ssdpDiscover.encode('ASCII'), ("239.255.255.250", 1900))
        sock.settimeout(2)
        try:
            while True:
                data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
                location_result = location_regex.search(data.decode('ASCII'))
                if location_result and (location_result.group(1) in locations) == False:
                    locations.append(location_result.group(1))
        except socket.error:
            sock.close()

    return locations

def findWiiM(locations = [], name: string = None):
    """
    Function to find the WiiM Mini given a list of UPnP location URLs
    
    :param list locations : list of UPnP location URLs
    :param str name       : name of the devie that we are looking for

    :return URL of the device we are looking for or None if not found
    """
    frinedlyNameSTR = "./{urn:schemas-upnp-org:device-1-0}device/{urn:schemas-upnp-org:device-1-0}friendlyName"
    device = []
    if name:
        if len(locations) > 0:
            for location in locations:
                try:
                    resp = requests.get(location, timeout=2)
                    try:
                        xmlRoot = ET.fromstring(resp.text)
                    except:
                        print('\t[!] Failed XML parsing of %s' % location)
                        continue;
                    if name in xmlRoot.find(frinedlyNameSTR).text:
                        device.append(location)
                except requests.exceptions.ConnectionError:
                    print('[!] Could not load %s' % location)
                except requests.exceptions.ReadTimeout:
                    print('[!] Timeout reading from %s' % location)
        else:
            print('ERROR: No list of UPnP location URLs was provided.')
    else:
        print('ERROR: No name to look for was provided.')

    return device

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

def main():
    PORT = 8080 # Port we are going to listen on
    locations = findUPnPlocations()
    wiim = findWiiM(locations, 'WiiM Mini')
    ####################################################################
    #### Change the ip address to that of your WiiM Mini
    #### wiim = 'http://192.168.1.254:49152/description.xml'
    ####################################################################

    devs = []
    for w in wiim:
        devs.append(upnpclient.Device(w))

    # Create an object of the above class
    handler_object = MyHttpRequestHandler

    print('Starting servers...')

    my_servers = []
    for dev in devs:
        my_servers.append(socketserver.TCPServer(("", PORT), handler_object))
        print(f'     http://localhost:{PORT}/   ==> {dev.friendly_name}')
        PORT += 1

    threads = []
    for server in my_servers:
        threads.append(threading.Thread(target=server.serve_forever))

    # Start the server
    for t in threads:
        t.start()
        
    for t in threads:
        t.join()

if __name__ == '__main__':
    main()
