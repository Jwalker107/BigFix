"""
Example of retrieving a Session Relevance result and outputting as a JSON dictionary with key/value pairs

As an added bonus, HTTPAdapter and Retry are used to automatically retry on retryable HTTP return codes such as 'server busy' or 'server unavailable'
"""
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3 import Retry
import os
import json


### Configuration settings ###
server="https://bes-root.local:52311"

# file storing credentials as key/value pairs for 'username' and 'password'
creds_file='c:\\github\\conf\\lab-creds.json'
with open(creds_file, 'r') as file:
    creds=json.load(file)

username=creds["username"]
password=creds["password"]

# File in which to save output
output_file='c:\\temp\\result.json'
# result_columns maps the positions of elements in the query result to the column names that should be used for dictionary keys
result_columns=["Computer ID", "Computer Name", "CPU", "Total Size of System Drive", "Free Space on System Drive"]
query="""
(
 id of item 0 of it
 , name of item 0 of it | "[Name Not Reported]"
 , (if exists results (item 0 of it, item 1 of it) then unique value of concatenation ";" of values of results (item 0 of it, item 1 of it) else "[Not Reported]") of it
 , (if exists results (item 0 of it, item 2 of it) then unique value of concatenation ";" of values of results (item 0 of it, item 2 of it) else "[Not Reported]") of it
 , (if exists results (item 0 of it, item 3 of it) then unique value of concatenation ";" of values of results (item 0 of it, item 3 of it) else "[Not Reported]") of it
 ) of
(
 elements of item 0 of it
 , item 1 of it
 , item 2 of it
 , item 3 of it
) 
of (set of bes computers
, bes properties whose (reserved flag of it and name of it = "CPU")
, bes properties whose (default flag of it and name of it = "Total Size of System Drive")
, bes properties whose (default flag of it and name of it = "Free Space on System Drive")
)
"""


my_session=Session()
# TODO - consider adding Certificate Verification
my_session.verify=False

# Provide the credentials that will be persisted in the Session object
my_session.auth = (username, password)

# Bonus - Add automatic retries & timeouts to the Session operations
adapter=HTTPAdapter(
        max_retries=Retry(total=4,
            backoff_factor=1,
            allowed_methods=None,
            status_forcelist=[429,500,502,503,504]
            )
        )

my_session.mount("http://", adapter)
my_session.mount("http2://", adapter)


# Test the session login
response=my_session.get(url=server + "/api/login")

if not response.ok:
    raise ValueError(f"Server login failed with {response.status_code} : {response.text}")

response=my_session.post(url=server + "/api/query", data={"relevance":query,"output":"json"}, auth=(username, password))
if not response.ok:
    raise ValueError(f"Query failed with {response.status_code} : {response.text}")

response_json=json.loads(response.text)
# Check for Relevance Evaluation error
if "error" in response_json.keys():
    raise ValueError(f"Relevance evaluation error occurred: {str(response_json['error'])}")
else:
    results_array=[]
    column_count=len(result_columns)
    # Loop through result rows
    for result in response_json["result"]:
        # Loop through each column of the result, creating a dicationary with key from column map and value from query result.
        result_dict={}
        for i in range(0, column_count):
            result_dict[result_columns[i]]=result[i]
        results_array.append(result_dict)
    
    # Save the result to a json file
    with open(output_file, "w") as output:
        output.write(json.dumps(results_array, indent=4))