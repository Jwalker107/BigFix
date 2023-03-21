"""
Example using requests.Session to perform repeated operations over a single HTTPS session
This loops through each Task in a given directory and PUTS the task to the BigFix Server at the given URL
The 'localdir' should contain a number of Tasks in the format "123.bes", "456.bes", etc.
Each file should have the '.bes' extension and the filename component should be a numeric Task ID in the Site

As an added bonus, HTTPAdapter and Retry are used to automatically retry on retryable HTTP return codes such as 'server busy' or 'server unavailable'
"""
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3 import Retry
import os


### Configuration settings ###
server="https://bes-root.local:52311"
username="mo"
password="Not Gonna Get Me Today!"

server_repo="/api/task/custom/Temp"
localdir="C:\\Temp\\apitest\\Temp\\task"


my_session=Session()
# Todo - add Certificate Verification
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

# Loop through each .bes file in local directory
for filename in os.listdir(localdir):
    if not filename.endswith('.bes'):
        print(f"Skipping {filename}, not a .bes file")
        continue
    # Split filename on the last period, expect the id should be an integer fixlet/task ID
    id=filename.rsplit(".",1)[0]
    if not id.isnumeric():
        print(f"Filename {filename} does not translate to a numeric ID, skipping")
        continue
    
    target_url=f"{server}{server_repo}/{id}"
    print(f"PUT {filename} to {target_url}")
    with open(os.path.join(localdir, filename), 'rb') as filecontent:
        response=my_session.put(url=target_url, data=filecontent)
        print(f"Result OK:{response.ok}, Code:{response.status_code}, Text:{response.text}")
    

    


