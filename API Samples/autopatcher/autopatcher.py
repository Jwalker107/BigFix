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


def parse_arguments(argv=[]) -> argparse.Namespace:
    """Parse command-line arguments and return them as a Namespace object."""
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
        help="Path to file containing baseline template XML. Default is baseline_template.xml in the same directory as this script",
        type=str,
        default=os.path.join(get_script_path(), "baseline_template.xml"),
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
        "--action-template",
        help="Path to file containing SourceFixletAction template XML. Default is action_template.xml in the same directory as this script",
        type=str,
        default=os.path.join(get_script_path(), "action_template.xml"),
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

    # Load the API password from keyring
    config["bes_password"] = keyring.get_password(
        config.get("keyring_system_name"), config.get("bes_username")
    )
    if not config.get("bes_password", None):
        raise ValueError(
            f"Password for {config['bes_username']} not found in keyring {config.get('keyring_system_name')}; run save_keyring.py set it"
        )
    return config


def bes_time(
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


def bes_date(
    date=datetime.datetime.now(datetime.datetime.now().astimezone().tzinfo),
):
    """
    Given a datetime object with timezone(defaulting to current time and local time zone),
    return a BES formatted date string, i.e. '2024-04-23'
    """
    return date.strftime("%Y-%m-%d")


def check_login(bigfix_server: str, session: requests.Session) -> bool:
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


def load_xml_template(template_file: str, **kwargs) -> ElementTree.Element:
    """Load the baseline template into an Element, substituting some dynamic parameters
    Use of kwargs allows the caller to include their own set of parameters to be substituted into the template.
    This function provides for {current_date} and {current_time} to be substituted into the template.
    Any other local variables (including the kwargs) can also be substituted into the template.
    """
    ## Using kwargs, the caller can include their own set of parameters to be substituted into the template.
    ## current_date and current_time might be substituted into the template
    current_date = bes_date()
    current_time = bes_time()

    xml_template = read_text_file(template_file).format(**locals())
    root = ElementTree.fromstring(xml_template)
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


def create_action_target_element(
    AllComputers: bool = None,
    ComputerName: str = None,
    ComputerID: str = None,
    CustomRelevance: str = None,
) -> ElementTree.Element:
    """Creates a Target Element for the SourcedFixletAction XML."""

    target = ElementTree.Element("Target")

    if CustomRelevance:
        ElementTree.SubElement(target, "CustomRelevance").text = CustomRelevance

    elif ComputerName:
        if isinstance(ComputerName, list):
            for item in ComputerName:
                ElementTree.SubElement(target, "ComputerName").text = item
        else:
            ElementTree.SubElement(target, "ComputerName").text = ComputerName

    elif ComputerID:
        if isinstance(ComputerID, list):
            for item in ComputerID:
                ElementTree.SubElement(target, "ComputerID").text = item
        else:
            ElementTree.SubElement(target, "ComputerID").text = ComputerID

    elif AllComputers:
        ElementTree.SubElement(target, "AllComputers").text = "True"
    else:
        raise ValueError(
            "No target computers specified. Use --target-computer-query, --target-computer-names, --target-computer-ids, or --target-allcomputers"
        )

    return target


def get_parent_element(root, target):
    parent = [element for element in root.iter() if target in element.findall("./")]
    return parent[0] if parent else None


def replace_element(
    root: ElementTree.Element,
    old_element: ElementTree.Element,
    new_element: ElementTree.Element,
):
    """Replaces an old element in the XML tree with a new element."""
    parent = get_parent_element(root, old_element)
    if parent is None:
        raise ValueError("The old element has no parent, cannot replace it.")
    old_element_index = list(parent).index(old_element)

    parent.remove(old_element)
    parent.insert(old_element_index, new_element)


def sourced_fixlet_action_xml(
    action_template: ElementTree.Element,
    gather_url: str,
    content_id: str,
    AllComputers: bool = None,
    ComputerName: str = None,
    ComputerID: str = None,
    CustomRelevance: str = None,
) -> ElementTree.Element:
    """Creates an ElementTree XML DOM of a SourcedFixletAction
    content is an Element describing the action to be performed, such as a Baseline or Fixlet.
    target_computers is a dictionary containing at least one of the keys 'ComputerName', 'ComputerID', 'CustomRelevance', or 'AllComputers'.
    """

    sourcefixlet = action_template.find("./SourcedFixletAction/SourceFixlet")
    ElementTree.SubElement(sourcefixlet, "GatherURL").text = gather_url
    ElementTree.SubElement(sourcefixlet, "FixletID").text = content_id

    target = action_template.find(".//Target")
    new_target = create_action_target_element(
        AllComputers=AllComputers,
        ComputerName=ComputerName,
        ComputerID=ComputerID,
        CustomRelevance=CustomRelevance,
    )

    replace_element(action_template, target, new_target)

    return action_template


def read_text_file(file_path: str) -> str:
    """Read a text file return it as a string"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} does not exist")
    if not os.path.isfile(file_path):
        raise ValueError(f"{file_path} is not a file")
    with open(file_path, "r") as f:
        return f.read()


def get_components_queries_from_files(filelist: str) -> list[str]:
    """Load multiple queries from a list of files and return them as a list of strings"""
    queries = []
    if not filelist:
        raise ValueError("No query files provided")

    for query_file in filelist:
        queries.append(read_text_file(query_file))

    return queries


def get_fixlet_list(session: requests.Session, server_url, query: str) -> list:
    """Retrieve a list of Fixlets from the BigFix server based on the provided query.  The properties returned by the query should match the expected fixlet fields."""
    fixlet_query = {"relevance": query, "output": "json"}

    response = session.get(url=f"{server_url}/api/query", params=fixlet_query)
    if not response.ok:
        raise ValueError(
            f"Fixlet Query failed, code:{response.status_code}, message:{response.text} "
        )
    if response.json().get("error"):
        raise ValueError(f'Fixlet Query gave an error: {response.json()["error"]} ')
    fixlet_list = response.json()["result"]
    return fixlet_list


def add_components_to_group(
    baseline_component_group: ElementTree.Element,
    session: requests.Session,
    server_url: str,
    component_query: str,
) -> None:
    """Executes a Session Relevance query to retrieve a list of Fixlets and adds them to the provided BaselineComponentGroup ElementTree.Element."""

    fixlet_list = get_fixlet_list(session, server_url, component_query)
    print(f"Adding {len(fixlet_list)} fixlets to the BaselineComponentGroup")

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


def add_baseline_component_groups(
    *,
    session: requests.Session,
    server_url: str,
    baseline: ElementTree.Element,
    query_list: list[str],
) -> ElementTree.Element:
    """Appends BaselineComponentGroups to the provided baseline ElementTree.Element
    based on the provided component queries.
    Each query should return a list of fixlet fields in the proper order"""

    # Retrieve the list of queries we are going to run by looping through the provided query files

    baseline_component_collection = baseline.find(
        "Baseline/BaselineComponentCollection"
    )

    # for each query in the component_queries list, create a BaselineComponentGroup populated by the Fixlets/Tasks returned by the query
    for query in query_list:
        baseline_component_group = ElementTree.SubElement(
            baseline_component_collection, "BaselineComponentGroup"
        )
        add_components_to_group(baseline_component_group, session, server_url, query)

    return baseline


def get_site_gather_url(session, url) -> str:
    """Retrieve the GatherURL of the specified site from the BigFix server."""
    ### This is necessary because the GatherURL may not be the same as the site URL we are using.
    ### for instance we might be using the IP address or an alias of the root server to connect to REST, but the GatherURL must match the actual site URL.

    response = session.get(url)
    if not response.ok:
        raise ValueError(
            f"Failed to retrieve site {url} , code:{response.status_code}, message:{response.text} "
        )
    site_xml = ElementTree.fromstring(response.content)
    gather_url = site_xml.find(".//GatherURL").text
    return gather_url


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
    query_list = [read_text_file(query_file) for query_file in args.query]

    baseline = load_xml_template(args.template)

    # The functions runs all the fixlet queries and adds the results to the baseline
    add_baseline_component_groups(
        session=session,
        server_url=config["bigfix_server"],
        baseline=baseline,
        query_list=query_list,
    )
    # If we are in preview mode, print the baseline XML and exit without posting
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
        baseline_response = ElementTree.fromstring(response.text)
        baseline_id = baseline_response.find("./Baseline/ID").text
        print(f"Successfully posted baseline ID {baseline_id}")
    else:
        raise ValueError(
            f"Baseline creation failed with {response.status_code}, message {response.text}, unable to continue"
        )

    if args.action or args.preview_action:
        print("Generating Action XML for the Baseline")
        action = load_xml_template(args.action_template)
        baseline_gather_url = get_site_gather_url(
            session, f"{config['bigfix_server']}/api/site/{config['baselines_site']}"
        )

        target_parameters = {
            "CustomRelevance": (
                read_text_file(args.target_computer_query)
                if args.target_computer_query
                else None
            ),
            "ComputerName": args.target_computer_names,
            "ComputerID": args.target_computer_ids,
            "AllComputers": args.target_allcomputers,
        }

        action_request = sourced_fixlet_action_xml(
            action, baseline_gather_url, baseline_id, **target_parameters
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
