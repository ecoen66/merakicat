![published](https://static.production.devnetcloud.com/codeexchange/assets/images/devnet-published.svg)

# ![merakicat](https://github.com/ecoen66/merakicat/raw/main/images/merakicat.png) merakicat

This package makes migrating [Cisco](https://www.cisco.com) Catalyst switches to [Meraki](https:www.meraki.com) Dashboard much easier. #merakicat

![merakicat](https://github.com/ecoen66/merakicat/raw/main/images/mc_quick.gif)

This Python app can be run in Webex Teams [Bot mode](#Bot) or in [command-line mode](#command-line).  

Below is the list of configurations the tool can currently translate:

switch:

- Hostname
- Spanning Tree RSTP
- Stack
- Static Routing

port:

- Port Description
- Port Status
- Port Speed
- Port Duplex
- Port Type
- PoE Enabled
- Allowed VLANs
- Data VLAN
- Voice VLAN
- Private VLAN
- Layer 3 Interface
- STP RootGuard
- STP Loop Guard
- STP BPDU Guard
- Etherchannel LACP
- NM Ports

Once installed, you can print the entire index of the feature encyclopedia, or to print the index based on either supported and translatable items or both, enter:

```
cd src/merakicat
python mc_pedia [support] [translatable]
```



# Prerequisites for using in Bot mode

If you don't already have a [Webex Teams](https://www.webex.com/products/teams/index.html) account, go ahead and [register](https://www.webex.com/pricing/free-trial.html) for one.  They are free.

1. You'll need to start by adding your Bot to the Webex Teams website.
  [https://developer.webex.com/my-apps](https://developer.webex.com/my-apps)
2. Click **Create a New App**
  ![add-app](https://github.com/ecoen66/merakicat/raw/main/images/newapp.jpg)
3. Click **Create a Bot**.
  ![create-bot](https://github.com/ecoen66/merakicat/raw/main/images/createbot.jpg)
4. Fill out all the details about your Bot.  You'll need to set a name, username, icon (either upload one or choose a sample), and provide a description.
  ![add-bot](https://github.com/ecoen66/merakicat/raw/main/images/newbot.jpg)
5. Click **Add Bot**.
6. On the Congratulations screen, make sure to copy the *Bot's Access Token*, you will need this in a second.
  ![enter-details](https://github.com/ecoen66/merakicat/raw/main/images/botcongrats.jpg)



# Installation

> Python 3.11 is recommended.

- Clone the github repository and install the requirements

```
git clone https://github.com/ecoen66/merakicat
cd merakicat
pip install -r requirements_dev.txt
```



# Usage

- The easiest way to use this module is to set a few environment variables
- You can also put the same `KEY=value` entries in a `.env` file (see `.env.example`).
  > Note: As an alternative, you may edit the variables in mc_user_info.py.  Although more convenient, it is less secure.

In addition to these settings, various debugs and a choice of PDF vs. DOCX report format can be enabled in the mc_user_info.py file.

```
> Note: For PDF report generation, MS Word must be installed on the host with merakicat.
```



# Bot

To run merakicat as a Bot, just start it without any parameters:

```
cd src/merakicat
python merakicat.py
```

**Bot commands include the following:**

Check a Catalyst switch config for both translatable and possible Meraki features:

```
check [host <FQDN or IP address> | file <filespec>] [with timing] [with details]
```

Check one or more Catalyst switch config files for both translatable and possible Meraki features:

```
check <drag-and-drop files> [with timing] [with details]
```

Check the configs of cloud monitored Catalyst switches for both translatable and possible Meraki features:

```
check network <Meraki network name> [with timing] [with details]
```

Register a Catalyst switch to the Meraki Dashboard:

```
register [host <FQDN or IP address>] [with timing]
```

Claim Catalyst switches to a Meraki Network:

```
claim [<Meraki serial numbers>] [to <Meraki network name>] [with timing]
```

Translate a Catalyst switch config from a file or host to claimed Meraki serial numbers:

```
translate [host <FQDN or IP address> | file <filespec>] [to <Meraki serial numbers>] [with timing]
```

Migrate a Catalyst switch to a Meraki switch - register, claim & translate:

```
migrate [host <FQDN or IP address>] [to <Meraki network name>] [with timing]
```

List all Meraki networks in the configured organization:

```
get networks
```

Create a demo report for all features currently in the feature encyclopedia:

```
demo report
```



# Command-line

To run merakicat from the command-line (or from a shell script), enter any of the following:

Check a Catalyst switch config for both translatable and possible Meraki features:

```
cd src/merakicat
python merakicat.py check host <FQDN or IP address> | file <filespec> [with timing] [with details]
```

Check a list of switches specified in a CSV or Excel file (use `hosts_template.xlsx` as a template):

```
cd src/merakicat
check hosts <filespec> [with timing]
```

Check the configs of cloud monitored Catalyst switches for both translatable and possible Meraki features:

```
cd src/merakicat
python merakicat.py check network <Meraki network name> [with timing] [with details]
```

Get the Cloud ID for a Catalyst switch:

```
cd src/merakicat
python merakicat.py get cloud-id <FQDN or IP address> [with timing]
```

Get Cloud IDs for hosts listed in a CSV or Excel file (use `hosts_template.xlsx` as a template):

```
cd src/merakicat
python merakicat.py get cloud-ids <filespec> [with timing]
```

List all Meraki networks in the configured organization:

```
cd src/merakicat
python merakicat.py get networks
```

Register a Catalyst switch or stack to the Meraki Dashboard:

```
cd src/merakicat
python merakicat.py register host <FQDN or IP address> [with timing]
```

Claim Catalyst switches to a Meraki Network:

```
cd src/merakicat
python merakicat.py claim <Meraki serial numbers> to <Meraki network name> [with timing]
```

Translate a Catalyst switch or stack config from a file or host to claimed Meraki serial numbers:

```
cd src/merakicat
python merakicat.py translate host <FQDN or IP address> | file <filespec> to <Meraki serial numbers> [with timing]
```

Migrate a Catalyst switch to a Meraki switch - register, claim & translate:

```
cd src/merakicat
python merakicat.py migrate host <FQDN or IP address> to <Meraki network name> [with timing]
```

Create a demo report for all features currently in the feature encyclopedia:

```
cd src/merakicat
python merakicat.py demo report
```

Upgrade IOS software (see [IOS software upgrades](#ios-software-upgrades)):

```
cd src/merakicat
python merakicat.py upgrade host <FQDN or IP address> [<url>] [-y] [--allow-downgrade] [--ios-software <directory>]
```

Upgrade IOS software on hosts listed in a CSV or Excel file (use `hosts_template.xlsx` as a template; see [IOS software upgrades](#ios-software-upgrades)):

```
cd src/merakicat
python merakicat.py upgrade hosts <filespec> [<url>] [-y] [--allow-downgrade] [--ios-software <directory>]
```

`-y` skips the confirmation prompt (the software URL is then required). `--allow-downgrade` permits installing an older version than the switch is currently running. `--ios-software <directory>` selects the local directory of IOS images. When omitted, merakicat looks for an `ios-software` directory in the working directory and at the repository root.

# Parallel bulk operations

`check hosts`, `get cloud-ids`, and `upgrade hosts` contact switches in parallel. The worker limit is `DEFAULT_PARALLEL_MAX_WORKERS` in `src/merakicat/mc_constants.py` (currently 20). The pool size is the smaller of that value and the number of hosts in the file. Change the constant to raise or lower how many switches are contacted at once.

# IOS software upgrades

Before using `upgrade host` or `upgrade hosts`, place the Catalyst IOS XE images in the `ios-software` directory at the repo root, in the subdirectory that matches each platform:


| Platform                               | Directory                  |
| -------------------------------------- | -------------------------- |
| Catalyst 9300 / 9500 (and other Cat9K) | `ios-software/cat9k/`      |
| Catalyst 9200 (`cat9k_lite`)           | `ios-software/cat9k_lite/` |
| IE-35XX                                | `ios-software/ie35xx/`     |


Put at most one `.bin` image in each platform directory (`cat9k/`, `cat9k_lite/`, and `ie35xx/`). 

To use a directory that is not in the default location, use the optional `--ios-software` parameter:

```
python merakicat.py upgrade host <FQDN or IP address> --ios-software <directory>
```

The switches download those images over the network. You must serve the `ios-software` directory from **the same host that runs** `merakicat.py` for the upgrades. From the `ios-software` directory (or the directory given with `--ios-software`), start the included HTTP server (no virtual environment needed; the script uses only Python built-in modules):

```
cd ios-software
python3 http-server.py
```

Then pass that server’s base URL to the upgrade command (for example `http://<this-host>:8000/`). If you omit the URL and do not use `-y`, merakicat will prompt for it. The URL must point at this host’s `ios-software` content — the default directory, or the directory passed with `--ios-software` — so the switches can fetch the same images merakicat selected locally.

# Donations

If you found this repo to be useful, please consider donating to Life Decisions, Rockford, IL through a purchase from the [Merakicat store](https://bonfire.com/store/merakicat).

# Credits

**This project is *heavily* based on the work of others:**

`Catalyst_to_Meraki_Migration_Tool` by [Fady Sharobeem](https://github.com/fadysharobeem).

`Catalyst_2_Meraki_Config_Checker` by [Fady Sharobeem](https://github.com/fadysharobeem).

The bot functionality is using `webex_bot` by [Finbarr Brady](https://github.com/fbradyirl).