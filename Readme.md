AI-usecase-for-Check-in-Readings

We analyze automotive diagnostic report files containing DTCs and environmental data from various vehicle models and software releases. We manually review DTCs of the ECU we own and related ECUs to determine root causes. The process is repetitive, time-consuming and requires correlation across multiple ECUs and historical datasets. We can leverage AI to automatically analyze large volumes of such reports, identify DTC trends across software releases, detect recurring issues after specific releases, correlate faults between interacting ECUs, and generate actionable diagnostic insights.

This development involves 5 levels, at present level 1 is complete i.e., building a DTC Intelligence Database using the dummy diagnostics files. Refer the documents from the Doc folder for more details.

The list of tools those were used in Level - 1 implementation -

VSCode - IDE for Python coding
PostGreSQL - Data Base (configure the database with username & passsword, these same credentials would be hardcoded in the script)
Here are the details of the 5 levels involved -

Level 1 - Build a DTC Intelligence Database
Level 2 - AI-Assisted Root Cause Intelligence
Level 3 - Cross-ECU Correlation Engine
Level 4 - Release Regression Detection
Level 5 - Predictive Failure Analysis
Note -

Directory Python Code\Input\diagnostic_reports contains the dummy diagnostic files for processing Directory Python Code\output is auto generated, do not modify that. Export of excel & csv files is configurable by the configuration flag - EXPORT_CSV & EXPORT_EXCEL (change them to "True" if you want to generate the excel & csv reports)
Steps to run the scripts -

Install the required tools mentioned above
Install the required python dependencies mentioned in the requirements.txt file
Download the repo
In the VSCode terminal, in the path AI-usecase-for-Check-in-Readings\Python Code run the command .\run_parser.bat
If the tools installation & all the python dependencies are in place, you will see output folder generated. In the PostGreSQL, a new databse named MyDB will created with 4 tables containing the diagnostics info.
