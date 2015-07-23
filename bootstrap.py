#!/usr/bin/python
import subprocess32
import logging
import fleet.v1 as fleet
import netifaces
import requests
from netaddr import IPNetwork
from sys import getfilesystemencoding
import argparse

# ARGS
parser = argparse.ArgumentParser(
    description='Bootstrap a CoreOS Weave node'
)

parser.add_argument(
    '-weave-binary',
    dest='weave',
    metavar='/opt/bin/weave',
    action='store',
    default="/opt/bin/weave",
    help='Location of Weave binary (Default: /opt/bin/weave)'
)

parser.add_argument(
    '-etcd-addr',
    dest='etcd',
    metavar='endpoint',
    action='store',
    default="http://127.0.0.1:4001",
    help='Etcd endpoint (Default: http://127.0.0.1:4001)'
)

parser.add_argument(
    '-etcd-key',
    dest='etcd_key',
    metavar='/my/key',
    action='store',
    default="/bootstrap/weave/dns/lastaddr",
    help='Etcd key for storing last used DNS address (Default: /bootstrap/weave/dns/lastaddr)'
)

parser.add_argument(
    '-dns-range',
    dest='dns_range',
    metavar='CIDR',
    action='store',
    default="10.100.0.0/24",
    help='Weave DNS subnet (Default: 10.100.0.0/24)'
)

try:
    args = parser.parse_args()
except Exception, e:
    logger.error("Could not parse args", str(e))
    raise e

# LOGGING
logger = logging.getLogger('weave-bootstrap')
logger.setLevel(logging.DEBUG)

# create console handler
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter and add it to the handlers
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
ch.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(ch)

def main():
    try:
        members = get_fleet_ips('http+unix://%2Fvar%2Frun%2Ffleet.sock')
    except Exception, e:
        logger.error("Could not connect to Fleet")

    # Remove localhost from Fleet member list
    #   so we don't try to connect to ourself
    try:
        my_addrs = get_local_ips()
    except Exception, e:
        logger.error("Could not get local IP list")
    
    for addr in my_addrs:
        if addr in members:
            members.remove(addr)

    # Add whomever's left to Weave network
    add_to_weave(members)
    start_weave_dns()
    logger.info("Complete!")

def get_fleet_ips(url):
    try:
        c = fleet.Client(url)
    except Exception, e:
        logger.error("Unable to discover fleet")

    try:
        ips = []
        for machine in c.list_machines():
            ips.append(machine.primaryIP)
    except Exception, e:
        logger.error("Unable to list nodes")
    return ips

def get_local_ips():
    my_addrs = []
    try:
        for iface in netifaces.interfaces():
            try:
                for a in netifaces.ifaddresses(iface)[netifaces.AF_INET]:
                    if a['addr'] == '127.0.0.1':
                        break
                    my_addrs.append(a['addr'])
            except Exception, e:
                pass
    except Exception, e:
        logger.error("Could not get local IP list")
    return my_addrs

def add_to_weave(ip_list):
    try:
        for ip in ip_list:
            # Add the peer to weave & wait for the command to finish
            subprocess32.Popen([args.weave, 'connect', ip], bufsize=0).wait()
    except Exception, e:
        logger.error("Failed weave command: " + str(e))
        return e

def start_weave_dns():
    my_dns_ip = get_dns_ip()
    try:
        # For some reason Weave DNS wants the CIDR range included on the DNS addr
        subprocess32.Popen([args.weave, 'launch-dns', str(my_dns_ip)+'/'+args.dns_range.split('/')[-1]], bufsize=0).wait()
    except Exception, e:
        logger.error("Failed weave dns command: " + str(e))
        return e

def get_dns_ip():
    di = requests.get(args.etcd+"/v2/keys"+args.etcd_key)
    # If no previous DNS addr exists @ this etcd key, start from the beginning
    #   else get the next one in order
    if di.status_code == 404 or di.json()['node']['value'] == '':
        # This will come back as X.X.X.0
        addr = get_next_ip_in_range(args.dns_range, '')
    else:
        addr = di.json()['node']['value']
    # Get the next IP (if no existing value addr will be the X.X.X.0 address)
    dns_ip = get_next_ip_in_range(args.dns_range, str(addr))
    # Set the new value in etcd before returning
    new = requests.put(args.etcd+"/v2/keys"+args.etcd_key, data={ 'value' : dns_ip})
    # Validate current node for success
    if new.json()['node']['value'] != dns_ip:
        logger.info(new.json()['node']['value'] + " | " + str(new.status_code))
        logger.error("Failed to set new lastaddr!")
    return dns_ip

def get_next_ip_in_range(subnet, addr):
    net = IPNetwork(subnet)
    # If addr not passed, return the first address
    if addr == "":
        return net[0]
    i=0
    for ip in net:
        if str(ip) == addr:
            return str(net[i+1])
        else:
            i+=1

# Workaround for pyinstaller:
# https://github.com/pyinstaller/pyinstaller/issues/885
def _sys_getenc_wrapper():
    return 'UTF-8'

sys.getfilesystemencoding = _sys_getenc_wrapper

if __name__ == "__main__":
    main()
