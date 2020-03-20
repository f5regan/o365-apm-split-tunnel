# BIG-IP APM Split Tunnelling & Dynamic Exclusion of Office 365 (O365) URLs/IPs

This Python script fetches Office 365 URLs and IPs (IPv4 and/or IPv6) from Microsoft (details here: https://docs.microsoft.com/en-us/office365/enterprise/office-365-ip-web-service), dynamically updates Network Access List "Exclude" properties for one or more Network Access Lists, and applies changes to the affected Access Policies, and finally, if the BIG-IPs are in an HA pair the active BIG-IP synchronizes the changes to the standby unit.

## Requirements:
-	TMOS 12.1.0 or higher
-	BIG-IP must be capable of resolving internet DNS names (ex. via DNS Lookup Server configuration)
-	BIG-IP must be able to reach endpoints.office.com via TCP 443 (via Management or TMM interface)
- 

## What it does not do:
-	This script does not enable “split tunneling” or make any other modifications, other than those mentioned, to the Network Access List(s) that may be required to enable the desired functionality.
