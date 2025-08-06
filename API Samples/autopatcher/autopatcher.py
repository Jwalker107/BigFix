"""
Generates the XML of a Baseline, retrieves Fixlets to add Components, adds targets, and POSTs the action to the BigFix server.
"""

import os
import sys
import requests
import keyring
import argparse
import json

# Disable SSL warnings - urllib3 is used internally by 'requests'
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings as urllib3_disable_warnings

urllib3_disable_warnings(InsecureRequestWarning)

## HTTPAdapter and Retry are used for automatic retries on network requests
from requests.adapters import HTTPAdapter

# import urllib3
from urllib3 import Retry

# Import the XML Parser
from xml.etree import ElementTree
import time
import datetime


def get_script_path():
    """Returns the directory of the running script.  Useful for defaulting a configuration file path to match the script itself."""
    if getattr(sys, "frozen", False):
        # If the application is run as a bundle (precompiled binary), the PyInstaller bootloader
        # # extends the sys module by a flag frozen=True and sets the app
        # # path into variable _MEIPASS'.
        # print("Using frozen config")
        return os.path.dirname(os.path.abspath(sys.executable))
    else:
        return os.path.dirname(os.path.abspath(__file__))


def load_config(config_file):
    """Load the configuration from a JSON file"""
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Configuration file {config_file} does not exist")
    with open(config_file, "r") as f:
        config = json.load(f)

    config["bes_password"] = keyring.get_password(
        config.get("keyring_system_name"), config.get("bes_username")
    )
    if not config.get("bes_password", None):
        raise ValueError(
            f"Password for {config['bes_username']} not found in keyring {config.get('keyring_system_name')}; run save_keyring.py set it"
        )
    return config


def parse_arguments(argv=[]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config",
        help="Path to json file containing configuration options. Default is config.json in the same directory as this script",
        type=str,
        default=os.path.join(get_script_path(), "config.json"),
        required=False,
    )
    parser.add_argument(
        "--template",
        help="Path to file containing baseline template XML. Default is baseline_template.txt in the same directory as this script",
        type=str,
        default=os.path.join(get_script_path(), "baseline_template.txt"),
        required=False,
    )

    parser.add_argument(
        "--query",
        help="Path to a file containing the query to select components.  Repeat for multiple queries to add multiple BaselineComponentGroups",
        type=str,
        action="append",
        # nargs="+",
        required=True,
    )
    parser.add_argument(
        "--preview",
        help="Print Baseline XML but do not POST the baseline to the server",
        action="store_true",
        default=False,
        required=False,
    )

    parser.add_argument(
        "--target-computer-query",
        help="Target computers using CustomRelevance query contained in the specified file",
        type=str,
        required=False,
    )

    parser.add_argument(
        "--target-computer-names",
        help="Target computers using computername, i.e. --target-computer-names TESTMACHINE01 TESTMACHINE02",
        type=str,
        nargs="+",
        required=False,
    )

    parser.add_argument(
        "--target-computer-ids",
        help="Target computers using computername, i.e. --target-computer-ids 123 456 789",
        type=str,
        nargs="+",
        required=False,
    )

    parser.add_argument(
        "--target-allcomputers",
        help="Target all computers",
        action="store_true",
        default=False,
        required=False,
    )

    parser.add_argument(
        "--preview-action",
        help="Generate the Action XML but do not POST it to the server",
        action="store_true",
        default=False,
        required=False,
    )
    parser.add_argument(
        "--action",
        help="Send an Action for the new baseline",
        action="store_true",
        default=False,
        required=False,
    )

    args = parser.parse_args(argv)
    return args


def to_bes_time(
    time=datetime.datetime.now(datetime.datetime.now().astimezone().tzinfo),
):
    """
    Given a datetime object with timezone(defaulting to current time and local time zone),
    return a BES formatted time string with zone offset
    Examples:
    to_bes_time() -> 'Sun, 22 Sep 2024 15:50:44 -0500'
    to_bes_time(datetime.datetime.now().astimezone(datetime.timezone.utc)) -> 'Sun, 22 Sep 2024 20:51:38 +0000'
    """
    return time.strftime("%a, %d %b %Y %H:%M:%S %z")


def to_bes_date(
    date=datetime.datetime.now(datetime.datetime.now().astimezone().tzinfo),
):
    """
    Given a datetime object with timezone(defaulting to current time and local time zone),
    return a BES formatted date string, i.e. '2024-04-23'
    """
    return date.strftime("%Y-%m-%d")


def check_login(bigfix_server, session: requests.Session) -> bool:
    """Check if the login to the BigFix server is successful"""
    response = session.get(url=f"{bigfix_server}/api/login")
    return response.ok


def setup_session(*, username=None, password=None, verify=True) -> requests.Session:
    """Set up a requests.Session object, to make repeated requests more efficient.
    Uses HTTPAdapter and configures some retries for common network errors"""
    # Set up a requests.Session object, to make repeated requests more efficient.
    session = requests.Session()
    # certificate verification is configured on the Session instead of each individual request
    session.verify = verify

    # user authentication options are persisted on the Session instead of each individual request
    if username and password:
        session.auth = (username, password)

    # create a custom HTTPAdapter to configure the retries
    # see https://requests.readthedocs.io/en/latest/user/advanced/
    adapter = HTTPAdapter(
        max_retries=Retry(
            total=4,
            backoff_factor=1,
            allowed_methods=None,
            status_forcelist=[429, 500, 502, 503, 504],
        )
    )
    # mount this custom HTTPAdapter for the 'http://' and 'https://' protocols of the requests.Session object
    session.mount("http://", adapter)
    session.mount("http2://", adapter)
    return session


def load_baseline_template(template_file: str, **kwargs) -> ElementTree.Element:
    """Load the baseline template into an Element, substituting some dynamic parameters"""
    ## Using kwargs, the caller can include their own set of parameters to be substituted into the template.
    ## current_date and current_time might be substituted into the template
    current_date = to_bes_date()
    current_time = to_bes_time()

    baseline_template = read_text_file(template_file).format(**locals())
    root = ElementTree.fromstring(baseline_template)
    return root


def create_baseline_component(
    *,  # enforce named parameters for readability and to avoid errors.  Every parameter must be passed by name.
    name,
    source_site_url,
    source_id,
    action_name,
    action_script,
    relevance,
    success_criteria="OriginalRelevance",
    script_type="application/x-Fixlet-Windows-Shell",
    include_in_relevance="true",
    success_relevance="",
) -> ElementTree.Element:
    """Creates a BaselineComponent Element from the provided parameters."""
    # Create a new Element of type "BaselineComponent"
    component = ElementTree.Element("BaselineComponent")
    component.attrib["Name"] = name
    component.attrib["IncludeInRelevance"] = include_in_relevance
    component.attrib["SourceSiteURL"] = source_site_url
    component.attrib["SourceID"] = str(source_id)
    component.attrib["ActionName"] = action_name

    actionscript_node = ElementTree.Element("ActionScript")
    actionscript_node.attrib["MIMEType"] = script_type
    actionscript_node.text = action_script
    component.append(actionscript_node)

    successcriteria_node = ElementTree.Element("SuccessCriteria")
    successcriteria_node.attrib["Option"] = success_criteria
    successcriteria_node.text = success_relevance

    component.append(successcriteria_node)
    relevance_node = ElementTree.Element("Relevance")
    relevance_node.text = relevance
    component.append(relevance_node)
    return component


def sourced_fixlet_action_xml(
    gather_url: str, content_id: str, target_computers: dict
) -> ElementTree.Element:
    """Creates an ElementTree XML DOM of a SourcedFixletAction
    content is an Element describing the action to be performed, such as a Baseline or Fixlet.
    target_computers is a dictionary containing at least one of the keys 'ComputerName', 'ComputerID', 'CustomRelevance', or 'AllComputers'.
    """
    action_template = """<?xml version="1.0" encoding="UTF-8"?>
<BES xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="BES.xsd">
<SourcedFixletAction>
 <SourceFixlet />
 <Target />
 <Settings />
</SourcedFixletAction>
</BES>
"""
    root = ElementTree.fromstring(action_template)
    sourcefixlet = root.find("./SourcedFixletAction/SourceFixlet")
    ElementTree.SubElement(sourcefixlet, "GatherURL").text = gather_url
    ElementTree.SubElement(sourcefixlet, "FixletID").text = content_id

    target = root.find(".//Target")
    # Multiple entries of ComputerName or ComputerID are allowed, so we loop through the target_computers dictionary
    for targettype in ["ComputerName", "ComputerID"]:
        if target_computers.get(targettype, None) is not None:
            if isinstance(target_computers[targettype], list):
                for value in target_computers[targettype]:
                    ElementTree.SubElement(target, targettype).text = value

            elif isinstance(target_computers[targettype], str):
                ElementTree.SubElement(target, targettype).text = target_computers[
                    targettype
                ]

            else:
                raise ValueError(
                    f"Invalid type for target_computers[{targettype}]: {type(target_computers[targettype])}"
                )

    if target_computers.get("CustomRelevance", None):
        if isinstance(target_computers["CustomRelevance"], str):
            ElementTree.SubElement(target, "CustomRelevance").text = target_computers[
                "CustomRelevance"
            ]

    if target_computers.get("AllComputers", False):
        ElementTree.SubElement(target, "AllComputers").text = "True"

    return root


def read_text_file(file_path: str) -> str:
    """Read a text file return it as a string"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} does not exist")

    with open(file_path, "r") as f:
        return f.read()


def get_components_queries(filelist: str) -> list:
    """Load multiple queries from a list of files and return them as a list of strings"""
    queries = []
    if not filelist:
        raise ValueError("No query files provided")

    for query_file in filelist:
        queries.append(read_text_file(query_file))

    return queries


def get_fixlet_list(session: requests.Session, query: str) -> list:
    """Retrieve a list of Fixlets from the BigFix server based on the provided query.  The properties returned by the query should match the expected fixlet fields."""
    fixlet_query = {"relevance": query, "output": "json"}

    response = session.get(
        url=f"{config['bigfix_server']}/api/query", params=fixlet_query
    )
    if not response.ok:
        raise ValueError(
            f"Fixlet Query failed, code:{response.status_code}, message:{response.text} "
        )
    if response.json().get("error"):
        raise ValueError(f'Fixlet Query gave an error: {response.json()["error"]} ')
    fixlet_list = response.json()["result"]
    return fixlet_list


def main(argv):
    args = parse_arguments(argv)
    config = load_config(args.config)
    session = setup_session(
        username=config["bes_username"],
        password=config["bes_password"],
        verify=config["verify"],
    )

    # test the login credentials
    if not check_login(config["bigfix_server"], session):
        raise ValueError(f"Login failed, unable to continue")

    start_time = time.time()
    # create the template action XML content
    baseline = load_baseline_template(args.template)
    # Retrieve the list of queries we are going to run by looping through the provided query files
    components_definitions = get_components_queries(args.query)

    baseline_component_collection = baseline.find(
        "Baseline/BaselineComponentCollection"
    )

    for components_query in components_definitions:
        fixlet_list = get_fixlet_list(session, components_query)
        print(
            f"Adding BaselineComponentGroup with {len(fixlet_list)} fixlets to the Baseline"
        )

        baseline_component_group = ElementTree.SubElement(
            baseline_component_collection, "BaselineComponentGroup"
        )
        baseline_component_group.attrib["Name"] = "Components Group"

        # Loop through the fixlets retrieved by the query, and create a BaselineComponent for each.
        for fixlet in fixlet_list:
            component = create_baseline_component(
                name=fixlet[0],
                source_site_url=fixlet[1],
                source_id=fixlet[2],
                action_name=fixlet[3],
                action_script=fixlet[4],
                relevance=fixlet[5],
                success_criteria=fixlet[6],
                script_type=fixlet[7],
                include_in_relevance=("true" if fixlet[8] == "Fixlet" else "false"),
            )

            baseline_component_group.append(component)

    if args.preview:
        # Print preview and exit without posting
        print(ElementTree.tostring(baseline, encoding="unicode"))
        print("Preview mode, skipping baseline POST")
        return

    # POST the baseline to the server
    print(
        f"Posting Baseline to {config['bigfix_server']}/api/site/{config['baselines_site']}"
    )
    response = session.post(
        url=f"{config['bigfix_server']}/api/baselines/{config['baselines_site']}",
        data=ElementTree.tostring(baseline),
        headers={"Content-Type": "text/xml"},
    )

    if response.ok:
        print(f"Baseline creation succeeded with {response.status_code}")
        besapi_response = ElementTree.fromstring(response.text)
        # Extract the Baseline ID from the response
        baseline_id = besapi_response.find("./Baseline/ID").text
        print(f"Baseline ID is {baseline_id}")
    else:
        raise ValueError(
            f"Baseline creation failed with {response.status_code}, message {response.text}, unable to continue"
        )

    if args.action or args.preview_action:
        print("Generating Action XML for the Baseline")
        # Determine GatherURL of the Baseline site
        response = session.get(
            f"{config['bigfix_server']}/api/site/{config['baselines_site']}"
        )
        if not response.ok:
            raise ValueError(
                f"Failed to retrieve site {config['bigfix_server']}/api/site/{config['baselines_site']} , code:{response.status_code}, message:{response.text} "
            )
        site_xml = ElementTree.fromstring(response.content)
        gather_url = site_xml.find(".//GatherURL").text

        if args.target_computer_query:
            target_computers = {
                "CustomRelevance": read_text_file(args.target_computer_query)
            }
        elif args.target_computer_names:
            target_computers = {"ComputerName": args.target_computer_names}
        elif args.target_computer_ids:
            target_computers = {"ComputerID": args.target_computer_ids}
        elif args.target_allcomputers:
            target_computers = {"AllComputers": True}
        else:
            raise ValueError(
                "No target computers specified. Use --target-computer-query, --target-computer-names, --target-computer-ids, or --target-allcomputers"
            )

        action_request = sourced_fixlet_action_xml(
            gather_url, baseline_id, target_computers
        )
        if args.preview_action:
            # Print preview of the Action XML and exit without posting
            print(ElementTree.tostring(action_request, encoding="unicode"))
            print("Preview mode, skipping action POST")
            return
        elif args.action:
            print(f"Posting Action to {config['bigfix_server']}/api/actions")
            response = session.post(
                url=f"{config['bigfix_server']}/api/actions",
                data=ElementTree.tostring(action_request),
                headers={"Content-Type": "text/html"},
            )
            if not response.ok:
                raise ValueError(
                    f"Action POST failed, code:{response.status_code}, message:{response.text} "
                )
            else:
                print(f"Action POST succeeded with {response.status_code}")
                action_response = ElementTree.fromstring(response.text)
                print("Action Response:")
                print(ElementTree.tostring(action_response, encoding="unicode"))
                action_id = action_response.find("./Action/ID").text
                print(f"Action ID is {action_id}")
    print(f"Execution Time:  {round(time.time() - start_time, 2)}")


if __name__ == "__main__":
    main(sys.argv[1:])
