from mc_user_info import *
import os


def File_exists(filespec):
    """
    Returns True if filespec (str) can be found, and is a file.
    Also returns True and a new filespec if the file can be found in our files directory
    Also returns true if it just needs a ".cfg" appended
    """
    debug = DEBUG or DEBUG_FILE
    
    does_exist = False
    x=0
    working_file = filespec
    while x <= 1:
        if debug:
            print(f"x = {x}")
            print(f"working_file = {working_file}")
        if os.path.isfile(working_file):
            if debug:
                print(f"{working_file} does exist")
            does_exist = True
            filespec = working_file
            break
        test_file = "../files/" + os.path.split(working_file)[1]
        if debug:
            print(f"x = {x}")
            print(f"test_file = {test_file}")
        if os.path.isfile(test_file):
            if debug:
                print(f"{test_file} does exist")
            does_exist = True
            filespec = test_file
            break
        working_file += ".cfg"
        x +=1
    if debug:
        print(f"In the end, {filespec} exists = {does_exist}")
    return filespec, does_exist
