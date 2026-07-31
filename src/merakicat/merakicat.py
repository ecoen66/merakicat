#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Meraki Cat webexteamsbot is a chat bot with a swiss army knife
of functions for checking & translating Catalyst IOSXE to Meraki
switch configs, registering Catalyst switches to Dashboard and
claiming them.  It can also be run from the command line or in
batch from a shell script.


Please excuse the code, I need to refactor it -- badly.
"""

import json
import os
import re
import shutil
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import datetime
from functools import reduce
from importlib import import_module
from itertools import islice
from typing import Literal
from urllib.error import HTTPError, URLError

import docx
import docx.opc.constants
import docx.oxml
import meraki
import meraki.exceptions
import requests
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches
from docx2pdf import convert
from mc_cfg_check import CheckFeatures
from mc_claim import Claim
from mc_cloud_id import (
    extract_cloud_ids_for_dashboard_paste,
    format_cloud_id_lookup_msg,
    format_get_cloud_id_msg,
    get_cloud_ids_for_host,
    write_cloud_ids_log,
)
from mc_cloud_mon import CloudSwitch
from mc_config import (
    IOS_PASSWORD,
    IOS_PORT,
    IOS_SECRET,
    IOS_USERNAME,
    MERAKI_API_KEY,
    MERAKI_ORG_NAME,
    TEAMS_BOT_APP_NAME,
    TEAMS_BOT_EMAIL,
    TEAMS_BOT_TOKEN,
    TEAMS_EMAILS,
    validate,
)
from mc_constants import DEFAULT_FILES_FOLDER, REPO_API_URL, REPO_RAW_URL, VERSION
from mc_file_exists import FileExists
from mc_get_config import GetConfig
from mc_get_networks import get_networks
from mc_get_nms import GetNmList
from mc_hostnames_file import load_hostnames_from_file
from mc_inventory import get_switch_inventory_by_mac
from mc_meraki_dry_run import (
    apply_dry_run_session,
    meraki_requests_request,
    set_meraki_dry_run,
)
from mc_parallel import run_parallel_indexed
from mc_ping import Ping
from mc_register import Register
from mc_splitcheck_serials import SplitCheckSerials
from mc_translate import Evaluate, MerakiConfig
from mc_utils import check_host_minimum_ios
from netmiko.exceptions import ConnectionException, NetmikoTimeoutException
from paramiko.ssh_exception import AuthenticationException
from tabulate import tabulate
from webex_bot.models.command import Command
from webex_bot.models.response import Response
from webex_bot.webex_bot import WebexBot

# Populated by initialize_merakicat() from main().
MERAKI_DRY_RUN = False
FORCE_PEDIA_REFRESH = False
DEBUG = False
DEBUG_MAIN = False
PDF = False
debug = False
mc_pedia = {}
BOT = False
ios_username = ""
ios_password = ""
ios_secret = ""
ios_port = 22
meraki_api_key = ""
meraki_org_name = ""
bot = None
bot_commands = []
command_list = []
payload = None
organizations = {}
api = ""
configured_ports = defaultdict(list)
unconfigured_ports = defaultdict(list)
unified_os = False
command_line_msg = Response()
times = False
report = False
detailed = False
config_file = ""
host_id = ""
nm_list = []
meraki_serials = []
meraki_orgs = []
meraki_networks = []
meraki_org = ""
meraki_net = ""
meraki_net_name = ""
meraki_urls = []
bot_email = ""
bot_app_name = ""
teams_token = ""
teams_emails = []
bot_fname = ""


class RunCheck(Command):
    def __init__(self, dashboard_api):
        self.dashboard_api = dashboard_api
        super().__init__(
            command_keyword="check",
            help_message="Check a Catalyst switch config for both translatable and possible \
Meraki features",
            delete_previous_message=True,
        )

    def execute(self, message, attachment_actions, activity):
        return greeting(attachment_actions, self.dashboard_api)


class RunRegister(Command):
    def __init__(self, dashboard_api):
        self.dashboard_api = dashboard_api
        super().__init__(
            command_keyword="register",
            help_message="Register a Catalyst switch to the Meraki Dashboard",
            delete_previous_message=True,
        )

    def execute(self, message, attachment_actions, activity):
        return greeting(attachment_actions, self.dashboard_api)


class RunClaim(Command):
    def __init__(self, dashboard_api):
        self.dashboard_api = dashboard_api
        super().__init__(
            command_keyword="claim",
            help_message="Claim Catalyst switches to a Meraki Network",
            delete_previous_message=True,
        )

    def execute(self, message, attachment_actions, activity):
        return greeting(attachment_actions, self.dashboard_api)


class RunTranslate(Command):
    def __init__(self, dashboard_api):
        self.dashboard_api = dashboard_api
        super().__init__(
            command_keyword="translate",
            help_message="Translate a Catalyst switch config from a file or \
host to claimed Meraki serial numbers",
            delete_previous_message=True,
        )

    def execute(self, message, attachment_actions, activity):
        return greeting(attachment_actions, self.dashboard_api)


class RunMigrate(Command):
    def __init__(self, dashboard_api):
        self.dashboard_api = dashboard_api
        super().__init__(
            command_keyword="migrate",
            help_message="Migrate a Catalyst switch to a Meraki switch - \
register, claim & translate",
            delete_previous_message=True,
        )

    def execute(self, message, attachment_actions, activity):
        return greeting(attachment_actions, self.dashboard_api)


class RunDemo(Command):
    def __init__(self, dashboard_api):
        self.dashboard_api = dashboard_api
        super().__init__(
            command_keyword="demo",
            help_message="Create a demo report for all features currently in \
the feature encyclopedia",
            delete_previous_message=True,
        )

    def execute(self, message, attachment_actions, activity):
        return greeting(attachment_actions, self.dashboard_api)


class RunHelp(Command):
    def __init__(self, dashboard_api):
        self.dashboard_api = dashboard_api
        super().__init__(
            command_keyword="help|?",
            help_message="Get help",
            delete_previous_message=True,
        )

    def execute(self, message, attachment_actions, activity):
        return greeting(attachment_actions, self.dashboard_api)


class RunHello(Command):
    def __init__(self, dashboard_api):
        self.dashboard_api = dashboard_api
        super().__init__(
            command_keyword="hello|hi",
            help_message="Say hello",
            delete_previous_message=True,
        )

    def execute(self, message, attachment_actions, activity):
        return greeting(attachment_actions, self.dashboard_api)


# The greeting processes user input before calling the correct command.
# The default behavior of the bot is to return the 'help' command response
# If there is an English language command line, try to work with that.


def greeting(incoming_msg, dashboard: meraki.DashboardAPI | None):

    global config_file, host_id, meraki_net, meraki_net_name
    global meraki_serials, times, report, detailed

    if debug:
        print(f"incoming_msg = {incoming_msg}")

    # Create a Response object to later craft a reply in Markdown.
    response = Response()

    # This will be our copy of the user input to work with
    user_text = incoming_msg.text
    user_roomId = incoming_msg.roomId
    user_files = list()
    user_files = incoming_msg.files

    # Grab the first word from the user's input.
    command = user_text.split()[0].lower()

    if BOT:
        # If first word from the user's input was Bot's first name, remove it
        if user_text.split()[0] == bot_fname:
            user_text = user_text.split(bot_fname + " ", 1)[1]

    if debug:
        print(f"user_text = {user_text}")
        print(f"command = {command}")

    # If the user asked for timing, we will try to give it to them
    times = False
    regex = r"\swith\stimings|\swith\stiming|\swith\stime|\swith\stimes"
    if re.search(regex, user_text, re.IGNORECASE) is not None:
        user_text = re.sub(regex, "", user_text, re.IGNORECASE)
        times = True

    # If the user asked for detailed reports, we will try to give it to them
    detailed = False
    regex = r"\swith\sdetails|\swith\sdetail"
    if re.search(regex, user_text, re.IGNORECASE) is not None:
        user_text = re.sub(regex, "", user_text, re.IGNORECASE)
        detailed = True

    # If the command is 'check' and the user attached any config files to
    # the bot message, we will try to use them
    if user_text.lower() == "check" and (user_files is not None):
        x = 0
        while x < len(user_files):
            config_file = save(user_files[x])
            response.markdown = check_switch(
                incoming_msg,
                config=config_file,
                report_label=os.path.basename(config_file),
            )
            create_message(user_roomId, response.markdown, style="html")
            x += 1
        return

    # If the user asked for a report, we will try to give it to them
    if user_text.lower().startswith("check network "):
        # Now let's see if they specified target models...
        targets = ["C9300"]
        regex = re.compile(r"\s*target\s *|\s*targets\s *", flags=re.I)
        if len(regex.split(user_text)) > 1:
            if not regex.split(user_text)[1] == "":
                maybe_targets = regex.split(user_text)[1]
                user_text = regex.split(user_text)[0].strip()
                if re.search(",", maybe_targets, re.IGNORECASE) is not None:
                    maybe_targets = maybe_targets.replace(" ", "")
                if debug:
                    print(f"maybe_targets = {maybe_targets}")
                if not len(maybe_targets) == 0:
                    targets = re.split(r";|,|\s", maybe_targets)
                    if debug:
                        print(
                            f"regex.split(user_text)[0] = {regex.split(user_text)[0]}"
                        )
        if debug:
            print(f"targets = {targets}")
        # Did they enter a network name after "network"?
        dest_net = meraki_net
        regex = re.compile(r"\s*network\s *", flags=re.I)
        if not regex.split(user_text)[1] == "":
            # They did, so register it!
            dest_net_name = regex.split(user_text)[1]
            dest_net = ""
            test = [d["id"] for d in meraki_networks if d["name"] == dest_net_name]
            if not len(test) == 0:
                dest_net = test[0]
                meraki_net_name = dest_net_name
            if dest_net == "":
                r = "I'm sorry, but {} is ".format(dest_net_name)
                r += "not in your list of Meraki networks."
                response.markdown = r
            else:
                if debug:
                    print(f"dest_net = {dest_net}")
        if dest_net == "":
            r = "You need to enter a Meraki network to register into."
            response.markdown = r
        else:
            response.markdown = check_network(incoming_msg, dest_net, dashboard, targets=targets)

    # If the user asked for a report, we will try to give it to them
    report = False
    regex = r"\swith\sreports|\swith\sreports|\swith\sreporting"
    if re.search(regex, user_text, re.IGNORECASE) is not None:
        user_text = re.sub(regex, "", user_text, re.IGNORECASE)
        report = True

    serials = list()

    # Test if it is equivalent to a command.
    match command:
        case "cloud":
            # If the only thing the user typed was "cloud"...
            if user_text.lower() == "cloud":
                if host_id == "":
                    # Just missing the host
                    r = "I'm sorry, but I don't have a host "
                    r += "that we are working with."
                    response.markdown = r
                else:
                    # We did, so mess with it!
                    response.markdown = cloud_switch(incoming_msg, dashboard, host=host_id)
            elif not len(user_text.split()) >= 3:
                r = "Syntax is **cloud (host <_fqdn or ip address_>**"
                response.markdown = r
            # Well, did they type "cloud host" ?
            elif re.search("host ", user_text, re.IGNORECASE):
                if not user_text.lower().split("host ", 1)[1] == "":
                    host_id = user_text.lower().split("host ", 1)[1]
                    if debug:
                        print(f"Ping({host_id}) = {Ping(host_id)}")
                    if not Ping(host_id):
                        r = "I was unable to ping that host."
                        response.markdown = r
                        return response
                    if BOT:
                        response.html = cloud_switch(incoming_msg, dashboard, host=host_id)
                    else:
                        response.markdown = cloud_switch(incoming_msg, dashboard, host=host_id)
                else:
                    r = "I'm sorry, but I don't have a host that we are "
                    r += "working with."
                    response.markdown = r
            else:
                r = "Syntax is **check (host <_fqdn or ip address_>**"
                response.markdown = r

        case "demo":
            # If the only thing the user typed was "demo report""...
            if user_text.lower() == "demo report":
                # It was so check it!
                print("should be calling check_switch with demo")
                response.markdown = check_switch(incoming_msg, demo=True)
                if BOT:
                    print(f"response.markdown={response.markdown}")
                    create_message(user_roomId, response.markdown, style="html")
                    return

            else:
                # It was not...?!
                response.markdown = "I'm sorry, but I don't know what "
                response.markdown += "you mean."

        case "migrate":
            # If the only thing the user typed was "migrate"...
            if user_text.lower() == "migrate":
                # Check and see if we have a global stateful
                # host and network to work with
                if host_id == "" and meraki_net == "":
                    # We did not...
                    r = "I'm sorry, but I don't have a host "
                    r += "or a Network that we are working with."
                    response.markdown = r
                elif host_id == "":
                    # Just missing the host
                    r = "I'm sorry, but I don't have a host "
                    r += "that we are working with."
                    response.markdown = r
                elif meraki_net == "":
                    # Just missing the Network
                    r = "I'm sorry, but I don't have a Network "
                    r += "that we are working with."
                    response.markdown = r
                else:
                    # We did, so migrate it!
                    response.markdown = migrate_switch(
                        incoming_msg, dashboard, host=host_id, dest_net=meraki_net
                    )

            # Well, did they type more after "migrate" ?
            elif user_text.lower().startswith("migrate"):
                dest_net = meraki_net
                # Did they enter a network name after "to"?
                if re.search("to ", user_text, re.IGNORECASE):
                    regex = re.compile(r"\s*to\s *", flags=re.I)
                    if not regex.split(user_text)[1] == "":
                        # They did, so register it!
                        dest_net_name = regex.split(user_text)[1]
                        dest_net = ""
                        test = [
                            d["id"]
                            for d in meraki_networks
                            if d["name"] == dest_net_name
                        ]
                        if not len(test) == 0:
                            dest_net = test[0]
                            meraki_net_name = dest_net_name
                        if dest_net == "":
                            r = "I'm sorry, but {} is ".format(dest_net_name)
                            r += "not in your list of Meraki networks."
                            response.markdown = r
                        else:
                            if debug:
                                print(f"dest_net = {dest_net}")
                if dest_net == "":
                    r = "You need to enter a Meraki network to register into."
                    response.markdown = r
                host = host_id
                # Did they type "migrate host <something>" ?
                if re.search("host ", user_text, re.IGNORECASE):
                    if debug:
                        print("I made it to host...")
                    if not user_text.split("host ", 1)[1] == "":
                        # They did, so migrate it!
                        maybe_host = user_text.split("host ", 1)[1]
                        regex = re.compile(r"\s*to\s *", flags=re.I)
                        the_rest = regex.split(maybe_host)[0]
                        host = the_rest.strip()
                        if debug:
                            print(f"host = {host}")
                        if not Ping(host):
                            r = "I was unable to ping that host."
                            response.markdown = r
                        else:
                            r = migrate_switch(
                                incoming_msg, dashboard, host=host, dest_net=dest_net
                            )
                            response.markdown = r
                    else:
                        # They did not, so BUMP the user.
                        r = "I'm sorry, but I don't have a host that we are "
                        r += "working with.  Use the **/check** command."
                        response.markdown = r
                if host == "":
                    r = "I'm sorry, but I don't have a host that we are "
                    r += "working with.  Use the **/check** command."
                    response.markdown = r
            else:
                response.markdown = migrate_switch(incoming_msg, dashboard, dest_net=dest_net)

        case "translate":
            # If the only thing the user typed was "translate""...
            if user_text.lower() == "translate":
                # Check and see if we have a global stateful config
                # filespec to work with
                if config_file == "" and host_id == "":
                    # We did not...
                    r = "I'm sorry, but I don't have a config or host that we "
                    r += "are working with.  Use the **/check** command."
                    response.markdown = r
                else:
                    if not len(meraki_serials) == 0:
                        # We did, so translate it!
                        serials = meraki_serials
                        r = translate_switch(
                            incoming_msg,
                            dashboard,
                            config=config_file,
                            host=host_id,
                            serials=serials,
                        )
                        response.markdown = r
                    else:
                        r = "I'm sorry, but I don't have a list of Meraki "
                        r += "switch serial numbers that we are working with."
                        response.markdown = r
            # Well, did they type more after "translate" ?
            elif user_text.lower().startswith("translate"):
                # Did they enter a list of Meraki switch serial numbers
                # after "to" ?
                serials = meraki_serials
                if re.search("to ", user_text, re.IGNORECASE):
                    if debug:
                        print(
                            "user_text.split('to ',1)[1] = "
                            + f"{user_text.split('to ', 1)[1]}"
                        )
                    if not user_text.split("to ", 1)[1] == "":
                        serials, r = SplitCheckSerials(user_text, "Translate")
                        if debug:
                            print(f"serials = {serials}")
                            print(f"r = {r}")
                            print(f"r=='' = {r == ''}")
                        if not r == "":
                            response.markdown = r
                            return response
                # Did they type "translate file <something>" ?
                if re.search("file ", user_text, re.IGNORECASE):
                    if not user_text.split("file ", 1)[1] == "":
                        # They did, so translate it!
                        maybe_file = user_text.split("file ", 1)[1].split()[0]
                        if debug:
                            print(f"maybe_file = {maybe_file}")
                        maybe_file, exists = FileExists(maybe_file)
                        if not exists:
                            r = "I'm sorry, but I could not find that file."
                            response.markdown = r
                        else:
                            r = translate_switch(
                                incoming_msg, dashboard, config=maybe_file, serials=serials
                            )
                            response.markdown = r
                    else:
                        # They did not, so BUMP the user.
                        r = "I'm sorry, but I don't have a config that we are "
                        r += "working with.  Use the **/check** command."
                        response.markdown = r
                # Did they type "translate host <something>" ?
                elif re.search("host ", user_text, re.IGNORECASE):
                    if debug:
                        print("I made it to host...")
                    if not user_text.split("host ", 1)[1] == "":
                        # They did, so translate it!
                        maybe_host = user_text.split("host ", 1)[1]
                        regex = re.compile(r"\s*to\s *", flags=re.I)
                        the_rest = regex.split(maybe_host)[0]
                        host_id = the_rest.strip()
                        if debug:
                            print(f"host_id = {host_id}")
                        if not Ping(host_id):
                            r = "I was unable to ping that host."
                            response.markdown = r
                        else:
                            r = translate_switch(
                                incoming_msg, dashboard, host=host_id, serials=serials
                            )
                            response.markdown = r
                        return response
                    else:
                        # They did not, so BUMP the user.
                        r = "I'm sorry, but I don't have a host that we are "
                        r += "working with.  Use the **/check** command."
                        response.markdown = r
                else:
                    if debug:
                        print(f"len(serials) = {len(serials)}")
                    if len(serials) == 0:
                        if debug:
                            print("Why am I here???")
                        r = "You need to enter a list of Meraki switch serial "
                        r += "numbers."
                        response.markdown = r
                    else:
                        response.markdown = translate_switch(
                            incoming_msg, dashboard, serials=serials
                        )

        case "get":
            if dashboard is None:
                response.markdown = (
                    "This command requires Meraki Dashboard access; run with credentials configured."
                )
                return response
            if user_text.lower().startswith("get"):
                if re.fullmatch(r"get\s+networks\s*", user_text, re.IGNORECASE):
                    response.markdown = get_networks(dashboard, meraki_org)
                elif re.search(r"\bcloud-ids\s+", user_text, re.IGNORECASE):
                    rest = re.split(
                        r"\bcloud-ids\s+", user_text, maxsplit=1, flags=re.IGNORECASE
                    )
                    if len(rest) < 2 or not rest[1].strip():
                        r = "Syntax is **get cloud-ids <_filespec_>** "
                        r += "(CSV or Excel with a Hostname column)."
                        response.markdown = r
                    else:
                        maybe_file = rest[1].split()[0]
                        maybe_file, exists = FileExists(maybe_file)
                        if not exists:
                            response.markdown = "I'm sorry, but I could not find that file."
                        else:
                            try:
                                hostnames = load_hostnames_from_file(maybe_file)
                            except ValueError as err:
                                response.markdown = str(err)
                            else:
                                inventory_by_mac = get_switch_inventory_by_mac(
                                    dashboard, meraki_org
                                )

                                def get_cloud_ids_worker(_idx, hn):
                                    if not Ping(hn, quiet=True):
                                        rp, ln = format_get_cloud_id_msg(
                                            hn, "Unable to ping", bot=BOT
                                        )
                                        return {
                                            "host": hn,
                                            "cloud_ids_by_host": {hn: []},
                                            "already_claimed": False,
                                            "response_piece": rp,
                                            "log_line": ln,
                                        }
                                    started = time.time()
                                    try:
                                        cloud_ids_by_host, already_claimed = (
                                            get_cloud_ids_for_host(
                                                hn,
                                                ios_username,
                                                ios_password,
                                                ios_port,
                                                ios_secret,
                                                inventory_by_mac,
                                            )
                                        )
                                        timing_short = ""
                                        if times:
                                            timing_short = " (%.2fs)" % round(
                                                (time.time() - started), 2
                                            )
                                        rp, ln = format_cloud_id_lookup_msg(
                                            hn,
                                            cloud_ids_by_host,
                                            already_claimed,
                                            timing_short=timing_short,
                                            bot=BOT,
                                        )
                                    except AuthenticationException:
                                        cloud_ids_by_host = {hn: []}
                                        already_claimed = False
                                        rp, ln = format_get_cloud_id_msg(
                                            hn, "SSH authentication failed", bot=BOT
                                        )
                                    except NetmikoTimeoutException as exc:
                                        cloud_ids_by_host = {hn: []}
                                        already_claimed = False
                                        rp, ln = format_get_cloud_id_msg(
                                            hn,
                                            f"SSH connection timed out: {exc}",
                                            bot=BOT,
                                        )
                                    except ConnectionException as exc:
                                        cloud_ids_by_host = {hn: []}
                                        already_claimed = False
                                        rp, ln = format_get_cloud_id_msg(
                                            hn,
                                            f"SSH connection failed: {exc}",
                                            bot=BOT,
                                        )
                                    except Exception:
                                        cloud_ids_by_host = {hn: []}
                                        already_claimed = False
                                        timing_short = ""
                                        if times:
                                            timing_short = " (%.2fs)" % round(
                                                (time.time() - started), 2
                                            )
                                        rp, ln = format_cloud_id_lookup_msg(
                                            hn,
                                            cloud_ids_by_host,
                                            already_claimed,
                                            timing_short=timing_short,
                                            bot=BOT,
                                        )
                                    return {
                                        "host": hn,
                                        "cloud_ids_by_host": cloud_ids_by_host,
                                        "already_claimed": already_claimed,
                                        "response_piece": rp,
                                        "log_line": ln,
                                    }

                                def on_get_cloud_id_complete(result):
                                    log_line = result["log_line"]
                                    print(log_line, end="")

                                row_results = run_parallel_indexed(
                                    hostnames,
                                    get_cloud_ids_worker,
                                    on_complete=on_get_cloud_id_complete,
                                )
                                parts = [row["response_piece"] for row in row_results]
                                log_output = "".join(row["log_line"] for row in row_results)
                                cloud_ids = extract_cloud_ids_for_dashboard_paste(
                                    [
                                        (
                                            row["cloud_ids_by_host"],
                                            row["already_claimed"],
                                        )
                                        for row in row_results
                                    ]
                                )
                                log_file = write_cloud_ids_log(log_output, cloud_ids)
                                print("\nLog written to " + os.path.abspath(log_file))
                                print(
                                    "which includes a list of Cloud IDs formatted for pasting into the Meraki Dashboard."
                                )
                                if BOT:
                                    response.html = "<hr><br>".join(parts)
                                else:
                                    response.markdown = ""
                elif re.search(r"\bcloud-id\s+", user_text, re.IGNORECASE):
                    rest = re.split(
                        r"\bcloud-id\s+", user_text, maxsplit=1, flags=re.IGNORECASE
                    )
                    if len(rest) < 2 or not rest[1].strip():
                        response.markdown = (
                            "Syntax is **get cloud-id <_fqdn or ip address_>**"
                        )
                    else:
                        host = rest[1].split()[0]
                        if not Ping(host):
                            response.markdown = "I was unable to ping that host."
                            return response
                        inventory_by_mac = get_switch_inventory_by_mac(
                            dashboard, meraki_org
                        )
                        started = time.time()
                        try:
                            cloud_ids_by_host, already_claimed = get_cloud_ids_for_host(
                                host,
                                ios_username,
                                ios_password,
                                ios_port,
                                ios_secret,
                                inventory_by_mac,
                            )
                            timing_short = ""
                            if times:
                                timing_short = " (%.2fs)" % round(
                                    (time.time() - started), 2
                                )
                            response_piece, _log_line = format_cloud_id_lookup_msg(
                                host,
                                cloud_ids_by_host,
                                already_claimed,
                                timing_short=timing_short,
                                bot=BOT,
                            )
                        except AuthenticationException:
                            response_piece, _log_line = format_get_cloud_id_msg(
                                host, "SSH authentication failed", bot=BOT
                            )
                        except NetmikoTimeoutException as exc:
                            response_piece, _log_line = format_get_cloud_id_msg(
                                host, f"SSH connection timed out: {exc}", bot=BOT
                            )
                        except ConnectionException as exc:
                            response_piece, _log_line = format_get_cloud_id_msg(
                                host, f"SSH connection failed: {exc}", bot=BOT
                            )
                        except Exception:
                            timing_short = ""
                            if times:
                                timing_short = " (%.2fs)" % round(
                                    (time.time() - started), 2
                                )
                            response_piece, _log_line = format_cloud_id_lookup_msg(
                                host,
                                {host: []},
                                False,
                                timing_short=timing_short,
                                bot=BOT,
                            )
                        if BOT:
                            response.html = response_piece
                        else:
                            response.markdown = response_piece
                else:
                    r = "Syntax is **get (networks | cloud-id <_fqdn or ip address_> | "
                    r += "cloud-ids <_filespec_>)**"
                    response.markdown = r

        case "get-cloud-id" | "get-cloud-ids":
            r = "Use **get cloud-id <_fqdn or ip address_>** or "
            r += "**get cloud-ids <_filespec_>**."
            response.markdown = r

        case "check":
            if user_text.lower() == "check":
                if host_id == "" and config_file == "":
                    # We did not...
                    r = "I'm sorry, but I don't know what switch or filespec "
                    r += "we are working with.  Use the **/check** command."
                    response.markdown = r
                else:
                    # We did, so check it!
                    response.markdown = check_switch(
                        incoming_msg,
                        host=host_id,
                        config=config_file,
                        report_label=host_id or None,
                    )
            elif not len(user_text.split()) >= 3:
                r = "Syntax is **check (host <_fqdn or ip address_> | "
                r += "hosts <_filespec_> | file <_filespec_>)**"
                response.markdown = r
            elif user_text.lower().startswith("check"):
                if re.search(r"\bhosts\s+", user_text, re.IGNORECASE):
                    rest = re.split(
                        r"\bhosts\s+", user_text, maxsplit=1, flags=re.IGNORECASE
                    )
                    if len(rest) < 2 or not rest[1].strip():
                        r = "Syntax is **check hosts <_filespec_>** "
                        r += "(CSV or Excel with a Hostname column)."
                        response.markdown = r
                    else:
                        maybe_file = rest[1].split()[0]
                        maybe_file, exists = FileExists(maybe_file)
                        if not exists:
                            r = "I'm sorry, but I could not find that file."
                            response.markdown = r
                        else:
                            try:
                                hostnames = load_hostnames_from_file(maybe_file)
                            except ValueError as err:
                                response.markdown = str(err)
                            else:
                                log_parts = []

                                def check_hosts_format_err(host_label, msg):
                                    log_line = f"{host_label}: {msg}\n"
                                    if BOT:
                                        response_piece = (
                                            "<h3>"
                                            + host_label
                                            + "</h3><p>"
                                            + msg
                                            + "</p>"
                                        )
                                    else:
                                        response_piece = log_line
                                    return response_piece, log_line

                                def check_hosts_worker(_idx, hn):
                                    if not Ping(hn, quiet=True):
                                        return check_hosts_format_err(
                                            hn, "Unable to ping"
                                        )
                                    try:
                                        switch_output = check_switch(
                                            incoming_msg,
                                            host=hn,
                                            report_label=hn,
                                            cli_one_line=True,
                                            set_session_globals=False,
                                        )
                                        return switch_output, switch_output
                                    except AuthenticationException:
                                        return check_hosts_format_err(
                                            hn,
                                            "SSH authentication failed",
                                        )
                                    except NetmikoTimeoutException as exc:
                                        return check_hosts_format_err(
                                            hn,
                                            f"SSH connection timed out: {exc}",
                                        )
                                    except ConnectionException as exc:
                                        return check_hosts_format_err(
                                            hn,
                                            f"SSH connection failed: {exc}",
                                        )
                                    except Exception as exc:
                                        return check_hosts_format_err(
                                            hn,
                                            f"error: {exc}",
                                        )

                                def on_check_host_complete(result):
                                    _response_piece, log_line = result
                                    print(log_line, end="")
                                    log_parts.append(log_line)

                                row_results = run_parallel_indexed(
                                    hostnames,
                                    check_hosts_worker,
                                    on_complete=on_check_host_complete,
                                )
                                parts = [row[0] for row in row_results]
                                log_output = "".join(log_parts)
                                log_file = write_check_hosts_log(log_output)
                                print("\nNote: Some supported features may have caveats when translating to Cloud Management mode. Check the docx files for details.")
                                print("\nLog written to " + os.path.abspath(log_file))
                                if BOT:
                                    response.html = "<hr><br>".join(parts)
                                else:
                                    # CLI already streamed each host result as it completed.
                                    # Leave markdown empty to avoid printing the full list again.
                                    response.markdown = ""
                elif re.search("file", user_text, re.IGNORECASE):
                    if not user_text.split("file ", 1)[1] == "":
                        maybe_file = user_text.split("file ", 1)[1].split()[0]
                        maybe_file, exists = FileExists(maybe_file)
                        if not exists:
                            r = "I'm sorry, but I could not find that file."
                            response.markdown = r
                        else:
                            response.markdown = check_switch(
                                incoming_msg,
                                config=maybe_file,
                                report_label=os.path.basename(maybe_file),
                            )
                    else:
                        r = "I'm sorry, but I don't have a config that we are "
                        r += "working with.  Use the **/check** command."
                        response.markdown = r
                elif re.search("host ", user_text, re.IGNORECASE):
                    if not user_text.lower().split("host ", 1)[1] == "":
                        host_id = user_text.lower().split("host ", 1)[1]
                        if debug:
                            print(f"Ping({host_id}) = {Ping(host_id)}")
                        if not Ping(host_id):
                            r = "I was unable to ping that host."
                            response.markdown = r
                            return response
                        if BOT:
                            response.html = check_switch(incoming_msg, host=host_id)
                        else:
                            response.markdown = check_switch(
                                incoming_msg, host=host_id, report_label=host_id
                            )
                    else:
                        r = "I'm sorry, but I don't have a host that we are "
                        r += "working with.  Use the **/check** command."
                        response.markdown = r
            else:
                r = "Syntax is **check (host <_fqdn or ip address_> | "
                r += "hosts <_filespec_> | file <_filespec_>)**"
                response.markdown = r

        case "register":
            # If the only thing the user typed was register...
            if user_text.lower() == "register":
                # Check and see if we have a global stateful host to work with
                if host_id == "":
                    # We did not...
                    r = "I'm sorry, but I don't have a host that we are "
                    r += "working with.  Use the **/check** command."
                    response.markdown = r
                else:
                    # We did, so translate it!
                    response.markdown = register_switch(incoming_msg, dashboard, host=host_id)
            # Well, did they type more after "register" ?
            elif user_text.lower().startswith("register"):
                # Did they type "register file <something>" ?
                if re.search("host ", user_text, re.IGNORECASE):
                    if not user_text.split("host ", 1)[1] == "":
                        # They did, so register it!
                        host_id = user_text.split("host ", 1)[1]
                        if not Ping(host_id):
                            r = "I was unable to ping that host."
                            response.markdown = r
                            return response
                        response.markdown = register_switch(incoming_msg, dashboard, host=host_id)
                    else:
                        # They did not, so BUMP the user.
                        r = "I'm sorry, but I don't have a host that we are "
                        r += "working with.  Use the **/check** command."
                        response.markdown = r
                else:
                    r = "Either enter **register host _fqdn or ip address_**."
                    response.markdown = r

        case "claim":
            # If the only thing the user typed was register...
            if user_text.lower() == "claim":
                # Check and see if we have a global stateful list of Meraki
                # serial numbers to work with
                if len(meraki_serials) == 0 and meraki_net == "":
                    # We did not...
                    r = "I'm sorry, but I don't have a Network a list of "
                    r += "Meraki serial numbers that we are working with."
                    response.markdown = r
                else:
                    if len(meraki_serials) == 0:
                        # We did not...
                        r = "I'm sorry, but I don't have a list of Meraki "
                        r += "serial numbers that we are working with."
                        response.markdown = r
                    elif meraki_net == "":
                        # We did not...
                        r = "I'm sorry, but I don't have a Network that we "
                        r += "are working with."
                        response.markdown = r
                    else:
                        # We did, so claim it!
                        r = claim_switch(
                            incoming_msg, dashboard, dest_net=meraki_net, serials=meraki_serials
                        )
                        response.markdown = r

            # Well, did they type more after "claim" ?
            elif user_text.lower().startswith("claim"):
                # Did they enter a Meraki network after "to" ?
                dest_net = meraki_net
                if re.search("to ", user_text, re.IGNORECASE):
                    regex = re.compile(r"\s*to\s *", flags=re.I)
                    if not regex.split(user_text)[1] == "":
                        # They did, so let's grab and test it
                        dest_net_name = regex.split(user_text)[1]
                        regex = r"\sto\s" + dest_net_name
                        user_text = re.sub(regex, "", user_text, re.IGNORECASE)
                        test_net = [
                            d["id"]
                            for d in meraki_networks
                            if d["name"] == dest_net_name
                        ]
                        if not len(test_net) == 0:
                            dest_net = test_net[0]
                            meraki_net_name = dest_net_name
                        else:
                            r = "I'm sorry, but {} is ".format(dest_net_name)
                            r += "not in your list of Meraki networks."
                # Set the list of serial numbers to the global stateful list in
                # case nothing was entered by the user
                serials = list()
                # Did the user enter a list of serial numbers after "Claim" ?
                if not user_text.lower() == "claim":
                    maybe_serials, r = SplitCheckSerials(user_text, "Claim")
                    if debug:
                        print(
                            "In case: 'claim': after SplitCheckSerials, "
                            + f"serials = {serials}, maybe_serials = "
                            + f"{maybe_serials}, r = {r}"
                        )
                    # If we didn't get back some kind of error response,
                    # use the returned list
                    if r == "":
                        serials = maybe_serials
                    else:
                        response.markdown = r
                else:
                    serials = meraki_serials
                # NOW let's see if we have any serial numbers and a Network
                # to work with...
                if len(serials) == 0 and dest_net == "":
                    # No to both
                    r = "Try entering **claim _meraki serial numbers_ to "
                    r += "_meraki Network name_**."
                    response.markdown = r
                else:
                    if len(serials) == 0:
                        # Just missing serial numbers
                        r = "I'm sorry, but I don't have a list of Meraki "
                        r += "serial numbers that we are working with."
                        response.markdown = r
                    elif dest_net == "":
                        # Just missing a network
                        r = "I'm sorry, but I don't have a Network that we "
                        r += "are working with."
                        response.markdown = r
                    else:
                        # All good, let's go claim the serial numbers to
                        # the network
                        response.markdown = claim_switch(
                            incoming_msg, dashboard, dest_net=dest_net, serials=serials
                        )

        case "help" | "?":
            if BOT:
                # Lookup details about sender for our default response
                sender = bot.teams.people.get(incoming_msg.personId)
                r = "Well {}, here's a list of ".format(sender.firstName)
                r += "commands that I understand. "
                response.markdown = r
                for line in bot_commands:
                    response.markdown += "\n" + line[0] + ": " + line[1]
                response.markdown += f"\n\nMerakicat version {VERSION}"
            else:
                r = (
                    f"\nMerakicat version {VERSION}\n\n"
                    + tabulate(command_list, headers=["Command Format", "Function"])
                    + "\n"
                )
                response.markdown = r

        case "hi" | "hello":
            if BOT:
                # Lookup details about sender for our default response
                sender = bot.teams.people.get(incoming_msg.personId)
                response.markdown = "Hi, {}! ".format(sender.firstName)
                response.markdown += "What do you want me to do today?\nSee "
                response.markdown += "what I can do by asking for **help**."

        case _:
            if BOT:
                # Lookup details about sender for our default response
                sender = bot.teams.people.get(incoming_msg.personId)
                response.markdown = "Hello {}, I'm ".format(sender.firstName)
                response.markdown += "really just a glorified chat bot. "
                response.markdown += "See what I can do by asking for "
                response.markdown += "**help**."
            else:
                response.markdown = "See what I can do by asking for help."

    # Whatever just happened up above, send our response back to the user.
    return response


def save(file):
    """
    This function will save an attached file from a Webex Teams message.
    :param file: The file URL from the Teams message
    :return: The path and filename of the saved file
    """
    headers = {"Authorization": "Bearer " + str(teams_token)}
    req = urllib.request.Request(file, headers=headers)
    path = os.path.join(os.getcwd(), DEFAULT_FILES_FOLDER)
    response = urllib.request.urlopen(req)
    f_path = os.path.join(
        path, response.info()["Content-Disposition"][21:].replace('"', "")
    )
    out_file = open(f_path, "wb")
    if debug:
        print("Saving: " + f_path)
    shutil.copyfileobj(response, out_file)
    return f_path


def get_log_filename_suffix() -> str:
    """Return a timestamp suffix in YYYY-MM-DD-HHMMSS format."""
    return datetime.now().strftime("%Y-%m-%d-%H%M%S")


def write_check_hosts_log(contents: str) -> str:
    """Write check-hosts output to DEFAULT_FILES_FOLDER and return file path."""
    output_dir = os.path.join(os.getcwd(), DEFAULT_FILES_FOLDER)
    os.makedirs(output_dir, exist_ok=True)
    log_file = os.path.join(output_dir, f"check-hosts-{get_log_filename_suffix()}.log")
    with open(log_file, "w") as fh:
        fh.write(contents)
    return log_file


def minimum_ios_message(status) -> str:
    """Return a user-facing message for failed minimum IOS/model checks."""
    if status.reason == "not_met":
        return (
            "IOS XE version not supported "
            + f"({status.current_version} < {status.required_version})"
        )
    if status.reason == "unsupported_model":
        return f"Switch model {status.model} is not supported"
    if status.reason == "unknown_model":
        return "Could not determine switch model"
    if status.reason == "unknown_version":
        return "Could not determine current IOS version"
    return "Switch firmware check failed"


# Create functions that will be linked to bot commands to add capabilities
# ------------------------------------------------------------------------


CHECK_TRANS_MARK = "✓"


def _feature_row_note_blank(row):
    """True if encyclopedia note (index 3) is empty."""
    if len(row) < 4:
        return True
    return str(row[3]).strip() == ""


def _feature_row_note_not_supported(row):
    """True when note text explicitly says the feature is not supported."""
    if len(row) < 4:
        return False
    return "not supported" in str(row[3]).strip().lower()


def _feature_row_countable(row):
    """
    True if this row should be included in one-line gap counts.
    Excludes rows with notes and the Model feature.
    """
    if len(row) > 0 and str(row[0]).strip().lower() == "model":
        return False
    return _feature_row_note_blank(row)


def check_feature_counts(can_list_doc, not_list_doc):
    """
    Count configured features lacking Meraki availability or translation support.
    Rows with notes are usually informational/caveat lines and are ignored, except
    notes containing "Not supported", which are counted as not available in Meraki.

    :param can_list_doc: Full feature rows with Meraki availability (from CheckFeatures)
    :param not_list_doc: Full feature rows without Meraki availability
    :return: (not_available_count, not_translatable_count among counted available rows)
    """
    n_not_available = 0
    for row in not_list_doc:
        if _feature_row_countable(row) or _feature_row_note_not_supported(row):
            n_not_available += 1
    for row in can_list_doc:
        if _feature_row_note_not_supported(row):
            n_not_available += 1

    n_not_translatable = 0
    for row in can_list_doc:
        if not _feature_row_countable(row):
            continue
        if len(row) < 3:
            n_not_translatable += 1
        elif str(row[2]).strip() != CHECK_TRANS_MARK:
            n_not_translatable += 1
    return n_not_available, n_not_translatable


def format_precheck_console(issues: list[str]) -> str:
    """Format registration readiness issues for CLI output."""
    if not issues:
        return ""
    out = "\n\nRegistration readiness issues:\n"
    for issue in issues:
        if issue.startswith("  "):
            out += f"  {issue}\n"
        else:
            out += f"  - {issue}\n"
    return out


def format_precheck_html(issues: list[str]) -> str:
    """Format registration readiness issues for BOT HTML output."""
    if not issues:
        return ""
    items = []
    for issue in issues:
        escaped = (
            issue.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        items.append(f"<li>{escaped}</li>")
    return (
        "<h4>Registration readiness issues</h4><ul>"
        + "".join(items)
        + "</ul>"
    )


def add_precheck_issues_to_docx(document, precheck_issues: list[str] | None) -> None:
    """Add registration readiness checks section to a docx report."""
    if not precheck_issues:
        return
    document.add_heading("Registration readiness checks", level=2)
    for issue in precheck_issues:
        document.add_paragraph(issue, style="List Bullet")


def check_network(incoming_msg, dest_net, dashboard, targets=["C9300", "9200"]):
    """
    This function will get a list of all switches in a Meraki network, parse
    it for any cloud-monitored Catalyst switches that cold be cloud-managed.
    It then grabs their configs one by one and sends them through the
    check_switch function to generate a report for each.
    :param incoming_msg: The incoming message object from Teams
    :param dest_net: The Meraki network to check
    :return: A text or markdown based reply
    """

    # Create a Response object to later craft a reply in Markdown.
    response = Response()

    # This will be our copy of the user input to work with
    user_roomId = incoming_msg.roomId

    # Grab the list of devices for that Network
    try:
        devices = dashboard.networks.getNetworkDevices(dest_net)
    except meraki.exceptions.APIError:
        r = "We were unable to get the list of devices for that network. (Meraki network names are case sensitive.)"
        return r
    if debug:
        print(f"devices = {devices}")

    # Loop through the devices searching for cloud monitored C9300s
    success_list = list()
    if targets == []:
        targets = ["C9300", "9200"]
    if debug:
        print(f"targets = {targets}")
    x = 0
    while x <= len(devices) - 1:
        if debug:
            print(f"\ndevice = {devices[x]}")
        if devices[x]["firmware"].startswith("ios-xe"):
            short_mod = devices[x]["model"][:5]
            if debug:
                print(f"short_mod = {short_mod}")
            if short_mod in targets:
                # Found one...
                sw_name = devices[x]["name"]

                # Grab the list of config files archived for the switch
                try:
                    url = "https://api.meraki.com/api/v1/devices/"
                    url += f"{devices[x]['serial']}/switch/configs"
                    payload = {}
                    headers = {"X-Cisco-Meraki-API-Key": meraki_api_key}
                    response = meraki_requests_request(
                        "GET",
                        url,
                        dry_run=MERAKI_DRY_RUN,
                        headers=headers,
                        data=payload,
                    )
                except requests.RequestException:
                    print(f"ERROR getting the config list for {sw_name}")
                    x += 1
                conf_list = response.json()
                # If the Python meraki SDK ever supports this it should look
                # like this:
                #
                # conf_list = dashboard.devices.getSwitchConfigs(
                #   devices[x]['serial'])

                if debug:
                    print(f"conf_list = {conf_list}")
                    print(f"len(conf_list) = {len(conf_list)}")
                    print(f"conf_list[0] = {conf_list[0]}")

                # Assuming there are and configs in the list, we will grab a
                # copy of the first (latest) one.
                if len(conf_list) > 0:
                    url += "/" + conf_list[0]["id"]
                    if debug:
                        print(f"url = {url}")
                    try:
                        response = meraki_requests_request(
                            "GET",
                            url,
                            dry_run=MERAKI_DRY_RUN,
                            headers=headers,
                            data=payload,
                        )
                    except requests.RequestException:
                        print(f"ERROR getting config for {sw_name}")
                        x += 1
                    c = response.json()
                    # If the Python meraki SDK ever supports this it should
                    # look like this:
                    #
                    # c = dashboard.devices.getSwitchConfigs(
                    #   devices[x]['serial'],conf_list[0]['id'])

                    # Now that we have the config, let's save a copy
                    path = os.path.join(os.getcwd(), DEFAULT_FILES_FOLDER)
                    config_file = os.path.join(path, sw_name + ".cfg")
                    file = open(config_file, "w")
                    file.writelines(c["config"])
                    file.close()
                    success_list.append(sw_name)

                    # Run the Check report on that config file
                    response.markdown = check_switch(  #type: ignore
                        incoming_msg, config=config_file, report_label=sw_name
                    )  
                    if BOT:
                        create_message(user_roomId, response.markdown) 
                    else:
                        print(response.markdown)  #type: ignore
        x += 1

    # Prep the overall return status and pass it back
    if len(success_list) > 0:
        r = "We successfully downloaded the config file"
        if len(success_list) == 1:
            r += " for " + success_list[0] + "."
        else:
            r += "s for " + ",".join(success_list) + "."
    else:
        r = "We were unsuccessful locating cloud monitored switch model"
        if len(targets) == 1:
            r += ": " + ",".join(targets) + "."
        else:
            r += "s: " + ",".join(targets) + "."
    return r


def check_switch(
    incoming_msg,
    config="",
    host="",
    demo=False,
    report_label=None,
    *,
    cli_one_line=False,
    return_counts=False,
    set_session_globals=True,
):
    """
    This function will check a Catalyst switch config for feature mapping to
    Meraki.
    :param incoming_msg: The incoming message object from Teams
    :param config: The incoming config filespec
    :param host: The incoming hostname or IP address
    :param demo: Indicates whether or not we are creating a fake demo report
    :param report_label: Name to use in cli_one_line console output (defaults to
        switch hostname from config)
    :param cli_one_line: If True (non-BOT), print one summary line instead of the
        full feature table (used by check hosts)
    :param return_counts: If True with cli_one_line, return (summary_line, n_na, n_nt)
    :param set_session_globals: If False, do not mutate module-level host_id/config_file
        (use from parallel bulk checks so workers do not clobber each other).
    :return: HTML for BOT; otherwise full table or one-line per cli_one_line; docx/pdf
        always written from check_report_writer.
    """

    start_time = time.time()
    min_ios_status = None
    precheck_issues: list[str] = []

    if set_session_globals:
        global config_file, host_id

    if not demo:
        if config == "":
            # Since we weren't passed a config filespec, check for a
            # hostname or IP address
            if host == "":
                return "You need to enter either a host or a filename."

            # We were passed a hostname or IP address...
            else:
                if set_session_globals:
                    host_id = host

                min_ios_status = check_host_minimum_ios(
                    host, ios_username, ios_password, ios_port, ios_secret
                )
                if min_ios_status.reason in {"unsupported_model", "unknown_model"}:
                    model_label = min_ios_status.model if min_ios_status.model else "unknown"
                    if cli_one_line:
                        label = (
                            report_label
                            if report_label is not None
                            else (host or model_label or "switch")
                        )
                        out = (
                            f"{label}: Switch model {model_label} is not supported\n"
                        )
                        if return_counts:
                            return out, 0, 0
                        return out
                    if BOT:
                        return (
                            "<h3>Unsupported switch model</h3><p>"
                            + f"Switch model <b>{model_label}</b> is not supported."
                            + "</p>"
                        )
                    return (
                        f"Switch model {model_label} is not supported."
                    )

            # Get the config file from a switch/stack
            switch_name, config, precheck = GetConfig(
                host,
                ios_username,
                ios_password,
                ios_port,
                ios_secret,
                run_prechecks=True,
            )
            precheck_issues = precheck.issues

        # Update the global stateful variable for later (single-threaded / bot use)
        if set_session_globals:
            config_file = config

        # Run the function in config_checker to get the list of
        # features configured on the switch (supported and not)
        host_name, the_list = CheckFeatures(config)
        switch_name = host_name
    else:
        print("In check_switch in the demo area")
        # Prep for a demo report
        host_name = switch_name = "Demonstration"
        the_list = list()
        switch_pedia = mc_pedia.get("switch")
        if isinstance(switch_pedia, dict):
            for k in switch_pedia:
                value = switch_pedia[k]
                if not value["regex"] == "":
                    the_list.append(
                        [
                            value["name"],
                            value["support"],
                            value["translatable"],
                            value["note"] if "note" in value.keys() else "",
                            value["url"] if "url" in value.keys() else "",
                        ]
                    )
        port_pedia = mc_pedia.get("port")
        if isinstance(port_pedia, dict):
            for k in port_pedia:
                value = port_pedia[k]
                if not value["regex"] == "":
                    the_list.append(
                        [
                            value["name"],
                            value["support"],
                            value["translatable"],
                            value["note"] if "note" in value.keys() else "",
                            value["url"] if "url" in value.keys() else "",
                        ]
                    )

    # Clear some variables for the next step
    can_list = list()
    can_list_doc = list()
    can_list_console = list()
    not_list = list()
    not_list_doc = list()
    not_list_console = list()

    # Go through the outcome from the read_conf functions and split the
    # supported and unsupported features as well as the additional text
    # and links for the unsupported
    x = 0
    not_notes = list()
    while x < (len(the_list)):
        if not the_list[x][1] == "":
            can_list_doc.append(the_list[x])
            can_list_console.append(list(islice(the_list[x], 5)))
            can_list.append([the_list[x][0], the_list[x][1], the_list[x][2]])
        else:
            not_list_doc.append(the_list[x])
            not_list_console.append(list(islice(the_list[x], 5)))
            not_list.append([the_list[x][0], " ", " "])
            not_notes.append([the_list[x][3], the_list[x][4]])
        x += 1
    all_list = list(list())
    all_list.extend(can_list)
    all_list.extend(not_list)
    all_list_console = list(list())
    all_list_console.extend(can_list_console)
    all_list_console.extend(not_list_console)
    all_list_doc = list(list())
    all_list_doc.extend(can_list_doc)
    all_list_doc.extend(not_list_doc)

    if min_ios_status is not None:
        if min_ios_status.reason == "met":
            min_notes = f"IOS {min_ios_status.current_version} supported"
            min_available = "Yes"
            min_translatable = ""
            min_more_info = (
                "https://documentation.meraki.com/Switching/Cloud_Management_with_IOS_XE"
            )
        elif min_ios_status.reason == "not_met":
            min_notes = (
                "Version not supported "
                + f"({min_ios_status.current_version} < "
                + f"{min_ios_status.required_version})"
            )
            min_available = "No"
            min_translatable = ""
            min_more_info = (
                "https://documentation.meraki.com/Switching/Cloud_Management_with_IOS_XE"
            )
        elif min_ios_status.reason == "unsupported_model":
            min_notes = (
                "minimum IOS unknown "
                + f"(no mapping for model {min_ios_status.model})"
            )
            min_available = "Unknown"
            min_translatable = ""
            min_more_info = ""
        elif min_ios_status.reason == "unknown_version":
            min_notes = (
                "minimum IOS unknown "
                + "(could not determine current IOS version)"
            )
            min_available = "Unknown"
            min_translatable = ""
            min_more_info = ""
        else:
            min_notes = "minimum IOS unknown (could not determine model)"
            min_available = "Unknown"
            min_translatable = ""
            min_more_info = ""

        all_list.append(
            ["Supported firmware", min_available, min_translatable]
        )
        all_list_console.append(
            [
                "Supported firmware",
                min_available,
                min_translatable,
                min_notes,
                min_more_info,
            ]
        )

    if BOT:
        tabulate.PRESERVE_WHITESPACE = True  
        # Build the report.
        if debug:
            print(f"all_list = {all_list}")
        report = tabulate(
            all_list,
            colalign=["left", "center", "center"],
            headers=["Feature", "Available", "Translatable"],
        )
        report_lines = report.splitlines()
        report_line_len = len(report_lines[1])
        x = 0
        bad_start = len(can_list) + 2
        while x < len(report_lines):
            results = [
                (m.start(), m.end() - 1) for m in re.finditer(r"\S+", report_lines[x])
            ]
            fix_line = ""
            last_word = 0
            for result in results:
                if not last_word == 0:
                    num = result[0] - last_word
                    if num > 1:
                        fix_line += "".join(["&nbsp" * num])
                    fix_line += " "
                fix_line += report_lines[x][result[0] : result[1] + 1]
                last_word = result[1] + 1
            num = report_line_len - last_word
            fix_line += "".join(["&nbsp" * num])
            report_lines[x] = fix_line
            if x > 1:
                if all_list[x - 2][1] in [" ", ""]:
                    report_lines[x] += "&nbsp"
                if all_list[x - 2][2] in [" ", ""]:
                    report_lines[x] += "&nbsp"
            report_lines[x] = "<code>" + report_lines[x] + "</code>"
            x += 1
        x = 0
        while x < len(not_list):
            if not not_notes[x][0] == "":
                hotlink = '<a href ="' + not_notes[x][1]
                hotlink += '" rel="nofollow">' + not_notes[x][0] + "</a>"
                report_lines[bad_start + x] += hotlink
            x += 1
        new_report = "<br>".join(report_lines)
        new_report = "<p>" + new_report + "</p>"
        new_report = (
            "<h3>Merakicat Feature Report for " + switch_name + "</h3><br>" + new_report
        )
        new_report += format_precheck_html(precheck_issues)
        fname = check_report_writer(
            switch_name,
            can_list_doc,
            not_list_doc,
            min_ios_status=min_ios_status,
            precheck_issues=precheck_issues,
        )
        timing = ""
        if times:
            timing = "<br>=== That config check took %s seconds" % str(
                round((time.time() - start_time), 2)
            )
        return (
            new_report
            + "<br><br><b>Please review the results above</b>,"
            + " or in the file "
            + fname
            + " on the system where I'm"
            + " running.<br>Results based on encyclopedia "
            + mc_pedia["version"]
            + ", published on "
            + mc_pedia["dated"]
            + """.<br>If you wish, I can migrate the Translatable features
 to an existing switch in the Meraki Dashboard.  Type <b>translate</b> and
 a Meraki switch serial number.<br>If you prefer, I can prepare for the
 switch to become a Meraki managed switch, keeping the translated config.
  Just type <b>migrate [to <i>meraki network</i>]</b>.
"""
            + timing
        )

    # Not a BOT: full table by default; one line only when cli_one_line (check hosts)
    else:
        if debug:
            print(f"all_list = {all_list}")
        fname = check_report_writer(
            switch_name,
            can_list_doc,
            not_list_doc,
            min_ios_status=min_ios_status,
            precheck_issues=precheck_issues,
        )
        timing = ""
        if times:
            timing = "\n=== That config check took %s seconds" % str(
                round((time.time() - start_time), 2)
            )
        if cli_one_line:
            n_na, n_nt = check_feature_counts(can_list_doc, not_list_doc)
            label = (
                report_label if report_label is not None else (switch_name or "switch")
            )
            timing_short = ""
            if times:
                timing_short = " (%.2fs)" % round((time.time() - start_time), 2)
            if n_na == 0 and n_nt == 0 and not precheck_issues:
                line = (
                    f"{label}: All configured features are available and "
                    f"translatable"
                )
            else:
                parts = []
                if n_na:
                    parts.append(f"{n_na} feature(s) not available in Meraki")
                if n_nt:
                    parts.append(f"{n_nt} feature(s) not translatable")
                if precheck_issues:
                    parts.append(f"{len(precheck_issues)} precheck(s) failed")
                line = f"{label}: " + "; ".join(parts)
            if min_ios_status is not None:
                if min_ios_status.reason == "met":
                    pass
                elif min_ios_status.reason == "not_met":
                    line += (
                        "; IOS XE version not supported "
                        + f"({min_ios_status.current_version} < "
                        + f"{min_ios_status.required_version})"
                    )
                elif min_ios_status.reason == "unsupported_model":
                    line += (
                        "; minimum IOS unknown "
                        + f"(no mapping for model {min_ios_status.model})"
                    )
                elif min_ios_status.reason == "unknown_version":
                    line += (
                        "; minimum IOS unknown "
                        + "(could not determine current IOS version)"
                    )
                else:
                    line += "; minimum IOS unknown (could not determine model)"
            line += f"; details in {fname}"
            out = line + timing_short + "\n"
            if return_counts:
                return out, n_na, n_nt
            return out
        report = tabulate(
            all_list_console,
            headers=[
                "Feature",
                "Available",
                "Translatable",
                "Notes",
                "For more info, see this URL",
            ],
        )
        out = (
            "\n\n"
            + report
            + format_precheck_console(precheck_issues)
            + "\n\nPlease review the results above, or "
            + "in the file "
            + fname
            + ".\nResults based on encyclopedia "
            + mc_pedia["version"]
            + ", published on "
            + mc_pedia["dated"]
            + ".\nIf you wish, I can translate or migrate the "
            + "Translatable features to an existing switch in the Meraki "
            + "Dashboard."
            + timing
            + "\n"
        )
        if return_counts:
            n_na, n_nt = check_feature_counts(can_list_doc, not_list_doc)
            return out, n_na, n_nt
        return out


def cloud_switch(incoming_msg, dashboard, host=""):
    """ """

    start_time = time.time()
    timing = ""

    # Import the global stateful variables
    global host_id, times

    # Since we weren't passed a config filespec, check for a hostname or
    # IP address
    if host == "":
        return "You need to enter a host FQDN or IP address."
    else:
        # We were passed a hostname or IP address...
        # Update the global stateful variable for later
        host_id = host

    # SSH to the switch with netmiko, read the config, grab the hostname,
    # write the config out to a file using the hostname as part of the
    # filespec
    sw_name, config_file = CloudSwitch(
        dashboard, meraki_org, host, ios_username, ios_password, ios_port, ios_secret
    )
    """
    if debug:
        print(f"In cloud_switch, status = {status}")
    if status == "successfully":
        meraki_serials = registered_serials
        if debug:
            for switch in registered_switches:
                print(f"In register_switch status = {status}")
                print(f"switch = {switch}")
                print("switch['Migration Status'] = " +
                      f"{switch['migration_status']}")
    if debug:
        print(f"After registering switches, meraki_serials = {meraki_serials}")
    # Report back on what happened
    if called == "":
        timing = ""
        if not len(registered_switches) == 0:
            vals = reduce(lambda x, y: x + y, [list(dic.values())
                          for dic in registered_switches])
            header = registered_switches[0].keys()
            rows = [x.values() for x in registered_switches]
            thing = tabulate(rows, header)
            if times:
                t = "\n=== That registraion took "
                t += "%s seconds" % str(round((time.time() - start_time), 2))
                timing = t
            if BOT:
                payload = "```\n%s" % thing + "\n```" + timing
                r = f"We **{status}** registered **{vals.count('Registered')}"
                r += "** switch"
                r += f"{'es' if (vals.count('Registered') > 1) else ''}"
                return (r + f":\n{payload}")
            else:
                payload = "\n%s" % thing + timing
                r = f"\n\nWe {status} registered {vals.count('Registered')}"
                r += f"switch{'es' if (vals.count('Registered') > 1) else ''}"
                return (r + f":\n{payload}")
        else:
            payload = ""
            for issue in issues:
                payload += issue + "\n"
            r = f"We were unsuccessful registering {host}:\n\n{payload}"
            return (r + timing)
    else:
        return (status, issues, registered_switches)
    """
    if times:
        t = "%s seconds!" % str(round((time.time() - start_time), 2))
        timing = " And it only took " + t
    return "Well, that was fun!" + timing


def check_report_writer(
    switch_name,
    can_list_doc,
    not_list_doc,
    min_ios_status=None,
    precheck_issues=None,
):

    global detailed

    def _display_ios_version(version: str) -> str:
        parts = version.split(".")
        normalized_parts = []
        for part in parts:
            if part.isdigit():
                normalized_parts.append(str(int(part)))
            else:
                normalized_parts.append(part)
        return ".".join(normalized_parts)

    document = docx.Document()
    section = document.sections[0]

    # Header with graphics and the switch/stack name
    header = section.header
    paragraph = header.paragraphs[0]
    logo_run = paragraph.add_run()
    logo_run.add_picture("../../images/merakicat.png", width=Inches(1))
    text_run = paragraph.add_run()
    if detailed:
        t = "\tMerakicat Detailed Report for " + switch_name
        t += "\t"  # For center align of text
        text_run.text = t
    else:
        t = "\t" + "Merakicat Feature Check Report for "
        t += switch_name + "\t"  # For center align of text
        text_run.text = t
    logo_run = paragraph.add_run()
    logo_run.add_picture("../../images/cisco_meraki.png", width=Inches(1))

    # Footer with date and time of the report
    footer = section.footer
    paragraph = footer.paragraphs[0]
    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
  
    t = "Based on encyclopedia " + str(mc_pedia["version"])
    t += ", published on " + str(mc_pedia["dated"]) + "\nReport run on "
    paragraph.text = t + datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

    if detailed:
        # Report as a document
        # Loop through the can_list_doc items and add to the table
        h = "Available features in Meraki Dashboard, by line number"
        heading = document.add_heading(h, level=1)
        heading.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for line in can_list_doc:
            heading = document.add_heading(line[0] + "\t\t", level=2)
            add_hyperlink(heading, line[3], line[4], "0000FF", False)
            if len(line[5][0]) == 1:
                paragraph = document.add_paragraph()
                for ios_line in line[5]:
                    paragraph.text += "\t" + str(ios_line[0].linenum)
                    paragraph.text += "\t" + ios_line[0].text + "\n"
            else:
                for ios_line in line[5]:
                    h = "\t" + str(ios_line[1].linenum)
                    h += "\t" + ios_line[1].text
                    heading = document.add_heading(h, level=3)
                    paragraph = document.add_paragraph()
                    paragraph.text += "\t" + str(ios_line[0].linenum)
                    paragraph.text += "\t" + ios_line[0].text + "\n"
        document.add_page_break()
        h = "Features NOT currently availaible in Meraki Dashboard, "
        h += "by line number"
        heading = document.add_heading(h, level=1)
        heading.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for line in not_list_doc:
            heading = document.add_heading(line[0] + "\t\t", level=2)
            add_hyperlink(heading, line[3], line[4], "0000FF", False)
            if len(line[5][0]) == 1:
                paragraph = document.add_paragraph()
                for ios_line in line[5]:
                    paragraph.text += "\t" + str(ios_line[0].linenum)
                    paragraph.text += "\t" + ios_line[0].text + "\n"
            else:
                for ios_line in line[5]:
                    h = "\t" + str(ios_line[1].linenum)
                    h += "\t" + ios_line[1].text
                    heading = document.add_heading(h, level=3)
                    paragraph = document.add_paragraph()
                    paragraph.text += "\t" + str(ios_line[0].linenum)
                    paragraph.text += "\t" + ios_line[0].text + "\n"
        if min_ios_status is not None:
            heading = document.add_heading(
                "Supported firmware?", level=2
            )
            paragraph = document.add_paragraph()
            if min_ios_status.reason == "met":
                status_text = (
                    "IOS "
                    + f"{_display_ios_version(min_ios_status.current_version)} "
                    + "supported"
                )
                add_hyperlink(
                    paragraph,
                    status_text,
                    "https://documentation.meraki.com/Switching/Cloud_Management_with_IOS_XE",
                    "0000FF",
                    False,
                )
            elif min_ios_status.reason == "not_met":
                status_text = (
                    "Version not supported "
                    + f"({min_ios_status.current_version} < "
                    + f"{min_ios_status.required_version})"
                )
                add_hyperlink(
                    paragraph,
                    status_text,
                    "https://documentation.meraki.com/Switching/Cloud_Management_with_IOS_XE",
                    "0000FF",
                    False,
                )
            elif min_ios_status.reason == "unsupported_model":
                paragraph.text = (
                    "minimum IOS unknown "
                    + f"(no mapping for model {min_ios_status.model})"
                )
            elif min_ios_status.reason == "unknown_version":
                paragraph.text = (
                    "minimum IOS unknown "
                    + "(could not determine current IOS version)"
                )
            else:
                paragraph.text = "minimum IOS unknown (could not determine model)"
        add_precheck_issues_to_docx(document, precheck_issues)
    else:
        # Report as a table
        table = document.add_table(rows=1, cols=4)
        table.autofit = False
        col_count = len(table.columns)
        headers = ["Feature", "Available", "Translatable", "More Information"]
        heading_cells = table.rows[0].cells
        set_col_widths(table.rows[0])

        # Setup a repeating heading row for the table
        x = 0
        while x < col_count:
            heading_cells[x].text = headers[x]
            heading_cells[x].paragraphs[0].runs[0].font.bold = True  # Bold
            x += 1
        heading_cells[3].paragraphs[
            0
        ].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        set_repeat_table_header(table.rows[0])

        # Loop through the can_list_doc items and add to the table
        for line in can_list_doc:
            row = table.add_row()
            set_col_widths(row)
            cells = row.cells
            x = 0
            while x < col_count - 1:
                cells[x].text = line[x]
                x += 1
            cells[1].paragraphs[
                0
            ].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cells[2].paragraphs[
                0
            ].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Loop through the not_list_doc items and add to the table,
        # creating any hyperlinks
        for line in not_list_doc:
            row = table.add_row()
            set_col_widths(row)
            cells = row.cells
            cells[2].merge(cells[3])
            x = 0
            while x < col_count - 1:
                cells[x].text = line[x]
                x += 1
            p_table = cells[2].paragraphs[0]
            p_table.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            add_hyperlink(p_table, line[3], line[4], "0000FF", False)

        if min_ios_status is not None:
            row = table.add_row()
            set_col_widths(row)
            cells = row.cells
            cells[0].text = "Supported firmware"
            cells[1].paragraphs[0].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cells[2].paragraphs[0].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if min_ios_status.reason == "met":
                cells[1].text = "Yes"
                cells[2].text = ""
                status_text = (
                    "IOS "
                    + f"{_display_ios_version(min_ios_status.current_version)} "
                    + "supported"
                )
                p_table = cells[3].paragraphs[0]
                p_table.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                add_hyperlink(
                    p_table,
                    status_text,
                    "https://documentation.meraki.com/Switching/Cloud_Management_with_IOS_XE",
                    "0000FF",
                    False,
                )
            elif min_ios_status.reason == "not_met":
                cells[1].text = "No"
                cells[2].text = ""
                status_text = (
                    "Version not supported "
                    + f"({min_ios_status.current_version} < "
                    + f"{min_ios_status.required_version})"
                )
                p_table = cells[3].paragraphs[0]
                p_table.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                add_hyperlink(
                    p_table,
                    status_text,
                    "https://documentation.meraki.com/Switching/Cloud_Management_with_IOS_XE",
                    "0000FF",
                    False,
                )
            elif min_ios_status.reason == "unsupported_model":
                cells[1].text = "Unknown"
                cells[2].text = ""
                cells[3].text = (
                    "minimum IOS unknown "
                    + f"(no mapping for model {min_ios_status.model})"
                )
            elif min_ios_status.reason == "unknown_version":
                cells[1].text = "Unknown"
                cells[2].text = ""
                cells[3].text = (
                    "minimum IOS unknown "
                    + "(could not determine current IOS version)"
                )
            else:
                cells[1].text = "Unknown"
                cells[2].text = ""
                cells[3].text = "minimum IOS unknown (could not determine model)"

        add_precheck_issues_to_docx(document, precheck_issues)

    # Write out the report as a docx file
    path = os.path.join(os.getcwd(), DEFAULT_FILES_FOLDER)
    fname = switch_name + ".docx"
    fname_pdf = switch_name + ".pdf"
    document.save(os.path.join(path, fname))

    # If PDF setting in mc_user_info.py file is True,convert docx to PDF
    # and delete the docx file
    if PDF:
        convert(os.path.join(dir, fname), (os.path.join(dir, fname_pdf)))
        os.remove(os.path.join(dir, fname))
        fname = fname_pdf
    return fname


# document.tables[0].rows[0].cells[0].paragraphs[0].runs[0]
#   .font.color.rgb = RGBColor(50, 0, 255)  # Blue Color
# document.tables[0].rows[0].cells[0].paragraphs[0].runs[0]
#   .font.blod = True  # Bold


def set_col_widths(row):
    """adjust column widths for docx"""
    widths = (Inches(2), Inches(1), Inches(1.1), Inches(2))
    for idx, width in enumerate(widths):
        row.cells[idx].width = width


def set_repeat_table_header(row):
    """set repeat table row on every new page for docx"""
    tr = row._tr
    trPr = tr.get_or_add_trPr()
    tblHeader = OxmlElement("w:tblHeader")
    tblHeader.set(qn("w:val"), "true")
    trPr.append(tblHeader)
    return row


def add_hyperlink(paragraph, text, url, color, underline):
    """creates a hyperlink for insertion into a docx file"""
    # This gets access to the document.xml.rels file and gets a new
    # relation id value
    part = paragraph.part
    r_id = part.relate_to(
        url, docx.opc.constants.RELATIONSHIP_TYPE.HYPERLINK, is_external=True
    )
    # Create the w:hyperlink tag and add needed values
    hyperlink = docx.oxml.shared.OxmlElement("w:hyperlink")
    hyperlink.set(
        docx.oxml.shared.qn("r:id"),
        r_id,
    )
    # Create a w:r element
    new_run = docx.oxml.shared.OxmlElement("w:r")
    # Create a new w:rPr element
    rPr = docx.oxml.shared.OxmlElement("w:rPr")
    # Add color if it is given
    if color is not None:
        c = docx.oxml.shared.OxmlElement("w:color")
        c.set(docx.oxml.shared.qn("w:val"), color)
        rPr.append(c)
    # Remove underlining if it is requested
    if not underline:
        u = docx.oxml.shared.OxmlElement("w:u")
        u.set(docx.oxml.shared.qn("w:val"), "none")
        rPr.append(u)
    # Join all the xml elements together  add the required
    # text to the w:r element
    new_run.append(rPr)
    new_run.text = text
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)
    return hyperlink


def register_switch(incoming_msg, dashboard, host="", called=""):
    """
    This function will register a Catalyst switch to the Meraki Dashboard.
    :param incoming_msg: The incoming message object from Teams
    :param host: The incoming hostname or IP address
    :param called: Indicates this was called from another function vs greeting
    :return: A text/markdown based reply if called from greeting (called="")
    :      : Or, status, issues & registered switch list otherwise
    """

    start_time = time.time()

    # Import the global stateful variables
    global host_id, meraki_serials, nm_list, times, unified_os

    # Since we weren't passed a config filespec, check for a hostname
    # or IP address
    if host == "":
        return "You need to enter a host FQDN or IP address."
    else:
        # We were passed a hostname or IP address...
        # Update the global stateful variable for later
        host_id = host

    support_status = check_host_minimum_ios(
        host, ios_username, ios_password, ios_port, ios_secret
    )
    if support_status.reason != "met":
        msg = minimum_ios_message(support_status)
        if called == "":
            return f"We were unsuccessful registering {host}:\n\n{msg}\n"
        return ("unsuccessfully", [msg], [])

    # SSH to the switch with netmiko, read the config, grab the hostname,
    # write the config out to a file using the hostname as part of the
    # filespec
    inventory_by_mac = get_switch_inventory_by_mac(dashboard, meraki_org)
    (
        status,
        issues,
        registered_switches,
        registered_serials,
        nm_list,
        unified_os,
        already_claimed,
    ) = Register(
        host,
        ios_username,
        ios_password,
        ios_port,
        ios_secret,
        inventory_by_mac
    )
    if debug:
        print(f"In register_switch, status = {status}")
        print(f"In register_switch, already_claimed = {already_claimed}")
    if status == "successfully":
        meraki_serials = registered_serials
        if debug:
            for switch in registered_switches:
                print(f"In register_switch status = {status}")
                print(f"switch = {switch}")
                print("switch['Migration Status'] = " + f"{switch['migration_status']}")
    if debug:
        print(f"After registering switches, meraki_serials = {meraki_serials}")
    # Report back on what happened
    if called == "":
        timing = ""
        if not len(registered_switches) == 0:
            vals = reduce(
                lambda x, y: x + y, [list(dic.values()) for dic in registered_switches]
            )
            header = registered_switches[0].keys()
            rows = [x.values() for x in registered_switches]
            thing = tabulate(rows, header)
            if times:
                t = "\n=== That registraion took "
                t += "%s seconds" % str(round((time.time() - start_time), 2))
                timing = t
            note = ""
            if issues:
                note = "\n\n" + "\n".join(issues)
            if BOT:
                payload = "```\n%s" % thing + "\n```" + timing
                r = f"We **{status}** registered **{vals.count('Registered')}"
                r += "** switch"
                r += f"{'es' if (vals.count('Registered') > 1) else ''}"
                return r + f":\n{payload}" + note
            else:
                payload = "\n%s" % thing + timing
                r = f"\n\nWe {status} registered {vals.count('Registered')} "
                r += f"switch{'es' if (vals.count('Registered') > 1) else ''}"
                return r + f":\n{payload}" + note
        else:
            payload = ""
            for issue in issues:
                payload += issue + "\n"
            r = f"We were unsuccessful registering {host}:\n\n{payload}"
            return r + timing
    else:
        return (status, issues, registered_switches)


def claim_switch(incoming_msg, dashboard, dest_net=meraki_net, serials=meraki_serials, called=""):
    """
    This function will Claim a Registered Catalyst switch in the Dashboard.
    :param incoming_msg: The incoming message object from Teams
    :param dest_net: The Meraki destination Network to claim devices to
    :param serials: The list of Meraki serial numbers to claim
    :param called: Indicates if this was called from a function vs greeting
    :return: A text/markdown based reply if called from greeting (called="")
    :      : Or, status, issues, already claimed & claimed switch lists
    """

    start_time = time.time()

    global host_id, meraki_net, meraki_serials, meraki_net_name, times
    issues = ""
    if debug:
        print(f"At start of claim_switch, serials = {serials}")
    claimed_switches = serials
    ac_switches = list()
    bad_switches = list()

    if dest_net == "":
        return "claim_switch was called with no dest_net!"
    if debug:
        p = len([d["name"] for d in meraki_networks if d["id"] == dest_net])
        print(
            "len([d['name'] for d in meraki_networks if d['id']=="
            + f"{dest_net}]) = {p}"
        )
    if (not dest_net == meraki_net) and (
        not len([d["name"] for d in meraki_networks if d["id"] == dest_net]) == 1
    ):
        r = "claim_switch was called with a dest_net that doesn't"
        return r + " match any of your Meraki Network IDs!"
    if len(serials) == 0:
        return "claim_switch was called with no serials!"

    issues, bad_switches, ac_switches, claimed_switches = Claim(
        dashboard, dest_net, serials, ios_username, ios_password, ios_secret
    )

    # If the claim went fine, update the global stateful variables for later
    if len(bad_switches) == 0:
        meraki_net = dest_net
        meraki_serials = serials
        test_net = [d["name"] for d in meraki_networks if d["id"] == meraki_net]
        if not len(test_net) == 0:
            meraki_net_name = test_net[0]

    # Report back on what happened

    # If we were not called from another function,
    # if there were no Bad_switches, return a nice message
    # otherwise return the list of issues
    if called == "":
        if len(bad_switches) == 0:
            r = "I was able to claim those switches to your Network.\n"
            if times:
                r += "=== That claiming process took "
                r += "%s seconds" % str(round((time.time() - start_time), 2))
            return r
        else:
            return issues
    # If we were called from another function,
    # return the list of issues, lists of claimed & already claimed switches
    # and a status of "OK" if no bad switches, or a status of "Issues"
    else:
        status = "Ok" if len(bad_switches) == 0 else "Issues"
        if debug:
            print("At the end of our claim_switch call:")
            print(f"status = {status}")
            print(f"issues = {issues}")
            print(f"ac_switches = {ac_switches}")
            print(f"claimed_switches = {claimed_switches}")
        return (status, issues, ac_switches, claimed_switches)


def translate_switch(
    incoming_msg,
    dashboard,
    config=config_file,
    host=host_id,
    serials: list[int | str] = meraki_serials,
    verb="translate",
):
    """
    This function will translate a Catalyst switch stack config to features in
    an existing set of Meraki switches.
    :param incoming_msg: The incoming message object from Teams
    :param config: The incoming config filespec
    :param host: The incoming hostname or IP address
    :param serials: The incoming list of Meraki serials
    :param verb: 'translate' or 'migrate' depending on how we were called
    :return: A text or markdown based reply
    """
    start_time = time.time()

    # Import the global stateful variables
    global config_file, host_id, meraki_org, meraki_serials
    global meraki_urls, nm_list, meraki_api_key, unified_os, times

    if debug:
        print(f"In translate, config_file = {config_file}")
    # Clear some variables for the next step
    switch_name = ""
    # Check whether or not we were passed a list of up to
    # 8 Meraki serial numbers
    if len(serials) > 8:
        return "A switch stack can contain a maximum of 8 switches."
    # Update the global stateful variable for later
    meraki_serials = serials
    if debug:
        print(f"meraki_serials = {meraki_serials}")
    # Check whether or not we were passed a config filespec

    switch_name = ""
    if not config == "":
        ext = os.path.splitext(config)[1]
        switch_name = os.path.split(config)[1].replace(ext, "")
    elif not config_file == "":
        ext = os.path.splitext(config_file)[1]
        switch_name = os.path.split(config_file)[1].replace(ext, "")
    if config == "" and config_file == "":
        if host == "" and host_id == "":
            return "You need to enter either a host or a config filespec."
        else:
            if host == "":
                host = host_id
            host_id = host
            support_status = check_host_minimum_ios(
                host_id, ios_username, ios_password, ios_port, ios_secret
            )
            if support_status.reason != "met":
                return minimum_ios_message(support_status)
            # SSH to the switch with netmiko, read the config, grab the
            # switch name, write the config out to a file using the switch
            # name as part of the filespec
            if debug:
                print(f"meraki_serials = {meraki_serials}")
            session_info = {
                "device_type": "cisco_xe",
                "host": host_id,
                "username": ios_username,
                "password": ios_password,
                "port": ios_port,  # optional, defaults to 22
                "secret": ios_secret,  # optional, defaults to ''
            }
            if debug:
                print(f"session_info = {session_info}")
            # Get the config file from a switch/stack
            switch_name, config = GetConfig(
                host_id, ios_username, ios_password, ios_port, ios_secret
            )

            # Grab the uplink module in each switch
            nm_list = GetNmList(
                host_id, ios_username, ios_password, ios_port, ios_secret
            )
    else:
        if config == "":
            config = config_file

    # Update the global stateful variable for later
    config_file = config

    # If we don't have an nm_list, create an empty list 9 switches long
    # which is larger than a stack so we can test for this later
    if nm_list == []:
        nm_list = ["", "", "", "", "", "", "", "", ""]

    # Evaluate the Catalyst config and break it into lists we can work with
    Intf_list, Other_list, port_dict, switch_dict = Evaluate(
        config_file, nm_list, unified_os
    )

    # Creating a list of the downlink port configurations to push to Meraki
    ToBeConfigured = {}
    z = 0
    while z < len(Intf_list):
        interface = Intf_list[z]
        ToBeConfigured[interface] = port_dict[interface]
        z += 1

    #
    # Start the meraki config migration after confirmation from the user
    #
    blurb = "Evaluated the switch config based on encyclopedia "
    blurb += str(mc_pedia["version"]) + ", published on " + str(mc_pedia["dated"]) + "."
    if times:
        blurb += "\n--- That took "
        blurb += "%s seconds" % str(round((time.time() - start_time), 2))
    if len(nm_list) == 9:
        blurb += "\n\nSKIPPING NM MODULES, because we only had a config file"
        blurb += " to work with..."
    blurb += "\n\nPushing the translated items to the Dashboard in a large"
    blurb += " batch.\nThis will take a while, but I'll message you"
    blurb += " when I'm done..."
    if BOT:
        create_message(incoming_msg.roomId, blurb)
    else:
        print(blurb)

    port_cfg_start_time = time.time()

    configured_ports, unconfigured_ports, port_dict, meraki_urls, meraki_net = (
        MerakiConfig(
            dashboard,
            meraki_org,
            switch_name,
            meraki_serials,
            port_dict,
            Intf_list,
            Other_list,
            switch_dict,
            nm_list,
            unified_os,
            meraki_api_key,
        )
    )

    if debug:
        print(f"configured_ports = {configured_ports}")
        print(f"unconfigured_ports = {unconfigured_ports}")
    path = os.path.join(os.getcwd(), DEFAULT_FILES_FOLDER)
    with open(os.path.join(path, switch_name + ".pd"), "w") as file:
        file.write(json.dumps(port_dict))  # use `json.loads` to reverse
        file.close()

    x = 0
    r = ""
    if debug:
        print(f"meraki_serials = {meraki_serials}")
    last_sw = 1 if len(meraki_serials) == 1 else len(meraki_serials) + 1
    while x <= last_sw - 1:
        switch = "stack" if (len(meraki_serials) > 1 and x == last_sw - 1) else x
        if last_sw == 1:
            r += "\nFor the switch [" + str(meraki_serials[switch]) #type: ignore
            r += "](" + meraki_urls[switch] + "):\n"
        else:
            if len(meraki_serials) > 1 and x == last_sw - 1:
                r += "\nFor switch stack " + switch_name + ":\n"
            else:
                r += "\nFor switch " + str(x + 1) + " [" + str(meraki_serials[switch]) #type: ignore
                r += "](" + meraki_urls[switch] + "):\n"
        if len(configured_ports[switch]) > 0:
            if BOT:
                r += "We were able to **successfully** " + verb + " ports: "
            else:
                r += "We were able to successfully " + verb + " ports: "
            c_port = 0
            while c_port <= len(configured_ports[switch]) - 2:
                r += configured_ports[switch][c_port] + ", "
                c_port += 1
            r += configured_ports[switch][c_port] + "\n\n"
        if len(unconfigured_ports[switch]) > 0:
            if BOT:
                r += "We were **unable** to " + verb + " ports: "
            else:
                r += "We were unable to " + verb + " ports: "
            u_port = 0
            while u_port <= len(unconfigured_ports[switch]) - 2:
                r += unconfigured_ports[switch][u_port] + ", "
                u_port += 1
            r += unconfigured_ports[switch][u_port] + "\n\n"
        x += 1

    if verb == "translate" and times:
        r += "\n--- Pushing to Dashboard took "
        r += "%s seconds" % str(round((time.time() - port_cfg_start_time), 2))
        r += "\n=== That entire translation took "
        r += "%s seconds" % str(round((time.time() - start_time), 2))
    return r


def migrate_switch(incoming_msg, dashboard, host=host_id, dest_net=meraki_net):
    """
    This function will register a Catalyst switch stack to the Meraki
    Dashboard, claim the stack to a Meraki Network, then translate the
    switch stack config to Meraki. Once finished, the user can edit the
    Meraki stack config before manually initiating migration to Cloud
    Management via "service meraki start" CLI command on the stack.
    :param incoming_msg: The incoming message object from Teams
    :param host: The incoming hostname or IP address
    :param dest_net: The Meraki destination Network to claim devices to
    :return: A text or markdown based reply
    """

    start_time = time.time()

    # Import the global stateful variables
    global config_file, host_id, nm_list, unified_os, times
    global meraki_net, meraki_net_name, meraki_serials, meraki_urls

    # Clear some variables for the next step
    switch_name = ""
    status = ""
    issues = ""
    ac_switches = list()
    claimed_switches = list()

    if debug:
        print("At the start of migrate_switch:")
        print(f"host = {host}")
        print(f"dest_net = {dest_net}")
    # Were we passed a hostname or IP address?
    if host == "":
        return "You need to provide a host."
    else:
        # We were passed a hostname or IP address...
        host_id = host
    support_status = check_host_minimum_ios(
        host_id, ios_username, ios_password, ios_port, ios_secret
    )
    if support_status.reason != "met":
        return minimum_ios_message(support_status)

    # Were we passed a Meraki Network?
    if dest_net == "":
        return "You need to provide a Meraki network."
    else:
        # We were passed a network name
        # Is it in the list of the user's Meraki networks?
        if debug:
            print(f"meraki_networks = {meraki_networks}")
        if not dest_net == meraki_net:
            if debug:
                print(f"In migrate_switch, {dest_net} != {meraki_net}")
            if (
                not len([d["name"] for d in meraki_networks if d["id"] == dest_net])
                == 1
            ):
                if debug:
                    print(
                        f"In migrate_switch, {dest_net} != "
                        + f"{[d['id'] for d in meraki_networks]}"
                    )
                return "You need to provide a Meraki network."
        # It was in the list of the user's Meraki networks, so save it
        meraki_net = dest_net
        test_net = [d["name"] for d in meraki_networks if d["id"] == meraki_net]
        if not len(test_net) == 0:
            meraki_net_name = test_net[0]

    # Get the config file from a switch/stack
    switch_name, config = GetConfig(
        host_id, ios_username, ios_password, ios_port, ios_secret
    )

    blurb = "Logged in to " + host_id + ", grabbed a copy of the running "
    blurb += "config and saved it as " + switch_name + ".cfg."
    if times:
        blurb += "\n--- That took "
        blurb += "%s seconds" % str(round((time.time() - start_time), 2))
    if BOT:
        create_message(incoming_msg.roomId, blurb)
    else:
        print(blurb)

    # Update the global stateful variable for later
    config_file = config

    # Register the switch stack to the Meraki dashboard
    if debug:
        print(
            "in migrate before register_switch, meraki_serials = " + f"{meraki_serials}"
        )

    register_start_time = time.time()

    status, issues, registered_switches = register_switch(
        incoming_msg, dashboard, host=host_id, called="yes"
    )

    if debug:
        print(
            "in migrate after register_switch, meraki_serials = " + f"{meraki_serials}"
        )

    # If we were not fully successful, just return with the report
    if not status == "successfully":
        vals = reduce(
            lambda x, y: x + y, [list(dic.values()) for dic in registered_switches]
        )
        header = registered_switches[0].keys()
        rows = [x.values() for x in registered_switches]
        thing = tabulate(rows, header)
        payload = "```\n%s" % thing
        r = f"We **{status}** registered **{vals.count('Registered')}**"
        r += f" switch{'es' if (vals.count('Registered') > 1) else ''}"
        return r + f":\n{payload}"
    string_serials = ", ".join(meraki_serials)
    blurb = "Registered " + host_id + " to Dashboard as "
    blurb += string_serials + ".\n"
    if times:
        t = "%s seconds" % str(round((time.time() - register_start_time), 2))
        blurb += "--- That took " + t
    if BOT:
        create_message(incoming_msg.roomId, blurb)
    else:
        print(blurb)
    if debug:
        print("in migrate before claim_switch, meraki_serials = " + f"{meraki_serials}")
    # Claim the switch stack to a Network in the Meraki dashboard
    claim_start_time = time.time()
    status, issues, ac_switches, claimed_switches = claim_switch(
        incoming_msg, dashboard, dest_net=meraki_net, serials=meraki_serials, called="yes"
    )
    if debug:
        print("in migrate after claim_switch, meraki_serials = " + f"{meraki_serials}")

    # If the attempt to claim the switch stack had issues, return them
    if not status == "Ok":
        return issues
    blurb = "Claimed " + string_serials + " to Meraki network "
    blurb += meraki_net_name + ".\n"
    if times:
        t = "%s seconds" % str(round((time.time() - claim_start_time), 2))
        blurb += "--- That took " + t
    if BOT:
        create_message(incoming_msg.roomId, blurb)
    else:
        print(blurb)
    if debug:
        print("in migrate before translate, meraki_serials = " + f"{meraki_serials}")
    # Translate the switch stack to the Meraki switches we just claimed
    translate_start_time = time.time()
    r = "\n\n" + translate_switch(
        incoming_msg, dashboard, config=config_file, serials=meraki_serials, verb="migrate"
    )
    blurb = "\nTranslated " + switch_name + ".cfg to Meraki switches "
    blurb += string_serials + " based on encyclopedia " + mc_pedia["version"]
    blurb += ", published on " + str(mc_pedia["dated"]) + ".\n"
    if times:
        t = "%s seconds" % str(round((time.time() - translate_start_time), 2))
        blurb += "--- That took " + t
        t = "%s seconds" % str(round((time.time() - start_time), 2))
        blurb += "\n=== For a total time of " + t
    if BOT:
        create_message(incoming_msg.roomId, blurb)
    else:
        print(blurb)
    r += "\nPlease review the configuration in Dashboard and add/modify what "
    r += "you want prior to converting the switch to Meraki Cloud Management."
    if BOT:
        r += "\n**Converting the switch will _remove all configuration_, "
        r += "so you do so at your own risk!**"
    else:
        r += "\nCONVERTING THE SWITCH WILL REMOVE ALL CONFIGURATION, "
        r += "SO YOU DO SO AT YOUR OWN RISK!"
    r += "\n To convert the switch, enter the following:\n"
    if BOT:
        if unified_os:
            r += "```\nenable\nconfig t\nservice meraki connect"
        else:
            r += "```\nenable\nservice meraki start"
    else:
        if unified_os:
            r += "\n    enable\n    config t\n    service meraki connect"
        else:
            r += "\n    enable\n    service meraki start"
    return r


def create_message(rid, msgtxt, style="markdown"):
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": "Bearer " + str(teams_token),
    }

    url = "https://api.ciscospark.com/v1/messages"
    if style == "markdown":
        data = {"roomId": rid, "markdown": msgtxt}
    else:
        data = {"roomId": rid, "html": msgtxt}
    print(f"roomId={rid}")
    response = requests.post(url, json=data, headers=headers)
    print(f"response from create_message was: {response}")
    return response.json()


# Temporary function to send a message with a card attachment (not yet
# supported by webexteamssdk, but there are open PRs to add this
# functionality)
def create_message_with_attachment(rid, msgtxt, attachment):
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": "Bearer " + str(teams_token,)
    }

    url = "https://api.ciscospark.com/v1/messages"
    data = {"roomId": rid, "attachments": [attachment], "markdown": msgtxt}
    response = requests.post(url, json=data, headers=headers)
    return response.json()


def init_dry_run_argv() -> None:
    """Strip --dry-run from argv and configure dry-run Meraki session."""
    global MERAKI_DRY_RUN
    MERAKI_DRY_RUN = "--dry-run" in sys.argv
    if MERAKI_DRY_RUN:
        sys.argv = [sys.argv[0]] + [a for a in sys.argv[1:] if a != "--dry-run"]
    set_meraki_dry_run(MERAKI_DRY_RUN)
  

def init_force_pedia_refresh_argv() -> None:
    """Strip --force-pedia-refresh from argv and configure pedia refresh."""
    global FORCE_PEDIA_REFRESH
    FORCE_PEDIA_REFRESH = "--force-pedia-refresh" in sys.argv
    if FORCE_PEDIA_REFRESH:
        sys.argv = [sys.argv[0]] + [
            a for a in sys.argv[1:] if a != "--force-pedia-refresh"
        ]


def get_repo_file_commit_epoch(file_path: str) -> float | None:
    """Return the latest repo commit time for a file path."""
    commits_url = f"{REPO_API_URL}/commits"
    try:
        response = requests.get(
            commits_url,
            params={"path": file_path, "per_page": 1},
            timeout=10,
        )
    except requests.RequestException as error:
        if debug:
            print(f"Unable to query commit date for {file_path}: {error}")
        return None

    if response.status_code != 200:
        if debug:
            print(
                f"Unable to query commit date for {file_path}: "
                f"{response.status_code}"
            )
        return None

    commit_data = response.json()
    if not commit_data:
        return None

    date_text = commit_data[0].get("commit", {}).get("committer", {}).get("date")
    if not date_text:
        return None

    try:
        return datetime.fromisoformat(date_text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        if debug:
            print(f"Invalid commit date returned for {file_path}: {date_text}")
        return None


def should_download_repo_file(local_file: str, repo_file: str) -> bool:
    """Return True only when local file is missing or older than the repo copy."""
    if FORCE_PEDIA_REFRESH or not os.path.exists(local_file):
        return True

    repo_commit_epoch = get_repo_file_commit_epoch(repo_file)
    if repo_commit_epoch is None:
        return False

    return os.path.getmtime(local_file) < repo_commit_epoch


def init_debug_flags() -> None:
    global DEBUG, DEBUG_MAIN, PDF, debug
    try:
        user_info = import_module("mc_user_info")
    except ImportError:
        DEBUG = False
        DEBUG_MAIN = False
        PDF = False
    else:
        DEBUG = getattr(user_info, "DEBUG", False)
        DEBUG_MAIN = getattr(user_info, "DEBUG_MAIN", False)
        PDF = getattr(user_info, "PDF", False)
    debug = DEBUG or DEBUG_MAIN


def init_mc_pedia() -> None:
    global mc_pedia
    dstFile = "mc_pedia2.py"
    repo_pedia_path = "src/merakicat/mc_pedia2.py"
    filetime = (
        time.strftime("%a, %d %b %Y %X GMT", time.gmtime(os.path.getmtime(dstFile)))
        if os.path.exists(dstFile)
        else "not found"
    )
    if debug:
        print("Checking if the local encyclopedia is older than the repo copy.")
        print("File Last Modified: {0}".format(filetime))
    url = f"{REPO_RAW_URL}/main/src/merakicat/mc_pedia2.py"
    if debug:
        print(f"url = {url}")
    if should_download_repo_file(dstFile, repo_pedia_path):
        if debug:
            print("Downloading a fresh copy of the encyclopedia.")
        try:
            urllib.request.urlretrieve(url, dstFile)
            if debug:
                print("Done.")
        except HTTPError as error:
            print(error.status, error.reason)
        except URLError as error:
            print(error.reason)
        except TimeoutError:
            print("Request timed out")
    else:
        if debug:
            print("Local encyclopedia is newer than repo. Skipping download.")

    compat_dst_file = "mc_min_ios_version.py"
    repo_compat_path = "src/merakicat/mc_min_ios_version.py"
    compat_url = f"{REPO_RAW_URL}/main/src/merakicat/mc_min_ios_version.py"
    if should_download_repo_file(compat_dst_file, repo_compat_path):
        try:
            urllib.request.urlretrieve(compat_url, compat_dst_file)
            if debug:
                print("Updated minimum IOS version compatibility file.")
        except HTTPError as error:
            # Silently skip if the compatibility file is not in the repo.
            if error.status != 404:
                print(error.status, error.reason)
        except URLError as error:
            print(error.reason)
        except TimeoutError:
            print("Request timed out")

    mc_pedia = import_module("mc_pedia2").mc_pedia


def set_bot_from_argv() -> None:
    """Set global BOT from whether the process was launched with no CLI arguments."""
    global BOT
    BOT = len(sys.argv) == 1


def cli_startup_kind() -> Literal["bot", "cli_help", "cli_demo", "cli_full"]:
    """Classify startup after dry-run argv normalization; BOT must already be set."""
    if BOT:
        return "bot"
    text = " ".join(sys.argv[1:]).lower().strip()
    if text in ("help", "?"):
        return "cli_help"
    if text == "demo report":
        return "cli_demo"
    return "cli_full"


def apply_runtime_globals_from_config() -> None:
    """Copy IOS, Meraki, and (when BOT) Teams settings from mc_config into module globals."""
    global ios_username, ios_password, ios_secret, ios_port, meraki_api_key, meraki_org_name
    global bot_email, bot_app_name, teams_token, teams_emails, bot_fname
    ios_username = IOS_USERNAME
    ios_password = IOS_PASSWORD
    ios_secret = IOS_SECRET
    ios_port = IOS_PORT
    meraki_api_key = MERAKI_API_KEY
    meraki_org_name = MERAKI_ORG_NAME
    if BOT:
        bot_email = TEAMS_BOT_EMAIL
        bot_app_name = TEAMS_BOT_APP_NAME
        teams_token = TEAMS_BOT_TOKEN
        teams_emails = TEAMS_EMAILS
        bot_fname = bot_app_name.split()[0].strip()


def init_shared_globals() -> None:
    global payload, organizations, api, configured_ports, unconfigured_ports, unified_os
    global command_line_msg, times, report, detailed
    global config_file, host_id, nm_list, meraki_serials, meraki_orgs, meraki_networks
    global meraki_org, meraki_net, meraki_net_name, meraki_urls
    payload = {}
    organizations = {}
    api = ""
    payload = None
    configured_ports = defaultdict(list)
    unconfigured_ports = defaultdict(list)
    unified_os = False
    command_line_msg = Response()
    times = False
    report = False
    detailed = False
    config_file = ""
    host_id = ""
    nm_list = list()
    meraki_serials = list()
    meraki_orgs = list()
    meraki_networks = list()
    meraki_org = ""
    meraki_net = ""
    meraki_net_name = ""
    meraki_urls = list()


def init_dashboard_and_meraki_org():
    global meraki_orgs, meraki_networks, meraki_org
    if debug:
        print("Trying to setup a dashboard instance")
    dashboard_api = meraki.DashboardAPI(
        api_key=meraki_api_key, output_log=False, suppress_logging=True
    )
    if MERAKI_DRY_RUN:
        apply_dry_run_session(dashboard_api)

    if debug:
        print("Got it, now trying to get the list of Orgs")
    try:
        meraki_orgs = dashboard_api.organizations.getOrganizations()
    except meraki.exceptions.APIError:
        print("We were unable to get the list of Orgs.")
        sys.exit()
    if debug:
        print(f"meraki_orgs = {meraki_orgs}")
    x = 0
    while x <= len(meraki_orgs) - 1:
        if meraki_orgs[x]["name"] == meraki_org_name:
            try:
                raw_nets = dashboard_api.organizations.getOrganizationNetworks(
                    organizationId=meraki_orgs[x]["id"]
                )
            except meraki.exceptions.APIError:
                print(
                    "We were unable to get the list of networks"
                    + f" for {meraki_orgs[x]['name']}."
                )
                sys.exit()
            if debug:
                print(raw_nets)
            y = 0
            while y <= len(raw_nets) - 1:
                meraki_networks.append(raw_nets[y])
                y += 1
            break
        x += 1
    if debug:
        print(f"meraki_networks = {meraki_networks}")

    matched_org = None
    for org in meraki_orgs:
        if org.get("name") == meraki_org_name:
            matched_org = org
            break
    if matched_org:
        print(f"Connected to organization: {meraki_org_name}\n")
        meraki_org = matched_org["id"]
        if debug:
            print(f"meraki_org = {meraki_org}")
            print(f"meraki_org_name = {meraki_org_name}")
    else:
        print(f'Error: No organization found matching "{meraki_org_name}".')
        sys.exit()

    return dashboard_api


def init_webex_bot_if_bot(dashboard_api) -> None:
    global bot
    if not BOT:
        return
    if debug:
        print(f"teams_emails = {teams_emails}")
    bot = WebexBot(
        teams_token,
        bot_name=bot_app_name,
        # Comment out the approved_users lines if you don't care...
        approved_users=teams_emails,
        # approved_domains=[],
        # approved_rooms=[],
        threads=False,
        help_command=RunHelp(dashboard_api),
        log_level="ERROR",
    )


def register_bot_commands_or_cli_help(dashboard_api: meraki.DashboardAPI | None) -> None:
    global bot_commands, command_list
    if BOT:
        bot_commands = list(list())
        bot_commands.extend(
            [
                ["* **help**", "Get help."],
                [
                    "* **check [network _Meraki network name_] [with timing] \
[with details]**",
                    "Check the configs of cloud monitored Catalyst switches \
for both translatable and possible Meraki features",
                ],
                [
                    "* **check _drag-and-drop files_ [with timing] [with details]**",
                    "Check one or more Catalyst switch config files for both \
translatable and possible Meraki features",
                ],
                [
                    "* **check [host _FQDN or IP address_ | file _filespec_] \
[with timing] [with details]**",
                    "Check a Catalyst switch config for both translatable \
and possible Meraki features",
                ],
                [
                    "* **register [host _FQDN or IP address_] [with timing] \
[with details]**",
                    "Register a Catalyst switch to the Meraki Dashboard",
                ],
                [
                    "* **claim [_Meraki serial numbers_] [to _Meraki network \
name_] [with timing]**",
                    "Claim Catalyst switches to a Meraki Network",
                ],
                [
                    "* **translate [host _FQDN or IP address_ | file _filespec_] \
[to _Meraki serial numbers_] [with timing]**",
                    "Translate a Catalyst switch config from a file or host to claimed \
Meraki serial numbers",
                ],
                [
                    "* **migrate [host _FQDN or IP address_] [to _Meraki network name_] \
[with timing]**",
                    "Migrate a Catalyst switch to a Meraki switch - register, claim & \
translate",
                ],
                [
                    "* **get networks**",
                    "List all Meraki networks in the configured organization",
                ],
                [
                    "* **demo report**",
                    "Create a demo report for all features currently in the feature \
encyclopedia",
                ],
            ]
        )
        bot.add_command(RunHello(dashboard_api))
        bot.add_command(RunHelp(dashboard_api))
        bot.add_command(RunCheck(dashboard_api))
        bot.add_command(RunRegister(dashboard_api))
        bot.add_command(RunClaim(dashboard_api))
        bot.add_command(RunTranslate(dashboard_api))
        bot.add_command(RunMigrate(dashboard_api))
        bot.add_command(RunDemo(dashboard_api))
    else:
        command_list = list(list())
        command_list.extend(
            [
                ["help", "This list of commands"],
                [
                    "check network <Meraki network name> [with timing] [with details]",
                    "Check the configs of cloud monitored Catalyst switches for both \
translatable and possible Meraki features",
                ],
                [
                    "check host <FQDN or IP address> | file <filespec> [with timing] \
[with details]",
                    "Check a Catalyst switch config for both translatable and possible \
Meraki features",
                ],
                [
                    "check hosts <filespec> [with timing]",
                    "Check a list of switches specified in a CSV or Excel file (use `hosts_template.xlsx` as a template)",
                ],
                [
                    "get cloud-id <FQDN or IP address> [with timing]",
                    "Get the Cloud ID for a Catalyst switch",
                ],
                [
                    "get cloud-ids <filespec> [with timing]",
                    "Get Cloud IDs for hosts listed in a CSV or Excel file (use `hosts_template.xlsx` as a template)",
                ],
                [
                    "get networks",
                    "List all Meraki networks in the configured organization",
                ],
                [
                    "register host <FQDN or IP address> [with timing]",
                    "Register a Catalyst switch to the Meraki Dashboard",
                ],
                [
                    "claim <Meraki serial numbers> to <Meraki network name> [with \
timing]",
                    "Claim Catalyst switches to a Meraki Network",
                ],
                [
                    "translate host <FQDN or IP address> | file <filespec> to <Meraki \
serial numbers> [with timing]",
                    "Translate a Catalyst switch config from a file or host to claimed \
Meraki serial numbers",
                ],
                [
                    "migrate host <FQDN or IP address> to <Meraki network name> [with \
timing]",
                    "Migrate a Catalyst switch to a Meraki switch - register, claim & \
translate",
                ],
                [
                    "demo report",
                    "Create a demo report for all features currently in the feature \
encyclopedia",
                ],
            ]
        )


def initialize_merakicat() -> meraki.DashboardAPI | None:
    tabulate.PRESERVE_WHITESPACE = True  # type: ignore
    init_dry_run_argv()
    init_force_pedia_refresh_argv()
    init_debug_flags()
    set_bot_from_argv()
    kind = cli_startup_kind()

    # Don't need to validate environment variables for CLI help or demo report
    if kind == "cli_help":
        init_shared_globals()
        register_bot_commands_or_cli_help(None)
        return None

    if kind == "cli_demo":
        init_mc_pedia()
        init_shared_globals()
        register_bot_commands_or_cli_help(None)
        return None

    init_mc_pedia()
    validate(BOT, require_operational=True)
    apply_runtime_globals_from_config()
    init_shared_globals()
    dashboard_api = init_dashboard_and_meraki_org()
    init_webex_bot_if_bot(dashboard_api)
    register_bot_commands_or_cli_help(dashboard_api)
    return dashboard_api


def main() -> None:
    dashboard_api = initialize_merakicat()
    if BOT:
        bot.run()
    else:
        if debug:
            print(f"The number of command line args is {len(sys.argv) - 1}")
        args = sys.argv
        del args[0]
        if debug:
            print(f"The args are: {str(args)}")
        text = " ".join(args)
        if debug:
            print(f"The user input was: {text}")
        command_line_msg.text = text
        if debug:
            print(f"command_line_msg = {command_line_msg}")
        print(greeting(command_line_msg, dashboard_api).markdown)


if __name__ == "__main__":
    main()
