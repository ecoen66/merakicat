import re
from mc_user_info import *


def Split_check_serials(user_text,search_type):
    debug = DEBUG or DEBUG_SPLIT
    maybe_serials = list()
    regex = re.compile(r"\s*to\s *", flags=re.I)
    if search_type == "Claim":
        the_rest = regex.split(user_text)[0]
        the_rest = the_rest.strip()
        if debug:
            print(f"the_rest = {the_rest}")
        if debug:
            print(f"len(the_rest) = {len(the_rest)}")
        if len(the_rest) > 14:
            regex2 = re.compile(r"claim\s *", flags=re.I)
            maybe_serials = regex2.split(the_rest)[1]
    elif search_type == "Translate":
        maybe_serials = regex.split(user_text)[1]

    if debug:
        print(f"maybe_serials = {maybe_serials}")
        
    if len(maybe_serials)==0:
        return([],"I'm sorry, but {} is not a list of Meraki serial numbers delimited by commas, spaces or semicolons.".format(the_rest))
        
    serials = re.split(';|,|\s',maybe_serials)
    if debug:
        print(f"serials = {serials}")
    x = 0
    while x <= len(serials)-1:
        if debug:
            print(f"serials[{x}] = {serials[x]}")
            print(f"len(serials[{x}]) = {len(serials[x])}")
        if not len(serials[x]) == 14:
            return([],"I'm sorry, but {} is not a list of Meraki serial numbers delimited by commas, spaces or semicolons.".format(maybe_serials))
        x+=1
    return(serials,"")