[![published](https://static.production.devnetcloud.com/codeexchange/assets/images/devnet-published.svg)](https://developer.cisco.com/codeexchange/github/repo/ecoen66/merakicat)
# ![merakicat](https://github.com/ecoen66/merakicat/raw/main/images/merakicat.png) merakicat

This package makes migrating [Cisco](https://www.cisco.com) Catalyst switches to [Meraki](https:www.meraki.com) Dashboard much easier. #merakicat
 
![merakicat](https://github.com/ecoen66/merakicat/raw/main/images/mc_quick.gif)
 
This Python app can be run in Webex Teams [Bot mode](#Bot) or in [command-line mode](#command-line).  It can also be called from shell scripts for [bulk-mode](#bulk-mode).

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

1. Click **Create a New App**

    ![add-app](https://github.com/ecoen66/merakicat/raw/main/images/newapp.jpg)

1. Click **Create a Bot**.

    ![create-bot](https://github.com/ecoen66/merakicat/raw/main/images/createbot.jpg)

2. Fill out all the details about your Bot.  You'll need to set a name, username, icon (either upload one or choose a sample), and provide a description.

    ![add-bot](https://github.com/ecoen66/merakicat/raw/main/images/newbot.jpg)

3. Click **Add Bot**.

1. On the Congratulations screen, make sure to copy the *Bot's Access Token*, you will need this in a second.

    ![enter-details](https://github.com/ecoen66/merakicat/raw/main/images/botcongrats.jpg)

# Installation

> Python 3.11+ is recommended.

 - Clone the github repository and install the requirements

```
git clone https://github.com/ecoen66/merakicat
cd merakicat
pip install -r requirements_dev.txt
```

# Usage

 - The easiest way to use this module is to set a few environment variables

    > Note: As an alternative, you may edit the variables in mc_user_info.py.  Although more convenient, it is less secure.

    > Note: See [ngrok](#ngrok) for details on setting up an easy HTTP tunnel for webhooks callbacks for Bot mode.

    ```
    # These exports are used for Webex bot mode:
    export NGROK_AUTHTOKEN=<your ngrok Authtoken>
    export TEAMS_BOT_TOKEN=<your bot's token>
    export TEAMS_BOT_EMAIL=<your bot's email>
    export TEAMS_BOT_APP_NAME=<your bot's name>
    export TEAMS_EMAILS=<a comma delimited list of email addresses the bot will respond to>
    
    # These exports are required regardless of mode:
    export IOS_USERNAME=<the ssh username for the Catalyst switches>
    export IOS_PASSWORD=<the ssh password for the Catalyst switches>
    export IOS_SECRET=<the CLI secret password for the Catalyst switches>
    export IOS_PORT=<the ssh port number for the Catalyst switches - usually 22>
    export MERAKI_API_KEY=<your meraki dashboard API key>
    ```
In addition to these settings, various debugs and a choice of PDF vs. DOCX report format can be enabled in the mc_user_info.py file.

    > Note: For PDF report generation, MS Word must be installed on the host with merakicat.

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
Check the configs of cloud monitored Catalyst switches for both translatable and possible Meraki features:
```
cd src/merakicat
python merakicat.py check network <Meraki network name> [with timing] [with details]
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


# Bulk-mode

To run merakicat in bulk-mode, create a shell script to call merakicat in command line mode.  Example scripts included in the repo are:

Generate Check config reports for a list of Catalyst switches, 20 switches at a time, until the entire list is exhausted. The list is provided in an input file, one hostname/fqdn/IP address per line:
```
cd src/merakicat
bulk_check.sh <input file>
```
Migrate a list of Catalyst switches to a Meraki network, 20 switches at a time, until the entire list is exhausted. The list is provided in an input file, one hostname/fqdn/IP address per line:
```
cd src/merakicat
bulk_migrate.sh <input file> <Meraki network name>
```


# ngrok

[ngrok](http://ngrok.com) will make it easy for you to interact with merakicat as a bot.

You can find account instructions here under `Sign up for free!`: [https://dashboard.ngrok.com/login](https://dashboard.ngrok.com/login)

1. After you've created an `ngrok` account, you will need to get your Authtoken.  Click on `Your Authtoken` on the ngrok dashboard and copy it.


1. You can now export it to the OS environment variables like this:

    ```
    export NGROK_AUTHTOKEN=<your ngrok Authtoken>
    ```

1. Now launch the bot!!

    ```
    python merakicat.py
    ```

# Credits
**This project is _heavily_ based on the work of others:**

`Catalyst_to_Meraki_Migration_Tool` by [Fady Sharobeem](https://github.com/fadysharobeem).

`Catalyst_2_Meraki_Config_Checker` by [Fady Sharobeem](https://github.com/fadysharobeem).

The bot functionality is based on the `webexteamsbot` project by [Hank Preston](https://github.com/hpreston).

The initial packaging of the original `ciscosparkbot` project was done by [Kevin Corbin](https://github.com/kecorbin).

