######
# This is a purpose-built small demo for sending multiple SourcedFixletAction to multiple Targets with a Secure Parameter
# The specific case is for Compliance Checklists for Oracle, that require periodically running a script with Oracle credentials against each
# Oracle Instance.
######
import sys

# requires "pip install requests"
import requests

import getpass

# to suppress SSL "untrusted certificate" warnings
import warnings


from xml.etree import ElementTree
from xml.dom import minidom

import json
import os
import argparse

# Suppress InsecureRequestWarning warnings from requests module
#  These are generated when we do not have a trusted CA certificate on the BES Server
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def pretty_print(node, indent=" ", newl="\r", encoding="utf-8"):
    dom = minidom.parseString(
        ElementTree.tostring(node, encoding=encoding, method="xml").decode()
    )
    return dom.toprettyxml(indent=indent, newl=newl, encoding=encoding)


def main():
    global root_url
    parser = argparse.ArgumentParser()
    parser.add_argument("config_file", help="<path\\to\\config.json>")
    xmlTemplate = """<?xml version="1.0" encoding="UTF-8"?>
<BES xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="BES.xsd">
  <SourcedFixletAction>
	<SourceFixlet>
	</SourceFixlet>
	<Target>
	</Target>
</SourcedFixletAction>
</BES>
"""
    #    args = parser.parse_args()
    # parse sample arguments
    args = parser.parse_args(["oracle_config.json"])
    config_file = args.config_file
    print(f"Loading {os.path.realpath(config_file)}")
    if os.path.exists(config_file):
        print(f'Loading configuration from "{config_file}"')
        with open(config_file) as json_file:
            config = json.load(json_file)
    else:
        raise ValueError(
            f'Configuration file not found at "{config_file}", cannot continue'
        )
    print(str(config))
    root_url = config.get("root_url")
    source_fixlet_site = config.get("source_fixlet_site")
    source_fixlet_id = config.get("source_fixlet_id")
    source_action_name = config.get("source_action_name")
    target_list = config.get("targets")
    # InputVal is a comma-delimited list of potentially multiple database instances
    # for each instance, should have "instancename,username,password,instancepath"
    # action_secure_parameters= {"InputVal": "instance1,user1,password1,/u01/app/oracle/product/11.2.0.4/db_1,instance2,user2,password2,/u01/app/oracle/product/11.2.0.4/db_2"}

    bes_username = input("Enter username for BigFix Operator:")
    bes_password = getpass.getpass("Enter password:")
    session = requests.Session()

    session.auth = (bes_username, bes_password)
    response = session.request(url=root_url + "/api/login", method="GET", verify=False)
    if not response.ok:
        print(
            f"Failed to log on to root server, HTTP {response.status_code}: {response.text}"
        )
        sys.exit(1)

    oracle_username = input("Enter Oracle user account name:")
    oracle_password = getpass.getpass("Enter Oracle user password:")

    for target in target_list:
        target_computernames = target.get("computer_names", [])
        target_computerids = target.get("computer_ids", [])
        instance_list = []
        for instance in target.get("instances", []):
            instance_list.append(
                ",".join(
                    [
                        instance.get("instance_name"),
                        oracle_username,
                        oracle_password,
                        instance.get("instance_home"),
                    ]
                )
            )

        instances_string = ",".join(instance_list)

        tree = ElementTree.fromstring(xmlTemplate)

        sourced_fixlet_action = tree.find("SourcedFixletAction")
        source_fixlet_node = sourced_fixlet_action.find("SourceFixlet")
        newchild = ElementTree.Element("Sitename")
        newchild.text = source_fixlet_site
        source_fixlet_node.append(newchild)

        newchild = ElementTree.Element("FixletID")
        newchild.text = str(source_fixlet_id)
        source_fixlet_node.append(newchild)

        newchild = ElementTree.Element("Action")
        newchild.text = str(source_action_name)
        source_fixlet_node.append(newchild)

        target_node = tree.find("SourcedFixletAction/Target")

        # Prefer ComputerID if it is provided, otherwise we have to lookup ComputerName to ComputerID mappings
        for target_computerid in target_computerids:
            newchild = ElementTree.Element("ComputerID")
            newchild.text = str(target_computerid)
            target_node.append(newchild)
        for target_computername in target_computernames:
            # Sending with Secure Parameters requires computer IDs, not computer Names; send queries to lookup each ComputerID
            relevance = f'ids of bes computers whose (name of it as lowercase = "{target_computername}" as lowercase)'
            response = session.request(
                method="POST",
                url=root_url + "/api/query",
                data={"relevance": relevance, "output": "json"},
                verify=False,
            )
            if not response.ok:
                print(
                    f"Lookup of BES Computer Name to ID failed for '{target_computername}', error {response.status_code}: {response.text}\n, aborting"
                )
                sys.exit(1)

            response_json = json.loads(response.text)
            computerids = response_json.get("result", [])
            for computerid in computerids:
                newchild = ElementTree.Element("ComputerID")
                newchild.text = str(computerid)
                target_node.append(newchild)

        instances_element = ElementTree.Element("SecureParameter")
        instances_element.set("Name", "InputVal")
        instances_element.text = instances_string

        target_index = list(sourced_fixlet_action).index(target_node)
        sourced_fixlet_action.insert(target_index + 1, instances_element)
        # print(pretty_print(tree))
        response = session.request(
            method="POST",
            url=root_url + "/api/actions",
            data=pretty_print(tree).decode(),
        )
        print(f"Action sent: response {response.status_code}: {response.text}")


if __name__ == "__main__":
    global scriptPath
    if getattr(sys, "frozen", False):
        # If the application is run as a bundle, the PyInstaller bootloader
        # # extends the sys module by a flag frozen=True and sets the app
        # # path into variable _MEIPASS'.
        # print("Using frozen config")

        scriptPath = os.path.dirname(os.path.abspath(sys.executable))
    else:
        scriptPath = os.path.dirname(os.path.abspath(__file__))

    main()