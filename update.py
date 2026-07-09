import json
import os
import socket
import ipaddress
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration file path
CONFIG_FILE = 'config.json'
DOMAIN_OUTPUT = 'speedtest_domain.list'
IP_OUTPUT = 'speedtest_ipcidr.list'

def is_ip(address):
    """Check if the string is a valid IPv4 address."""
    try:
        return ipaddress.ip_address(address).version == 4
    except ValueError:
        return False

def add_ip(ip_list, address):
    ip = ipaddress.ip_address(address)
    ip_list.add(f"{ip}/{32 if ip.version == 4 else 128}")

def resolve_domains(domain_list, ip_list):
    domains = sorted(domain_list)
    resolved = 0
    failed = 0

    if not domains:
        print("Resolved domains: 0, failed: 0.")
        return

    def lookup(domain):
        try:
            return {
                info[4][0]
                for info in socket.getaddrinfo(domain, None, proto=socket.IPPROTO_TCP)
            }
        except socket.gaierror:
            return set()

    with ThreadPoolExecutor(max_workers=min(32, len(domains))) as executor:
        futures = {executor.submit(lookup, domain): domain for domain in domains}
        for future in as_completed(futures):
            addresses = future.result()
            if not addresses:
                failed += 1
                continue
            resolved += 1
            for address in addresses:
                add_ip(ip_list, address)

    print(f"Resolved domains: {resolved}, failed: {failed}.")

def fetch_nodes():
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: {CONFIG_FILE} not found.")
        return

    with open(CONFIG_FILE, 'r', encoding='ascii') as f:
        config = json.load(f)
    
    targets = config.get('targets', [])
    domain_list = set()
    ip_list = set()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for target in targets:
        keyword = target.get('keyword')
        target_cc = target.get('cc')
        print(f"Fetching nodes for: {keyword} ({target_cc})...")
        
        url = f"https://www.speedtest.net/api/js/servers?engine=js&search={urllib.parse.quote(keyword)}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status != 200:
                    continue
                nodes = json.load(resp)
                count = 0
                for node in nodes:
                    # Strict CC matching
                    if node.get("cc") == target_cc:
                        host_with_port = node.get("host", "")
                        if host_with_port:
                            # Strip port number
                            host = host_with_port.split(':')[0].lower()
                            
                            if is_ip(host):
                                add_ip(ip_list, host)
                            else:
                                domain_list.add(host)
                                ookla_suffix = ".prod.hosts.ooklaserver.net"
                                if host.endswith(ookla_suffix):
                                    base_domain = host[:-len(ookla_suffix)]
                                    domain_list.add(base_domain)
                                    if is_ip(base_domain):
                                        add_ip(ip_list, base_domain)
                            count += 1
                print(f"Added {count} nodes for {target_cc}.")
        except Exception as e:
            print(f"Failed to fetch {keyword}: {e}")

    resolve_domains(domain_list, ip_list)

# Write Domain List
    with open(DOMAIN_OUTPUT, "w", encoding="ascii") as f:
        if not domain_list:
            f.write("placeholder.test\n")
        else:
            for d in sorted(list(domain_list)):
                f.write(f"{d}\n")

    # Write IP CIDR List
    with open(IP_OUTPUT, "w", encoding="ascii") as f:
        if not ip_list:
            f.write("198.51.100.1/32\n")
        else:
            for ip in sorted(list(ip_list)):
                f.write(f"{ip}\n")

    print(f"Update completed. Domains: {len(domain_list)}, IPs: {len(ip_list)}.")

if __name__ == "__main__":
    fetch_nodes()
