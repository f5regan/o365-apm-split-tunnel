# Changelog
## [1.1] - 2020-04-01
Modified script parameters to default to Microsoft's recommended practices for O365 & Split Tunnel VPN as documented at https://docs.microsoft.com/en-us/office365/enterprise/office-365-vpn-split-tunnel

* Disabled URL fetching by default (use_url - 0)
* Added support for "category" element - see "o365_categories" in Appendix for usage guidelines
* Set default "category" to "Optimize" (o365_categories = 0)
* Removed unused variables: failover_state, id

## [1.0] - 2020-03-18
Initial version of APM Split Tunnel script published