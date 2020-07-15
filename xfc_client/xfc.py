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

# switch off warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class settings:
    """Settings for the xfc command line tool."""
    # location of the xfc_control server / app
    XFC_SERVER_URL = "https://xfc.ceda.ac.uk/xfc_control"
    XFC_API_URL = XFC_SERVER_URL + "/api/v1/"
    USER = os.environ["USER"]
    VERSION = "0.4.5" # version of this software
    VERIFY = False


unit_list = list(zip(['bytes', 'kB', 'MB', 'GB', 'TB', 'PB', 'EB'],
                     [0, 0, 1, 1, 1, 1, 1]))

def sizeof_fmt(num):
    """Human friendly file size"""
    if num > 1:
        exponent = min(int(log(num, 1024)), len(unit_list) - 1)
        quotient = float(num) / 1024**exponent
        unit, num_decimals = unit_list[exponent]
        format_string = '{:>5.%sf} {}' % (num_decimals)
        return format_string.format(quotient, unit)
    elif num == 1:
        return '1 byte'
    else:
        return '0 bytes'


class bcolors:
    MAGENTA   = '\033[95m'
    BLUE      = '\033[94m'
    GREEN     = '\033[92m'
    YELLOW    = '\033[93m'
    RED       = '\033[91m'
    BOLD      = '\033[1m'
    UNDERLINE = '\033[4m'
    INVERT    = '\033[7m'
    ENDC      = '\033[0m'


def user_not_initialized_message():
    sys.stdout.write(bcolors.RED+\
                  "** ERROR ** - User " + settings.USER + " not initialised yet." + bcolors.ENDC +\
                  "  Run " + bcolors.YELLOW + "xfc.py init" + bcolors.ENDC + " first.\n")


def print_response_error(response):
    """Print a concise summary of the error, rather than a whole output of html"""
    for il in response.content.split("\n"):
        if "Exception" in il:
            print(il)


def error_from_response(response):
    try:
        data = response.json()
        if "error" in data:
            sys.stdout.write(bcolors.RED + "** ERROR ** - " + data["error"] + bcolors.ENDC + "\n")
    except:
        sys.stdout.write(bcolors.RED + "** ERROR ** " + str(response.status_code) + bcolors.ENDC + "\n")


def do_init(email=""):
    """Send the HTTP request (POST) to initialize a user's cache space."""
    url = settings.XFC_API_URL + "user"
    data = {"name" : settings.USER}
    if email != "":
        data["email"] = email

    response = requests.post(url, data=json.dumps(data), verify=settings.VERIFY)
    # check the response code
    if response.status_code == 200:
        data = response.json()
        sys.stdout.write( bcolors.GREEN+\
              "** SUCCESS ** - user initialised with:\n" + bcolors.ENDC +\
              "    Username            : " + data["name"] + "\n" +\
              "    Email               : " + data["email"] + "\n" +\
              "    Temporal Quota (TQ) : " + sizeof_fmt(data["quota_size"]) + " days\n" +\
              "    Hard Quota (HQ)     : " + sizeof_fmt(data["hard_limit_size"]) + "\n" +\
              "    Path                : " + data["cache_path"] + "\n")
    else:
        sys.stdout.write(bcolors.RED+\
              "** ERROR ** - cannot initialise user " + settings.USER + bcolors.ENDC + "\n")
        error_from_response(response)


def do_email(email=""):
    """Update the email address of the user by sending a PUT request if an email is given,
       or return the email if no email supplied."""
    url = settings.XFC_API_URL + "user?name=" + settings.USER
    if email != "":
        data = {"name" : settings.USER,
                "email": email}
        response = requests.put(url, data=json.dumps(data), verify=settings.VERIFY)
        if response.status_code == 200:
            data = response.json()
            sys.stdout.write(bcolors.GREEN+\
                  "** SUCCESS ** - user email updated to: " + data["email"] + bcolors.ENDC + "\n")
        elif response.status_code == 404:
            user_not_initialized_message()
        else:
            error_from_response(response)
    else:
        data = {"name" : settings.USER}
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
        sys.stdout.write( bcolors.GREEN+\
          "** SUCCESS ** - user info:\n" + bcolors.ENDC +\
          "    Username            : " + data["name"] + "\n" +\
          "    Email               : " + data["email"] + "\n" +\
          "    Temporal Quota (TQ) : " + sizeof_fmt(data["quota_size"]) + " days\n" +\
          "    Hard Quota (HQ)     : " + sizeof_fmt(data["hard_limit_size"]) + "\n" +\
          "    Path                : " + data["cache_path"] + "\n")
    elif response.status_code == 404:
        user_not_initialized_message()
    else:
        error_from_response(response)


def do_path():
    """Send the HTTP request (GET) and process to get the path to the user space on the cache."""
    url = settings.XFC_API_URL + "user?name=" + settings.USER
    response = requests.get(url, verify=settings.VERIFY)
    if response.status_code == 200:
        data = response.json()
        sys.stdout.write(data["cache_path"]+"\n")
    elif response.status_code == 404:
        user_not_initialized_message()
    else:
        error_from_response(response)



def do_quota():
    """Send the HTTP request (GET) and process to get the remaining quota and total quota for the user."""
    url = settings.XFC_API_URL + "user?name=" + settings.USER
    response = requests.get(url, verify=settings.VERIFY)
    if response.status_code == 200:
        data = response.json()
        used = data["quota_used"]
        allocated = data["quota_size"]
        total = data["total_used"]
        hard_limit = data["hard_limit_size"]
        sys.stdout.write(bcolors.MAGENTA+\
              "-----------------------------\n" +\
              "Quota for user: " + settings.USER + "\n" +\
              "-----------------------------\n" + bcolors.ENDC +\
              "  Temporal Quota (TQ)\n"
              "    Used      : " + sizeof_fmt(used) + " days\n" +\
              "    Allocated : " + sizeof_fmt(allocated) + " days\n")
        if allocated - used < 0:
            sys.stdout.write(bcolors.RED)
        else:
            sys.stdout.write(bcolors.GREEN)
        sys.stdout.write("    Remaining : " + sizeof_fmt(allocated - used) + bcolors.ENDC + " days\n")

        sys.stdout.write("-----------------------------\n")
        sys.stdout.write("  Hard Quota (HQ)\n")
        sys.stdout.write("    Used      : " + sizeof_fmt(total) + "\n")
        sys.stdout.write("    Allocated : " + sizeof_fmt(hard_limit) + "\n")
        if hard_limit - total < 0:
            sys.stdout.write(bcolors.RED)
        else:
            sys.stdout.write(bcolors.GREEN)
        sys.stdout.write("    Remaining : " + sizeof_fmt(hard_limit - total) + bcolors.ENDC + "\n")

    elif response.status_code == 404:
        user_not_initialized_message()
    else:
        error_from_response(response)


def print_file_list(data, full_path, info, sort_tq, sort_hq, list_limit):
    """Write out the file list held in data, optionally printing the extra info.
       The list can first be sorted by temporal quota, hard quota and limited in number of files output."""

    # check which key we should sort by
    if sort_tq:
        sorted_data = sorted(data, key=lambda fl: fl["quota_used"], reverse=True)
    elif sort_hq:
        sorted_data = sorted(data, key=lambda fl: fl["size"], reverse=True)
    else:
        sorted_data = data
    # check for limit
    if list_limit > 0:
        limited_data = sorted_data[:list_limit]
    else:
        limited_data = sorted_data

    # loop over just the limited data
    for d in limited_data:
        if info:
            # colour code size
            if d["size"] >= 1024**2 and d["size"] < 1024**3:
                sys.stdout.write(bcolors.GREEN)
            elif d["size"] >= 1024**3 and d["size"] < 1024**4:
                sys.stdout.write(bcolors.YELLOW)
            elif d["size"] >= 1024**4:
                sys.stdout.write(bcolors.RED)
            sys.stdout.write(sizeof_fmt(d["size"]))
            sys.stdout.write(bcolors.ENDC)
            # the date
            date = dateutil.parser.parse(d["first_seen"])
            sys.stdout.write("% 2i %s %d %02d:%02d  " % (date.day, calendar.month_abbr[date.month], date.year, date.hour, date.minute))
            # colour code quota
            sys.stdout.write(bcolors.MAGENTA + "(TQ)")
            sys.stdout.write(sizeof_fmt(d["quota_used"]) + "d " + bcolors.ENDC)
        if full_path:
            path = d["cache_disk"] + "/" + d["path"]
        else:
            path = d["path"]

        sys.stdout.write(path)
        # sys.stdout.write( out the other info if requested
        sys.stdout.write("\n")


def do_list(full_path, file_match, info, sort_tq, sort_hq, list_limit):
    """Send the HTTP request (GET) to list the user's files in the transfer cache."""
    url = settings.XFC_API_URL + "file?name=" + settings.USER
    if file_match:
        url += "&match=" + file_match
    # send the request
    response = requests.get(url, verify=settings.VERIFY)
    if response.status_code == 200:
        data = response.json()
        print_file_list(data, full_path, info, sort_tq, sort_hq, list_limit)
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
        put_url = settings.XFC_API_URL + "user?name=" + settings.USER
        put_data = {"name" : settings.USER,
                    "notify": not notify}
        response = requests.put(url, data=json.dumps(put_data), verify=settings.VERIFY)
        if response.status_code == 200:
            data = response.json()
            sys.stdout.write(bcolors.GREEN+\
                  "** SUCCESS ** - user notifcations updated to: " + ["off", "on"][put_data["notify"]] + bcolors.ENDC +"\n")

    elif response.status_code == 404:
        user_not_initialized_message()
    else:
        error_from_response(response)



def do_schedule(full_path, info, sort_tq, sort_hq, list_limit):
    """Send the HTTP request (GET) to list the user's files which are scheduled for deletion."""
    # Get a list of scheduled deletions for this user
    url = settings.XFC_API_URL + "scheduled_deletions?name=" + settings.USER
    response = requests.get(url, verify=settings.VERIFY)
    if response.status_code == 200:
        # HTTP API supports multiple scheduled deletions per user, even though this
        # functionality is not used yet, so just get the first
        data = response.json()[0]
        if len(data["files"]) == 0:
            sys.stdout.write(bcolors.GREEN + "No files scheduled for deletion\n" + bcolors.ENDC)
            return

        date = dateutil.parser.parse(data["time_delete"])
        # print the Scheduled message
        sys.stdout.write(bcolors.RED + "Files scheduled for deletion on")
        sys.stdout.write("% 2i %s %d %02d:%02d" % (date.day, calendar.month_abbr[date.month], date.year, date.hour, date.minute))
        sys.stdout.write(bcolors.ENDC + "\n")
        # print the files
        print_file_list(data["files"], full_path, info, sort_tq, sort_hq, list_limit)
    elif response.status_code == 404:
        user_not_initialized_message()
    else:
        error_from_response(response)


def do_predict(full_path, info, sort_tq, sort_hq, list_limit):
    """Send the HTTP request to the service which predicts when the user will exceed their quota"""
    # Get a list of scheduled deletions for this user
    url = settings.XFC_API_URL + "predict_deletions?name=" + settings.USER
    response = requests.get(url, verify=settings.VERIFY)
    if response.status_code == 200:
        # HTTP API supports multiple scheduled deletions per user, even though this
        # functionality is not used yet, so just get the first
        data = response.json()
        if len(data["files"]) == 0:
            sys.stdout.write(bcolors.GREEN + "Quota will never be exceeded!\n" + bcolors.ENDC)
            return
        date = dateutil.parser.parse(data["time_predict"])
        sys.stdout.write(bcolors.RED + "Quota is predicted to be exceeded on")
        sys.stdout.write("% 2i %s %d %02d:%02d" % (date.day, calendar.month_abbr[date.month], date.year, date.hour, date.minute))
        sys.stdout.write(" by " + sizeof_fmt(data["over_quota"]) + " days")
        sys.stdout.write(bcolors.ENDC + "\n")
        # print the Scheduled message
        sys.stdout.write("Files predicted to be deleted\n")
        # print the files
        print_file_list(data["files"], full_path, info, sort_tq, sort_hq, list_limit)
    elif response.status_code == 404:
        user_not_initialized_message()
    else:
        print_response_error(response)
        error_from_response(response)


def main():
    # help string for the command parsing
    command_help = "Available commands are : \n" +\
                   "init     : Initialize the transfer cache for your JASMIN login\n"+\
                   "email    : view, set or update email address\n"+\
                   "info     : Get the user info\n"+\
                   "notify   : Switch on / off email notifications of scheduled deletions (default is off)\n"+\
                   "path     : Get the path to your storage area in the transfer cache\n"+\
                   "quota    : Get the remaining free space in your quota\n"+\
                   "list     : List the files in your storage area in the transfer cache\n"+\
                   "schedule : List the files that are scheduled for deletion and their deletion time\n"+\
                   "predict  : Predict when the quota will be exceeded based on the current files\n"

    parser = argparse.ArgumentParser(prog="XFC", formatter_class=argparse.RawTextHelpFormatter,
                                     description="JASMIN transfer cache (XFC) command line tool")
    parser.add_argument("--version", action="version", version="%(prog)s " + settings.VERSION)
    parser.add_argument("cmd", choices=["init", "path", "email", "info", "quota", "list", "notify", "schedule", "predict", "version"],
                               help=command_help, metavar="command")
    parser.add_argument("--email", action="store", default="", help="Email address for user in the init and email commands.")
    parser.add_argument("-f", action="store_true", default=False, help="Show full paths in list / schedule / predict (default is False)")
    parser.add_argument("-m", action="store", default="", help="Pattern to match against (substring search) in list / schedule / predict")
    parser.add_argument("-i", action="store_true", default=False, help="Get file information in list / schedule / predict (default is False)")
    parser.add_argument("-t", action="store_true", default=False, help="Sort by temporal quota in list / schedule / predict (default is False)")
    parser.add_argument("-s", action="store_true", default=False, help="Sort by file size in list / schedule / predict (default is False)")
    parser.add_argument("-l", action="store", default="", help="Limit number of files output in list / schedule / predict")

    args = parser.parse_args()

    # do we show relative or full paths?
    if args.f:
        full_path = True
    else:
        full_path = False

    # file to match against
    if args.m:
        file_match = args.m
    else:
        file_match = ""

    if args.i:
        info = args.i
    else:
        info = False

    if args.email:
        email = args.email
    else:
        email = ""

    if args.t and args.s:
        sys.stdout.write(bcolors.RED + "** ERROR ** cannot sort by both Temporal Quota used (TQ) and file size (HQ)." + bcolors.ENDC + "\n")
        sys.exit()

    if args.t:
        sort_tq = args.t
    else:
        sort_tq = False

    if args.s:
        sort_hq = args.s
    else:
        sort_hq = False

    if args.l:
        list_limit = int(args.l)
    else:
        list_limit = 0

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
    elif args.cmd == "list":
        do_list(full_path, file_match, info, sort_tq, sort_hq, list_limit)
    elif args.cmd == "notify":
        do_notify()
    elif args.cmd == "schedule":
        do_schedule(full_path, info, sort_tq, sort_hq, list_limit)
    elif args.cmd == "predict":
        do_predict(full_path, info, sort_tq, sort_hq, list_limit)

if __name__ == "__main__":
    main()
