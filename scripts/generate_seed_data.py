"""
Seed Dataset Generator for DigiPlus AI Service Desk.

This module generates:
1. data/seed/kb_articles.jsonl: 40 rich technical runbooks across 8 IT categories.
2. data/seed/tickets.jsonl: 300 realistic historical incident tickets with verified resolutions.
3. eval/golden_set.jsonl: 60 held-out evaluation tickets strictly excluded from the search index.

Usage:
    python scripts/generate_seed_data.py [--seed 42]
"""

import argparse
import json
import os
import random
from pathlib import Path
from typing import List, Literal
from pydantic import BaseModel, Field

# Supported categories as specified in UPGRADE_SPEC.md
CATEGORIES = [
    "network",
    "email",
    "VPN and access",
    "hardware",
    "software installation",
    "account and password",
    "database",
    "performance",
]

PriorityType = Literal["Low", "Medium", "High", "Urgent"]


class KBArticle(BaseModel):
    """Schema for a seed Knowledge Base Article."""
    id: int
    title: str = Field(..., min_length=5)
    body: str = Field(..., min_length=20)
    category: str


class Ticket(BaseModel):
    """Schema for a seed Historical Ticket."""
    id: int
    title: str = Field(..., min_length=5)
    description: str = Field(..., min_length=20)
    category: str
    priority: PriorityType
    resolution: str = Field(..., min_length=20)
    kb_article_id: int


class GoldenTicket(BaseModel):
    """Schema for a Held-out Evaluation Ticket (Strictly Excluded from Index)."""
    ticket_id: int
    title: str = Field(..., min_length=5)
    description: str = Field(..., min_length=20)
    expected_kb_article_id: int
    reference_resolution: str = Field(..., min_length=20)


# 40 Canonical Technical Runbooks (5 per Category)
RAW_KB_ARTICLES = [
    # 1. Network
    {
        "id": 1,
        "title": "Core Switch VLAN Mismatch & Packet Drop Troubleshooting",
        "category": "network",
        "body": (
            "### Problem Overview\n"
            "Inter-VLAN traffic between engineering subnets and internal services experiences intermittent 100% packet loss "
            "or severe throughput throttling. Typically caused by 802.1Q trunk native VLAN mismatches or spanning-tree loop-guard blocks.\n\n"
            "### Diagnostic Steps\n"
            "1. SSH into the switch and verify port trunk negotiation: `show interfaces trunk`\n"
            "2. Inspect Native VLAN configuration: `show vlan brief`\n"
            "3. Check for spanning tree topology change notifications: `show spanning-tree detail | include is executing`\n"
            "4. Verify CRC frame error counts on physical uplink: `show interfaces GigabitEthernet1/0/1 counters errors`\n\n"
            "### Resolution SOP\n"
            "1. Ensure both ends of the 802.1Q trunk share the identical native VLAN (e.g. VLAN 999 default).\n"
            "2. Re-enable STP portfast on client edge access ports: `spanning-tree portfast edge`\n"
            "3. Clear dynamic MAC address learning table: `clear mac address-table dynamic interface Gi1/0/1`\n"
            "4. Run continuous ping from source subnet to verify 0% packet drop: `ping -c 50 10.10.20.1`"
        )
    },
    {
        "id": 2,
        "title": "Subnet DHCP Scope Exhaustion and IP Allocation Failures",
        "category": "network",
        "body": (
            "### Problem Overview\n"
            "Workstations connecting to the corporate LAN or office Wi-Fi receive an APIPA address (169.254.x.x) "
            "with error 'DHCP lookup failed: No offer received'. The DHCP server has exhausted all available leases.\n\n"
            "### Diagnostic Steps\n"
            "1. In Windows PowerShell (DHCP Server): `Get-DhcpServerv4ScopeStatistics -ScopeId 10.150.0.0`\n"
            "2. Identify expired or stale leases not reclaimed: `Get-DhcpServerv4Lease -ScopeId 10.150.0.0 -AllLeases | Measure-Object`\n"
            "3. Verify IP helper-address on edge gateway: `show running-config interface Vlan150 | include ip helper`\n\n"
            "### Resolution SOP\n"
            "1. Shorten DHCP lease duration from 8 days to 4 hours in dynamic hot-desking offices.\n"
            "2. Force-reclaim dead leases: `Remove-DhcpServerv4Lease -ScopeId 10.150.0.0 -BadLeases`\n"
            "3. Expand scope mask from /24 to /23 if client density permanently increased.\n"
            "4. On client workstation, release and renew: `ipconfig /release && ipconfig /renew`"
        )
    },
    {
        "id": 3,
        "title": "Internal DNS Resolution Failures and Recursive Forwarder Timeouts",
        "category": "network",
        "body": (
            "### Problem Overview\n"
            "Internal microservices and intranet hostnames fail to resolve (NXDOMAIN or SERVFAIL), while external sites "
            "resolve normally. Occurs when internal BIND/Windows DNS conditional forwarders become unresponsive.\n\n"
            "### Diagnostic Steps\n"
            "1. Test internal query: `nslookup internal-auth.corp.local 10.0.0.53`\n"
            "2. Check DNS response flags and query latency: `dig @10.0.0.53 internal-auth.corp.local +trace`\n"
            "3. Inspect DNS service logs on primary domain controller: Event ID 4015 / 4004 (DNS Server).\n\n"
            "### Resolution SOP\n"
            "1. Restart DNS server service: `Restart-Service DNS` (or `systemctl restart named`).\n"
            "2. Flush internal resolver cache: `Clear-DnsServerCache` on server and `ipconfig /flushdns` on clients.\n"
            "3. Verify upstream DNS forwarder root hints IP addresses are updated and reachable over UDP/TCP port 53."
        )
    },
    {
        "id": 4,
        "title": "Enterprise Wi-Fi 802.1X RADIUS Authentication Failures",
        "category": "network",
        "body": (
            "### Problem Overview\n"
            "Laptops and corporate mobile devices fail to associate with the 'Corporate-Secure' WPA3-Enterprise SSID. "
            "Clients report 'Can't connect to this network' after entering valid enterprise credentials.\n\n"
            "### Diagnostic Steps\n"
            "1. Check NPS/FreeRADIUS accounting log for EAP-TLS / PEAP-MSCHAPv2 failure code 16 (Auth Failure).\n"
            "2. Verify RADIUS server SSL certificate expiration date.\n"
            "3. Inspect intermediate CA trust chain on client device using `certmgr.msc`.\n\n"
            "### Resolution SOP\n"
            "1. If the RADIUS certificate expired, renew it on the Enterprise Root CA and rebind in NPS.\n"
            "2. Push the updated Root and Intermediate CA certs to devices via Microsoft Intune / Jamf profile.\n"
            "3. On Windows clients, forget the Wi-Fi profile: `netsh wlan delete profile name=\"Corporate-Secure\"` and reconnect."
        )
    },
    {
        "id": 5,
        "title": "Asymmetric Routing and MTU Blackhole Packet Fragmentation",
        "category": "network",
        "body": (
            "### Problem Overview\n"
            "Large file downloads or SSH connections freeze immediately after negotiation (during TLS handshake or key exchange). "
            "Ping works, but TCP sessions stall due to Path MTU Discovery (PMTUD) packet drops by stateful firewalls.\n\n"
            "### Diagnostic Steps\n"
            "1. Test max MTU without fragmentation: `ping -f -l 1472 <target-ip>` (Windows) or `ping -M do -s 1472 <target-ip>` (Linux).\n"
            "2. Check router WAN interface MTU and MSS clamping configuration: `show interface GigabitEthernet0/0 | include MTU`\n"
            "3. Inspect firewall ICMP Type 3 Code 4 (Fragmentation Needed) filter rules.\n\n"
            "### Resolution SOP\n"
            "1. Enable TCP MSS clamping on VPN and GRE tunnels: `ip tcp adjust-mss 1360` on WAN interfaces.\n"
            "2. Ensure edge firewalls do not block ICMP Type 3 (Destination Unreachable / Fragmentation Needed).\n"
            "3. Temporarily set client MTU to 1420 for verification: `netsh interface ipv4 set subinterface \"Ethernet\" mtu=1420 store=persistent`"
        )
    },

    # 2. Email
    {
        "id": 6,
        "title": "Exchange Online / M365 Inbound Mail Delivery Latency & Queue Backlog",
        "category": "email",
        "body": (
            "### Problem Overview\n"
            "External emails to corporate inboxes are delayed by 45 to 120 minutes. Sender domains receive delayed delivery notices. "
            "Caused by throttling on inbound connectors or security scanning queue backlogs.\n\n"
            "### Diagnostic Steps\n"
            "1. Check Exchange Admin Center Message Trace: `Get-MessageTrace -StartDate (Get-Date).AddHours(-4) -Status Pending`\n"
            "2. Inspect Microsoft 365 Service Health for Incident EX820491 (Mailflow Delays).\n"
            "3. Check header timestamps using Microsoft Message Header Analyzer.\n\n"
            "### Resolution SOP\n"
            "1. If message trace shows 'Deferred: 451 4.7.500 Server busy', verify tenant inbound rate limits.\n"
            "2. Bypass secondary third-party email hygiene gateway temporarily if its upstream relay is throttled.\n"
            "3. Whitelist high-volume automated transactional relay IP addresses in Enhanced Anti-Spam inbound connection filter."
        )
    },
    {
        "id": 7,
        "title": "SPF, DKIM, and DMARC Alignment Failures Causing Outbound Quarantine",
        "category": "email",
        "body": (
            "### Problem Overview\n"
            "Emails sent from Salesforce, ServiceNow, or marketing platforms using the `@company.com` domain are rejected "
            "with error '550 5.7.26 DMARC Policy Rejection' or delivered directly into recipient Spam folders.\n\n"
            "### Diagnostic Steps\n"
            "1. Query public DNS SPF record: `dig TXT company.com +short`\n"
            "2. Validate DKIM selector: `dig TXT selector1._domainkey.company.com +short`\n"
            "3. Inspect DMARC XML aggregate reports (RUA) for alignment failures (DKIM vs Envelope From header mismatch).\n\n"
            "### Resolution SOP\n"
            "1. Add the SaaS provider include mechanism to SPF: e.g. `v=spf1 include:_spf.salesforce.com include:spf.protection.outlook.com ~all`.\n"
            "2. Ensure total DNS lookups inside the SPF TXT record do not exceed the RFC limit of 10.\n"
            "3. Configure CNAME records for custom 2048-bit DKIM key signing in the external sender platform."
        )
    },
    {
        "id": 8,
        "title": "Outlook OST Data File Corruption and Offline Sync Stalls",
        "category": "email",
        "body": (
            "### Problem Overview\n"
            "Desktop Outlook client displays 'Disconnected' or 'Trying to connect...', crashes on launch, or freezes during search. "
            "Caused by a bloated or corrupted local offline storage table (.ost) file exceeding 45 GB.\n\n"
            "### Diagnostic Steps\n"
            "1. Check OST file size in `%LOCALAPPDATA%\\Microsoft\\Outlook\\`.\n"
            "2. Run Outlook in Safe Mode: `outlook.exe /safe` to rule out conflicting COM add-ins.\n"
            "3. Check Windows Application Event Log for Event ID 1000 (Faulting application name: OUTLOOK.EXE).\n\n"
            "### Resolution SOP\n"
            "1. Close Outlook and kill hanging background processes: `Stop-Process -Name OUTLOOK -Force`.\n"
            "2. Rename the corrupted file to `outlook.ost.old`.\n"
            "3. Reopen Outlook; Exchange will automatically generate a fresh, synchronized `.ost` file.\n"
            "4. Configure Sync Slider to '1 Year' under Account Settings to prevent future bloat."
        )
    },
    {
        "id": 9,
        "title": "Microsoft 365 Shared Mailbox Permissions and Auto-Mapping Disruption",
        "category": "email",
        "body": (
            "### Problem Overview\n"
            "Users assigned delegate access to a department shared mailbox (e.g. `billing@company.com`) cannot view "
            "the mailbox in Outlook Desktop, or receive error 'Cannot display the folder. Access denied.'\n\n"
            "### Diagnostic Steps\n"
            "1. In Exchange Online PowerShell, verify mailbox permissions: `Get-MailboxPermission -Identity \"billing\" -User \"user@company.com\"`\n"
            "2. Check if AutoMapping is enabled: Look for `AutoMapping: True` in output.\n"
            "3. Check Send-As and SendOnBehalf rights: `Get-RecipientPermission -Identity \"billing\"`\n\n"
            "### Resolution SOP\n"
            "1. Remove and re-grant permissions with AutoMapping disabled: `Remove-MailboxPermission -Identity \"billing\" -User \"user@company.com\" -AccessRights FullAccess`\n"
            "2. Re-add explicitly: `Add-MailboxPermission -Identity \"billing\" -User \"user@company.com\" -AccessRights FullAccess -AutoMapping $false`\n"
            "3. Manually add the shared mailbox as an additional mailbox in Outlook Account Settings -> Advanced."
        )
    },
    {
        "id": 10,
        "title": "Corporate Email Security Gateway Phishing Quarantine False Positives",
        "category": "email",
        "body": (
            "### Problem Overview\n"
            "Legitimate client invoices and vendor contracts are blocked by the Proofpoint / Mimecast / Defender email security gateway "
            "flagged as 'High Confidence Phishing' due to URL weaponization or password-protected zip attachments.\n\n"
            "### Diagnostic Steps\n"
            "1. Search Quarantine portal by Network Message ID or recipient email address.\n"
            "2. Review threat intelligence verdict: Look at URL Sandbox (safe links) detonation report.\n"
            "3. Inspect DMARC / SPF authentication headers for the sender.\n\n"
            "### Resolution SOP\n"
            "1. Verify sender authenticity with requester via out-of-band communication.\n"
            "2. Release email from Security Admin Quarantine portal with admin override.\n"
            "3. Add sender domain to Tenant Allow List with explicit domain and certificate binding."
        )
    },

    # 3. VPN and Access
    {
        "id": 11,
        "title": "GlobalProtect / AnyConnect SSL VPN Tunnel Gateway Connection Timeouts",
        "category": "VPN and access",
        "body": (
            "### Problem Overview\n"
            "Remote employees receive 'Connection timeout (Error 504)' or 'Gateway not responding' when attempting to connect "
            "to corporate VPN gateways. Common after firewall firmware upgrades or ISP IPv6 routing issues.\n\n"
            "### Diagnostic Steps\n"
            "1. Test VPN gateway TCP/443 and UDP/4501 reachability: `Test-NetConnection -ComputerName vpn.company.com -Port 443`\n"
            "2. Inspect PanGPS client log: `%LOCALAPPDATA%\\Palo Alto Networks\\GlobalProtect\\PanGPS.log`\n"
            "3. Check firewall portal active session limits: `show running resource-monitor`\n\n"
            "### Resolution SOP\n"
            "1. If client ISP has broken IPv6 routing, disable IPv6 on Wi-Fi adapter temporarily: `Disable-NetAdapterBinding -Name \"Wi-Fi\" -ComponentID ms_tcpip6`.\n"
            "2. In VPN Client settings -> Preferences, clear saved portal authentication tokens.\n"
            "3. Switch gateway selection from 'Auto (Geo)' to manual fallback secondary gateway (e.g. `vpn-uswest.company.com`)."
        )
    },
    {
        "id": 12,
        "title": "Azure AD Conditional Access MFA Policy Evaluation Lockouts",
        "category": "VPN and access",
        "body": (
            "### Problem Overview\n"
            "Users attempting to authenticate from remote locations or personal home offices are blocked with: "
            "'Sign-in was blocked: You cannot access this application from your current location (Conditional Access 53003)'.\n\n"
            "### Diagnostic Steps\n"
            "1. Check Microsoft Entra ID -> Users -> Sign-in logs -> Conditional Access tab.\n"
            "2. Identify the blocking policy: e.g. 'Block untrusted country' or 'Require Compliant Device'.\n"
            "3. Review the client IP and detected GPS location against Named Locations definitions.\n\n"
            "### Resolution SOP\n"
            "1. If user is traveling internationally, create a temporary 7-day exception in the Named Locations / Trusted Countries list.\n"
            "2. If device is unmanaged, guide user through Intune Company Portal device registration to achieve 'Compliant' state.\n"
            "3. Reset the user's risky sign-in status in Identity Protection to clear risk flags."
        )
    },
    {
        "id": 13,
        "title": "SAML Single Sign-On (SSO) RelayState & InResponseTo Verification Errors",
        "category": "VPN and access",
        "body": (
            "### Problem Overview\n"
            "Users clicking an enterprise SSO tile in Okta/Azure Portal receive error 'SAML response status code was Responder' "
            "or 'InResponseTo field does not match Request ID' on the target application landing page.\n\n"
            "### Diagnostic Steps\n"
            "1. Capture SAML assertion payload using Chrome DevTools or SAML-tracer browser extension.\n"
            "2. Verify IdP signing certificate expiration date against SP metadata.\n"
            "3. Inspect system clock skew between client, IdP, and SP: Ensure drift is under 3 minutes.\n\n"
            "### Resolution SOP\n"
            "1. Synchronize server NTP clocks if clock skew exceeded allowed tolerance.\n"
            "2. Update the SP Entity ID and Assertion Consumer Service (ACS) URL in IdP application configuration.\n"
            "3. Download the renewed IdP X.509 signing certificate and upload it into the application admin security settings."
        )
    },
    {
        "id": 14,
        "title": "Okta FastPass Device Trust and Biometric Attestation Failures",
        "category": "VPN and access",
        "body": (
            "### Problem Overview\n"
            "Engineers using Okta Verify FastPass on macOS or Windows 11 get looped into password/SMS prompts because "
            "device trust attestation fails with 'Biometrics or security key is required but not detected'.\n\n"
            "### Diagnostic Steps\n"
            "1. Check Okta System Log: `eventType eq \"user.authentication.auth_via_mfa\" and outcome.result eq \"FAILURE\"`\n"
            "2. Check TPM 2.0 status in Windows: `Get-Tpm`\n"
            "3. On macOS, check Touch ID enclave registration in Terminal: `bioutil -r`\n\n"
            "### Resolution SOP\n"
            "1. Re-enroll Windows Hello or Touch ID in OS Settings.\n"
            "2. In Okta Verify app, select 'Account Details' -> 'Re-enable Touch ID / Windows Hello'.\n"
            "3. If TPM state was corrupted by BIOS update, run `Clear-Tpm` and restart machine."
        )
    },
    {
        "id": 15,
        "title": "PAM CyberArk / HashiCorp Vault SSH Bastion Access Denied",
        "category": "VPN and access",
        "body": (
            "### Problem Overview\n"
            "DevOps engineers cannot connect to production Kubernetes clusters or Linux hosts via the PAM SSH proxy bastion. "
            "Terminal output reports 'Permission denied (publickey,keyboard-interactive)' or 'Certificate expired'.\n\n"
            "### Diagnostic Steps\n"
            "1. Check Vault token validity: `vault token lookup`\n"
            "2. Inspect signed SSH client certificate expiry: `ssh-keygen -Lf ~/.ssh/id_rsa-cert.pub`\n"
            "3. Check bastion `/var/log/secure` for SSH CA principal mismatch.\n\n"
            "### Resolution SOP\n"
            "1. Request new ephemeral certificate: `vault write -field=signed_key ssh-client-signer/sign/devops public_key=@~/.ssh/id_rsa.pub > ~/.ssh/id_rsa-cert.pub`\n"
            "2. Ensure the requested principal (e.g. `ubuntu`, `ec2-user`) is listed in the user's Vault role policy.\n"
            "3. Connect explicitly specifying the signed certificate: `ssh -i ~/.ssh/id_rsa-cert.pub -i ~/.ssh/id_rsa bastion.corp.com`"
        )
    },

    # 4. Hardware
    {
        "id": 16,
        "title": "Enterprise Thermal Throttling and CPU Frequency Capping on Workstations",
        "category": "hardware",
        "body": (
            "### Problem Overview\n"
            "High-spec developer laptops (Dell Precision / Lenovo ThinkPad) become sluggish, with CPU frequency locked at "
            "0.79 GHz (PROCHOT CPU throttling) even when CPU utilization is reported below 20%.\n\n"
            "### Diagnostic Steps\n"
            "1. Check CPU frequency in PowerShell: `Get-CimInstance Win32_Processor | Select-Object CurrentClockSpeed, MaxClockSpeed`\n"
            "2. Run HWMonitor or CoreTemp to check thermal sensor temperatures (> 95°C indicates paste degradation).\n"
            "3. Check Power Plan settings: `powercfg /getactivescheme`\n\n"
            "### Resolution SOP\n"
            "1. Ensure air vents are cleared of dust accumulation using compressed air.\n"
            "2. Update workstation BIOS / UEFI firmware to latest release (resolves Intel DPTF firmware bugs).\n"
            "3. Reset power plan: `powercfg -restoredefaultschemes` and verify 130W OEM USB-C power brick is attached instead of a 65W phone charger."
        )
    },
    {
        "id": 17,
        "title": "Dual 4K DisplayPort Flickering on Thunderbolt 4 USB-C Docks",
        "category": "hardware",
        "body": (
            "### Problem Overview\n"
            "External monitors connected to Dell WD19TB / HP G4 Thunderbolt docks go black for 2–3 seconds every few minutes. "
            "Audio crackles or USB keyboard keystrokes drop simultaneously.\n\n"
            "### Diagnostic Steps\n"
            "1. Open Device Manager -> System devices -> Check Thunderbolt Controller driver version.\n"
            "2. Check Display Settings -> Advanced Display -> Refresh rate (ensure 60 Hz, not 59.94 Hz or unstable custom mode).\n"
            "3. Verify DisplayPort 1.4 HBR3 vs DSC (Display Stream Compression) support in dock management utility.\n\n"
            "### Resolution SOP\n"
            "1. Flash Thunderbolt Dock firmware using manufacturer utility (e.g. Dell Dock Firmware Update Tool).\n"
            "2. Replace passive DisplayPort cables with VESA-certified DP 1.4 or active HDMI 2.1 cables.\n"
            "3. In Intel Graphics Command Center, turn OFF 'Panel Self-Refresh' and 'Display Power Saving Technology'."
        )
    },
    {
        "id": 18,
        "title": "Zebra Thermal Industrial Barcode Printer Driver Spooler Crashes",
        "category": "hardware",
        "body": (
            "### Problem Overview\n"
            "Warehouse and shipping stations cannot print 4x6 packing labels. Print jobs stall in queue with status 'Error - Printing', "
            "and the Windows Print Spooler service (`spoolsv.exe`) crashes repeatedly.\n\n"
            "### Diagnostic Steps\n"
            "1. Check Print Spooler service status: `Get-Service spooler`\n"
            "2. Check Event Viewer -> Applications and Services -> Microsoft -> Windows -> PrintService -> Operational for Event ID 372.\n"
            "3. Inspect corrupt spool files in `%SystemRoot%\\System32\\spool\\PRINTERS\\`.\n\n"
            "### Resolution SOP\n"
            "1. Stop Print Spooler: `Stop-Service spooler -Force`\n"
            "2. Purge stuck spool buffer files: `Remove-Item C:\\Windows\\System32\\spool\\PRINTERS\\* -Force`\n"
            "3. Restart spooler: `Start-Service spooler`\n"
            "4. Upgrade printer driver to ZDesigner v10.x and calibrate label gap sensor via Zebra Setup Utilities."
        )
    },
    {
        "id": 19,
        "title": "NVMe SSD Controller S.M.A.R.T. Read-Only Fail-Safe Recovery",
        "category": "hardware",
        "body": (
            "### Problem Overview\n"
            "Laptops lock up with Blue Screen of Death (BSOD) `CRITICAL_PROCESS_DIED`. On reboot, BIOS reports 'No bootable device found' "
            "or the disk is mounted read-only due to NVMe SSD endurance exhaustion.\n\n"
            "### Diagnostic Steps\n"
            "1. In Windows PowerShell: `Get-PhysicalDisk | Get-StorageReliabilityCounter | Select-Object Wear, ReadErrorsTotal`\n"
            "2. In Linux Live USB: `nvme smart-log /dev/nvme0n1`\n"
            "3. Check Percentage Used attribute (> 100% means spare blocks exhausted).\n\n"
            "### Resolution SOP\n"
            "1. If read-only, boot into Live Linux USB and image user data immediately: `ddrescue /dev/nvme0n1 /mnt/backup/drive.img`\n"
            "2. Dispatch replacement PCIe Gen4 NVMe drive under manufacturer enterprise warranty.\n"
            "3. Image new SSD with standard corporate Windows 11 Enterprise SOE."
        )
    },
    {
        "id": 20,
        "title": "Conference Room Microphones and USB Polycom Audio Dropouts",
        "category": "hardware",
        "body": (
            "### Problem Overview\n"
            "Meeting room Microsoft Teams Rooms (MTR) systems fail to detect the Poly Studio USB video bar. "
            "Participants report robotic audio or 'Microphone not found' during scheduled video calls.\n\n"
            "### Diagnostic Steps\n"
            "1. Check Teams Room Settings -> Peripherals -> Audio Input.\n"
            "2. In Windows Device Manager, inspect Universal Serial Bus controllers for Code 43 (Device Descriptor Request Failed).\n"
            "3. Check powered USB extender link LED (Crestron / Extron USB-over-CAT6).\n\n"
            "### Resolution SOP\n"
            "1. Power-cycle the Poly Studio unit and the USB-over-CAT6 transceiver boxes.\n"
            "2. In Device Manager, right-click the malfunctioning USB Root Hub -> Disable then Re-enable.\n"
            "3. Disable USB Selective Suspend in Power Options: `powercfg /SETACVALUEINDEX SCHEME_CURRENT 2a737441-1930-4402-8d77-b2bebba4d5a0 48e6b7a6-50f5-4782-a5d4-53bb8f07e226 0`"
        )
    },

    # 5. Software Installation
    {
        "id": 21,
        "title": "Silent MSI / Intune Application Packaging Deployment Error 1603",
        "category": "software installation",
        "body": (
            "### Problem Overview\n"
            "Enterprise software (e.g. Cisco Webex, Docker Desktop, Autodesk) pushed via Microsoft Intune fails on client devices "
            "with generic failure code `0x80070643` or Windows Installer Error `1603` (Fatal error during installation).\n\n"
            "### Diagnostic Steps\n"
            "1. Inspect Intune Management Extension log: `C:\\ProgramData\\Microsoft\\IntuneManagementExtension\\Logs\\AgentExecutor.log`\n"
            "2. Open verbose MSI installation log: Search for `Return value 3` (indicates the exact failing action).\n"
            "3. Verify pending system reboot status: `Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Component Based Servicing\\RebootPending'`\n\n"
            "### Resolution SOP\n"
            "1. If a reboot is pending from monthly Windows updates, restart the machine before retrying install.\n"
            "2. Uninstall previous partial version using Microsoft Program Install and Uninstall troubleshooter utility.\n"
            "3. Add required silent flags and suppress restart: `msiexec /i package.msi /qn /norestart /l*v C:\\temp\\install.log`"
        )
    },
    {
        "id": 22,
        "title": "macOS Application Gatekeeper Unsigned Developer Notarization Blocks",
        "category": "software installation",
        "body": (
            "### Problem Overview\n"
            "macOS Sequoia / Sonoma users attempting to open internal developer utilities receive a modal prompt: "
            "'App cannot be opened because Apple cannot check it for malicious software' or 'App is damaged and can\\'t be opened'.\n\n"
            "### Diagnostic Steps\n"
            "1. Inspect extended file attributes: `xattr -l /Applications/InternalTool.app`\n"
            "2. Look for `com.apple.quarantine` attribute tag.\n"
            "3. Verify code signature: `codesign -dv --verbose=4 /Applications/InternalTool.app`\n\n"
            "### Resolution SOP\n"
            "1. For verified internal apps, remove quarantine flag: `sudo xattr -d com.apple.quarantine /Applications/InternalTool.app`\n"
            "2. In System Settings -> Privacy & Security -> Click 'Open Anyway' under Security.\n"
            "3. Ensure enterprise build pipeline signs binaries with Apple Developer Enterprise ID and submits for notarization: `xcrun notarytool submit`"
        )
    },
    {
        "id": 23,
        "title": "Visual Studio Code / JetBrains Remote SSH Host Key Fingerprint Mismatches",
        "category": "software installation",
        "body": (
            "### Problem Overview\n"
            "Developers using VS Code Remote - SSH or JetBrains Gateway cannot connect to remote development EC2/VM instances. "
            "Error: 'Host key verification failed. The authenticity of host cannot be established. Remote host identification has changed!'.\n\n"
            "### Diagnostic Steps\n"
            "1. Read error message for offending line number in `~/.ssh/known_hosts`.\n"
            "2. Confirm instance re-provisioning or IP address reassignment with cloud engineering.\n\n"
            "### Resolution SOP\n"
            "1. Remove stale fingerprint from known hosts: `ssh-keygen -R <server-ip-or-hostname>`\n"
            "2. Connect once manually in terminal to accept and cache new ECDSA/ED25519 fingerprint: `ssh user@<server-ip>`\n"
            "3. Reopen VS Code Remote SSH session."
        )
    },
    {
        "id": 24,
        "title": "Node.js & Python Enterprise Proxy SSL Self-Signed CA Certificate Failures",
        "category": "software installation",
        "body": (
            "### Problem Overview\n"
            "Developers running `npm install`, `pip install`, or `git clone` on corporate networks receive SSL handshake failures: "
            "`SELF_SIGNED_CERT_IN_CHAIN` or `certificate verify failed: self signed certificate in certificate chain`.\n\n"
            "### Diagnostic Steps\n"
            "1. Identify corporate TLS inspection proxy (Zscaler, Netskope, Palo Alto Prisma).\n"
            "2. Check if Python / Node.js is using its bundled CA store instead of Windows / macOS system Keychain.\n\n"
            "### Resolution SOP\n"
            "1. For Node.js / NPM: Configure corporate CA certificate path: `npm config set cafile \"C:\\Certs\\CorporateRootCA.crt\"`\n"
            "2. For Python: Install `pip-system-certs` or set environment variable: `export REQUESTS_CA_BUNDLE=\"/etc/ssl/certs/ca-certificates.crt\"`\n"
            "3. For Git: `git config --global http.sslCAInfo \"C:/Certs/CorporateRootCA.crt\"`"
        )
    },
    {
        "id": 25,
        "title": "Windows Sandbox & WSL2 Virtualized Nested Hyper-V Conflicts",
        "category": "software installation",
        "body": (
            "### Problem Overview\n"
            "Developers installing WSL2 or Docker Desktop receive: 'WslRegisterDistribution failed with error: 0x80370102' "
            "or 'Hardware-assisted virtualization is disabled in the BIOS'.\n\n"
            "### Diagnostic Steps\n"
            "1. Check virtualization status in Task Manager -> Performance -> CPU -> 'Virtualization: Enabled'.\n"
            "2. In PowerShell: `Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform`\n"
            "3. Check hypervisor launch type: `bcdedit /enum | findstr hypervisorlaunchtype`\n\n"
            "### Resolution SOP\n"
            "1. Enable hypervisor in BCD: `bcdedit /set hypervisorlaunchtype auto`\n"
            "2. Enable required Windows features: `dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart`\n"
            "3. Restart physical machine and verify Intel VT-x / AMD-V is enabled in motherboard BIOS settings."
        )
    },

    # 6. Account and Password
    {
        "id": 26,
        "title": "Active Directory BadPwdCount Account Lockout Loop Detection",
        "category": "account and password",
        "body": (
            "### Problem Overview\n"
            "An employee's Active Directory domain account locks out repeatedly within seconds of being unlocked by IT support. "
            "Workstation displays 'Your account has been locked. Contact your support person.'\n\n"
            "### Diagnostic Steps\n"
            "1. In PowerShell ActiveDirectory module, locate locking source computer: `Get-ADUser -Identity <username> -Properties BadPwdCount, badPasswordTime, LockedOut`\n"
            "2. Inspect Security Event Log on Primary Domain Controller for Event ID 4740 (A user account was locked out) -> Check 'Caller Computer Name'.\n\n"
            "### Resolution SOP\n"
            "1. Identify the caller device (often a mobile phone with an expired ActiveSync password, stale Wi-Fi profile, or scheduled batch script).\n"
            "2. On caller computer, open Windows Credential Manager -> Clear stored generic credentials under Windows Credentials.\n"
            "3. Check for lingering mapped network drives: `net use * /delete /yes`\n"
            "4. Unlock account in AD: `Unlock-ADAccount -Identity <username>`"
        )
    },
    {
        "id": 27,
        "title": "Kerberos Pre-Authentication Clock Skew Authentication Timeouts",
        "category": "account and password",
        "body": (
            "### Problem Overview\n"
            "Users cannot log into domain workstations or access corporate file shares, receiving error: 'The system cannot log you on due to clock skew' "
            "or Kerberos error `KRB_AP_ERR_SKEW` (Event ID 14).\n\n"
            "### Diagnostic Steps\n"
            "1. Compare local workstation system time against Domain Controller time: `net time \\\\dc01.corp.local`\n"
            "2. Kerberos protocol permits a maximum drift of 5 minutes (300 seconds).\n"
            "3. Check Windows Time service status: `w32tm /query /status`\n\n"
            "### Resolution SOP\n"
            "1. Unregister and re-register Windows Time service on client: `w32tm /unregister && w32tm /register`\n"
            "2. Force immediate resynchronization with PDC emulator: `w32tm /resync /force`\n"
            "3. Purge existing tickets: `klist purge` and re-authenticate."
        )
    },
    {
        "id": 28,
        "title": "AWS IAM AssumeRole Token Expiration and Session Permission Boundaries",
        "category": "account and password",
        "body": (
            "### Problem Overview\n"
            "Developers running Terraform or AWS CLI receive `AccessDenied: User is not authorized to perform: sts:AssumeRole` "
            "or `ExpiredToken: The security token included in the request is expired` during production deployment workflows.\n\n"
            "### Diagnostic Steps\n"
            "1. Check current identity: `aws sts get-caller-identity`\n"
            "2. Check role Trust Relationship policy: Verify `Principal` includes the IAM user or SAML federated role.\n"
            "3. Check IAM Permissions Boundary attached to the role.\n\n"
            "### Resolution SOP\n"
            "1. If session expired, re-authenticate via AWS IAM Identity Center (SSO): `aws sso login --profile production`\n"
            "2. Increase max session duration on the IAM role from 1 hour to 4 hours in AWS Console.\n"
            "3. Ensure MFA token is supplied if the role requires `aws:MultiFactorAuthPresent: true`."
        )
    },
    {
        "id": 29,
        "title": "Self-Service Password Reset (SSPR) Telephony Loop Failure",
        "category": "account and password",
        "body": (
            "### Problem Overview\n"
            "Remote employees locked out of their accounts cannot complete Self-Service Password Reset (SSPR). "
            "SMS codes never arrive on their mobile phones, or Microsoft phone call verification drops immediately.\n\n"
            "### Diagnostic Steps\n"
            "1. Check user authentication methods in Entra Admin Center -> Users -> Authentication methods.\n"
            "2. Verify mobile phone number country code formatting (must be E.164 format: e.g. `+1 5550192834`).\n"
            "3. Check carrier SMS delivery status in Azure Monitor Audit logs.\n\n"
            "### Resolution SOP\n"
            "1. IT Service Desk performs verified identity check via secure video call.\n"
            "2. Generate a Temporary Access Pass (TAP) in Entra ID admin center (valid for 8 hours).\n"
            "3. Direct user to `myaccount.microsoft.com` using the TAP to re-register Microsoft Authenticator push notifications."
        )
    },
    {
        "id": 30,
        "title": "GitHub Enterprise Organization SAML Member De-provisioning Sync Lag",
        "category": "account and password",
        "body": (
            "### Problem Overview\n"
            "Contractors or transferred employees retain access to internal GitHub repositories hours after departure, "
            "or newly onboarded engineers cannot see internal repositories after Okta assignment.\n\n"
            "### Diagnostic Steps\n"
            "1. In GitHub Enterprise Cloud -> Organization -> Settings -> Audit Log: Filter by `action:org.add_member`.\n"
            "2. In Okta -> Applications -> GitHub Enterprise -> Push Groups tab: Look for SCIM synchronization errors.\n\n"
            "### Resolution SOP\n"
            "1. In Okta, click 'Push Now' on the desynchronized engineering security group.\n"
            "2. If SCIM bearer token is expired, generate a new Personal Access Token (PAT) with `admin:org` scope and rebind in Okta.\n"
            "3. Manually revoke SAML identity link in GitHub Org Settings -> SAML SSO -> Manage members."
        )
    },

    # 7. Database
    {
        "id": 31,
        "title": "PostgreSQL RDS Connection Pool Exhaustion and Deadlock Resolution",
        "category": "database",
        "body": (
            "### Problem Overview\n"
            "Backend microservices report `FATAL: remaining connection slots are reserved for non-replication superuser connections` "
            "or `500 Internal Server Error`. Database active connections reach 100% of `max_connections`.\n\n"
            "### Diagnostic Steps\n"
            "1. Connect via superuser psql and inspect active queries: "
            "`SELECT pid, usename, state, now() - query_start AS duration, query FROM pg_stat_activity WHERE state != 'idle' ORDER BY duration DESC;`\n"
            "2. Check for lock blocking tree: `SELECT blocked_locks.pid AS blocked_pid, blocking_locks.pid AS blocking_pid FROM pg_catalog.pg_locks blocked_locks...`\n"
            "3. Inspect RDS CloudWatch metric `DatabaseConnections`.\n\n"
            "### Resolution SOP\n"
            "1. Terminate long-running locking queries gracefully: `SELECT pg_cancel_backend(<pid>);` (or `pg_terminate_backend(<pid>)` if unyielding).\n"
            "2. Deploy PgBouncer or AWS RDS Proxy between applications and Postgres to multiplex client connections.\n"
            "3. Ensure applications configure idle client timeout (`idle_in_transaction_session_timeout = '30s'`)."
        )
    },
    {
        "id": 32,
        "title": "MySQL InnoDB Log Sequence Gap and Replication Thread Lag",
        "category": "database",
        "body": (
            "### Problem Overview\n"
            "Read-replica MySQL instances fall behind master by thousands of seconds (`Seconds_Behind_Master > 3600`). "
            "Reporting dashboards query stale data and replica disk fills rapidly with relay logs.\n\n"
            "### Diagnostic Steps\n"
            "1. On replica: `SHOW REPLICA STATUS\\G` (or `SHOW SLAVE STATUS\\G`).\n"
            "2. Check `Last_Error_Number` (e.g. 1062 Duplicate entry or 1032 Key not found).\n"
            "3. Inspect multi-threaded replica worker status: `SHOW PROCESSLIST`.\n\n"
            "### Resolution SOP\n"
            "1. Enable multi-threaded applier: `SET GLOBAL replica_parallel_workers = 8; SET GLOBAL replica_parallel_type = 'LOGICAL_CLOCK';`\n"
            "2. If replication broke due to a non-critical schema mismatch, inject GTID skip transaction: "
            "`SET GTID_NEXT='<gtid_set>'; BEGIN; COMMIT; SET GTID_NEXT='AUTOMATIC'; START REPLICA;`\n"
            "3. Rebuild replica from automated Percona XtraBackup snapshot if sequence divergence is permanent."
        )
    },
    {
        "id": 33,
        "title": "Redis Cluster Out-of-Memory Eviction Key Retention Spikes",
        "category": "database",
        "body": (
            "### Problem Overview\n"
            "Application sessions drop randomly and cache write commands fail with: `OOM command not allowed when used memory > 'maxmemory'`. "
            "Redis cluster CPU reaches 100% due to key eviction thrashing.\n\n"
            "### Diagnostic Steps\n"
            "1. Connect with redis-cli: `redis-cli -h <cluster-node> info memory`\n"
            "2. Scan for top memory consuming keys: `redis-cli --bigkeys`\n"
            "3. Check current eviction policy: `CONFIG GET maxmemory-policy`\n\n"
            "### Resolution SOP\n"
            "1. Change eviction policy to volatile-lru or allkeys-lru: `CONFIG SET maxmemory-policy allkeys-lru`\n"
            "2. Ensure all application session cache keys include an explicit TTL expiration (e.g. `EXPIRE session:abc 86400`).\n"
            "3. Scale Redis ElastiCache node type or add cluster shards to distribute memory load."
        )
    },
    {
        "id": 34,
        "title": "MongoDB Replica Set Election Split-Brain Quorum Loss",
        "category": "database",
        "body": (
            "### Problem Overview\n"
            "MongoDB cluster drops writes with error `NotWritablePrimary` or `Server selection timeout after 30000 ms`. "
            "All replica set members are in `SECONDARY` or `RECOVERING` state.\n\n"
            "### Diagnostic Steps\n"
            "1. In mongosh: `rs.status()`\n"
            "2. Check member voting status: `rs.conf().members`\n"
            "3. Inspect mongod logs for network partition heartbeats: `Heartbeat to <host> failed: NetworkTimeout`.\n\n"
            "### Resolution SOP\n"
            "1. Verify network connectivity between all nodes on port 27017.\n"
            "2. If an arbiter node crashed causing quorum loss in a 3-node set, temporarily force reconfig: "
            "`cfg = rs.conf(); cfg.members[2].votes = 0; rs.reconfig(cfg, {force: true})`\n"
            "3. Restart secondary node with corrupted oplog in repair mode."
        )
    },
    {
        "id": 35,
        "title": "SQL Server TempDB Filegroup Autogrowth Storage Saturation",
        "category": "database",
        "body": (
            "### Problem Overview\n"
            "Production Microsoft SQL Server databases freeze with error 1105: 'Could not allocate space for object in database tempdb "
            "because the PRIMARY filegroup is full'. Transactions rollback immediately.\n\n"
            "### Diagnostic Steps\n"
            "1. Check TempDB drive free space using Windows Explorer or `EXEC xp_fixeddrives`.\n"
            "2. Identify queries consuming TempDB internal objects: "
            "`SELECT session_id, internal_objects_alloc_page_count, user_objects_alloc_page_count FROM sys.dm_db_session_space_usage ORDER BY internal_objects_alloc_page_count DESC`\n"
            "3. Check for massive un-indexed sorting or hash joins in execution plans.\n\n"
            "### Resolution SOP\n"
            "1. Kill the runaway report query session: `KILL <session_id>`\n"
            "2. Shrink TempDB data files: `DBCC SHRINKDATABASE(tempdb, 10)`\n"
            "3. Pre-size TempDB files across multiple dedicated disk spindles with equal autogrowth settings (64 MB increments)."
        )
    },

    # 8. Performance
    {
        "id": 36,
        "title": "Kubernetes Pod CrashLoopBackOff Triggered by OOMKilled Memory Limits",
        "category": "performance",
        "body": (
            "### Problem Overview\n"
            "Application microservice pods continuously restart in production Kubernetes clusters. `kubectl get pods` shows status "
            "`CrashLoopBackOff` with `RESTARTS` count incrementing every 2 minutes.\n\n"
            "### Diagnostic Steps\n"
            "1. Inspect pod exit code: `kubectl describe pod <pod-name> -n production`\n"
            "2. Look for `Last State: Terminated`, `Reason: OOMKilled`, `Exit Code: 137`.\n"
            "3. Check current memory utilization curve in Grafana or Datadog.\n\n"
            "### Resolution SOP\n"
            "1. If application requires more working memory, increase deployment resource limits in Helm chart: "
            "`resources.limits.memory: 2Gi` (up from 512Mi).\n"
            "2. For Java/Node apps, set heap allocation flags explicitly: e.g. `--max-old-space-size=1536` for Node or `-XX:MaxRAMPercentage=75` for Java.\n"
            "3. Inspect code for memory leaks (unclosed streams, unbounded in-memory caches, retaining unreferenced objects)."
        )
    },
    {
        "id": 37,
        "title": "JVM Heap Garbage Collection Pauses and Tenured Generation Leaks",
        "category": "performance",
        "body": (
            "### Problem Overview\n"
            "Java Spring Boot microservices experience sudden latency spikes from 30ms to 8,000ms. Health check endpoints time out, "
            "causing AWS ALB to cycle containers out of target groups.\n\n"
            "### Diagnostic Steps\n"
            "1. Check GC logs: Look for `Full GC (Allocation Failure)` pauses exceeding 3,000ms.\n"
            "2. Capture thread dump: `jcmd <pid> Thread.print`\n"
            "3. Capture heap dump on OOM: Verify `-XX:+HeapDumpOnOutOfMemoryError` generated `.hprof` file.\n\n"
            "### Resolution SOP\n"
            "1. Switch GC algorithm to low-latency ZGC or G1GC: `-XX:+UseG1GC -XX:MaxGCPauseMillis=200`\n"
            "2. Analyze `.hprof` file with Eclipse Memory Analyzer (MAT) to identify leak suspects (e.g. static HashMaps).\n"
            "3. Ensure container has adequate CPU resources: GC threads starve when CPU throttling is triggered."
        )
    },
    {
        "id": 38,
        "title": "Node.js Microservice Event-Loop Latency Spikes Under Concurrent Load",
        "category": "performance",
        "body": (
            "### Problem Overview\n"
            "Node.js API servers show low CPU and memory utilization (30%), yet response times degrade exponentially under load. "
            "Prometheus reports `nodejs_eventloop_lag_seconds` exceeding 1.5 seconds.\n\n"
            "### Diagnostic Steps\n"
            "1. Profile CPU activity using Node Inspector: `node --cpu-prof index.js`\n"
            "2. Check for synchronous blocking operations: Synchronous regex (`eval-regex`), `JSON.parse` on 50MB files, or `fs.readFileSync`.\n"
            "3. Check crypto hashing operations on the main event thread.\n\n"
            "### Resolution SOP\n"
            "1. Offload heavy computational work (cryptography, PDF generation) to Worker Threads or BullMQ background worker queue.\n"
            "2. Replace synchronous fs calls with `fs.promises`.\n"
            "3. Scale horizontally using Node.js Cluster mode or increase Kubernetes replica count."
        )
    },
    {
        "id": 39,
        "title": "AWS Elastic Load Balancer (ALB) 504 Gateway Timeouts During Peak Traffic",
        "category": "performance",
        "body": (
            "### Problem Overview\n"
            "End users encounter `504 Gateway Time-out` during marketing campaigns or batch data syncs. "
            "AWS ALB CloudWatch metrics show elevated `HTTPCode_ELB_504_Count` and spikes in `TargetResponseTime`.\n\n"
            "### Diagnostic Steps\n"
            "1. Check ALB access logs in S3: Filter by `target_status_code == \"-\"` (indicates backend failed to respond within idle timeout).\n"
            "2. Check backend EC2 / ECS container CPU and connection queues.\n"
            "3. Compare ALB idle timeout (default 60s) with backend web server keepalive timeout.\n\n"
            "### Resolution SOP\n"
            "1. Ensure backend keep-alive timeout is GREATER than ALB idle timeout (e.g. Nginx `keepalive_timeout 65;`).\n"
            "2. Scale Target Group capacity via Auto Scaling Policy triggered on `RequestCountPerTarget`.\n"
            "3. Optimize slow SQL queries and external third-party API calls holding backend threads open."
        )
    },
    {
        "id": 40,
        "title": "Nginx Ingress Controller Upstream Buffer Overflow and 502 Bad Gateway",
        "category": "performance",
        "body": (
            "### Problem Overview\n"
            "Requests with large JWT headers or bulk JSON payloads fail with `502 Bad Gateway`. Ingress controller logs report: "
            "`upstream sent too big header while reading response header from upstream`.\n\n"
            "### Diagnostic Steps\n"
            "1. Inspect Nginx ingress controller pod logs: `kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx | grep 502`\n"
            "2. Inspect request header size (cookie payload size + OAuth token).\n\n"
            "### Resolution SOP\n"
            "1. Add buffer annotations to the Ingress resource:\n"
            "   `nginx.ingress.kubernetes.io/proxy-buffer-size: \"128k\"`\n"
            "   `nginx.ingress.kubernetes.io/proxy-buffers-number: \"4\"`\n"
            "   `nginx.ingress.kubernetes.io/proxy-busy-buffers-size: \"256k\"`\n"
            "2. In backend application, trim excessive Set-Cookie headers on redirects.\n"
            "3. Reload ingress configuration and verify successful 200 OK responses."
        )
    }
]

# Symptom & incident variants for generating realistic tickets mapped to KB articles
INCIDENT_TEMPLATES = {
    1: [  # Core Switch VLAN Mismatch
        ("Intermittent packet drops between Dev and QA subnets on switch SW-CORE-01",
         "Developers in subnet 10.10.40.0/24 report ping timeouts to services in 10.10.20.0/24. Trunk port Gi1/0/24 shows Native VLAN mismatch error in syslog.",
         "High",
         "Aligned native VLAN configuration on trunk interface Gi1/0/24 to VLAN 999. Cleared dynamic MAC address table. Verified 0% packet drop across subnets."),
        ("VLAN 20 routing failure after scheduled maintenance",
         "Following scheduled firmware updates, engineering VLAN 20 is unreachable from the DMZ. Logs report spanning tree port state blocked by loop-guard.",
         "Urgent",
         "Re-enabled spanning-tree portfast edge on access ports and corrected trunk encapsulation. Inter-VLAN routing restored."),
        ("Broadcast storm on Floor 3 access switch causing core packet loss",
         "Offices on 3rd floor experiencing network freezing. Switch uplink CRC errors incrementing rapidly due to loop on access port.",
         "Urgent",
         "Identified loop caused by unmanaged desktop switch. Enabled BPDU guard on port Gi1/0/12 which auto-disabled offending port. Network stabilized."),
    ],
    2: [  # Subnet DHCP Scope Exhaustion
        ("Engineering laptops receiving 169.254.x.x APIPA addresses on 4th floor",
         "Multiple staff arriving on Tuesday morning cannot connect to LAN. Windows reports 'No Internet, secured' with 169.254 address. DHCP server reports 100% scope utilization.",
         "High",
         "Shortened DHCP lease time from 7 days to 4 hours on hot-desking scope 10.150.0.0/24. Reclaimed 114 inactive leases. Clients received valid IP addresses."),
        ("Building B Wi-Fi clients failing to obtain IP address",
         "Guests and employees in Building B conference center cannot connect to corporate Wi-Fi. Access points report DHCP DISCOVER timeouts.",
         "High",
         "Expanded DHCP scope mask from /24 to /23 (added 254 additional lease addresses). Verified new clients successfully obtain IP within 2 seconds."),
    ],
    3: [  # Internal DNS Resolution Failures
        ("Internal service endpoints failing to resolve (NXDOMAIN)",
         "Applications reporting connection refused to internal-auth.corp.local. DNS query to primary domain controller returns SERVFAIL.",
         "Urgent",
         "Restarted DNS server service on DC01 and cleared resolver cache. Verified authoritative forward lookup zone replication completed successfully."),
        ("DNS recursive forwarder timeout during morning login peak",
         "Employees experiencing 30-second delays opening internal intranet and Jira. DNS forwarder queue saturated.",
         "Medium",
         "Configured secondary upstream DNS forwarder IP and cleared stale root hints cache. Query response latency returned to < 5ms."),
    ],
    4: [  # 802.1X RADIUS Failures
        ("Laptops unable to connect to Corporate-Secure Wi-Fi",
         "Staff reporting 'Can\\'t connect to this network' on WPA3 enterprise SSID. NPS server logs show EAP-TLS handshake failure code 16.",
         "Urgent",
         "Discovered RADIUS server SSL certificate expired at midnight. Renewed certificate on Enterprise CA, rebound in NPS policies, and verified association."),
        ("MacBook fleet rejecting 802.1X Wi-Fi profile",
         "Following macOS update, corporate MacBooks fail 802.1X RADIUS authentication due to untrusted intermediate certificate.",
         "High",
         "Pushed updated Intermediate CA bundle via Jamf MDM profile. Laptops successfully authenticated and joined Wi-Fi."),
    ],
    5: [  # Asymmetric Routing and MTU Blackhole
        ("SSH sessions and git push freezing on corporate VPN",
         "Developers connected to remote VPN experience SSH session freeze immediately after authentication. Small pings work, but large packets drop.",
         "Medium",
         "Diagnosed MTU blackhole on VPN concentrator. Configured 'ip tcp adjust-mss 1360' on tunnel interface. Git pushes and SSH sessions now stable."),
        ("Large file upload stalling over site-to-site IPsec tunnel",
         "Branch office unable to sync 100MB CAD files to headquarters file server. Packets larger than 1420 bytes dropped without ICMP fragmentation response.",
         "Medium",
         "Allowed ICMP Type 3 Code 4 on edge firewall and clamped TCP MSS to 1380. Verified 100MB file transfer completed without stall."),
    ],
    6: [  # Exchange Online Inbound Latency
        ("External customer emails delayed by 2 hours",
         "Customer support agents notice inbound ticket confirmations arriving 90-120 minutes late. Exchange message trace indicates deferred queue status.",
         "Urgent",
         "Identified throttling on third-party spam gateway relay IP. Whitelisted transactional sender IP in Exchange Enhanced Filtering. Queue cleared."),
        ("Inbound billing invoices stuck in pending status",
         "Finance team missing time-sensitive vendor invoices. Message headers show 45-minute pause at inbound connector.",
         "High",
         "Resolved connector concurrency limit. Re-routed high-priority vendor domain to direct TLS connector. Delay eliminated."),
    ],
    7: [  # SPF, DKIM, DMARC Failures
        ("Automated Salesforce customer emails rejected with DMARC 550",
         "Sales team reports quote notification emails sent from Salesforce are bouncing from customer domains with DMARC 550 5.7.26 policy failure.",
         "High",
         "Added include:_spf.salesforce.com to corporate DNS SPF record and configured custom 2048-bit DKIM keys in Salesforce admin portal."),
        ("Marketing newsletter landing in recipient spam folders",
         "HubSpot marketing campaign emails receiving low open rate. DKIM selector DNS check failed due to missing CNAME record.",
         "Medium",
         "Created missing DKIM CNAME records in Cloudflare DNS. Verified DMARC alignment passes at 100% on dmarcian inspector."),
    ],
    8: [  # Outlook OST File Corruption
        ("Outlook crashing on startup with Faulting Application error",
         "Executive assistant's Outlook crashes immediately upon launch. Event Viewer shows Event ID 1000 in OUTLOOK.EXE with ntdll.dll module.",
         "High",
         "Corrupt 48 GB OST file detected. Renamed outlook.ost to .old and relaunched Outlook in safe mode. Rebuilt clean OST file and enabled 1-year sync slider."),
        ("Outlook stuck on 'Loading Profile' and disconnected from Exchange",
         "User cannot view new emails; status bar permanently reads 'Disconnected'. Safe mode fails to launch profile.",
         "Medium",
         "Cleared credential manager tokens and regenerated local OST data store. Synchronized inbox within 15 minutes."),
    ],
    9: [  # Shared Mailbox Auto-mapping
        ("Support team member cannot access tier2-support shared mailbox",
         "New hire granted FullAccess to tier2-support shared mailbox, but folder does not appear in Outlook navigation pane after 24 hours.",
         "Medium",
         "Removed stale permission in Exchange Online PowerShell and re-added with AutoMapping set to false. Manually mapped mailbox in Outlook account settings."),
        ("Shared inbox permissions error: Cannot expand folder",
         "Accounting manager receives 'Cannot display the folder. Access denied' when clicking Payroll shared mailbox.",
         "High",
         "Re-granted FullAccess and SendAs permissions via Exchange Online PowerShell. Re-cached Address Book in Outlook client."),
    ],
    10: [  # Email Security Quarantine False Positives
        ("Legitimate vendor contract quarantined by security gateway",
         "Legal counsel awaiting multi-million dollar vendor agreement. Email flagged as high-confidence phishing due to password-protected PDF.",
         "Urgent",
         "Inspected detonation report in email security console. Verified vendor authenticity and released email with admin override. Whitelisted vendor domain."),
        ("Quarterly customer invoice blocked by inbound filter",
         "Client accounting invoice blocked due to newly registered vendor domain name heuristic rule.",
         "High",
         "Manually released invoice from Proofpoint quarantine and added vendor domain to corporate allowlist."),
    ],
    11: [  # GlobalProtect VPN Gateway Timeout
        ("Remote engineers cannot connect to US-East VPN Gateway",
         "Multiple staff in Virginia unable to connect to GlobalProtect. Client hangs at 'Connecting' and reports Error 504 gateway timeout.",
         "Urgent",
         "Identified ISP IPv6 routing degradation affecting primary gateway DNS. Switched GlobalProtect client to secondary IPv4 gateway. Connections restored."),
        ("VPN connection drops every 15 minutes on home Wi-Fi",
         "User experiences frequent VPN tunnel disconnections while working from home. Logs show SSL tunnel renegotiation failure.",
         "Medium",
         "Disabled IPv6 on client Wi-Fi adapter and lowered tunnel MTU to 1360 in GlobalProtect preferences. Connection remained stable for 8 hours."),
    ],
    12: [  # Azure AD Conditional Access Lockout
        ("User blocked by Conditional Access from home office (Error 53003)",
         "Senior VP travelling for conference cannot log into Office 365. Screen reports 'You cannot access this application from your current location'.",
         "Urgent",
         "Reviewed Entra ID sign-in logs. IP was flagged as untrusted foreign territory. Created approved 5-day Named Location exception in Conditional Access."),
        ("Non-compliant device block after Windows feature update",
         "Employee workstation blocked from Teams and Outlook because Intune reported device compliance evaluation failure.",
         "High",
         "Triggered manual sync in Intune Company Portal. Verified BitLocker status and OS build number. Compliance restored within 10 minutes."),
    ],
    13: [  # SAML SSO Verification Error
        ("SAML assertion error when logging into Datadog via Okta",
         "Engineers clicking Datadog tile in Okta dashboard receive 'SAML Response status code was Responder: InResponseTo invalid'.",
         "High",
         "Discovered 4-minute NTP clock skew on identity provider server. Re-synchronized NTP clock on IdP and updated ACS URL in Datadog SAML settings."),
        ("Single Sign-On failure: Certificate expired error on Jira",
         "DevOps team locked out of internal Jira instance. Browser displays SAML signature validation failed.",
         "Urgent",
         "Uploaded renewed X.509 signing certificate into Jira SSO configuration and refreshed metadata from Okta."),
    ],
    14: [  # Okta FastPass Device Trust
        ("Okta FastPass biometric attestation failing on MacBook Pro",
         "Developer cannot authenticate to AWS console using Touch ID. Okta Verify prompts for password loop.",
         "Medium",
         "Cleared corrupted Touch ID biometric enclave registration using bioutil. Re-enrolled fingerprint in macOS settings and re-linked Okta Verify account."),
        ("Windows Hello PIN not recognized by Okta Verify",
         "User receives 'Device trust verification failed' after motherboard replacement on ThinkPad laptop.",
         "High",
         "Cleared TPM state via TPM management console, re-enrolled Windows Hello PIN, and completed device re-registration in Okta Verify."),
    ],
    15: [  # PAM CyberArk Bastion SSH
        ("DevOps cannot SSH into production Kubernetes bastion",
         "SSH connection to bastion.prod.company.com returns Permission denied (publickey). HashiCorp Vault certificate rejected.",
         "Urgent",
         "Identified that signed SSH client certificate expired after 12-hour TTL. Re-generated signed certificate via Vault CLI with proper principals."),
        ("PAM session termination during emergency database patch",
         "DBA disconnected from database server mid-maintenance. CyberArk session monitoring flagged idle timeout.",
         "High",
         "Re-authenticated to CyberArk PAM portal with emergency change ticket number and resumed administrative session."),
    ],
    16: [  # Workstation Thermal Throttling
        ("Developer laptop CPU throttled to 0.79 GHz under load",
         "Software engineer reports extreme IDE freezing and compilation taking 45 minutes instead of 2 minutes. CPU clock speed locked at 798 MHz.",
         "High",
         "Discovered user was powering 130W Dell Precision laptop with an underpowered 45W monitor USB-C cable. Connected 130W OEM power adapter. CPU clock restored to 3.8 GHz."),
        ("ThinkPad P16 fan running at 100% with thermal shutdown",
         "Laptop powering off abruptly during Docker container builds. HWMonitor shows core temps hitting 100°C.",
         "Medium",
         "Cleaned dust blockage from cooling fins and updated BIOS to version 1.34 which includes updated thermal fan curve tables. Temperatures dropped to 65°C."),
    ],
    17: [  # Dual 4K DisplayPort Flickering
        ("Dual 4K monitors flickering black every 2 minutes on Dell dock",
         "Marketing director reports external screens going black intermittently when connected to WD19TBS Thunderbolt dock.",
         "Medium",
         "Upgraded dock firmware to latest package and disabled 'Panel Self-Refresh' in Intel Graphics Command Center. Replaced generic DP cables with certified DP 1.4 cables."),
        ("Thunderbolt dock USB keyboard and audio disconnecting",
         "Dock loses USB peripheral connections randomly while video continues working.",
         "Medium",
         "Updated Intel Thunderbolt Controller drivers and disabled USB Selective Suspend in Windows Advanced Power Plan."),
    ],
    18: [  # Zebra Thermal Printer Driver Spooler Crashes
        ("Shipping station Zebra ZT410 printer queue crashing Print Spooler",
         "Warehouse packing line halted because shipping labels are not printing. Windows Print Spooler service stops immediately upon start.",
         "Urgent",
         "Stopped spooler service, purged corrupted print jobs from C:\\Windows\\System32\\spool\\PRINTERS, and upgraded to ZDesigner v10 driver. Calibrated label gap."),
        ("Zebra label printer skipping every second label and printing misaligned",
         "Barcode labels printing off-center and feeding blank labels between items.",
         "Medium",
         "Performed manual media sensor calibration via Zebra Setup Utilities and set correct 4x6 label dimension in print preferences."),
    ],
    19: [  # NVMe SSD Read-Only Failure
        ("BSOD CRITICAL_PROCESS_DIED and SSD mounted read-only",
         "Engineering workstation crashed with BSOD. On reboot, drive is read-only and Windows fails to boot.",
         "Urgent",
         "Booted into Linux Live environment. SMART logs showed NVMe spare blocks exhausted (drive entered fail-safe read-only mode). Imaged user data to external drive and replaced SSD."),
        ("Disk write errors and filesystem corruption on NVMe drive",
         "User unable to save files or clone git repos. Event Viewer shows disk error controller nvme0 has error event 11.",
         "High",
         "Ran chkdsk /f /r and confirmed hardware controller failure. Replaced NVMe drive under manufacturer warranty and restored user backup."),
    ],
    20: [  # Conference Room Audio Dropouts
        ("Poly Studio USB video bar not detected in Boardroom Teams Room",
         "Executive meeting starting in 10 minutes; Teams Room console reports 'Microphone and Camera Disconnected'.",
         "Urgent",
         "Power-cycled the USB-over-CAT6 transmitter and receiver boxes behind boardroom display. Reset USB root hub in Device Manager. Poly Studio detected and functional."),
        ("Robotic audio and microphone clipping in conference room",
         "Remote participants complain of audio distortion during town hall call from Conference Room A.",
         "Medium",
         "Adjusted microphone gain in Poly Lens management utility and disabled acoustic fence boundary conflict. Audio clarity restored."),
    ],
    21: [  # MSI Package Deployment Error 1603
        ("Intune deployment of Cisco Webex failing with Error 1603",
         "Company-wide rollout of Webex failing on 40 endpoints with Fatal Error 1603 in Intune Management Extension log.",
         "High",
         "Inspected verbose MSI log and found pending reboot flag from previous patch. Added '/norestart /qn' flags and configured prerequisite reboot detection in Intune packaging."),
        ("Docker Desktop installation aborting on developer laptops",
         "MSI installer exits with code 0x80070643 during Hyper-V feature registration.",
         "Medium",
         "Removed leftover registry keys from prior partial install using Microsoft FixIt tool. Installation succeeded."),
    ],
    22: [  # macOS Gatekeeper Notarization
        ("Internal deployment CLI blocked by macOS Gatekeeper",
         "Developers on macOS Sequoia cannot run internal 'deploy-tool'. OS prompts 'App cannot be opened because Apple cannot check it for malicious software'.",
         "Medium",
         "Removed quarantine extended attribute via `xattr -d com.apple.quarantine`. Submitted binary to corporate Apple Developer Enterprise account for notarization."),
        ("macOS reporting internal build tool is damaged and can't be opened",
         "Engineers unable to launch proprietary data visualizer app after direct download.",
         "Medium",
         "Cleared quarantine attribute and updated distribution pipeline to sign binaries with developer ID certificate."),
    ],
    23: [  # VS Code SSH Host Key Verification
        ("VS Code Remote SSH host key verification failed for dev EC2",
         "Developer cannot connect to cloud dev instance. Terminal reports 'Host key verification failed. Remote host identification has changed!'.",
         "Medium",
         "Confirmed EC2 instance was re-created with new IP address. Removed old fingerprint via `ssh-keygen -R <host-ip>` and re-authenticated successfully."),
        ("JetBrains Gateway failing to establish remote development session",
         "Connection refused during SSH handshake when connecting to remote Linux workstation.",
         "Medium",
         "Updated known_hosts entry and verified user public key was deployed in remote authorized_keys file."),
    ],
    24: [  # Node.js & Python Proxy SSL Cert Failures
        ("npm install failing with SELF_SIGNED_CERT_IN_CHAIN on office Wi-Fi",
         "Node.js developers unable to install dependencies. npm reports request to registry.npmjs.org failed with self-signed certificate in chain.",
         "High",
         "Exported corporate Zscaler root CA certificate and configured npm: `npm config set cafile C:\\Certs\\CorporateRootCA.crt`. Dependency downloads functional."),
        ("pip install SSL: CERTIFICATE_VERIFY_FAILED in Python virtual environment",
         "Python developers cannot install packages due to corporate proxy SSL inspection.",
         "High",
         "Set global environment variable REQUESTS_CA_BUNDLE pointing to corporate root certificate bundle. Pip installs succeeded."),
    ],
    25: [  # Windows Sandbox & WSL2 Hyper-V Conflicts
        ("WSL2 registration failing with error 0x80370102 on Windows 11",
         "New developer laptop cannot launch Ubuntu in WSL2. Error states hardware-assisted virtualization is disabled.",
         "High",
         "Enabled 'hypervisorlaunchtype auto' via bcdedit and enabled VirtualMachinePlatform Windows feature. Restarted laptop and verified VT-x in BIOS."),
        ("Docker Desktop fails to start WSL2 engine on workstation",
         "Docker reports 'Failed to initialize WSL2 backend: virtualization not enabled'.",
         "Medium",
         "Enabled Virtual Machine Platform in Windows Features and updated WSL kernel via `wsl --update`."),
    ],
    26: [  # Active Directory Account Lockout Loop
        ("Account locking out repeatedly every 60 seconds for HR manager",
         "HR manager unlocks account, but it relocks within one minute. PDC logs show BadPwdCount incrementing from internal IP.",
         "Urgent",
         "Traced Event ID 4740 on PDC to user's tablet with stale password saved in corporate Wi-Fi profile. Updated saved password on tablet and cleared lockout."),
        ("Developer account locked out by automated scheduled task",
         "Software engineer account locking out at 3:00 AM every night.",
         "Medium",
         "Identified old scheduled batch job running under user credentials with expired password. Updated scheduled task to run under a Managed Service Account (gMSA)."),
    ],
    27: [  # Kerberos Clock Skew
        ("Logon failure: System cannot log you on due to clock skew",
         "User cannot log into domain computer. Event Viewer logs Kerberos error KRB_AP_ERR_SKEW (Event ID 14).",
         "High",
         "Discovered laptop local clock was 8 minutes behind Domain Controller. Re-registered w32time service and executed `w32tm /resync /force`. Kerberos login restored."),
        ("File share access denied due to Kerberos ticket mismatch",
         "Workstation unable to open shared network drives on file server FS01.",
         "Medium",
         "Synchronized system clock with domain NTP source and purged cached Kerberos tickets via `klist purge`."),
    ],
    28: [  # AWS IAM AssumeRole Token Expiry
        ("Terraform pipeline failing with AccessDenied on AssumeRole",
         "CI/CD deployment fails with error 'User is not authorized to perform sts:AssumeRole on role arn:aws:iam::12345:role/Deployer'.",
         "Urgent",
         "Discovered user session token expired. Re-authenticated with AWS SSO CLI and updated role trust policy to permit updated session boundary."),
        ("AWS CLI reporting ExpiredToken during S3 data migration",
         "Data engineer running batch upload encounters token expiration after 1 hour.",
         "High",
         "Increased maximum session duration for the IAM role to 4 hours in AWS IAM console. Migration completed without interruption."),
    ],
    29: [  # SSPR Telephony Loop
        ("User unable to reset password via SSPR due to missing SMS code",
         "Executive locked out during weekend business trip. SSPR portal does not deliver SMS verification code.",
         "Urgent",
         "Conducted identity verification via video call. Issued temporary access pass (TAP) and updated mobile phone number format to E.164 in Entra ID admin center."),
        ("Microsoft Authenticator prompt not ringing on user phone",
         "Employee cannot complete two-factor authentication because MFA phone call drops immediately.",
         "High",
         "Issued temporary bypass code and re-registered Microsoft Authenticator push notification method on user's new phone."),
    ],
    30: [  # GitHub Enterprise SAML De-provisioning
        ("Terminated contractor still appearing in GitHub Organization",
         "HR reported departure of contractor, but user still has access to sensitive source code repositories.",
         "Urgent",
         "Discovered Okta SCIM sync was lagging due to expired GitHub PAT token. Manually revoked user SAML identity in GitHub Org Settings and refreshed Okta SCIM token."),
        ("New engineer missing team repository access after Okta assignment",
         "New software engineer assigned to 'Frontend Team' in Okta cannot see GitHub repositories.",
         "Medium",
         "Triggered manual group push synchronization in Okta application settings. User received repository permissions within 5 minutes."),
    ],
    31: [  # PostgreSQL RDS Connection Pool Exhaustion
        ("PostgreSQL RDS connection pool exhausted during peak billing batch",
         "During the 2AM billing job, clients receive 500 Internal Server Error. Backend logs report: Connection pool exhausted (100/100 active connections). Postgres CPU at 95%.",
         "Urgent",
         "Terminated locking long-running billing aggregation query via pg_terminate_backend. Increased RDS max_connections and configured PgBouncer pool_size=50. Throughput restored."),
        ("Database deadlocks causing order processing timeouts",
         "E-commerce backend reports deadlock detected in transaction updating inventory table.",
         "High",
         "Identified non-deterministic row locking order in batch checkout service. Updated application query to sort IDs before acquiring row locks."),
    ],
    32: [  # MySQL Replication Lag
        ("MySQL read replica falling 4,000 seconds behind master",
         "Reporting dashboards showing stale analytical data. SHOW REPLICA STATUS indicates Seconds_Behind_Master is growing continuously.",
         "High",
         "Enabled multi-threaded replica appliers: `SET GLOBAL replica_parallel_workers = 8`. Replica caught up to master within 20 minutes."),
        ("MySQL replication broken with Error 1062 Duplicate Entry",
         "Replica stopped processing transactions after manual insert into reporting database.",
         "Urgent",
         "Skipped conflicting GTID transaction using `SET GTID_NEXT` and restarted replica. Configured read_only flag to prevent direct writes on replica."),
    ],
    33: [  # Redis OOM Eviction Spike
        ("Redis cluster memory 100% full, session writes failing with OOM",
         "Web application throws OOM command not allowed when used memory > maxmemory. Users being logged out abruptly.",
         "Urgent",
         "Identified unbounded analytics keys stored without TTL. Changed eviction policy to allkeys-lru and flushed unneeded analytics prefix keys. Memory dropped to 65%."),
        ("Redis latency spike to 500ms due to bigkey serialization",
         "Microservices experiencing timeout waiting for Redis cache response.",
         "High",
         "Identified single 150MB hash key using `redis-cli --bigkeys`. Refactored application to paginate data and deleted monolithic key."),
    ],
    34: [  # MongoDB Replica Set Quorum Loss
        ("MongoDB replica set has no primary node (NotWritablePrimary)",
         "Applications unable to perform database writes. mongosh rs.status() shows all nodes in SECONDARY state.",
         "Urgent",
         "Discovered network partition between primary datacenter and witness node. Restored connectivity and forced re-election. Primary elected successfully."),
        ("MongoDB secondary node stuck in RECOVERING state",
         "Node fails to sync oplog after unclean shutdown.",
         "Medium",
         "Resynced secondary node from healthy primary snapshot. Node rejoined replica set and resumed real-time replication."),
    ],
    35: [  # SQL Server TempDB Full
        ("SQL Server Error 1105: TempDB PRIMARY filegroup is full",
         "Database transactions failing across all enterprise ERP databases. TempDB disk free space at 0 MB.",
         "Urgent",
         "Identified runaway report query performing massive un-indexed Cartesian join. Terminated offending SPID, freed 120 GB, and pre-allocated TempDB with equal file growth."),
        ("TempDB autogrowth contention causing transaction log pauses",
         "Database latency spikes every 30 minutes during autogrowth events.",
         "High",
         "Pre-sized TempDB data files to 50 GB each and enabled Instant File Initialization (IFI) in Windows Local Security Policy."),
    ],
    36: [  # Kubernetes OOMKilled Pods
        ("Payment service pods CrashLoopBackOff with OOMKilled 137",
         "Payment processing microservice pods continuously restarting in production. kubectl describe shows Exit Code 137 OOMKilled.",
         "Urgent",
         "Increased container memory limits from 512Mi to 2Gi in Helm deployment values. Diagnosed and fixed unclosed PDF generation stream in application code."),
        ("Backend worker pods crash during daily batch data import",
         "Worker pods killed by Kubernetes killer when processing large CSV files.",
         "High",
         "Refactored file processor to stream CSV records instead of reading entire 500MB file into memory buffer. Memory footprint stabilized at 250MB."),
    ],
    37: [  # JVM Garbage Collection Pauses
        ("Java Spring Boot microservice experiencing 6-second GC pauses",
         "Prometheus alerts for high p99 latency on checkout service. GC logs report frequent Full GC (Allocation Failure) taking 6,200ms.",
         "Urgent",
         "Switched JVM garbage collector to G1GC with `-XX:+UseG1GC -XX:MaxGCPauseMillis=200`. Heap dumps identified memory leak in session cache, which was refactored with weak references."),
        ("JVM Metaspace memory exhaustion causing service crash",
         "Microservice terminated with java.lang.OutOfMemoryError: Metaspace.",
         "High",
         "Increased MaxMetaspaceSize to 512m and fixed classloader leak in dynamic proxy generator."),
    ],
    38: [  # Node.js Event Loop Lag
        ("Node.js API event loop lag exceeding 2,000ms under load",
         "Node.js API servers timing out on HTTP requests despite CPU utilization at only 35%. Prometheus reports extreme event loop lag.",
         "High",
         "Identified synchronous crypto.pbkdf2Sync operation on main thread. Replaced with asynchronous crypto.pbkdf2 and scaled container replicas from 2 to 6."),
        ("Server freezing when processing large JSON export requests",
         "Exporting user reports causes all concurrent requests to freeze for 10 seconds.",
         "Medium",
         "Offloaded JSON export generation to background BullMQ worker thread pool. Event loop lag returned to < 10ms."),
    ],
    39: [  # AWS ALB 504 Timeouts
        ("AWS Application Load Balancer returning 504 Gateway Timeouts",
         "Customers receive 504 Bad Gateway on checkout during flash sale. ALB metrics show elevated TargetResponseTime exceeding 60 seconds.",
         "Urgent",
         "Increased ALB idle timeout to match backend keep-alive timeout and scaled ECS task count from 4 to 16. Optimized bottleneck database query on promo code validation."),
        ("ALB dropping HTTP connections during container deployment",
         "Occasional 502/504 errors reported by monitoring during automated deployments.",
         "Medium",
         "Configured deregistation delay (connection draining) to 60 seconds and implemented graceful SIGTERM handling in web application."),
    ],
    40: [  # Nginx Ingress 502 Buffer Overflow
        ("Nginx Ingress returning 502 Bad Gateway on requests with large JWT tokens",
         "Users logging in with enterprise SSO receive 502 error. Ingress controller logs report: upstream sent too big header while reading response header.",
         "High",
         "Added proxy-buffer-size: 128k and proxy-buffers-number: 4 annotations to Kubernetes Ingress resource. Large header requests now complete with 200 OK."),
        ("Ingress controller dropping large file uploads with 413 Payload Too Large",
         "Engineers unable to upload 50MB diagnostic log files to internal support portal.",
         "Medium",
         "Added proxy-body-size: 100m annotation to Ingress definition. File uploads now succeed consistently."),
    ]
}

# 60 Held-out Evaluation Tickets for eval/golden_set.jsonl (Strictly Excluded from Index)
GOLDEN_SET_SPEC = [
    # Network (1-5)
    (1001, "Core switch 802.1Q native VLAN mismatch causing packet drop",
     "Inter-VLAN traffic between engineering and finance is experiencing severe packet loss. Switch trunk port Gi1/0/1 reports native VLAN mismatch error.",
     1,
     "Align native VLAN across trunk ports on both switches to VLAN 999. Clear dynamic MAC address learning table and test inter-VLAN ping."),
    (1002, "Floor 2 office DHCP scope depleted - clients getting 169.254 addresses",
     "Morning employees in Floor 2 cannot obtain valid IP address. Windows displays 169.254.x.x APIPA address.",
     2,
     "Shorten DHCP lease time from 7 days to 4 hours and purge expired leases using Remove-DhcpServerv4Lease."),
    (1003, "Internal microservice DNS lookup failing with SERVFAIL",
     "Backend containers cannot resolve internal-billing.corp.local. DNS query to primary domain controller returns SERVFAIL.",
     3,
     "Restart DNS server service on primary domain controller, clear DNS cache with Clear-DnsServerCache, and verify upstream forwarders."),
    (1004, "Corporate Wi-Fi rejecting laptops after RADIUS certificate renewal",
     "Laptops fail to connect to WPA3-Enterprise SSID. NPS server Event Log shows EAP-TLS failure code 16.",
     4,
     "Rebind renewed Enterprise CA certificate in NPS network policy and push intermediate CA bundle to devices via MDM."),
    (1005, "SSH and Git clone hanging over IPsec tunnel due to MTU size",
     "Developers connecting over IPsec VPN experience frozen terminal sessions on large git payloads.",
     5,
     "Enable TCP MSS clamping to 1360 bytes on VPN tunnel interface and permit ICMP Type 3 Code 4 fragmentation needed."),
    (1006, "APIPA address assigned on executive boardroom wired Ethernet",
     "Boardroom conference laptop unable to connect to internal network; Ethernet port receives 169.254 address.",
     2,
     "Clear exhausted DHCP lease reservations on subnet scope and reboot access switch port."),
    (1007, "Internal intranet domain name unresolvable after DNS maintenance",
     "Users across headquarters report intranet.corp.local returns NXDOMAIN.",
     3,
     "Flush DNS resolver cache on client machines and restart BIND forwarder daemon on secondary DNS server."),
    (1008, "Wi-Fi authentication loop on Corporate-Secure network",
     "Mobile devices and laptops prompt repeatedly for credentials without connecting to office Wi-Fi.",
     4,
     "Verify RADIUS shared secret on wireless LAN controller and re-issue client root certificates."),

    # Email (6-10)
    (1009, "Exchange Online incoming mail backlog with 451 4.7.500 Server busy",
     "Incoming customer emails delayed by over an hour. Exchange message trace indicates deferred delivery.",
     6,
     "Whitelist high-volume inbound relay IP in Exchange Enhanced Filtering and adjust inbound connector rate limits."),
    (1010, "Marketing transactional emails bouncing with DMARC rejection 550",
     "Emails sent from SendGrid using corporate domain fail delivery with 550 5.7.26 DMARC policy rejection.",
     7,
     "Add SendGrid include statement to public DNS SPF record and create CNAME records for custom 2048-bit DKIM keys."),
    (1011, "Outlook crashing on startup due to oversized 50GB OST data file",
     "Outlook fails to launch with Application Error Event ID 1000 in OUTLOOK.EXE.",
     8,
     "Rename corrupted outlook.ost file to .old, launch Outlook to regenerate fresh data store, and set sync slider to 1 year."),
    (1012, "New team member cannot view shared department inbox in Outlook",
     "FullAccess permission granted on customer-service mailbox, but mailbox is not auto-mapping in Outlook.",
     9,
     "Remove and re-grant mailbox permissions with AutoMapping set to false, then manually add mailbox in Outlook Advanced settings."),
    (1013, "Critical vendor invoice quarantined as false positive phishing",
     "Legitimate vendor invoice PDF blocked by email security gateway as High Confidence Phishing.",
     10,
     "Inspect threat sandbox report, release message from security admin quarantine with override, and add vendor domain to allowlist."),
    (1014, "Outgoing company emails marked as spam by Google Workspace recipients",
     "Clients using Gmail report our sales quotes are landing in their Spam folder.",
     7,
     "Validate SPF record syntax ensuring under 10 DNS lookups and align DKIM signing selector."),
    (1015, "Outlook disconnected and prompts for password continuously",
     "User Outlook client reports Disconnected and repeated credential prompt fails to accept valid password.",
     8,
     "Clear stored Office credentials in Windows Credential Manager and recreate Outlook mail profile."),

    # VPN and Access (11-15)
    (1016, "GlobalProtect VPN gateway timeout Error 504 on remote workers",
     "Remote employees in Chicago cannot connect to VPN. Client reports gateway not responding.",
     11,
     "Disable IPv6 binding on client Wi-Fi adapter and switch connection to secondary backup VPN gateway."),
    (1017, "Conditional access policy blocking employee traveling abroad (Error 53003)",
     "Engineer traveling in Europe blocked from accessing Microsoft 365 services due to location policy.",
     12,
     "Create temporary approved location exception in Entra ID Conditional Access and clear user sign-in risk flag."),
    (1018, "Okta SAML SSO login failing with InResponseTo mismatch error",
     "Users logging into Salesforce through Okta receive SAML response status code Responder.",
     13,
     "Synchronize NTP clocks between identity provider and service provider and update ACS URL in SAML configuration."),
    (1019, "Okta Verify Touch ID biometric attestation loop on MacBook",
     "Developer unable to authenticate with Touch ID in Okta Verify; app loops back to password prompt.",
     14,
     "Reset biometric Touch ID enclave using bioutil, re-enroll fingerprint in macOS, and re-link Okta Verify account."),
    (1020, "DevOps engineer denied access to production SSH bastion",
     "SSH connection to bastion returns Permission denied (publickey) due to expired Vault certificate.",
     15,
     "Request new signed SSH certificate from HashiCorp Vault with required principals and connect specifying certificate path."),
    (1021, "GlobalProtect VPN tunnel dropping during video conference calls",
     "VPN client disconnects intermittently every 20 minutes while working from home.",
     11,
     "Lower VPN client MTU setting to 1360 and clear saved gateway authentication tokens in preferences."),
    (1022, "Intune compliant device status lost after operating system upgrade",
     "Workstation blocked from accessing enterprise apps because device marked non-compliant.",
     12,
     "Run manual sync in Intune Company Portal, verify TPM and Secure Boot status, and refresh compliance status."),

    # Hardware (16-20)
    (1023, "Laptop CPU locked at 0.79 GHz under compilation workload",
     "Software engineer reports heavy IDE slowdown; CPU clock speed capped at 798 MHz despite low utilization.",
     16,
     "Connect 130W OEM power adapter instead of low-wattage USB-C charger and update BIOS firmware to resolve throttling."),
    (1024, "External dual 4K monitors flickering black on Thunderbolt 4 dock",
     "Dual external displays connected to Thunderbolt dock go dark for 2 seconds every few minutes.",
     17,
     "Update dock firmware to latest release, disable Panel Self-Refresh in Intel graphics console, and use certified DP 1.4 cables."),
    (1025, "Warehouse Zebra label printer crashing Windows Print Spooler",
     "Packing line stopped because shipping labels fail to print and spoolsv.exe crashes repeatedly.",
     18,
     "Stop print spooler, delete corrupted files in C:\\Windows\\System32\\spool\\PRINTERS, restart spooler, and upgrade ZDesigner driver."),
    (1026, "BSOD CRITICAL_PROCESS_DIED and NVMe SSD entered read-only mode",
     "Developer laptop crashes to blue screen and reports no bootable device; SMART shows wear at 100%.",
     19,
     "Boot into Linux live USB, image user data to external drive using ddrescue, and replace failed NVMe drive."),
    (1027, "Poly Studio conference room video bar not detected in Teams Room",
     "Meeting room console shows camera and microphone disconnected prior to board meeting.",
     20,
     "Power-cycle USB extender transceivers, reset USB root hub in Device Manager, and verify Poly Studio connection."),
    (1028, "Dell Precision workstation overheating and shutting down",
     "Workstation fan running at maximum speed with emergency thermal shutdown during 3D rendering.",
     16,
     "Clean dust blockage from CPU cooling heatsink, re-apply thermal paste, and update BIOS thermal tables."),
    (1029, "Zebra barcode printer feeding blank labels between print jobs",
     "Shipping station printer misaligned and prints across label boundaries.",
     18,
     "Perform gap sensor calibration via Zebra Setup Utilities and verify label dimension configuration."),

    # Software Installation (21-25)
    (1030, "Intune application deployment failing with Fatal Error 1603",
     "Enterprise software deployment to workstations fails with error code 0x80070643 / 1603 in AgentExecutor.log.",
     21,
     "Clear pending reboot registry flag, add /qn /norestart parameters to MSI command, and deploy cleanly."),
    (1031, "macOS Gatekeeper blocking internal developer CLI as unverified developer",
     "Mac users unable to open internal tool; system warns app cannot be checked for malicious software.",
     22,
     "Remove com.apple.quarantine attribute via xattr -d, click Open Anyway in Privacy settings, and notarize binary."),
    (1032, "VS Code Remote SSH host key verification failed after server rebuild",
     "Developer cannot connect to cloud VM; error states remote host identification has changed.",
     23,
     "Remove old host key using ssh-keygen -R <server-ip> and accept new fingerprint in interactive SSH session."),
    (1033, "npm install failing with SELF_SIGNED_CERT_IN_CHAIN on office network",
     "Node.js package installation fails due to corporate proxy SSL inspection certificate.",
     24,
     "Configure npm cafile setting pointing to corporate root certificate bundle in C:\\Certs\\CorporateRootCA.crt."),
    (1034, "WSL2 installation failing with error 0x80370102 on Windows 11",
     "Developer unable to launch WSL2 Ubuntu; error reports virtualization is disabled.",
     25,
     "Enable hypervisorlaunchtype auto via bcdedit, enable VirtualMachinePlatform Windows feature, and verify VT-x in BIOS."),
    (1035, "pip install failing with SSL CERTIFICATE_VERIFY_FAILED in Python",
     "Python pip command unable to connect to PyPI over corporate network.",
     24,
     "Set REQUESTS_CA_BUNDLE environment variable pointing to corporate trusted root certificate bundle."),
    (1036, "Docker Desktop failing to initialize Hyper-V backend",
     "Docker Desktop startup fails with error: Virtualization not enabled in BIOS.",
     25,
     "Enable Windows Virtual Machine Platform feature and update WSL kernel components via wsl --update."),

    # Account and Password (26-30)
    (1037, "Active Directory user account locking out repeatedly every minute",
     "Employee account locks immediately upon unlock; PDC logs show BadPwdCount incrementing from internal IP.",
     26,
     "Locate caller computer from Event ID 4740 on PDC, clear stale credentials in Windows Credential Manager, and unlock account."),
    (1038, "Logon failure due to Kerberos clock skew exceeding 5 minutes",
     "User cannot log into domain PC; Event Log records KRB_AP_ERR_SKEW Event ID 14.",
     27,
     "Re-register Windows time service, force time resync with Domain Controller via w32tm /resync, and purge klist tickets."),
    (1039, "AWS CLI failing with ExpiredToken during Terraform deployment",
     "CI deployment fails with error The security token included in the request is expired.",
     28,
     "Re-authenticate with AWS SSO CLI and extend maximum session duration on the IAM role to 4 hours."),
    (1040, "Employee unable to complete SSPR because SMS verification code never arrives",
     "Locked-out user cannot reset password via self-service portal.",
     29,
     "Verify identity via secure video call, issue temporary access pass (TAP), and correct phone number to E.164 format."),
    (1041, "Departed contractor retaining access to GitHub organization repos",
     "HR confirms contractor departure, but user remains in GitHub organization due to SCIM lag.",
     30,
     "Manually revoke SAML identity link in GitHub Org settings and trigger manual group push in Okta."),
    (1042, "Domain user locked out by legacy scheduled task with old password",
     "User account repeatedly locked out at midnight every night.",
     26,
     "Identify scheduled task on server running under user account, update task to use gMSA, and unlock domain account."),
    (1043, "Kerberos ticket authentication failing on file server share",
     "User receives access denied opening shared departmental drive after password change.",
     27,
     "Run klist purge to flush stale Kerberos tickets and reconnect network mapped drive."),

    # Database (31-35)
    (1044, "PostgreSQL RDS connection pool exhausted with FATAL remaining connection slots",
     "Billing service throws 500 errors; RDS active connections hit 100/100 limit with 95% CPU.",
     31,
     "Terminate locking long-running queries with pg_terminate_backend, increase max_connections, and deploy PgBouncer connection pooling."),
    (1045, "MySQL read replica lagging by 3,500 seconds behind primary",
     "Analytics dashboard shows stale metrics; Seconds_Behind_Master growing steadily.",
     32,
     "Enable multi-threaded replica applier with replica_parallel_workers=8 and verify replication catches up to primary."),
    (1046, "Redis cluster memory saturated and failing writes with OOM command not allowed",
     "Web sessions dropping; Redis cluster memory at 100% due to unexpired analytics keys.",
     33,
     "Configure maxmemory-policy to allkeys-lru, purge orphaned analytics keys, and ensure application keys include TTL."),
    (1047, "MongoDB replica set has no primary node (NotWritablePrimary error)",
     "Application writes failing across cluster; mongosh rs.status() shows all nodes in SECONDARY.",
     34,
     "Restore network connectivity to partition witness node, re-evaluate quorum, and verify primary elected successfully."),
    (1048, "SQL Server Error 1105: Could not allocate space for object in tempdb",
     "ERP database transactions rolling back due to exhausted disk space on TempDB drive.",
     35,
     "Kill runaway query session performing Cartesian product, shrink TempDB files, and pre-allocate data files with equal autogrowth."),
    (1049, "PostgreSQL deadlock detected in concurrent transaction batch",
     "Application logs report deadlock detected during simultaneous inventory updates.",
     31,
     "Refactor database transaction to enforce consistent row lock ordering across concurrent workers."),
    (1050, "MySQL replication stopped with Error 1062 Duplicate entry",
     "Replica SQL thread halted due to primary key conflict on reporting table.",
     32,
     "Inject GTID skip transaction on replica, restart slave thread, and set read_only=ON on replica instance."),

    # Performance (36-40)
    (1051, "Kubernetes pod CrashLoopBackOff with OOMKilled exit code 137",
     "Microservice pods restarting continuously; kubectl describe shows OOMKilled Exit Code 137.",
     36,
     "Increase pod memory limits from 512Mi to 2Gi in deployment spec and fix unclosed file stream in application code."),
    (1052, "Java Spring Boot API experiencing 5-second garbage collection pauses",
     "p99 latency spikes to 5,000ms; GC logs show Full GC Allocation Failure pauses.",
     37,
     "Switch JVM garbage collector to G1GC with -XX:+UseG1GC -XX:MaxGCPauseMillis=200 and analyze heap dump for memory leaks."),
    (1053, "Node.js API event loop lag exceeding 1.8 seconds under concurrent traffic",
     "API response times degrade under load; prometheus reports high nodejs_eventloop_lag_seconds.",
     38,
     "Offload synchronous cryptographic hashing to worker threads, replace sync file operations, and scale pods horizontally."),
    (1054, "AWS Application Load Balancer returning 504 Gateway Timeout during sale",
     "Customers experiencing 504 errors on checkout; ALB metrics show elevated TargetResponseTime.",
     39,
     "Adjust ALB idle timeout to align with backend keep-alive, scale target group capacity, and optimize slow checkout query."),
    (1055, "Nginx Ingress controller returning 502 Bad Gateway on large JWT requests",
     "Users logging in via SSO receive 502; ingress logs report upstream sent too big header.",
     40,
     "Add proxy-buffer-size: 128k and proxy-buffers-number: 4 annotations to Ingress resource and trim cookie payload."),
    (1056, "Container memory leak causing nightly pod eviction in production",
     "Worker service pod memory steadily climbs over 12 hours until Kubernetes evicts pod.",
     36,
     "Inspect application memory profile with pprof, fix unbounded in-memory cache, and configure rolling restart policy."),
    (1057, "JVM Metaspace OutOfMemoryError in Java microservice",
     "Java application crashes with java.lang.OutOfMemoryError: Metaspace under heavy classloading.",
     37,
     "Increase MaxMetaspaceSize parameter and resolve classloader leak in runtime dependency injection."),
    (1058, "Node.js microservice freezing during bulk report export",
     "Main thread blocked for 8 seconds when user triggers 50,000 row CSV export.",
     38,
     "Move CSV export generation to background job queue worker and stream response to user."),
    (1059, "AWS ALB connection drop during rolling deployment update",
     "Occasional 502 Bad Gateway errors observed during automated deployment rollout.",
     39,
     "Configure ALB target group deregistration delay to 60 seconds and implement graceful SIGTERM shutdown in backend."),
    (1060, "Nginx ingress rejecting file uploads with 413 Request Entity Too Large",
     "Users unable to attach 30MB diagnostic logs in customer support web portal.",
     40,
     "Add proxy-body-size: 50m annotation to Kubernetes Ingress manifest and reload ingress controller."),
]


def generate_seed_dataset(output_dir: Path, seed: int = 42) -> None:
    """
    Generates all Phase 0 datasets deterministically.
    
    Args:
        output_dir: Base directory where data/seed and eval folders are located.
        seed: Random seed for deterministic reproducibility.
    """
    random.seed(seed)
    
    seed_dir = output_dir / "data" / "seed"
    eval_dir = output_dir / "eval"
    seed_dir.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)

    kb_file = seed_dir / "kb_articles.jsonl"
    tickets_file = seed_dir / "tickets.jsonl"
    golden_file = eval_dir / "golden_set.jsonl"

    print(f"🚀 Generating Phase 0 Datasets (Random Seed = {seed})...")

    # 1. Generate KB Articles (40 articles, 5 per category)
    kb_articles: List[KBArticle] = []
    for item in RAW_KB_ARTICLES:
        article = KBArticle(**item)
        kb_articles.append(article)

    with open(kb_file, "w", encoding="utf-8") as f:
        for article in kb_articles:
            f.write(article.model_dump_json() + "\n")
    print(f"✅ Generated {len(kb_articles)} KB articles in: {kb_file}")

    # 2. Generate Historical Tickets (300 tickets)
    # Distribute tickets across all 40 KB articles with varied priorities
    priorities: List[PriorityType] = ["Low", "Medium", "High", "Urgent"]
    tickets: List[Ticket] = []
    ticket_id_counter = 1

    # First, populate from template variants
    for kb_id, variants in INCIDENT_TEMPLATES.items():
        article = next(a for a in kb_articles if a.id == kb_id)
        for title, desc, prio, res in variants:
            ticket = Ticket(
                id=ticket_id_counter,
                title=title,
                description=desc,
                category=article.category,
                priority=prio if prio in priorities else "Medium",
                resolution=res,
                kb_article_id=kb_id,
            )
            tickets.append(ticket)
            ticket_id_counter += 1

    # Fill remaining tickets up to 300 using realistic variations mapped to KB articles
    modifiers = [
        "during peak hours",
        "after routine patch cycle",
        "on secondary subnet",
        "affecting regional office staff",
        "reported by engineering lead",
        "affecting remote workforce",
        "intermittent degradation reported",
        "causing operational delay",
    ]

    while len(tickets) < 300:
        # Pick a random KB article
        kb = random.choice(kb_articles)
        base_templates = INCIDENT_TEMPLATES.get(kb.id)
        if base_templates:
            base_title, base_desc, base_prio, base_res = random.choice(base_templates)
        else:
            base_title, base_desc, base_prio, base_res = (
                f"Incident relating to {kb.title}",
                f"User encounters technical disruption with {kb.title}. Error confirmed in logs.",
                "Medium",
                f"Applied technical resolution runbook #{kb.id}. Issue resolved."
            )

        mod = random.choice(modifiers)
        prio = random.choice(priorities)
        title = f"{base_title} ({mod})"
        desc = f"{base_desc} Observed {mod}. Impacting standard daily workflows."
        res = f"{base_res} Verified fix resolved the issue."

        ticket = Ticket(
            id=ticket_id_counter,
            title=title,
            description=desc,
            category=kb.category,
            priority=prio,
            resolution=res,
            kb_article_id=kb.id,
        )
        tickets.append(ticket)
        ticket_id_counter += 1

    with open(tickets_file, "w", encoding="utf-8") as f:
        for t in tickets:
            f.write(t.model_dump_json() + "\n")
    print(f"✅ Generated {len(tickets)} historical tickets in: {tickets_file}")

    # 3. Generate Held-Out Golden Set Tickets (60 tickets)
    golden_tickets: List[GoldenTicket] = []
    for t_id, title, desc, exp_kb, ref_res in GOLDEN_SET_SPEC:
        gt = GoldenTicket(
            ticket_id=t_id,
            title=title,
            description=desc,
            expected_kb_article_id=exp_kb,
            reference_resolution=ref_res,
        )
        golden_tickets.append(gt)

    with open(golden_file, "w", encoding="utf-8") as f:
        for gt in golden_tickets:
            f.write(gt.model_dump_json() + "\n")
    print(f"✅ Generated {len(golden_tickets)} held-out golden set tickets in: {golden_file}")

    # 4. Strict Validation: Confirm Golden Set is completely disjoint from Tickets
    ticket_ids = {t.id for t in tickets}
    golden_ids = {gt.ticket_id for gt in golden_tickets}
    overlap = ticket_ids.intersection(golden_ids)
    assert len(overlap) == 0, f"Critical Error: Overlap found between tickets and golden set: {overlap}"
    print("🔒 Verified: Golden Set tickets are 100% disjoint from Historical Tickets!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Seed and Evaluation Datasets for DigiPlus AI Service Desk.")
    parser.add_argument("--output-dir", type=Path, default=Path.cwd(), help="Root directory of the project.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic generation.")
    args = parser.parse_args()

    generate_seed_dataset(output_dir=args.output_dir, seed=args.seed)
