***
This is not supported content.  Please do not contact the Support Desk for questions.  Please post to forum.bigfix.com or private message 
to @jasonwalker at forum.bigfix.com for any questions
********
This is an example of sending SourcedFixletAction instances, with Secure Parameters, using the REST API.
The specific use-case is to repeatedly action Oracle Compliance checking tasks, where each target 
may require different Instance Name and Instance Home Directory values.

Usage (tested on Python 3.11, expected to work on Python 3.9 or higher):
* Install Python 3.x
* Copy script, requirements.txt, and sample oracle_config.json to a common directory
* Install the required modules via `pip install -r requirements.txt`
* Update the JSON configuration file as needed (details below)
* execute   python RepeatActionsWithParameters.py oracle_config.json
	(substitute other JSON configuration files/paths as needed)

JSON configuration file notes:
* File is in JSON format
* root_url, source_fixlet_site, source_fixlet_id, and source_action_name is unique within the file.  For multiple Fixlets, use multiple configuraton files.
* 'Targets' is an array of multiple values.  This can be used to send multiple actions/configurations for the same source fixlet.
* Each Target contains an array of Computer Names or Computer IDs.  The action will be sent targeting all of the Computer Names or Computer IDs in the array.
   - Using Computer IDs is faster; with Computer Names, each name must be resolved to a Computer ID first, which is performed with a Session Relevance query.
* Each Target contains an array of Instances.  This must be provided, with an instance_name and instance_home value.  Multiple instances can be targeted by each Action.

The script itself prompts for BigFix credentials, as well as the Oracle credentials to embed when sending Actions.  The same credentials will be applied to each Action sent in the configuration file.

The Single/Multiple relationships is shown (crudely) below:
1 Configuration File -> 
   1 Source Fixlet -> 
      (Multiple Actions, one for each Target element) -> 
		(Multiple Computers, for each ComputerName/ComputerID) / (Multiple Instances, for all elements in Instances)
      (Multiple Actions, one for each Target element) -> 
		(Multiple Computers, for each ComputerName/ComputerID) / (Multiple Instances, for all elements in Instances)