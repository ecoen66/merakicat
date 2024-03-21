from ciscoconfparse2 import CiscoConfParse
from mc_user_info import DEBUG, DEBUG_CHECKER
from mc_pedia import mc_pedia


def CheckFeatures(sw_file):
    """
    This function will check a Catalyst switch config file for feature
    mapping to Meraki.
    :param sw_file: The incoming config filespec
    :return: The hostname, supportable features, unsupported features
    :      : with more info.
    """

    debug = DEBUG or DEBUG_CHECKER

    Features_configured = list()
    aux_features_config = list()
    host_name = ""

    # Here we will go through parsing/reading Cisco Catalyst configuration
    # file and capture specific configuration
    parse = CiscoConfParse(sw_file, syntax='ios', factory=True)

    for key, val in mc_pedia['switch'].items():
        newvals = {}
        if debug:
            print(f"key,val = {key},{val}\n")
        if not val['regex'] == "":
            sample = parse.find_objects(val['regex'])
            if not sample == []:
                if debug:
                    print(f"sample = {sample}")
                exec(val.get('iosxe'), locals(), newvals)
                if debug:
                    print(f"newvals = {newvals}\n")
                if not newvals[key] == "":
                    if debug:
                        print(f"newvals[{key}] = {newvals[key]}\n")
                    if key == "switch_name":
                        host_name = newvals['host_name']
                    hold_me = list()
                    hold_me.extend([val['name'],
                                    val['support'],
                                    val['translatable']])
                    if debug:
                        print(f"hold_me = {hold_me}")
                    try:
                        hold_me.extend([val['note']])
                    except:
                        hold_me.extend([""])
                    if debug:
                        print(f"hold_me = {hold_me}")
                    try:
                        hold_me.extend([val['url']])
                    except:
                        hold_me.extend([""])
                    if debug:
                        print(f"hold_me = {hold_me}")
                    sub_feature_iterations = list()
                    for sub_sample in sample:
                        sub_feature_iterations.append([sub_sample])
                    hold_me.extend([sub_feature_iterations])
                    if debug:
                        print(f"hold_me = {hold_me}\n")
                    Features_configured.append(hold_me)

    port_details = parse.find_objects(r'^interface')
    for detail in port_details:
        check_features = Interface_detail(detail)
        if debug:
            print(f"======{check_features}")
        # Go through a loop to read the return of the config under the
        # interface and then add them to the main list (Features_configured)
        x = 0
        while x < len(check_features):
            Features_configured.append(check_features[x])
            x += 1
    # Only capture unique values in a new list
    for entry in Features_configured:
        if debug:
            print(f"entry = {entry}")
        if len(aux_features_config) == 0:
            aux_features_config.append(entry)
            if debug:
                print("Created the first aux entry")
        else:
            found = False
            for i, lst in enumerate(aux_features_config):
                for j, feature_name in enumerate(lst):
                    if feature_name == entry[0]:
                        found = True
                        if debug:
                            print(f"aux_features_config[{i}][5] = " +
                                  f"{aux_features_config[i][5]}")
                            print(f"entry[5] = {entry[5]}")
                        aux_features_config[i][5].extend(entry[5])
            if not found:
                aux_features_config.append(entry)
    if debug:
        print(f"aux_features_config = {aux_features_config}")
    return (host_name, aux_features_config)


def Interface_detail(interface_value):
    """
    This sub-function is used to read the interface configuration.
    :param interface_value: An interface object from CiscoConfParse.
    :return: A combined list of  all the features on the interface.
    """

    debug = DEBUG or DEBUG_CHECKER

    if debug:
        print(f"interface_value = {interface_value}\n")

    feature_list_on_interface = list()
    # Check the configuration of the interfaces
    interface_children = interface_value.children
    for child in interface_children:
        parent = child.parent
        for key, val in mc_pedia['port'].items():
            newvals = {}
            if debug:
                print(f"key,val = {key},{val}\n")
            if not val['regex'] == "":
                if not child.re_match_typed(regex=val['regex']) == "":
                    if debug:
                        print(f"child = {child}")
                    exec(val.get('iosxe'), locals(), newvals)
                    if debug:
                        print(f"newvals[{key}] = {newvals[key]}\n")
                    if not newvals[key] == "":
                        hold_sub = list()
                        hold_sub.extend([val['name'],
                                         val['support'],
                                         val['translatable']])
                        try:
                            hold_sub.extend([val['note']])
                        except:
                            hold_sub.extend([""])
                        try:
                            hold_sub.extend([val['url']])
                        except:
                            hold_sub.extend([""])
                        if debug:
                            print(f"hold_sub = {hold_sub}")
                        hold_sub.append([[child, parent]])
                        if debug:
                            print(f"hold_sub = {hold_sub}")
                        feature_list_on_interface.append(hold_sub)
        if debug:
            print("feature_list_on_interface = " +
                  f"{feature_list_on_interface}")
    if debug:
        print(f"feature_list_on_interface for {interface_value} = " +
              f"{feature_list_on_interface}\n")

    # Combine all the features on the interface together
    # in a list and send it back
    return (feature_list_on_interface)
