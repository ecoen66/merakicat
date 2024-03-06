# merakicat

You will need to copy src/user_sample.py to src/mc_user_info.py in order to use this app.

# The rest of this file needs to be replaced!




This package makes migrating [Cisco](https://www.cisco.com) Catalyst switches to [Meraki](https:www.meraki.com) Dashboard super simple.  


# Prerequisites

If you don't already have a [Webex Teams](https://www.webex.com/products/teams/index.html) account, go ahead and [register](https://www.webex.com/pricing/free-trial.html) for one.  They are free.

1. You'll need to start by adding your bot to the Webex Teams website.

    [https://developer.webex.com/my-apps](https://developer.webex.com/my-apps)

1. Click **Create a New App**

    ![add-app](https://github.com/ecoen66/merakicat/raw/main/images/newapp.jpg)

1. Click **Create a Bot**.

    ![create-bot](https://github.com/ecoen66/merakicat/raw/main/images/createbot.jpg)

2. Fill out all the details about your bot.  You'll need to set a name, username, icon (either upload one or choose a sample), and provide a description.

    ![add-bot](https://github.com/ecoen66/merakicat/raw/main/images/newbot.jpg)

3. Click **Add Bot**.

1. On the Congratulations screen, make sure to copy the *Bot's Access Token*, you will need this in a second.

    ![enter-details](https://github.com/ecoen66/merakicat/raw/main/images/botcongrats.jpg)

# Installation

> Python 3.11+ is recommended.

1. Create a virtualenv and install the module

    ```
    python3.11 -m venv venv
    source venv/bin/activate
    pip install webexteamsbot
    ```

# Usage

1. The easiest way to use this module is to set a few environment variables

    > Note: As an alternative, you may rename mc_user_sample.py to mc_user_info.py and edit the variables there.  Although more convenient, it is considered less secure.

    > Note: See [ngrok](#ngrok) for details on setting up an easy HTTP tunnel for webhooks callbacks.

    ```
    export TEAMS_BOT_URL=https://mypublicsite.io (if using ngrok, use the Forwarding URL it provides)
    export TEAMS_BOT_TOKEN=<your bots token>
    export TEAMS_BOT_EMAIL=<your bots email>
    export TEAMS_BOT_APP_NAME=<your bots name>
    export TEAMS_EMAILS=<a comma delimited list of email addresses the bot will respond to>
    export IOS_USERNAME=<the ssh username for the Catalyst switches>
    export IOS_PASSWORD=<the ssh password for the Catalyst switches>
    export IOS_SECRET=<the CLI secret password for the Catalyst switches>
    export IOS_PORT=<the ssh port number for the Catalyst switches - usually 22>
    export MERAKI_API_KEY=<your meraki dashboard API key>
    ```

1. This app can be run either as a Webex Teams bot or as a standalone command line program.  To run it as a bot, just start it without any parameters:  

    ```cd src
    python3.11 merakicat.py
    ```
    Bot commands include the following:

    Check a Catalyst switch config for Meraki compatible settings using a card:
    ```/check
    ```

    Translate a Catalyst switch config to a Meraki switch with translatable settings using a card:
    ```/translate
    ```

    Check a Catalyst switch config for both translatable and possible Meraki features:
    ```check [host _FQDN or IP address_ | file _filespec_]
    ```

    Translate a Catalyst switch config from a file or host to claimed Meraki serial numbers:
    ```translate [host _FQDN or IP address_ | file _filespec_] [to _Meraki serial numbers_]
    ```

    Migrate a Catalyst switch to a Meraki switch - register, claim & translate:
    migrate [host _FQDN or IP address_] [to _Meraki network name_]
    Register a Catalyst switch to the Meraki Dashboard:
    register [host _FQDN or IP address_]
    Claim Catalyst switches to a Meraki Network:
    claim [_Meraki serial numbers_] [to _Meraki network name_]


1. To run it from the command line (or from a shell script), enter any of the following:

    Check a Catalyst switch config for both translatable and possible Meraki features:
    ```check host <FQDN or IP address> | file <filespec> 
    ```
    Register a Catalyst switch to the Meraki Dashboard
    ```register host <FQDN or IP address>
    ```
    Claim Catalyst switches to a Meraki Network
    ```claim <Meraki serial numbers> to <Meraki network name>
    ```
    Translate a Catalyst switch config from a file or host to claimed Meraki serial numbers
    ```translate host <FQDN or IP address> | file <filespec> to <Meraki serial numbers>
    ```
    Migrate a Catalyst switch to a Meraki switch - register, claim & translate"]
    ```migrate host <FQDN or IP address> to <Meraki network name>
    ```


# ngrok

[ngrok](http://ngrok.com) will make easy for you to develop your code with a live bot.

You can find installation instructions here: [https://ngrok.com/download](https://ngrok.com/download)

1. After you've installed `ngrok`, in another window start the service

    ```
    ngrok http 5000
    ```

1. You should see a screen that looks like this:

    ```
    ngrok by @inconshreveable                                                                                                                                 (Ctrl+C to quit)

    Session Status                online
    Version                       2.2.4
    Region                        United States (us)
    Web Interface                 http://127.0.0.1:4040
    Forwarding                    http://this.is.the.url.you.need -> localhost:5000
    Forwarding                    https://this.is.the.url.you.need -> localhost:5000

    Connections                   ttl     opn     rt1     rt5     p50     p90
                                  2       0       0.00    0.00    0.77    1.16

    HTTP Requests
    -------------

    POST /                         200 OK
    ```

1. Make sure and update your environment with this url:

    ```
    export TEAMS_BOT_URL=https://this.is.the.url.you.need

    ```

1. Now launch your bot!!

    ```
    python sample.py
    ```

## Local Development

If you have an idea for a feature you would like to see, we gladly accept pull requests.  To get started developing, simply run the following..

```
git clone https://github.com/ecoen66/merakicat
cd merakicat
pip install -r requirements_dev.txt
cd src
python3.11 merakicat.py
```

# Credits
The initial packaging of the original `ciscosparkbot` project was done by [Kevin Corbin](https://github.com/kecorbin).  

