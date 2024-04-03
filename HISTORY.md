# History

## 0.1.8 (04-03-2024)

  - Edited README.
  - Renamed mc_user_sample.py to mc_user_info.py and commented out possible environment variables.
  - Added logic to merakicat.py to handle missing variables on import from mc_user_info.py.

## 0.1.7 (04-01-2024)

  - Added the ability to Check the configs of cloud monitored Catalyst switches for both translatable and possible Meraki features.
  - Included "with timing" and "with details" options on check drag-n-drop.
  - Renamed some called functions in external modules.

## 0.1.6 (03-26-2024)

  - Updated encyclopedia.
  - Migrated batch helper code for cleaner installation.

## 0.1.5 (03-23-2024)

  - Supports NM ports.
  - Merged nm-specifics into the encyclopedia.

## 0.1.4 (03-21-2024)

  - Downloads a fresh copy of the encyclopedia from my repo if the local copy is over 24 hours old.

## 0.1.3 (03-21-2024)

  - Code beautification with flake8.
  - Setting up for publishing automation.
  - Changed directory structure for publishing.
  - Released on PyPI.
  
## 0.0.14 (03-19-2024)

  - Option added for check with drag and drop files in bot mode.
  - Added missing timing in check report in bot mode.
  - Still not yet released on PyPI.
  
## 0.0.13 (03-18-2024)

  - Option added for detailed check report "with detail".
  
## 0.0.12 (03-15-2024)

  - Option for PDF vs. DOCX reporting in checker.
  - Layer 3 Interfaces (interface VLAN) supported.
  - Static routes supported.
  - Command added for "demo report".
  
## 0.0.11 (03-12-2024)

  - New reporting in checker.
  - Port-channel LACP is working and fast.
  
## 0.0.10 (03-08-2024)

  - Using a single mc_pedia.
  
## 0.0.9 (03-07-2024)

  - Using both config_pedia and check_pedia.
  - Changed to ngrok API for bot functionality
  
## 0.0.8 (03-01-2024)

  - Lots of comment blocks added.
  
## 0.0.7 (03-01-2024)

  - Now using batch port updates to Meraki dashboard.
  
## 0.0.6 (03-01-2024)

  - Some light refactoring of mc_translate module.
  - More prep work for Uplink config.

## 0.0.5 (02-29-2024)

  - Added Catalyst NM module recognition and prep work for Uplink config.

## 0.0.4 (02-28-2024)

  - Removed external data fetch for list of unsupported features in prep for adding display of features that are semi-supported.
  - Added command line help **python merakicat.py help**.

## 0.0.3 (02-27-2024)

  - Created command line option vs BOT.
  - Just try **python merakicat.py convert host <host or ip address> to <meraki network>**.

## 0.0.2 (02-26-2024)

  - Not yet released on PyPI.

## 0.0.1 (02-26-2024)

