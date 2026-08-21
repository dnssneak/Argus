#!/usr/bin/env python3
"""
Module 3: Network Scanning
Performs safe Nmap scans using predefined command presets.
"""

import subprocess
import re
import ipaddress


class NetworkScanner:
    """
    Executes Nmap scans with predefined safe commands.
    No user input is ever passed directly to the shell.
    """

    # Predefined scan commands. Target is inserted at %s.
    SCAN_COMMANDS = {
        "ping": ["nmap", "-sn", "%s"],
        "full": ["nmap", "-sV", "-p", "1-1024,1433,3306,3389,5432,8080,8443", "--open", "%s"],
    }

    def __init__(self, target, scan_type):
        self.raw_target = target.strip()
        self.target = self.raw_target.lower()
        self.scan_type = scan_type.strip().lower()
        self.is_valid = self._validate_target()

    def _validate_target(self):
        """Validate that target is a domain or IP. No shell metacharacters allowed."""
        if not self.target:
            return False

        # Reject any input containing shell metacharacters
        dangerous = re.compile(r'[;&|`$<>\\]')
        if dangerous.search(self.raw_target):
            return False

        # Check if valid IP
        try:
            ipaddress.ip_address(self.target)
            return True
        except ValueError:
            pass

        # Check if valid domain (basic check)
        domain_pattern = re.compile(
            r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$'
        )
        if domain_pattern.match(self.target):
            return True

        return False

    def collect(self):
        """Run the selected scan and return structured results."""
        if not self.is_valid:
            return {
                "target": self.raw_target,
                "error": "Invalid target. Please enter a valid domain or IP address.",
                "host_status": "Unknown",
                "open_ports": [],
                "services": [],
                "scan_status": "Failed",
                "ping_output": "",
            }

        if self.scan_type not in self.SCAN_COMMANDS:
            return {
                "target": self.raw_target,
                "error": f"Invalid scan type: {self.scan_type}",
                "host_status": "Unknown",
                "open_ports": [],
                "services": [],
                "scan_status": "Failed",
                "ping_output": "",
            }

        return self._run_scan()

    def _run_scan(self):
        """Execute Nmap using subprocess with strict command list."""
        cmd = [arg if arg != "%s" else self.target for arg in self.SCAN_COMMANDS[self.scan_type]]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            return self._parse_output(result.stdout, result.returncode)
        except subprocess.TimeoutExpired:
            return {
                "target": self.raw_target,
                "error": "Scan timed out after 120 seconds.",
                "host_status": "Unknown",
                "open_ports": [],
                "services": [],
                "scan_status": "Timed Out",
                "ping_output": "",
            }
        except FileNotFoundError:
            return {
                "target": self.raw_target,
                "error": "Nmap not found. Please install Nmap.",
                "host_status": "Unknown",
                "open_ports": [],
                "services": [],
                "scan_status": "Failed",
                "ping_output": "",
            }
        except Exception as e:
            return {
                "target": self.raw_target,
                "error": f"Scan failed: {str(e)}",
                "host_status": "Unknown",
                "open_ports": [],
                "services": [],
                "scan_status": "Failed",
                "ping_output": "",
            }

    def _parse_output(self, output, returncode):
        """Parse Nmap output into structured data."""
        result = {
            "target": self.raw_target,
            "host_status": "Unknown",
            "open_ports": [],
            "services": [],
            "scan_status": "Completed",
            "ping_output": "",
            "raw_output": output,
        }

        if returncode != 0 and not output:
            result["scan_status"] = "Failed"
            result["error"] = "Nmap returned an error."
            return result

        lines = output.splitlines()

        # Ping scan parsing
        if self.scan_type == "ping":
            ping_lines = []
            host_up = False
            
            for line in lines:
                stripped = line.strip()
                if stripped:
                    ping_lines.append(stripped)
                
                if "Host is up" in stripped:
                    host_up = True
                    result["host_status"] = "Up"
                elif "0 hosts up" in stripped:
                    result["host_status"] = "Down"
                elif "1 host up" in stripped:
                    host_up = True
                    result["host_status"] = "Up"

            # Store the full ping output for display
            result["ping_output"] = "\n".join(ping_lines)
            
            if not host_up and result["host_status"] == "Unknown":
                result["host_status"] = "Down"
            
            return result

        # Full scan parsing (ports + services combined)
        for line in lines:
            # Match: 22/tcp open  ssh     OpenSSH 8.2p1
            # Match: 80/tcp open  http
            match = re.match(r'^\s*(\d+)/(tcp|udp)\s+open\s+(\S+)(?:\s+(.+))?', line)
            if match:
                port = int(match.group(1))
                protocol = match.group(2).upper()
                service = match.group(3)
                version = match.group(4).strip() if match.group(4) else ""

                result["open_ports"].append({
                    "port": port,
                    "protocol": protocol,
                    "state": "Open",
                })

                result["services"].append({
                    "port": port,
                    "protocol": protocol,
                    "name": service,
                    "version": version,
                })

        # Determine host status from full scan
        for line in lines:
            if "Host is up" in line:
                result["host_status"] = "Up"
                break
            elif "Host seems down" in line:
                result["host_status"] = "Down"
                break

        if not result["open_ports"] and result["host_status"] == "Up":
            result["host_status"] = "Up (No open ports found)"

        return result