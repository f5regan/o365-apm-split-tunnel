#!/bin/python
# -*- coding: utf-8 -*-
# O365 URL/IP update automation for BIG-IP
# Version: 1.1
# Last Modified: 01 April 2020
# Original author: Makoto Omura, F5 Networks Japan G.K.
#
# Modified for APM Network Access "Exclude Address Space" by Regan Anderson, F5 Networks
# 
# This Sample Software provided by the author is for illustrative
# purposes only which provides customers with programming information
# regarding the products. This software is supplied "AS IS" without any
# warranties and support.
#
# The author assumes no responsibility or liability for the use of the
# software, conveys no license or title under any patent, copyright, or
# mask work right to the product.
#
# The author reserves the right to make changes in the software without
# notification. The author also make no representation or warranty that
# such application will be suitable for the specified use without
# further testing or modification.
#-----------------------------------------------------------------------

import httplib
import urllib
import uuid
import os
import re
import json
import commands
import datetime
import sys

#-----------------------------------------------------------------------
# User Options - Configure as desired
#-----------------------------------------------------------------------

# Access Profile Name(s) - ex. SINGLE ["AP1"] OR MULTIPLE ["AP1", "AP2", "AP3"]
access_profiles = ["MyAccessProfile"]

# Network Access List Name(s) - ex. SINGLE ["NAL1"] OR MULTIPLE ["NAL1", "NAL2", "NAL3"]
na_lists = ["MyNetworkAccessList"]

# Microsoft Web Service Customer endpoints (ENABLE ONLY ONE ENDPOINT)
# These are the set of URLs defined by customer endpoints as described here: https://docs.microsoft.com/en-us/office365/enterprise/urls-and-ip-address-ranges
customer_endpoint = "Worldwide"
#customer_endpoint = "USGovDoD"
#customer_endpoint = "USGovGCCHigh"
#customer_endpoint = "China"
#customer_endpoint = "Germany"

# O365 "SeviceArea" (O365 endpoints) to consume, as described here: https://docs.microsoft.com/en-us/office365/enterprise/urls-and-ip-address-ranges
care_exchange = 1                       # "Exchange Online": 0=do not care, 1=care
care_sharepoint = 1                     # "SharePoint Online and OneDrive for Business": 0=do not care, 1=care
care_skype = 1                          # "Skype for Business Online and Microsoft Teams": 0=do not care, 1=care
care_common = 1                         # "Microsoft 365 Common and Office Online": 0=do not care, 1=care

# O365 Record types to download & update
use_url = 0                             # DNS/URL exclusions: 0=do not use, 1=use
use_ipv4 = 1                            # IPv4 exclusions: 0=do not use, 1=use
use_ipv6 = 0                            # IPv6 exclusions: 0=do not use, 1=use

# O365 Categories to download & update
o365_categories = 0                     # 0=Optimize only, 1= Optimize & Allow, 2 = Optimize, Allow, and Default

# O365 Endpoints to import - O365 required endpoints or all endpoints
# WARNING: "import all" includes non-O365 URLs that one may not want to bypass (ex. www.youtube.com)
only_required = 1                       # 0=import all, 1=O365 required only

# Don't import these O365 URLs (URL must be exact or ends_with match to URL as it exists in JSON record - pattern matching not supported)
# Provide URLs in list format - ex. [".facebook.com", "*.itunes.apple.com", "bit.ly"]
#noimport_urls = []
noimport_urls = [".symcd.com",".symcb.com",".entrust.net",".digicert.com",".identrust.com",".verisign.net",".globalsign.net",".globalsign.com",".geotrust.com",".omniroot.com",".letsencrypt.org",".public-trust.com","platform.linkedin.com"]

# Don't import these O365 IPs (IP must be exact match to IP as it exists in JSON record - IP/CIDR mask cannot be modified)
# Provide IPs (IPv4 and IPv6) in list format - ex. ["191.234.140.0/22", "2620:1ec:a92::152/128"]
noimport_ips = []

# Non-O365 URLs to add to DNS Exclude List
# Provide URLs in list format - ex. ["m.facebook.com", "*.itunes.apple.com", "bit.ly"]
additional_urls = []

# Non-O365 IPs to add to IPV4 Exclude List
# Provide IPs in list format - ex. ["191.234.140.0/22", "131.253.33.215/32"]
additional_ipv4 = []

# Non-O365 IPs to add to IPV6 Exclude List
# Provide IPs in list format - ex. ["2603:1096:400::/40", "2620:1ec:a92::152/128"]
additional_ipv6 = []

# Action if O365 endpoint list is not updated
force_o365_record_refresh = 0           # 0=do not update, 1=update (for test/debug purpose)

# BIG-IP HA Configuration
device_group_name = "device-group1"     # Name of Sync-Failover Device Group.  Required for HA paired BIG-IP.
ha_config = 0                           # 0=stand alone, 1=HA paired

# Log configuration
log_level = 1                           # 0=none, 1=normal, 2=verbose

#-----------------------------------------------------------------------
# System Options - Modify only when necessary
#-----------------------------------------------------------------------

# Working directory, file name for guid & version management
work_directory = "/shared/o365/"
file_name_guid = "/shared/o365/guid.txt"
file_ms_o365_version = "/shared/o365/o365_version.txt"
log_dest_file = "/var/log/o365_update"

# Microsoft Web Service URLs
url_ms_o365_endpoints = "endpoints.office.com"
url_ms_o365_version = "endpoints.office.com"
uri_ms_o365_version = "/version?ClientRequestId="

#-----------------------------------------------------------------------
# Implementation - Please do not modify
#-----------------------------------------------------------------------
list_urls_to_exclude = []
list_ipv4_to_exclude = []
list_ipv6_to_exclude = []

def log(lev, msg):
    if log_level >= lev:
        log_string = "{0:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now()) + " " + msg + "\n"
        f = open(log_dest_file, "a")
        f.write(log_string)
        f.flush()
        f.close()
    return

def main():
    # -----------------------------------------------------------------------
    # Check if this BIG-IP is ACTIVE for the traffic group (= traffic_group_name)
    # -----------------------------------------------------------------------
    result = commands.getoutput("tmsh show /cm failover-status field-fmt")

    if ("status ACTIVE" in result) or (ha_config == 0):
        log(1, "This BIG-IP is standalone or HA ACTIVE. Initiating O365 update.")
    else:
        log(1, "This BIG-IP is HA STANDBY. Aborting O365 update.")
        sys.exit(0)


    # -----------------------------------------------------------------------
    # GUID management
    # -----------------------------------------------------------------------
    # Create guid file if not existent
    if not os.path.isdir(work_directory):
        os.mkdir(work_directory)
        log(1, "Created work directory " + work_directory + " because it did not exist.")
    if not os.path.exists(file_name_guid):
        f = open(file_name_guid, "w")
        f.write("\n")
        f.flush()
        f.close()
        log(1, "Created GUID file " + file_name_guid + " because it did not exist.")

    # Read guid from file and validate.  Create one if not existent
    f = open(file_name_guid, "r")
    f_content = f.readline()
    f.close()
    if re.match('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', f_content):
        guid = f_content
        log(2, "Valid GUID is read from local file " + file_name_guid + ".")
    else:
        guid = str(uuid.uuid4())
        f = open(file_name_guid, "w")
        f.write(guid)
        f.flush()
        f.close()
        log(1, "Generated a new GUID, and saved it to " + file_name_guid + ".")


    # -----------------------------------------------------------------------
    # O365 endpoints list version check
    # -----------------------------------------------------------------------
    # Read version of previously received record
    if os.path.isfile(file_ms_o365_version):
        f = open(file_ms_o365_version, "r")
        f_content = f.readline()
        f.close()
        # Check if the VERSION record format is valid
        if re.match('[0-9]{10}', f_content):
            ms_o365_version_previous = f_content
            log(2, "Valid previous VERSION found in " + file_ms_o365_version + ".")
        else:
            ms_o365_version_previous = "1970010200"
            f = open(file_ms_o365_version, "w")
            f.write(ms_o365_version_previous)
            f.flush()
            f.close()
            log(1, "Valid previous VERSION was not found.  Wrote dummy value in " + file_ms_o365_version + ".")
    else:
        ms_o365_version_previous = "1970010200"
        f = open(file_ms_o365_version, "w")
        f.write(ms_o365_version_previous)
        f.flush()
        f.close()
        log(1, "Valid previous VERSION was not found.  Wrote dummy value in " + file_ms_o365_version + ".")


    # -----------------------------------------------------------------------
    # O365 endpoints list VERSION check
    # -----------------------------------------------------------------------
    request_string = uri_ms_o365_version + guid
    conn = httplib.HTTPSConnection(url_ms_o365_version)
    conn.request('GET', request_string)
    res = conn.getresponse()

    if not res.status == 200:
        # MS O365 version request failed
        log(1, "VERSION request to MS web service failed.  Assuming VERSIONs did not match, and proceed.")
        dict_o365_version = {}
    else:
        # MS O365 version request succeeded
        log(2, "VERSION request to MS web service was successful.")
        dict_o365_version = json.loads(res.read())

    ms_o365_version_latest = ""
    for record in dict_o365_version:
        if record.has_key('instance'):
            if record["instance"] == customer_endpoint and record.has_key("latest"):
                latest = record["latest"]
                if re.match('[0-9]{10}', latest):
                    ms_o365_version_latest = latest
                    f = open(file_ms_o365_version, "w")
                    f.write(ms_o365_version_latest)
                    f.flush()
                    f.close()

    log(2, "Previous VERSION is " + ms_o365_version_previous)
    log(2, "Latest VERSION is " + ms_o365_version_latest)

    if ms_o365_version_latest == ms_o365_version_previous and force_o365_record_refresh == 0:
        log(1, "You already have the latest MS O365 URL/IP Address list: " + ms_o365_version_latest + ". Aborting operation.")
        sys.exit(0)


    # -----------------------------------------------------------------------
    # Request O365 endpoints list & put it in dictionary
    # -----------------------------------------------------------------------
    request_string = "/endpoints/" + customer_endpoint + "?ClientRequestId=" + guid
    conn = httplib.HTTPSConnection(url_ms_o365_endpoints)
    conn.request('GET', request_string)
    res = conn.getresponse()

    if not res.status == 200:
        log(1, "ENDPOINTS request to MS web service failed. Aborting operation.")
        sys.exit(0)
    else:
        log(2, "ENDPOINTS request to MS web service was successful.")
        dict_o365_all = json.loads(res.read())

    # Process for each record(id) of the endpoint JSON data
    for dict_o365_record in dict_o365_all:
        service_area = str(dict_o365_record['serviceArea'])
        category = str(dict_o365_record['category'])

        if (o365_categories == 0 and category == "Optimize") \
            or (o365_categories == 1 and (category == "Optimize" or category == "Allow")) \
            or (o365_categories == 2):
    
            if (only_required == 0) or (only_required and str(dict_o365_record['required']) == "True"):

                if (care_common and service_area == "Common") \
                    or (care_exchange and service_area == "Exchange") \
                    or (care_sharepoint and service_area == "SharePoint") \
                    or (care_skype and service_area == "Skype"):

                    if use_url:
                        # Append "urls" if existent in each record
                        if dict_o365_record.has_key('urls'):
                            list_urls = list(dict_o365_record['urls'])
                            for url in list_urls:
                                list_urls_to_exclude.append(url)

                        # Append "allowUrls" if existent in each record
                        if dict_o365_record.has_key('allowUrls'):
                            list_allow_urls = list(dict_o365_record['allowUrls'])
                            for url in list_allow_urls:
                                list_urls_to_exclude.append(url)

                        # Append "defaultUrls" if existent in each record
                        if dict_o365_record.has_key('defaultUrls'):
                            list_default_urls = dict_o365_record['defaultUrls']
                            for url in list_default_urls:
                                list_urls_to_exclude.append(url)

                    if use_ipv4 or use_ipv6:
                        # Append "ips" if existent in each record
                        if dict_o365_record.has_key('ips'):
                            list_ips = list(dict_o365_record['ips'])
                            for ip in list_ips:
                                if re.match('^.+:', ip):
                                    list_ipv6_to_exclude.append(ip)
                                else:
                                    list_ipv4_to_exclude.append(ip)

    log(1, "Number of unique ENDPOINTS to import...")

    # Add administratively defined URLs/IPs and (Re)process to remove duplicates and excluded values
    if use_url:
        # Combine lists and remove duplicate URLs
        urls_undup = list(set(list_urls_to_exclude + additional_urls))

        ## Remove set of excluded URLs from the list of collected URLs
        for x_url in noimport_urls:
            urls_undup = [x for x in urls_undup if not x.endswith(x_url)]
        
        log(1, "URL: " + str(len(urls_undup)))
            
    if use_ipv4:
        # Combine lists and remove duplicate IPv4 addresses
        ipv4_undup = list(set(list_ipv4_to_exclude + additional_ipv4))

        ## Remove set of excluded IPv4 addresses from the list of collected IPv4 addresses
        for x_ip in noimport_ips:
            ipv4_undup = [x for x in ipv4_undup if not x.endswith(x_ip)]

        log(1, "IPv4 host/net: " + str(len(ipv4_undup)))

    if use_ipv6:
        # Combine lists and duplicate IPv6 addresses
        ipv6_undup = list(set(list_ipv6_to_exclude + additional_ipv6))

        ## Remove set of excluded IPv6 addresses from the list of collected IPv6 addresses
        for x_ip in noimport_ips:
            ipv6_undup = [x for x in ipv6_undup if not x.endswith(x_ip)]

        log(1, "IPv6 host/net: " + str(len(ipv6_undup)))


    # -----------------------------------------------------------------------
    # URLs, IPv4 & IPv6 addresses formatted for TMSH
    # -----------------------------------------------------------------------
    if use_url:
        # Initialize the URL string
        url_exclude_list = ""

        # Write URLs to string    
        for url in urls_undup:
            url_exclude_list = url_exclude_list + " " + url.lower()

    if use_ipv4:
        # Initialize the IPv4 string
        ipv4_exclude_list = ""

        # Write IPv4 addresses to string
        for ip4 in (list(sorted(ipv4_undup))):
            ipv4_exclude_list = ipv4_exclude_list + "{subnet " + ip4 + " } "


    if use_ipv6:
        # Initialize the IPv6 string
        ipv6_exclude_list = ""

        # Write IPv6 addresses to string
        for ip6 in (list(sorted(ipv6_undup))):
            ipv6_exclude_list = ipv6_exclude_list + "{subnet " + ip6 + " } "

    # -----------------------------------------------------------------------
    # Load URL and/or IPv4 and/or IPv6 lists into Network Access resource
    # -----------------------------------------------------------------------
    if use_url:
        for na in na_lists:
            result = commands.getoutput("tmsh modify /apm resource network-access " + na + " address-space-exclude-dns-name replace-all-with { " + url_exclude_list + " }") 
            log(2, "Updated " + na + " with latest O365 URL list.")

    if use_ipv4:
        for na in na_lists:
            result = commands.getoutput("tmsh modify /apm resource network-access " + na + " address-space-exclude-subnet { " + ipv4_exclude_list + " }") 
            log(2, "Updated " + na + " with latest IPv4 O365 address list.")
 
    if use_ipv6:
        for na in na_lists:
            result = commands.getoutput("tmsh modify /apm resource network-access " + na + " ipv6-address-space-exclude-subnet { " + ipv6_exclude_list + " }")
            log(2, "Updated " + na + " with latest IPv6 O365 address list.")

    #-----------------------------------------------------------------------
    # Apply Access Policy and Initiate Config Sync: Device to Group
    #-----------------------------------------------------------------------

    for ap in access_profiles:
        result = commands.getoutput("tmsh modify /apm profile access " + ap + " generation-action increment")

    if ha_config == 1:
        log(1, "Initiating Config-Sync.")
        result = commands.getoutput("tmsh run cm config-sync to-group " + device_group_name)
        log(2, result + "\n")

    log(1, "Completed O365 URL/IP address update process.")

if __name__=='__main__':
    main()
