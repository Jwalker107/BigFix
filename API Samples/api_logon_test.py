""" Test repeated API logins to the BES Root Server
Troubleshooting issue described as 'intermittent LDAP logon failures'
This script will repeatedly attempt to log on to the root server using a given credential
and track the number of success, failure, and exceptions for the connection attempts
The account to be tested must have the 'Can use REST API' right assigned
"""
# requires "pip install requests"
import requests

# to suppress SSL "untrusted certificate" warnings
import warnings

# Suppress InsecureRequestWarning warnings from requests module
#  These are generated when we do not have a trusted CA certificate on the BES Server
from requests.packages.urllib3.exceptions import InsecureRequestWarning
# tqdm progress bar, requires 'pip install tqdm'
from tqdm.auto import tqdm, trange
from time import sleep

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# server connection parameters
certverify = False    # ignore server certificate validation
url = "https://bes-root.domain.home:52311/api/login" # root server api login url

# username and password to try
username = "TestUser1@d.domain.home"
# username = "D\\TestUser1"  
# username = "TestUser1"
password = "## NOT TODAY ##"                

pbar = trange(50) # Number of attempts to make
count_success = 0   # number of successful logins
count_failure = 0   # number of failed logins
count_exception = 0 # number of exceptions (server offline, unreachable, etc.)

for logoncount in pbar:
    # delay between try attempts, 0.1 seconds
    sleep(0.1)
    try:
        response = requests.request(
            "GET",
            url,
            verify = certverify,
            auth = (username, password),
        )

    except Exception as e:
        # This could be an exception such as "server unreachable"
        print("Exception: " + str(e))
        count_exception += 1
    else:
        if not response.ok:
            # This could be an error such as "We connected to the server and got HTTP response, but the RESPONSE is "Access Denied" or "Page not Found")
            print("HTTP " + str(response.status_code) + " " + response.reason)
            count_failure += 1
        else:
            #print(response.text)
            count_success += 1
    # update progress bar description with counts
    pbar.set_description(f"Success: {count_success} , Failure: {count_failure} , Exception: {count_exception}")
