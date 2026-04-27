import requests
import json
import re
import os

# Configuration file path
CONFIG_FILE = 'config.json'
DOMAIN_OUTPUT = 'speedtest_domain.list'
IP_OUTPUT = 'speedtest_ipcidr.list'

def is_ip(address):
    """Check if the string is a valid IPv4 address."""
    return re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", address) is not None

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
        
        url = f"https://www.speedtest.net/api/js/servers?engine=js&search={requests.utils.quote(keyword)}"
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                nodes = resp.json()
                count = 0
                for node in nodes:
                    # Strict CC matching
                    if node.get("cc") == target_cc:
                        host_with_port = node.get("host", "")
                        if host_with_port:
                            # Strip port number
                            host = host_with_port.split(':')[0].lower()
                            
                            if is_ip(host):
                                ip_list.add(f"{host}/32")
                            else:
                                domain_list.add(host)
                                ookla_suffix = ".prod.hosts.ooklaserver.net"
                                if host.endswith(ookla_suffix):
                                    base_domain = host[:-len(ookla_suffix)]
                                    domain_list.add(base_domain)
                                    if is_ip(base_domain):
                                        ip_list.add(f"{base_domain}/32")
                print(f"Added {count} nodes for {target_cc}.")
        except Exception as e:
            print(f"Failed to fetch {keyword}: {e}")

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
