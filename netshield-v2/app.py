import os
import sys
from tk_runtime import prepare_tk

prepare_tk()

import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel, ttk, scrolledtext
import pyshark
import subprocess
import platform
from datetime import datetime
import threading
import asyncio
import re
import ipaddress
import shlex
import ctypes
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Setup logging for debugging
logging.basicConfig(filename=os.path.join(BASE_DIR, 'netshield_debug.log'), level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

LOG_FILE = os.path.join(BASE_DIR, "netshield_log.txt")
RULES_FILE = os.path.join(BASE_DIR, "custom_rules.json")
REPORT_FILE = os.path.join(BASE_DIR, "netshield_report.txt")

# Define VULNERABILITY_INFO dictionary
VULNERABILITY_INFO = {
    "port_scan": {
        "title": "Port Scanning Detected",
        "description": "Port scanning involves probing multiple ports to find open services, often a precursor to attacks.",
        "impact": "May indicate an attacker mapping your network for vulnerabilities.",
        "mitigation": "Block the offending IP address using firewall rules."
    },
    "dns_tunnel": {
        "title": "DNS Tunneling Suspicion",
        "description": "Long or complex DNS queries may indicate data exfiltration through DNS protocol.",
        "impact": "Can be used to bypass firewalls and exfiltrate data.",
        "mitigation": "Block suspicious DNS traffic on UDP port 53."
    },
    "http_creds": {
        "title": "Unencrypted Credentials",
        "description": "Sensitive data sent over HTTP is vulnerable to interception.",
        "impact": "Credentials can be stolen by attackers using packet sniffing.",
        "mitigation": "Block HTTP traffic or enforce HTTPS."
    },
    "large_file": {
        "title": "Large File Transfer",
        "description": "Unusually large HTTP transfers may indicate data exfiltration.",
        "impact": "Could be used to steal sensitive data or distribute malware.",
        "mitigation": "Restrict large HTTP transfers on port 80."
    },
    "unknown_ports": {
        "title": "Uncommon Ports",
        "description": "Traffic on non-standard ports may indicate malicious activity.",
        "impact": "Could be used for unauthorized services or backdoors.",
        "mitigation": "Block traffic on suspicious ports."
    }
}

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        logging.error("Failed to check admin privileges")
        return False

def log_action(action):
    try:
        with open(LOG_FILE, "a") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {action}\n")
    except Exception as e:
        logging.error(f"Failed to log action: {e}")

def save_custom_rule(name, command, description):
    try:
        parse_firewall_command(command)
        rules = load_custom_rules()
        rules[name] = {"command": command, "description": description}
        with open(RULES_FILE, "w") as f:
            json.dump(rules, f, indent=2)
        log_action(f"Saved custom rule: {name}")
        return True
    except Exception as e:
        logging.error(f"Failed to save custom rule: {e}")
        messagebox.showerror("Error", f"Failed to save custom rule: {e}")
        return False

def load_custom_rules():
    try:
        if os.path.exists(RULES_FILE):
            with open(RULES_FILE, "r") as f:
                return json.load(f)
        return {}
    except Exception as e:
        logging.error(f"Failed to load custom rules: {e}")
        return {}

def analyze_pcap(file_path, limit=2000, progress_callback=None):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    except Exception as e:
        logging.error(f"Failed to set up asyncio event loop: {e}")
        return [("Failed to set up event loop.", "", "error")], None

    try:
        cap = pyshark.FileCapture(file_path, use_json=True)
    except Exception as e:
        logging.error(f"Failed to load capture file: {e}")
        return [("Failed to load capture file.", "", "error")], None

    ports = set()
    ip_counter = {}
    port_scan_tracker = {}
    dns_queries = {}
    http_creds_found = False
    file_transfer_detected = False
    count = 0
    stats = {"protocols": {}, "ips": {}, "ports": {}}

    try:
        for pkt in cap:
            count += 1
            if count > limit:
                break

            if progress_callback:
                progress_callback(count, limit)

            try:
                proto = pkt.highest_layer
                stats["protocols"][proto] = stats["protocols"].get(proto, 0) + 1

                if proto == "DNS":
                    query = pkt.dns.qry_name
                    dns_queries[query] = dns_queries.get(query, 0) + 1
                if proto == "HTTP":
                    if hasattr(pkt.http, 'authorization') or ('login' in pkt.summary.lower()):
                        http_creds_found = True
                    if hasattr(pkt.http, 'content_length') and int(pkt.http.content_length) > 500000:
                        file_transfer_detected = True
                if hasattr(pkt, 'ip'):
                    src = str(ipaddress.ip_address(pkt.ip.src))
                    dst = pkt.ip.dst
                    stats["ips"][src] = stats["ips"].get(src, 0) + 1
                    if hasattr(pkt, 'tcp') and hasattr(pkt.tcp, 'dstport'):
                        port_number = int(pkt.tcp.dstport)
                        if not 1 <= port_number <= 65535:
                            continue
                        port = str(port_number)
                        ports.add(port)
                        stats["ports"][port] = stats["ports"].get(port, 0) + 1
                        if src not in port_scan_tracker:
                            port_scan_tracker[src] = set()
                        port_scan_tracker[src].add(port)
            except Exception as e:
                logging.warning(f"Error processing packet {count}: {e}")
                continue

        cap.close()
    except Exception as e:
        logging.error(f"Error during packet capture processing: {e}")
        return [("Error during analysis.", "", "error")], None

    options = []

    for ip, port_set in port_scan_tracker.items():
        if len(port_set) > 20:
            options.append((
                f"[High] Port scanning from IP {ip} (scanned {len(port_set)} ports)",
                f"netsh advfirewall firewall add rule name=\"Block_PortScan_{ip}\" dir=in action=block remoteip={ip}",
                "port_scan"
            ))
            break

    long_domains = [d for d in dns_queries if len(d) > 50 or d.count('.') > 5]
    if len(long_domains) > 3:
        options.append((
            f"[Medium] Possible DNS tunneling ({len(long_domains)} suspicious queries)",
            "netsh advfirewall firewall add rule name=\"Block_DNS_Tunnel\" dir=out action=block protocol=UDP localport=53",
            "dns_tunnel"
        ))

    if http_creds_found:
        options.append((
            "[High] Unencrypted credentials over HTTP",
            "netsh advfirewall firewall add rule name=\"Block_HTTP_Creds\" dir=in action=block protocol=TCP localport=80",
            "http_creds"
        ))

    if file_transfer_detected:
        options.append((
            "[Medium] Large HTTP file transfer detected",
            "netsh advfirewall firewall add rule name=\"Block_Large_HTTP\" dir=in action=block protocol=TCP localport=80",
            "large_file"
        ))

    unknown_ports = [p for p in ports if p not in ["80", "443", "53"]]
    if unknown_ports:
        options.append((
            f"[Low] Uncommon ports: {', '.join(unknown_ports[:3])}",
            f"netsh advfirewall firewall add rule name=\"Block_Unknown_Ports\" dir=in action=block protocol=TCP localport={','.join(unknown_ports[:3])}",
            "unknown_ports"
        ))

    if not options:
        options.append(("No critical vulnerabilities detected.", "echo No fix applied", "none"))

    return options, stats

def parse_firewall_command(command):
    """Validate the narrow netsh grammar this application is allowed to run."""
    parts = shlex.split(command, posix=True)
    if parts[:5] != ["netsh", "advfirewall", "firewall", "add", "rule"]:
        raise ValueError("Only 'netsh advfirewall firewall add rule' commands are allowed.")

    values = {}
    allowed = {"name", "dir", "action", "remoteip", "protocol", "localport"}
    for item in parts[5:]:
        if "=" not in item:
            raise ValueError("Every firewall argument must use key=value syntax.")
        key, value = item.split("=", 1)
        if key not in allowed or key in values:
            raise ValueError(f"Unsupported or duplicate firewall argument: {key}")
        values[key] = value

    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", values.get("name", "")):
        raise ValueError("Rule names may only contain safe letters, numbers, and ._:- characters.")
    if values.get("dir") not in {"in", "out"} or values.get("action") not in {"block", "allow"}:
        raise ValueError("A valid direction and action are required.")
    if "protocol" in values and values["protocol"] not in {"TCP", "UDP"}:
        raise ValueError("Only TCP and UDP rules are supported.")
    if "remoteip" in values:
        ipaddress.ip_address(values["remoteip"])
    if "localport" in values:
        ports = values["localport"].split(",")
        if not ports or any(not p.isdigit() or not 1 <= int(p) <= 65535 for p in ports):
            raise ValueError("Ports must be comma-separated numbers from 1 to 65535.")
    return parts, values["name"]


def apply_firewall_rule(command, rule_name=None):
    if platform.system() != "Windows":
        messagebox.showerror("Platform Error", "This tool only works on Windows.")
        return False

    try:
        command_args, validated_name = parse_firewall_command(command)
        rule_name = rule_name or validated_name
        if rule_name:
            check_cmd = ["netsh", "advfirewall", "firewall", "show", "rule", f"name={rule_name}"]
            check_result = subprocess.run(check_cmd, shell=False, capture_output=True, text=True)
            if "No rules match the specified criteria" not in check_result.stdout:
                delete_cmd = ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={rule_name}"]
                subprocess.run(delete_cmd, shell=False, check=False)
                log_action(f"Deleted existing rule: {rule_name}")

        result = subprocess.run(command_args, shell=False, capture_output=True, text=True)
        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            log_action(f"Error applying rule: {error_msg}")
            messagebox.showerror("Execution Error", f"Failed to apply rule.\n\nError:\n{error_msg}")
            return False
        else:
            log_action(f"Applied firewall rule: {command}")
            messagebox.showinfo("Success", "Firewall rule applied successfully.")
            return True
    except Exception as e:
        log_action(f"Unexpected exception: {e}")
        messagebox.showerror("Unexpected Error", f"An unexpected error occurred:\n{e}")
        return False

class NetShieldApp:
    def __init__(self, master):
        self.master = master
        self.master.title("NetShield - Network Security Analyzer")
        self.master.geometry("1000x700")
        self.master.configure(bg="#1e293b")

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.configure_styles()

        try:
            self.main_frame = ttk.Frame(master, padding=20, style='Main.TFrame')
            self.main_frame.pack(fill=tk.BOTH, expand=True)

            header_frame = ttk.Frame(self.main_frame, style='Main.TFrame')
            header_frame.pack(fill=tk.X, pady=(0, 20))
            ttk.Label(header_frame, text="NetShield", font=('Helvetica', 24, 'bold'), style='Header.TLabel').pack(side=tk.LEFT)
            ttk.Label(header_frame, text="Network Security Analyzer", font=('Helvetica', 12), style='Subheader.TLabel').pack(side=tk.LEFT, padx=10)

            content_frame = ttk.Frame(self.main_frame, style='Main.TFrame')
            content_frame.pack(fill=tk.BOTH, expand=True)

            left_panel = ttk.Frame(content_frame, style='Panel.TFrame')
            left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))

            upload_frame = ttk.LabelFrame(left_panel, text="File Upload", style='Section.TLabelframe')
            upload_frame.pack(fill=tk.X, pady=10)
            ttk.Label(upload_frame, text="Select .pcapng file:", style='Label.TLabel').pack(pady=5)
            ttk.Button(upload_frame, text="Browse", command=self.upload_file, style='Accent.TButton').pack(pady=5)

            settings_frame = ttk.LabelFrame(left_panel, text="Scan Settings", style='Section.TLabelframe')
            settings_frame.pack(fill=tk.X, pady=10)
            ttk.Label(settings_frame, text="Max packets (100-10000):", style='Label.TLabel').pack(anchor='w', padx=5)
            self.packet_limit = tk.IntVar(value=2000)
            ttk.Entry(settings_frame, textvariable=self.packet_limit, width=10, style='Entry.TEntry').pack(anchor='w', padx=5, pady=5)

            actions_frame = ttk.LabelFrame(left_panel, text="Actions", style='Section.TLabelframe')
            actions_frame.pack(fill=tk.X, pady=10)
            ttk.Button(actions_frame, text="Scan & Analyze", command=self.show_fixes, style='Primary.TButton').pack(fill=tk.X, pady=5, padx=5)
            ttk.Button(actions_frame, text="Apply Selected Fix", command=self.apply_fix, style='Primary.TButton').pack(fill=tk.X, pady=5, padx=5)
            ttk.Button(actions_frame, text="Export Report", command=self.export_report, style='Primary.TButton').pack(fill=tk.X, pady=5, padx=5)
            ttk.Button(actions_frame, text="Manage Rules", command=self.show_rule_manager, style='Primary.TButton').pack(fill=tk.X, pady=5, padx=5)
            ttk.Button(actions_frame, text="Help", command=self.show_help, style='Primary.TButton').pack(fill=tk.X, pady=5, padx=5)

            right_panel = ttk.Frame(content_frame, style='Panel.TFrame')
            right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            self.status_label = ttk.Label(right_panel, text="", style='Status.TLabel')
            self.status_label.pack(fill=tk.X, pady=5)

            self.progress = ttk.Progressbar(right_panel, mode='determinate', style='Custom.TProgressbar', length=700)
            self.progress.pack(fill=tk.X, pady=5)

            self.options_frame = ttk.LabelFrame(right_panel, text="Analysis Results", style='Section.TLabelframe')
            self.options_frame.pack(fill=tk.BOTH, expand=True, pady=10)

            self.var = tk.IntVar()
            self.firewall_options = []
            self.stats = None
            self.file_path = ""
        except Exception as e:
            logging.error(f"GUI initialization error: {e}")
            messagebox.showerror("Initialization Error", f"Failed to initialize GUI: {e}")
            self.master.destroy()

    def configure_styles(self):
        try:
            self.style.configure('Main.TFrame', background='#1e293b')
            self.style.configure('Panel.TFrame', background='#334155')
            self.style.configure('Section.TLabelframe', background='#334155', foreground='#f1f5f9')
            self.style.configure('Section.TLabelframe.Label', background='#334155', foreground='#f1f5f9')
            self.style.configure('Header.TLabel', background='#1e293b', foreground='#3b82f6')
            self.style.configure('Subheader.TLabel', background='#1e293b', foreground='#94a3b8')
            self.style.configure('Label.TLabel', background='#334155', foreground='#f1f5f9')
            self.style.configure('Status.TLabel', background='#334155', foreground='#22c55e')
            self.style.configure('Primary.TButton', background='#3b82f6', foreground='#ffffff', padding=10, font=('Helvetica', 10))
            self.style.map('Primary.TButton', background=[('active', '#2563eb')])
            self.style.configure('Accent.TButton', background='#22c55e', foreground='#ffffff', padding=10, font=('Helvetica', 10))
            self.style.map('Accent.TButton', background=[('active', '#16a34a')])
            self.style.configure('Entry.TEntry', fieldbackground='#475569', foreground='#f1f5f9')

            self.style.configure('Custom.TProgressbar', troughcolor='#475569', background='#3b82f6')
            self.style.layout('Custom.TProgressbar', 
                            [('Horizontal.TProgressbar.trough',
                              {'children': [
                                  ('Horizontal.TProgressbar.pbar',
                                   {'side': 'left', 'sticky': 'ns'})
                              ]})])
            logging.info("Styles configured successfully")
        except Exception as e:
            logging.error(f"Failed to configure styles: {e}")
            self.style.configure('Custom.TProgressbar', troughcolor='#475569', background='#3b82f6')

    def upload_file(self):
        try:
            self.file_path = filedialog.askopenfilename(filetypes=[("PCAP files", "*.pcapng")])
            if self.file_path:
                log_action(f"Uploaded file: {self.file_path}")
                messagebox.showinfo("File Uploaded", f"File uploaded successfully:\n{self.file_path}")
        except Exception as e:
            logging.error(f"Error in upload_file: {e}")
            messagebox.showerror("Error", f"Failed to upload file: {e}")

    def update_status(self, message):
        try:
            self.status_label.config(text=message)
            self.master.update_idletasks()
        except Exception as e:
            logging.error(f"Error updating status: {e}")

    def update_progress(self, count, limit):
        try:
            percentage = (count / limit) * 100
            self.progress['value'] = percentage
            self.update_status(f"Scanning packet #{count}/{limit} ({percentage:.1f}%)")
        except Exception as e:
            logging.error(f"Error updating progress: {e}")

    def show_fixes(self):
        try:
            if not self.file_path:
                messagebox.showwarning("No File", "Please upload a .pcapng file first.")
                return

            limit = self.packet_limit.get()
            if not (100 <= limit <= 10000):
                messagebox.showerror("Invalid Input", "Packet limit must be between 100 and 10000.")
                return

            self.progress['value'] = 0
            self.update_status("Starting analysis...")
            self.master.config(cursor="wait")
            self.options_frame.master.config(cursor="wait")

            def analyze_and_update():
                result = [None]
                stats = [None]

                def run_analysis():
                    try:
                        result[0], stats[0] = analyze_pcap(self.file_path, limit, progress_callback=self.update_progress)
                    except Exception as e:
                        logging.error(f"Error in analysis thread: {e}")
                        result[0] = [("Analysis failed.", f"echo analysis error: {e}", "error")]

                analysis_thread = threading.Thread(target=run_analysis)
                analysis_thread.start()
                analysis_thread.join()

                def update_ui():
                    try:
                        if not result[0]:
                            result[0] = [("Analysis timed out or failed.", "echo timeout", "error")]

                        self.firewall_options = result[0]
                        self.stats = stats[0]
                        
                        for widget in self.options_frame.winfo_children():
                            widget.destroy()

                        for i, (desc, cmd, vuln_type) in enumerate(self.firewall_options):
                            frame = ttk.Frame(self.options_frame, style='Panel.TFrame')
                            frame.pack(fill=tk.X, pady=5)
                            ttk.Radiobutton(frame, text=desc, variable=self.var, value=i, style='Custom.TRadiobutton').pack(side=tk.LEFT, padx=10)
                            if vuln_type != "none" and vuln_type != "error":
                                details_btn = ttk.Button(frame, text="Details", command=lambda vt=vuln_type: self.show_vuln_details(vt), style='Accent.TButton')
                                details_btn.pack(side=tk.RIGHT, padx=10)
                            stats_btn = ttk.Button(self.options_frame, text="Show Statistics", command=self.show_statistics, style='Primary.TButton')
                            stats_btn.pack(pady=5) if i == len(self.firewall_options) - 1 else None

                        self.update_status("Analysis complete.")
                        self.master.config(cursor="")
                        self.options_frame.master.config(cursor="")
                    except Exception as e:
                        logging.error(f"Error updating UI: {e}")
                        messagebox.showerror("Error", f"Failed to update UI: {e}")

                self.master.after(0, update_ui)

            threading.Thread(target=analyze_and_update).start()
        except Exception as e:
            logging.error(f"Error in show_fixes: {e}")
            messagebox.showerror("Error", f"Failed to start analysis: {e}")
            self.master.config(cursor="")
            self.options_frame.master.config(cursor="")

    def show_vuln_details(self, vuln_type):
        try:
            info = VULNERABILITY_INFO.get(vuln_type, {})
            if not info:
                raise ValueError(f"No vulnerability info for type: {vuln_type}")
            window = Toplevel(self.master)
            window.title(info.get("title", "Vulnerability Details"))
            window.geometry("600x350")
            window.configure(bg='#1e293b')

            frame = ttk.Frame(window, padding=20, style='Main.TFrame')
            frame.pack(fill=tk.BOTH, expand=True)

            text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=15, bg='#334155', fg='#f1f5f9', font=('Helvetica', 10))
            text.pack(fill=tk.BOTH, padx=10, pady=10)
            
            content = f"Title: {info.get('title', 'Unknown')}\n\n"
            content += f"Description: {info.get('description', 'No description available.')}\n\n"
            content += f"Impact: {info.get('impact', 'No impact information available.')}\n\n"
            content += f"Mitigation: {info.get('mitigation', 'No mitigation information available.')}"
            text.insert(tk.END, content)
            text.config(state='disabled')
        except Exception as e:
            logging.error(f"Error in show_vuln_details: {e}")
            messagebox.showerror("Error", f"Failed to show vulnerability details: {e}")

    def show_statistics(self):
        try:
            window = Toplevel(self.master)
            window.title("Network Statistics")
            window.geometry("1200x400")  # Increased size for better spacing
            window.configure(bg='#1e293b')

            plt.style.use('dark_background')
            fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6), gridspec_kw={'wspace': 0.4})
            
            protocols = self.stats["protocols"]
            ax1.pie(protocols.values(), labels=protocols.keys(), autopct='%1.1f%%', colors=['#3b82f6', '#22c55e', '#ef4444', '#f97316', '#6b7280'])
            ax1.set_title("Protocol Distribution", color='#f1f5f9', pad=20)
            
            top_ips = dict(sorted(self.stats["ips"].items(), key=lambda x: x[1], reverse=True)[:5])
            ax2.bar(list(top_ips.keys()), list(top_ips.values()), color='#3b82f6')
            ax2.set_title("Top 5 Source IPs", color='#f1f5f9', pad=20)
            ax2.tick_params(axis='x', rotation=45, colors='#f1f5f9', labelsize=10)
            ax2.tick_params(axis='y', colors='#f1f5f9', labelsize=10)
            
            top_ports = dict(sorted(self.stats["ports"].items(), key=lambda x: x[1], reverse=True)[:5])
            ax3.bar(list(top_ports.keys()), list(top_ports.values()), color='#3b82f6')
            ax3.set_title("Top 5 Destination Ports", color='#f1f5f9', pad=20)
            ax3.tick_params(axis='x', rotation=45, colors='#f1f5f9', labelsize=10)
            ax3.tick_params(axis='y', colors='#f1f5f9', labelsize=10)
            
            plt.tight_layout(pad=3.0)
            fig.patch.set_facecolor('#1e293b')
            canvas = FigureCanvasTkAgg(fig, master=window)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        except Exception as e:
            logging.error(f"Error in show_statistics: {e}")
            messagebox.showerror("Error", f"Failed to show statistics: {e}")

    def export_report(self):
        try:
            if not self.firewall_options:
                messagebox.showwarning("No Analysis", "Run a scan first to generate a report.")
                return

            report = f"NetShield Analysis Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            report += "=" * 50 + "\n\n"
            report += f"File: {self.file_path}\n"
            report += f"Packet Limit: {self.packet_limit.get()}\n\n"
            report += "Detected Vulnerabilities:\n"

            for desc, cmd, vuln_type in self.firewall_options:
                report += f"- {desc}\n"
                report += f"  Recommended Action: {cmd}\n"
                if vuln_type in VULNERABILITY_INFO:
                    info = VULNERABILITY_INFO[vuln_type]
                    report += f"  Details: {info['description']}\n"
                    report += f"  Impact: {info['impact']}\n"
                    report += f"  Mitigation: {info['mitigation']}\n"
                report += "\n"

            if self.stats:
                report += "Network Statistics:\n"
                report += f"Protocols: {self.stats['protocols']}\n"
                report += f"Top 5 IPs: {dict(sorted(self.stats['ips'].items(), key=lambda x: x[1], reverse=True)[:5])}\n"
                report += f"Top 5 Ports: {dict(sorted(self.stats['ports'].items(), key=lambda x: x[1], reverse=True)[:5])}\n"

            with open(REPORT_FILE, "w") as f:
                f.write(report)
            log_action("Exported analysis report")
            messagebox.showinfo("Report Exported", f"Report saved to {REPORT_FILE}")
        except Exception as e:
            logging.error(f"Error in export_report: {e}")
            messagebox.showerror("Error", f"Failed to export report: {e}")

    def apply_fix(self):
        try:
            if not self.firewall_options:
                messagebox.showwarning("No Options", "Run a scan first to get recommendations.")
                return

            selected = self.var.get()
            _, cmd, vuln_type = self.firewall_options[selected]
            if vuln_type in {"none", "error"}:
                messagebox.showinfo("No Action", "This result does not have a firewall action.")
                return
            match = re.search(r'name="([^"]+)"', cmd)
            rule_name = match.group(1) if match else None
            apply_firewall_rule(cmd, rule_name)
        except Exception as e:
            logging.error(f"Error in apply_fix: {e}")
            messagebox.showerror("Error", f"Failed to apply fix: {e}")

    def show_rule_manager(self):
        try:
            window = Toplevel(self.master)
            window.title("Firewall Rule Manager")
            window.geometry("800x600")
            window.configure(bg='#1e293b')

            frame = ttk.Frame(window, padding=20, style='Main.TFrame')
            frame.pack(fill=tk.BOTH, expand=True)

            ttk.Label(frame, text="Current Firewall Rules:", style='Label.TLabel').pack(anchor='w')
            rules_text = scrolledtext.ScrolledText(frame, height=10, bg='#334155', fg='#f1f5f9', font=('Helvetica', 10))
            rules_text.pack(fill=tk.BOTH, pady=10)
            
            try:
                result = subprocess.run(
                    ["netsh", "advfirewall", "firewall", "show", "rule", "name=all"],
                    shell=False,
                    capture_output=True,
                    text=True,
                )
                rules_text.insert(tk.END, result.stdout)
                rules_text.config(state='disabled')
            except:
                rules_text.insert(tk.END, "Error retrieving firewall rules")
                rules_text.config(state='disabled')

            ttk.Label(frame, text="Add/Edit Custom Rule:", style='Label.TLabel').pack(anchor='w', pady=10)
            
            ttk.Label(frame, text="Rule Name:", style='Label.TLabel').pack(anchor='w')
            name_entry = ttk.Entry(frame, style='Entry.TEntry')
            name_entry.pack(fill=tk.X, pady=5)
            
            ttk.Label(frame, text="Command:", style='Label.TLabel').pack(anchor='w')
            cmd_entry = ttk.Entry(frame, style='Entry.TEntry')
            cmd_entry.pack(fill=tk.X, pady=5)
            
            ttk.Label(frame, text="Description:", style='Label.TLabel').pack(anchor='w')
            desc_entry = ttk.Entry(frame, style='Entry.TEntry')
            desc_entry.pack(fill=tk.X, pady=5)

            def save_rule():
                try:
                    name = name_entry.get().strip()
                    cmd = cmd_entry.get().strip()
                    desc = desc_entry.get().strip()
                    if name and cmd and desc:
                        if save_custom_rule(name, cmd, desc):
                            messagebox.showinfo("Success", "Custom rule saved.")
                            window.destroy()
                    else:
                        messagebox.showerror("Error", "Please fill all fields.")
                except Exception as e:
                    logging.error(f"Error in save_rule: {e}")
                    messagebox.showerror("Error", f"Failed to save rule: {e}")

            ttk.Button(frame, text="Save Custom Rule", command=save_rule, style='Accent.TButton').pack(pady=10)

            ttk.Label(frame, text="Custom Rules:", style='Label.TLabel').pack(anchor='w')
            custom_rules_text = scrolledtext.ScrolledText(frame, height=5, bg='#334155', fg='#f1f5f9', font=('Helvetica', 10))
            custom_rules_text.pack(fill=tk.BOTH, pady=10)
            
            custom_rules = load_custom_rules()
            for name, rule in custom_rules.items():
                custom_rules_text.insert(tk.END, f"Name: {name}\nCommand: {rule['command']}\nDescription: {rule['description']}\n\n")
            custom_rules_text.config(state='disabled')
        except Exception as e:
            logging.error(f"Error in show_rule_manager: {e}")
            messagebox.showerror("Error", f"Failed to show rule manager: {e}")

    def show_help(self):
        try:
            window = Toplevel(self.master)
            window.title("NetShield Help")
            window.geometry("700x500")
            window.configure(bg='#1e293b')

            frame = ttk.Frame(window, padding=20, style='Main.TFrame')
            frame.pack(fill=tk.BOTH, expand=True)

            text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=20, bg='#334155', fg='#f1f5f9', font=('Helvetica', 10))
            text.pack(fill=tk.BOTH, padx=10, pady=10)

            help_content = "NetShield Help Guide\n" + "=" * 50 + "\n\n"
            help_content += "NetShield is a network security analyzer that scans PCAP files for vulnerabilities and suggests firewall rules.\n\n"
            help_content += "Vulnerability Types and Recommended Actions:\n"

            for vuln_type, info in VULNERABILITY_INFO.items():
                help_content += f"\n{info['title']}:\n"
                help_content += f"Description: {info['description']}\n"
                help_content += f"Impact: {info['impact']}\n"
                help_content += f"Mitigation: {info['mitigation']}\n"

            help_content += "\nCustom Rules:\n"
            help_content += "You can create custom firewall rules in the Rule Manager.\n"
            help_content += "Example: netsh advfirewall firewall add rule name=\"MyRule\" dir=in action=block protocol=TCP localport=1234\n"

            text.insert(tk.END, help_content)
            text.config(state='disabled')
        except Exception as e:
            logging.error(f"Error in show_help: {e}")
            messagebox.showerror("Error", f"Failed to show help: {e}")

if __name__ == "__main__":
    try:
        required_modules = ['tkinter', 'pyshark', 'matplotlib']
        for module in required_modules:
            __import__(module)

        if not is_admin():
            messagebox.showinfo("Admin Required", "This application requires administrative privileges. Relaunching with admin rights...")
            logging.info("Relaunching with admin privileges")
            script = os.path.abspath(__file__)
            params = subprocess.list2cmdline([script, *sys.argv[1:]])
            result = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, BASE_DIR, 1)
            if result <= 32:
                raise RuntimeError("Unable to request administrator privileges")
            sys.exit()

        root = tk.Tk()
        app = NetShieldApp(root)
        root.mainloop()
    except ImportError as e:
        logging.error(f"Missing dependency: {e}")
        messagebox.showerror("Dependency Error", f"Missing required module: {e}\nPlease install required dependencies: pip install pyshark matplotlib")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Startup error: {e}")
        messagebox.showerror("Startup Error", f"Failed to start application: {e}\nCheck netshield_debug.log for details.")
        sys.exit(1)
