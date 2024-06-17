# requires "pip install requests"
import requests

# to suppress SSL "untrusted certificate" warnings
import warnings

myXML = """<?xml version="1.0" encoding="UTF-8"?>
<BES xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="BES.xsd">
  <SingleAction>
	<Title>Test</Title>
	<Relevance>True</Relevance>
	<ActionScript MIMEType="application/x-Fixlet-Windows-Shell"><![CDATA[action log all

override wait
runas=localuser
user=Administrator
password=required
wait cmd /C "Echo Hello from %USERNAME% > c:\\temp\\hello.txt"]]></ActionScript>
  <SecureParameter Name="action override password">BES-Dev-1</SecureParameter>
  <!-- must target by ComputerID due to secure parameter -->
	<Target><ComputerID>539193122</ComputerID></Target>
  </SingleAction>
</BES>
"""

operation = "POST"
certverify = False
url = "https://bes-root.domain.home:52311/api/actions"
username = "mo"
password = "My-Password"

print("POSTing the following XML:")
print(myXML)

# Suppress InsecureRequestWarning warnings from requests module
#  These are generated when we do not have a trusted CA certificate on the BES Server
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Note that on any of these Exception handlers, we could either raise our own error and quit the script, or handle the error
# and move on to the next query or next server or ...
try:
    response = requests.request(
        operation,
        url,
        data=myXML,
        headers=None,
        verify=certverify,
        auth=(username, password),
        params=None,
    )

except Exception as e:
    # This could be an exception such as "server unreachable"
    print("Error encountered connecting to the API: " + str(e))
    # Quit now?
    # raise ValueError("Error encountered when connecting to API:" + str(e))
else:
    if not response.ok:
        # This could be an error such as "We connected to the server and got HTTP response, but the RESPONSE is "Access Denied" or "Page not Found")
        print("HTTP " + str(response.status_code) + " " + response.reason)
        # quit now?
        # raise ValueError("Error encountered when sending query to " + url + " [query was: " + str(response) + " ]: HTTP " + str(response.status_code) + " " + response.reason)

    else:
        print("Action sent:")
        print(response.text)
        # Posting an ACTION does not yield a JSON response, it's XML
