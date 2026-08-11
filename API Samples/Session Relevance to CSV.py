###########################
### DEMONSTRATION CODE ONLY         
### Not suitable for production use 
### May lack secure practices, error handling, flexibility, and other bugs
### For questions contact Jason Walker, HCL
###########################
# This is an example of connecting to a BigFix REST API,
#  executing a session relevance query,
#  and outputing the results to a CSV file

# requires "pip install requests"
import requests

# to suppress SSL "untrusted certificate" warnings
import warnings

# to use JSON-formatted data
# import json
# to use CSV-formatted data
import csv

output_csv="c:\\temp\\output.csv"
output_json="c:\\temp\\output.json"
operation="POST"
certverify=False
url="https://bes-root.local:52311/api/query"
username="mo"
password="MyPassWord"
# Headers for CSV file, column count should match the query result items count
csv_headers=[
      "ComputerID",
      "ComputerName",
      "LastReportTime",
      "DeviceType",
      "Make",
      "Model",
      "OS",
      "IPAddress",
      "MACAddress",
      "ADPath"
      ]

relevance="""
(
  (concatenation ";" of values of results (item 0 of it, elements of item 1 of it))
, (if (size of item 2 of it = 1) then ( concatenation ";" of values of results (item 0 of it, elements of item 2 of it)) else (if (size of item 2 of it > 1) then (("Property 2 duplicates: " & concatenation "|" of ((name of it) & "=" & (id of it as string)) of elements of item 2 of it) as string) else ("Property 2 does not exist")))
, (if (size of item 3 of it = 1) then ( concatenation ";" of values of results (item 0 of it, elements of item 3 of it)) else (if (size of item 3 of it > 1) then (("Property 3 duplicates: " & concatenation "|" of ((name of it) & "=" & (id of it as string)) of elements of item 3 of it) as string) else ("Property 3 does not exist")))
, (if (size of item 4 of it = 1) then ( concatenation ";" of values of results (item 0 of it, elements of item 4 of it)) else (if (size of item 4 of it > 1) then (("Property 4 duplicates: " & concatenation "|" of ((name of it) & "=" & (id of it as string)) of elements of item 4 of it) as string) else ("Property 4 does not exist")))
, (if (size of item 5 of it = 1) then ( concatenation ";" of values of results (item 0 of it, elements of item 5 of it)) else (if (size of item 5 of it > 1) then (("Property 5 duplicates: " & concatenation "|" of ((name of it) & "=" & (id of it as string)) of elements of item 5 of it) as string) else ("Property 5 does not exist")))
, (if (size of item 6 of it = 1) then ( concatenation ";" of values of results (item 0 of it, elements of item 6 of it)) else (if (size of item 6 of it > 1) then (("Property 6 duplicates: " & concatenation "|" of ((name of it) & "=" & (id of it as string)) of elements of item 6 of it) as string) else ("Property 6 does not exist")))
, (if (size of item 7 of it = 1) then ( concatenation ";" of values of results (item 0 of it, elements of item 7 of it)) else (if (size of item 7 of it > 1) then (("Property 7 duplicates: " & concatenation "|" of ((name of it) & "=" & (id of it as string)) of elements of item 7 of it) as string) else ("Property 7 does not exist")))
, (if (size of item 8 of it = 1) then ( concatenation ";" of values of results (item 0 of it, elements of item 8 of it)) else (if (size of item 8 of it > 1) then (("Property 8 duplicates: " & concatenation "|" of ((name of it) & "=" & (id of it as string)) of elements of item 8 of it) as string) else ("Property 8 does not exist")))
, (if (size of item 9 of it = 1) then ( concatenation ";" of values of results (item 0 of it, elements of item 9 of it)) else (if (size of item 9 of it > 1) then (("Property 9 duplicates: " & concatenation "|" of ((name of it) & "=" & (id of it as string)) of elements of item 9 of it) as string) else ("Property 9 does not exist")))
, (if (size of item 10 of it = 1) then ( concatenation ";" of values of results (item 0 of it, elements of item 10 of it)) else (if (size of item 9 of it > 1) then (("Property 9 duplicates: " & concatenation "|" of ((name of it) & "=" & (id of it as string)) of elements of item 9 of it) as string) else ("Property 10 does not exist")))
) of (
elements of item 0 of it /*expand the computer set - gets you one line per computer*/
,item 1 of it
,item 2 of it
,item 3 of it
,item 4 of it
,item 5 of it
,item 6 of it
,item 7 of it
,item 8 of it
,item 9 of it
,item 10 of it
) of (
set of BES computers
, set of  bes properties whose (reserved flag of it and name of it as lowercase = ("id") as lowercase)
, set of  bes properties whose (reserved flag of it and name of it as lowercase = ("computer name") as lowercase)
, set of  bes properties whose (reserved flag of it and name of it as lowercase = ("last report time") as lowercase)
, set of  bes properties whose (reserved flag of it and name of it as lowercase = ("device type") as lowercase)
, set of  bes properties whose ( name of it as lowercase = ("make") as lowercase)
, set of  bes properties whose ( name of it as lowercase = ("model") as lowercase)
, set of  bes properties whose (reserved flag of it and name of it as lowercase = ("os") as lowercase)
, set of  bes properties whose (reserved flag of it and name of it as lowercase = ("ip address") as lowercase)
, set of  bes properties whose (reserved flag of it and name of it as lowercase = ("mac address") as lowercase)
, set of  bes properties whose (reserved flag of it and name of it as lowercase = ("active directory path") as lowercase)
)
"""

query={"relevance":relevance, "output":"json"}

# Suppress InsecureRequestWarning warnings from requests module
#  These are generated when we do not have a trusted CA certificate on the BES Server
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Note that on any of these Exception handlers, we could either raise our own error and quit the script, or handle the error
# and move on to the next query or next server or ...
try:
    response = requests.request(operation, url , data=query, headers=None, verify=certverify, auth=(username, password), params=None)
    
except Exception as e:
    # This could be an exception such as "server unreachable"
    print("Error encountered connecting to the API: " + str(e) )
    # Quit now?
    #raise ValueError("Error encountered when connecting to API:" + str(e))
else:
    if not response.ok:
        # This could be an error such as "We connected to the server and got HTTP response, but the RESPONSE is "Access Denied" or "Page not Found")
        print("HTTP " + str(response.status_code) + " " + response.reason)
        # quit now?
        #raise ValueError("Error encountered when sending query to " + url + " [query was: " + str(response) + " ]: HTTP " + str(response.status_code) + " " + response.reason)

    else:
        response_json = response.json()
        # Check whether the Relevance Query returned an error before displaying results
        if (response_json.get("error",None) is not None):
            # A Relevance error was returned, provide that error message
            # Sample, based on misspelling "bes computers" in the query:
            # {'result': [], 'error': 'The operator "besx computers" is not defined.'}
            print("An error was encountered processing the Relevance Query.  Full response text follows:")
            print(response_json)
            print(f'Error encountered with Relevance Query:{response_json["error"]}')
            # quit now?
            raise ValueError(f'Error returned from query: {str(response_json["error"])}')
        else:
            # No error, show iterating the results in a couple of different ways...
            #print("Full response text follows:")
            #print(response_json)
            # Sample:  {'result': [[6223155, 'BES-DEV-ROOT'], [6799923, 'BFI-WIN'], [10132642, 'W10-000C291831D']], 'plural': True, 'type': '( integer, string )', 'evaltime_ms': 58}
            #print("Query Results:")
            #print(response_json["result"])
            # Sample: [[6223155, 'BES-DEV-ROOT'], [6799923, 'BFI-WIN'], [10132642, 'W10-000C291831D']]
            print(f'Result Count {len(response_json["result"])}')
            #print(f'Plural: {response_json}')
            #print(f'Result type(s): {response_json["type"]}')
            #print(f'Eval Time:{response_json["evaltime_ms"]}')
            #print(f'Results:')
            #print(str(response_json["result"]))
            
# now we will open a file for writing,
# write the header row,
# and loop through the JSON query result to write each row
results=response_json["result"]
with open(output_csv, 'w', newline='') as data_file:
    # create the csv writer object
    csv_writer = csv.writer(data_file)
    csv_writer.writerow(csv_headers)
    print(f"Wrote output to {output_csv}")    
    for result in results:
        csv_writer.writerow(result)
# with open(f'{output_json}', 'w') as json_out:
#    json_out.write(json.dumps(results, indent=4))
#    print(f"Wrote output to {output_json}")


    
    
