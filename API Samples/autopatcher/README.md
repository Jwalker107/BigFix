# Auto-Patcher Sample Script
This script demonstrates Creating, and optionally Actioning, a Baseline using custom selection criteria for the Fixlet content.

# Initial Setup
## Python Setup
Install Python 3.10 or higher.

Preferably, setup a Python Virtual Environment as described at https://docs.python.org/3/library/venv.html to isolate Python libraries and configuration.

In a command shell, switch to the directory containing this script and install any dependencies via
```
pip install -r requirements.txt
```
## Configuration File
In the script directory, update `config.json` for your environment; or copy it to another name and specify the path using the `--config` option when you run the autopatcher script.
Example content:
```
{
 "bigfix_server":"https://bes-root.local:52311",
 "bes_username": "api-user",
 "keyring_system_name":"autopatcher-keyring",
 "verify": false,   
 "baselines_site": "custom/Test"
}
```
`"bigfix_server"`: URL, including port number, to your BigFix Root Server REST API port.
`"bes_username"` : The user name that should be used to connect to the REST API on your BigFix Server.  At present time, LDAP accounts are supported but SAML authentication is not.
`"keyring_system_name"`: A name that you can create to store the password for the API account in your system using the 'keyring' module.  This allows you to store different passwords with different system names.  This can be any name you designate, and is the name under which the password will be stored in Windows Credential Manager.
`"verify"`: Whether the script should verify the HTTPS certificate of your BigFix REST API.  Generally set to 'true' if you are using custom REST certificates that are trusted by your client system, or 'false' if you are using the default self-signed certificates for BigFix REST API.
`"baselines_site"': The site, relative to "/api/sites", in which you want newly-generated Baselines to be stored.  Options include `custom/CustomSiteName`, `operator/UserName`, or `/master` (please don't use `/master` ! ).

## Patch Query Template Files
Update the template files, or create new ones, as needed.
`baseline_template.xml` is the default XML template used when creating Baselines.
`action_template.xml` is the default XML template used when creating an Action from the new Baseline.

Both of theese XML templates can perform some basic substitutions via bracketed strings; in the example templates `{current_date}` and `{current_time}` will be replaced with the actual current date and time of when the baseline or action was created.  If a literal `{some string}` is required in your template, you may need to escape it as `{{some string}}`

`componenentgroup1.txt` is an example Session Relevance Query used to include only Windows Service Packs or Servicing Stack Updates in a Baseline Component Group.
`componenentgroup2.txt` is an example Session Relevance Query used to include only Windows patches (excluding Service Packs and Servicing Stack Updates).
`componenentgroup3.txt` is an example Session Relevance Query used to include only Windows Application updates.

You may update these, or create additional query files, as these will be specified on the command line when running the autopatcher script.

In all cases, the query for fixlets *must* return these fields, in this order:
```
Fixlet Name, Fixlet Site URL, Fixlet ID, 
Fixlet Action ID, Fixlet Action Script,  Fixlet Relevance, 
Action Success Criteria, Fixlet Type
```

## Computer Targeting Template Files
`computers_query.txt` contains an example query for targeting computers when creating an Action.  query should return True or False when evaluated on client computers.  The example query is used to target only computers containing 'test' in their computer name.  

## Saving Password to Keyring
The script uses Python's 'keyring' module to store credentials into the system-provided keyring.  On Windows, this is the Windows Credential Store.  On Mac and Linux, several options are tried in a priority order to use the best available (but generally, is only usable with a graphical login).  For details see https://pypi.org/project/keyring/

For our purposes, what is important to know is that we need to execute the `save_keyring.py` script at least once, to store a password for the account matching the `keyring_system_name` and `bes_username` values specified in the config.json.  For instance, with the defaults of
```
 "bes_username": "api-user",
 "keyring_system_name":"autopatcher-keyring",
 ```
 we need to store that password by running the 'save_keyring.py' script and answering the prompts:
 ```
 (temp-venv) C:\BigFix\API Samples\autopatcher>python save_keyring.py
Enter the system name for the keyring: autopatcher-keyring
Enter the username for the keyring: api-user
Enter password for the keyring:
Confirm password:
Credential saved to keyring.
```
# Usage
## Running Autopatcher

To perform the example execution, after updating the configuration files described above, we may execute the autopatcher script from a command prompt.

### Generate a Baseline Preview without saving anything to the server
```
python autopatcher.py --query componentgroup1.txt --query componentgroup2.txt --query componentgroup3.txt --preview
```

### Create a Baseline and save it on the server in the site defined in the config.json
```
python autopatcher.py --query componentgroup1.txt --query componentgroup2.txt --query componentgroup3.txt

Adding 0 fixlets to the BaselineComponentGroup
Adding 13 fixlets to the BaselineComponentGroup
Adding 12 fixlets to the BaselineComponentGroup
Posting Baseline to https://bes-root.local:52311/api/site/custom/Test
Successfully posted baseline ID 195887
Execution Time:  6.64
```

### Create a Baseline, save it on the server, and generate a Preview of an Action (without submitting the action).  The action would be targeted to computers matching the query in 'computers_query.txt' 
```
python autopatcher.py --query componentgroup1.txt --query componentgroup2.txt --query componentgroup3.txt --preview-action --target-computer-query computers_query.txt

Adding 0 fixlets to the BaselineComponentGroup
Adding 13 fixlets to the BaselineComponentGroup
Adding 12 fixlets to the BaselineComponentGroup
Posting Baseline to https://bes-root.local:52311/api/site/custom/Test
Successfully posted baseline ID 195888
Generating Action XML for the Baseline
<BES xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="BES.xsd">
<SourcedFixletAction>
 <SourceFixlet><GatherURL>http://BES-Dev-Root:52311/cgi-bin/bfgather.exe/CustomSite_Test</GatherURL><FixletID>195888</FixletID></SourceFixlet>
 <Target><CustomRelevance>/*
Relevance query for targeting computers.  Must return True or False when evaluated by the computers.
*/

computer name as lowercase starts with "test"</CustomRelevance></Target><Settings />
</SourcedFixletAction>
</BES>
Preview mode, skipping action POST
```
### Create a Baseline, save it on the server, and take an Action from the baseline.  The action would be targeted to computers matching the query in 'computers_query.txt' 

```
 python autopatcher.py --query componentgroup1.txt --query componentgroup2.txt --query componentgroup3.txt --action --target-computer-query computers_query.txt

Adding 0 fixlets to the BaselineComponentGroup
Adding 13 fixlets to the BaselineComponentGroup
Adding 12 fixlets to the BaselineComponentGroup
Posting Baseline to https://bes-root.local:52311/api/site/custom/Test
Successfully posted baseline ID 195889
Generating Action XML for the Baseline
Posting Action to https://bes-root.local:52311/api/actions
Action POST succeeded with 200
Action Response:
<BESAPI xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="BESAPI.xsd">
        <Action Resource="https://bes-root.local:52311/api/action/195890" LastModified="Thu, 07 Aug 2025 14:28:25 +0000">  
                <Name>Autopatcher Baseline 2025-08-07</Name>
                <ID>195890</ID>
        </Action>
</BESAPI>
Action ID is 195890
Execution Time:  6.89
```

### Create a Baseline, save it on the server, and take an Action from the baseline.  The action would be statically-targeted to specific computer names
```
(temp-venv) C:\BigFix\API Samples\autopatcher>  python autopatcher.py --query componentgroup1.txt --query componentgroup2.txt --query componentgroup3.txt --action --target-computer-names Computer1 Computer2 Computer3
Adding 0 fixlets to the BaselineComponentGroup
Adding 13 fixlets to the BaselineComponentGroup
Adding 12 fixlets to the BaselineComponentGroup
Posting Baseline to https://bes-root.local:52311/api/site/custom/Test
Successfully posted baseline ID 195916
Generating Action XML for the Baseline
Posting Action to https://bes-root.local:52311/api/actions
Action POST succeeded with 200
Action Response:
<BESAPI xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="BESAPI.xsd">
        <Action Resource="https://bes-root.local:52311/api/action/195917" LastModified="Thu, 07 Aug 2025 14:29:53 +0000">  
                <Name>Autopatcher Baseline 2025-08-07</Name>
                <ID>195917</ID>
        </Action>
</BESAPI>
Action ID is 195917
Execution Time:  6.65
```

## All Comand-Line Options
```
--config <path-to-config-file>
  Use an alternate configuration file; useful for having a "Pre-Production" baseline in one site and "Production" baseline in another, or creating Baselines/Actions on multiple root servers.

--template <path-to-template.xml>
  Use an alternate Baseline template for creating the baseline.  Useful for things like changing baseline name conventions for differnet sites or servers.  Defaults to 'baseline_template.xml' in the script directory.

--query <path-to-query-template>
  Use the Session Relevance query contained in the text file to select Fixlets/Tasks to add to a Component Group.  May be specified multiple times to create multiple component groups, i.e. `--query servicepacks.txt --query servicing_stack_updates.txt --query critical-patches.txt`

--preview
  Only generate a Preview of a baseline, without posting the new baseline to the server

--preview-action
  After POSTing a Baseline, then generate a Preview of an Action from the new baseline.

--action
  After POSTing a Baseline, generate an Action from the new baseline.

--action-template <path-to-template.xml>
  When generating an Action or Action Preview, use the specified template for the new action.  Defaults to `action_template.xml` in the script directory.

--target-computer-query <path-to-file.txt>
  When generating an Action or Action Preview, use the client relevance from this file as a `<CustomRelevance>` targeting option.  Computers will evaluate this relevance to determine whether they should execute the action.

--target-computer-names <Name1 [Name2 ..]>
  When generating an Action or Action Preview, use the list of space-separated computer names to target the action.

--target-computer-names <id1 [id2 ..]>
  When generating an Action or Action Preview, use the list of space-separated computer IDs to target the action.

--target-allcomputers
  When generating an Action or Action Preview, use <AllComputers>True</AllComputers> to create an action that runs on every computer (if relevant).

```
