# BIG-IP APM Split Tunnelling & Dynamic Exclusion of Office 365 (O365) URLs/IPs

This Python script fetches Office 365 URLs and IPs (IPv4 and/or IPv6) from Microsoft's [Office 365 IP Address and URL web service](https://docs.microsoft.com/en-us/office365/enterprise/office-365-ip-web-service), dynamically updates Network Access List "Exclude" properties for one or more Network Access Lists, and applies changes to the affected Access Policies. If the script is running on an HA pair of BIG-IPs then the script will also initiate a ConfigSync to push the updated configuration from the active BIG-IP to the standby BIG-IP.

## Script Requirements
*	TMOS 12.1.0 or higher
*	BIG-IP must be capable of resolving internet DNS names (ex. via DNS Lookup Server configuration)
*	BIG-IP must be able to reach endpoints.office.com via TCP 443 (via Management or TMM interface)
* Administrative rights on the BIG-IP(s)
* Bash shell access on the BIG-IP(s)

## Things to Note
*	This script does not enable “split tunneling” or make any other modifications, other than those mentioned, to the Network Access List(s) that may be required to enable the desired functionality. For guidance relating to Network Access List / Split Tunnelling configuration refer to the [BIG-IP APM Knowledge Center](https://support.f5.com/csp/knowledge-center/software/BIG-IP?module=BIG-IP%20APM).
  * Some split tunneling guidance:
    * **Allow Local DNS Servers** should be enabled to allow client access to Office 365 when VPN is disconnected
    * Exclude doesn't work for IPv6 on macOS
    * Exclude by FQDN is not supported on macOS
* This script should not be used with BIG-IP Edge Client's Always Connected Mode: if Stonewall is configured to block traffic, then the excluded resources are not reachable (this is by design).
* Usage of DNS Address Exclusions requires the installation of the DNS Relay Proxy service on the VPN client
  * [K9694: Overview of the Windows DNS Relay Proxy service](https://support.f5.com/csp/article/K9694)
  * [K49720803: BIG-IP Edge Client operations guide | Chapter 3: Common approaches to configuring VPN](https://support.f5.com/csp/article/K49720803)
* While the endpoints retrieved by this script handle the vast majority of Office 365 traffic, it is possible some traffic related to Office 365 is not summarized in the endpoint lists and will still go through the VPN.
* HA: This script must be implemented on both members of an HA pair
* HA: Exclusion list updates will only take place on the Active member - changes are synced from the Active to Standby by the script
* This script tracks the version of the Office 365 service instance and will only update the exclusion lists if a newer version is detected. If modifications to the script's operating parameters (ex. Network Access Lists, O365 Service Areas, Additional URLs/IPs to Exclude) are made, they will NOT take effect until the script detects a new service instance version. To force the script to run with the updated parameters earlier, remove the o365_version.txt file from the script's working directory OR *temporarily* set `force_o365_record_refresh = 1`, then manually execute the script (`python /shared/o365/apm_o365_update.py`).
  
## Implementation

1. Modify the "User Options" in the script to match your environment and requirements
2. SSH to the standalone or active BIG-IP
3. Change to the bash shell  
  `bash`
4. Create the directory the script will reside in. The default directory is /shared/o365/.  
  `mkdir /shared/o365`  
  *Note: If not creating the directory as it is above, ensure you update the **work_directory** variable under **System Options** with the correct path.*
5. Upload or create the script (apm_o365_update.py) in the working directory (ex. /shared/o365/)
6. Manually run the script to confirm that it is working as expected  
  `python /shared/o365/apm_o365_update.py`
7. Confirm the script ran without error by displaying the log file (default path: /var/log/o365_update):  
  `cat /var/log/o365_update`
  
  ![alt text](images/run_and_log.png "Bash output showing execution of Python script and script logging")



If this is an HA pair, repeat steps 2 - 


## Apendix

### User Options
* **na_lists** - Specify the Network Access Lists that this script will load the Office 365 URLs/IPs into.
  * *Usage examples:*
    * Single Network Access List: na_lists = ["MyNAL"]
    * Multiple Network Access Lists: na_lists = ["MyNAL1", "MyNAL2", "MyNAL3"] (comma separated)
* **access_profiles** - Specify the Access Profiles/Policies that this script will apply after updating the Network Access Lists defined in **na_lists**. The script will execute the "Apply Access Policy" action on the Access Profiles defined in this list.
  * *Usage examples:*
    * Single Access Profile: access_profiles = ["MyAP"]
    * Multiple Access Profiles: access_profiles = ["MyAP1", "MyAP2", "MyAP3"] (comma separated)
* **customer_endpoint** - Specify the Office 365 instance to return endpoints for.
  * *Default:* Worldwide
  * *Usage example:*
    * Uncomment the desired endpoint. Only one endpoint is supported. For example, to specify the Worldwide endpoint remove the "#" at the beginning of that line:  
        
      customer_endpoint = "Worldwide"  
      #customer_endpoint = "USGovDoD"  
      #customer_endpoint = "USGovGCCHigh"  
      #customer_endpoint = "China"  
      #customer_endpoint = "Germany"
* **care_exchange** - Specify whether to import endpoints from the Exchange service area.
  * *Default:* 1
  * *Options:*
    * 0 - Do not import endpoints from this service area
    * 1 - Import endpoints from this service area
  * *Usage example:*
    * care_exchange = 1 (import Exchange endpoints)
* **care_sharepoint** - Specify whether to import endpoints from the SharePoint service area.
  * *Default:* 1
  * *Options:*
    * 0 - Do not import endpoints from this service area
    * 1 - Import endpoints from this service area
  * *Usage example:*
    * care_sharepoint = 0 (do not import SharePoint endpoints)
* **care_skype** - Specify whether to import endpoints from the Skype service area.
  * *Default:* 1
  * *Options:*
    * 0 - Do not import endpoints from this service area
    * 1 - Import endpoints from this service area
  * *Usage example:*
    * care_skype = 1 (import Skype endpoints)
* **care_common** - Specify whether to import endpoints from the Common service area.
  * *Default:* 1
  * *Options:*
    * 0 - Do not import endpoints from this service area
    * 1 - Import endpoints from this service area
  * *Usage example:*
    * care_common = 1 (import Common endpoints)
* **use_url** - Specify the Office 365 instance to return endpoints for.
  * *Usage:*
    * Uncomment the desired endpoint. Only one endpoint is supported.
* **use_ipv4** - Specify the Office 365 instance to return endpoints for.
  * *Usage:*
    * Uncomment the desired endpoint. Only one endpoint is supported.
* **use_ipv6** - Specify the Office 365 instance to return endpoints for.
  * *Usage:*
    * Uncomment the desired endpoint. Only one endpoint is supported.
* **only_required** - Specify the Office 365 instance to return endpoints for.
  * *Usage:*
    * Uncomment the desired endpoint. Only one endpoint is supported.
* **noimport_urls** - Specify the Office 365 instance to return endpoints for.
  * *Usage:*
    * Uncomment the desired endpoint. Only one endpoint is supported.
* **noimport_ips** - Specify the Office 365 instance to return endpoints for.
  * *Usage:*
    * Uncomment the desired endpoint. Only one endpoint is supported.
* **additional_urls** - Specify the Office 365 instance to return endpoints for.
  * *Usage:*
    * Uncomment the desired endpoint. Only one endpoint is supported.
* **additional_ipv4** - Specify the Office 365 instance to return endpoints for.
  * *Usage:*
    * Uncomment the desired endpoint. Only one endpoint is supported.
* **additional_ipv6** - Specify the Office 365 instance to return endpoints for.
  * *Usage:*
    * Uncomment the desired endpoint. Only one endpoint is supported.
* **force_o365_record_refresh** - Specify the Office 365 instance to return endpoints for.
  * *Usage:*
    * Uncomment the desired endpoint. Only one endpoint is supported.
* **device_group_name** - Specify the Office 365 instance to return endpoints for.
  * *Usage:*
    * Uncomment the desired endpoint. Only one endpoint is supported.
* **ha_config** - Specify the Office 365 instance to return endpoints for.
  * *Usage:*
    * Uncomment the desired endpoint. Only one endpoint is supported.
* **log_level** - Specify the logging level of the script. Log messages are written to the file specified in **log_dest_file**.
  * *Default:* 1
  * *Options:*
    * 0 - No logging
    * 1 - Normal level of logging
    * 2 - Debug level logging
  * *Usage example:*
    * log_level = 1 (normal logging)


SSH to the standalone or active BIG-IP.
