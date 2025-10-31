# Using Custom Web Reports

* Enable Custom Reports by adding configuration settings "AllowCustomReportCreation" and "AllowUserViewCustom" as documented at https://help.hcltechsw.com/bigfix/10.0/platform/Platform/Web_Reports/c_creating_a_custom_report.html
* In the Report List page, select the "Import Report" link.
* Browse to the Web Report you wish to import and select the type of report (XML or HTML; reports hosted here are generally XML)

# Disabling Content Security Policy
In BigFix 11.0, Web Reports added by default a Content-Security-Policy header that prevents the browser from downloading and executing JavaScript outside of those delivered by Web Reports itself.  That prevents the browser from sourcing the jQuery or dataTables javascript files used in these examples.
As a workaround, you may configure Web Reports 11.0.1 or higher to disable the CSPHeader.

Description is at [Enabling security policy for reports](https://help.hcl-software.com/bigfix/11.0/platform/Platform/Web_Reports/c_enabling_sec_policy.html)

In this case we would need to set EnableCSPHeader to 0 to disable using the CSPHeader.

A future version of Web Reports may allow an option to customize the CSP value (allow scripts from some sites and not from others), but for now it’s either On or Off; and if it’s On, no JavaScripts can be loaded from external servers.

An alternative workaround, is for the places in these Dashboards where I have a `<SCRIPT src=>` tag, to copy those JavaScript files to your Web Reports server directly and change these Script URLs to reference the scripts locally.


