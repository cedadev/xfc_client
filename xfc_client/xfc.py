#! /usr/bin/env python
"""Command line tool for interacting with the JASMIN transfer cache (XFC) for users who are
logged into JASMIN and have full JASMIN accounts."""

# Author : Neil R Massey
# Date   : 12/05/2017

import sys, os
import argparse
import requests
import json
import dateutil.parser
import calendar

from math import log
from xfc_client import VERSION

# switch off warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class settings:
    """Settings for the xfc command line tool."""

    # location of the xfc_control server / app
    XFC_SERVER_URL = "https://xfc.jasmin.ac.uk/xfc_control"
    XFC_SERVER_URL = "http://127.0.0.1:8000/xfc_control"
    XFC_API_URL = XFC_SERVER_URL + "/api/v1.1/"
    USER = os.environ["USER"]
    VERSION = VERSION  # version of this software
    VERIFY = False


unit_list = list(
    zip(["bytes", "kB", "MB", "GB", "TB", "PB", "EB"], [0, 0, 1, 1, 1, 1, 1])
)


def sizeof_fmt(num):
    """Human friendly file size"""
    if num > 1:
        exponent = min(int(log(num, 1024)), len(unit_list) - 1)
        quotient = float(num) / 1024**exponent
        unit, num_decimals = unit_list[exponent]
        format_string = "{:>5.%sf} {}" % (num_decimals)
        return format_string.format(quotient, unit)
    elif num == 1:
        return "1 byte"
    else:
        return "0 bytes"


class bcolors:
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    INVERT = "\033[7m"
    ENDC = "\033[0m"


def user_not_initialized_message():
    sys.stdout.write(
        bcolors.RED
        + "** ERROR ** - User "
        + settings.USER
        + " not initialised yet."
        + bcolors.ENDC
        + "  Run "
        + bcolors.YELLOW
        + "xfc init"
        + bcolors.ENDC
        + " first.\n"
    )


def print_response_error(response):
    """Print a concise summary of the error, rather than a whole output of html"""
    for il in response.content.split("\n"):
        if "Exception" in il:
            print(il)


def error_from_response(response):
    try:
        data = response.json()
        if "error" in data:
            sys.stdout.write(
                bcolors.RED + "** ERROR ** - " + data["error"] + bcolors.ENDC + "\n"
            )
    except:
        sys.stdout.write(
            bcolors.RED
            + "** ERROR ** "
            + str(response.status_code)
            + bcolors.ENDC
            + "\n"
        )


def do_init(email=""):
    """Send the HTTP request (POST) to initialize a user's cache space."""
    url = settings.XFC_API_URL + "user"
    data = {"name": settings.USER}
    if email != "":
        data["email"] = email

    response = requests.post(url, data=json.dumps(data), verify=settings.VERIFY)
    # check the response code
    if response.status_code == 200:
        data = response.json()
        sys.stdout.write(
            bcolors.GREEN
            + "** SUCCESS ** - user initialised with:\n"
            + bcolors.ENDC
            + "    Username            : "
            + data["name"]
            + "\n"
            + "    Email               : "
            + data["email"]
            + "\n"
            + "    Temporal Quota (TQ) : "
            + sizeof_fmt(data["quota_size"])
            + " days\n"
            + "    Hard Quota (HQ)     : "
            + sizeof_fmt(data["hard_limit_size"])
            + "\n"
            + "    Path                : "
            + data["cache_path"]
            + "\n"
        )
    else:
        sys.stdout.write(
            bcolors.RED
            + "** ERROR ** - cannot initialise user "
            + settings.USER
            + bcolors.ENDC
            + "\n"
        )
        error_from_response(response)


def do_email(email=""):
    """Update the email address of the user by sending a PUT request if an email is
    given, or return the email if no email supplied."""
    url = settings.XFC_API_URL + "user?name=" + settings.USER
    if email != "":
        data = {"name": settings.USER, "email": email}
        response = requests.put(url, data=json.dumps(data), verify=settings.VERIFY)
        if response.status_code == 200:
            data = response.json()
            sys.stdout.write(
                bcolors.GREEN
                + "** SUCCESS ** - user email updated to: "
                + data["email"]
                + bcolors.ENDC
                + "\n"
            )
        elif response.status_code == 404:
            user_not_initialized_message()
        else:
            error_from_response(response)
    else:
        data = {"name": settings.USER}
        response = requests.get(url, data=json.dumps(data), verify=settings.VERIFY)
        if response.status_code == 200:
            data = response.json()
            sys.stdout.write(data["email"] + "\n")
        elif response.status_code == 404:
            user_not_initialized_message()
        else:
            error_from_response(response)


def do_info():
    """(re)print the info you get on initialising a user"""
    url = settings.XFC_API_URL + "user?name=" + settings.USER
    response = requests.get(url, verify=settings.VERIFY)
    if response.status_code == 200:
        data = response.json()
        sys.stdout.write(
            bcolors.GREEN
            + "** SUCCESS ** - user info:\n"
            + bcolors.ENDC
            + "    Username            : "
            + data["name"]
            + "\n"
            + "    Email               : "
            + data["email"]
            + "\n"
            + "    Temporal Quota (TQ) : "
            + sizeof_fmt(data["quota_size"])
            + " days\n"
            + "    Hard Quota (HQ)     : "
            + sizeof_fmt(data["hard_limit_size"])
            + "\n"
            + "    Path                : "
            + data["cache_path"]
            + "\n"
        )
    elif response.status_code == 404:
        user_not_initialized_message()
    else:
        error_from_response(response)


def do_path():
    """Send the HTTP request (GET) and process to get the path to the user space on the
    cache."""
    url = settings.XFC_API_URL + "user?name=" + settings.USER
    response = requests.get(url, verify=settings.VERIFY)
    if response.status_code == 200:
        data = response.json()
        sys.stdout.write(data["cache_path"] + "\n")
    elif response.status_code == 404:
        user_not_initialized_message()
    else:
        error_from_response(response)


def do_quota():
    """Send the HTTP request (GET) and process to get the remaining quota and total
    quota for the user."""
    url = settings.XFC_API_URL + "user?name=" + settings.USER
    response = requests.get(url, verify=settings.VERIFY)
    if response.status_code == 200:
        data = response.json()
        used = data["quota_used"]
        allocated = data["quota_size"]
        total = data["total_used"]
        hard_limit = data["hard_limit_size"]
        sys.stdout.write(
            bcolors.MAGENTA
            + "-----------------------------\n"
            + "Quota for user: "
            + settings.USER
            + "\n"
            + "-----------------------------\n"
            + bcolors.ENDC
            + "  Temporal Quota (TQ)\n"
            "    Used      : "
            + sizeof_fmt(used)
            + " days\n"
            + "    Allocated : "
            + sizeof_fmt(allocated)
            + " days\n"
        )
        if allocated - used < 0:
            sys.stdout.write(bcolors.RED)
        else:
            sys.stdout.write(bcolors.GREEN)
        sys.stdout.write(
            "    Remaining : " + sizeof_fmt(allocated - used) + " days\n" + bcolors.ENDC
        )

        sys.stdout.write("-----------------------------\n")
        sys.stdout.write("  Hard Quota (HQ)\n")
        sys.stdout.write("    Used      : " + sizeof_fmt(total) + "\n")
        sys.stdout.write("    Allocated : " + sizeof_fmt(hard_limit) + "\n")
        if hard_limit - total < 0:
            sys.stdout.write(bcolors.RED)
        else:
            sys.stdout.write(bcolors.GREEN)
        sys.stdout.write(
            "    Remaining : " + sizeof_fmt(hard_limit - total) + bcolors.ENDC + "\n"
        )

    elif response.status_code == 404:
        user_not_initialized_message()
    else:
        error_from_response(response)


def do_notify():
    """Send the HTTP request (PUT) to switch on / off notifications for the user."""
    # first get the status of notifications
    url = settings.XFC_API_URL + "user?name=" + settings.USER
    response = requests.get(url, verify=settings.VERIFY)
    if response.status_code == 200:
        data = response.json()
        notify = data["notify"]
        # update to inverse
        put_data = {"name": settings.USER, "notify": not notify}
        response = requests.put(url, data=json.dumps(put_data), verify=settings.VERIFY)
        if response.status_code == 200:
            data = response.json()
            sys.stdout.write(
                bcolors.GREEN
                + "** SUCCESS ** - user notifications updated to: "
                + ["off", "on"][put_data["notify"]]
                + bcolors.ENDC
                + "\n"
            )
        else:
            error_from_response(response)

    elif response.status_code == 404:
        user_not_initialized_message()
    else:
        error_from_response(response)


def do_predict():
    """Send the HTTP request to the service which predicts when the user will exceed
    their quota"""
    url = settings.XFC_API_URL + "predict?name=" + settings.USER
    response = requests.get(url, verify=settings.VERIFY)
    if response.status_code == 200:
        pass
    elif response.status_code == 404:
        user_not_initialized_message()
    else:
        error_from_response(response)


def main():
    # help string for the command parsing
    command_help = (
        "Available commands are : \n"
        + "init     : Initialize the transfer cache for your JASMIN login\n"
        + "email    : view, set or update email address\n"
        + "info     : Get the user info\n"
        + "notify   : Switch on / off email notifications of scheduled deletions (default is off)\n"
        + "path     : Get the path to your storage area in the transfer cache\n"
        + "quota    : Get the remaining free space in your quota\n"
        + "predict  : Predict when the quota will be exceeded based on the current files\n"
    )

    parser = argparse.ArgumentParser(
        prog="XFC",
        formatter_class=argparse.RawTextHelpFormatter,
        description="JASMIN transfer cache (XFC) command line tool",
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + settings.VERSION
    )
    parser.add_argument(
        "cmd",
        choices=[
            "init",
            "path",
            "email",
            "info",
            "quota",
            "notify",
            "predict",
            "version",
        ],
        help=command_help,
        metavar="command",
    )
    parser.add_argument(
        "--email",
        action="store",
        default="",
        help="Email address for user in the init and email commands.",
    )

    args = parser.parse_args()

    if args.email:
        email = args.email
    else:
        email = ""

    # switch on the commands
    if args.cmd == "init":
        do_init(email)
    elif args.cmd == "email":
        do_email(email)
    elif args.cmd == "info":
        do_info()
    elif args.cmd == "path":
        do_path()
    elif args.cmd == "quota":
        do_quota()
    elif args.cmd == "notify":
        do_notify()
    elif args.cmd == "predict":
        do_predict()


if __name__ == "__main__":
    main()
