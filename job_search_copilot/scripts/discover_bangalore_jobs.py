#!/usr/bin/env python3
"""Discover Bangalore PM/TPM/Program Manager roles from public job board APIs."""

from __future__ import annotations

import csv
import json
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

USER_AGENT = "JobSearchCopilot/1.0 (personal job research)"
BANGALORE_PAT = re.compile(r"\b(bangalore|bengaluru|blr)\b", re.I)
ROLE_PAT = re.compile(
    r"\b("
    r"product\s+manager|senior\s+product\s+manager|group\s+product\s+manager|"
    r"principal\s+product\s+manager|lead\s+product\s+manager|staff\s+product\s+manager|"
    r"associate\s+product\s+manager|product\s+owner|technical\s+product\s+manager|"
    r"platform\s+product\s+manager|api\s+product\s+manager|director[,\s]+product|"
    r"program\s+manager|senior\s+program\s+manager|technical\s+program\s+manager|"
    r"group\s+program\s+manager|principal\s+program\s+manager|"
    r"product\s+lead|head\s+of\s+product|product\s+operations|delivery\s+manager"
    r")\b",
    re.I,
)
EXCLUDE_PAT = re.compile(
    r"\b(intern|internship|campus|fresher|software\s+engineer(?!\s+product)|"
    r"backend\s+engineer|frontend\s+engineer|data\s+scientist|sales\s+manager|"
    r"account\s+manager|recruiter|customer\s+support|graphic\s+designer|"
    r"product\s+design|business\s+analyst|design\s+director|ux\s+designer|"
    r"visual\s+designer|content\s+designer)\b",
    re.I,
)

GREENHOUSE_BOARDS = [
    ("stripe", "Stripe"), ("figma", "Figma"), ("notion", "Notion"), ("dropbox", "Dropbox"),
    ("gitlab", "GitLab"), ("hashicorp", "HashiCorp"), ("mongodb", "MongoDB"),
    ("cloudflare", "Cloudflare"), ("datadog", "Datadog"), ("hubspot", "HubSpot"),
    ("asana", "Asana"), ("databricks", "Databricks"), ("okta", "Okta"),
    ("pagerduty", "PagerDuty"), ("twilio", "Twilio"), ("elastic", "Elastic"),
    ("confluent", "Confluent"), ("rubrik", "Rubrik"), ("zscaler", "Zscaler"),
    ("crowdstrike", "CrowdStrike"), ("servicenow", "ServiceNow"), ("workday", "Workday"),
    ("salesforce", "Salesforce"), ("adobe", "Adobe"), ("intuit", "Intuit"),
    ("atlassian", "Atlassian"), ("reddit", "Reddit"), ("robinhood", "Robinhood"),
    ("plaid", "Plaid"), ("shopify", "Shopify"), ("grammarly", "Grammarly"),
    ("coursera", "Coursera"), ("duolingo", "Duolingo"), ("andela", "Andela"),
    ("chargebee", "Chargebee"), ("postman", "Postman"), ("freshworks", "Freshworks"),
    ("browserstack", "BrowserStack"), ("lambdatest", "LambdaTest"), ("clevertap", "CleverTap"),
    ("moengage", "MoEngage"), ("amplitude", "Amplitude"), ("mixpanel", "Mixpanel"),
    ("grafana", "Grafana Labs"), ("harness", "Harness"), ("launchdarkly", "LaunchDarkly"),
    ("snyk", "Snyk"), ("jfrog", "JFrog"), ("kong", "Kong"), ("cockroachlabs", "Cockroach Labs"),
    ("supabase", "Supabase"), ("miro", "Miro"), ("airtable", "Airtable"), ("zapier", "Zapier"),
    ("canva", "Canva"), ("deel", "Deel"), ("gong", "Gong"), ("zendesk", "Zendesk"),
    ("intercom", "Intercom"), ("palantir", "Palantir"), ("dell", "Dell"),
    ("intel", "Intel"), ("amd", "AMD"), ("nvidia", "Nvidia"), ("qualcomm", "Qualcomm"),
    ("broadcom", "Broadcom"), ("arm", "Arm"), ("synopsys", "Synopsys"), ("cadence", "Cadence"),
    ("ansys", "Ansys"), ("mathworks", "MathWorks"), ("autodesk", "Autodesk"),
    ("trimble", "Trimble"), ("hexagon", "Hexagon"), ("hp", "HP"), ("lenovo", "Lenovo"),
    ("supermicro", "Supermicro"), ("micron", "Micron"), ("western", "Western Digital"),
    ("seagate", "Seagate"), ("coinbase", "Coinbase"), ("discord", "Discord"),
    ("brex", "Brex"), ("ramp", "Ramp"), ("vercel", "Vercel"), ("linear", "Linear"),
    ("retool", "Retool"), ("netlify", "Netlify"), ("tailscale", "Tailscale"),
    ("1password", "1Password"), ("calendly", "Calendly"), ("loom", "Loom"),
    ("remote", "Remote"), ("outreach", "Outreach"), ("salesloft", "SalesLoft"),
    ("segment", "Segment"), ("planetscale", "PlanetScale"), ("bitwarden", "Bitwarden"),
    ("netflix", "Netflix"), ("spotify", "Spotify"), ("lyft", "Lyft"), ("doordash", "DoorDash"),
    ("instacart", "Instacart"), ("affirm", "Affirm"), ("square", "Block/Square"),
    ("roblox", "Roblox"), ("epicgames", "Epic Games"), ("unity", "Unity"),
    ("waymo", "Waymo"), ("rivian", "Rivian"), ("tesla", "Tesla"), ("spacex", "SpaceX"),
    ("mapbox", "Mapbox"), ("esri", "Esri"), ("garmin", "Garmin"), ("tomtom", "TomTom"),
    ("here", "HERE Technologies"), ("bosch", "Bosch"), ("harman", "Harman"),
    ("samsung", "Samsung"), ("marvell", "Marvell"), ("mediatek", "MediaTek"),
    ("siemens", "Siemens"), ("schneider", "Schneider Electric"), ("abb", "ABB"),
    ("ge", "GE"), ("honeywell", "Honeywell"), ("emerson", "Emerson"),
    ("rockwell", "Rockwell Automation"), ("ptc", "PTC"), ("aveva", "AVEVA"),
    ("dassault", "Dassault Systèmes"), ("bentley", "Bentley Systems"),
]

LEVER_SITES = [
    ("netflix", "Netflix"), ("spotify", "Spotify"), ("lyft", "Lyft"),
    ("doordash", "DoorDash"), ("instacart", "Instacart"), ("affirm", "Affirm"),
    ("square", "Block/Square"), ("roblox", "Roblox"), ("coinbase", "Coinbase"),
    ("discord", "Discord"), ("brex", "Brex"), ("ramp", "Ramp"),
    ("vercel", "Vercel"), ("linear", "Linear"), ("retool", "Retool"),
    ("netlify", "Netlify"), ("tailscale", "Tailscale"), ("1password", "1Password"),
    ("calendly", "Calendly"), ("loom", "Loom"), ("remote", "Remote"),
    ("outreach", "Outreach"), ("salesloft", "SalesLoft"), ("segment", "Segment"),
    ("planetscale", "PlanetScale"), ("bitwarden", "Bitwarden"), ("zendesk", "Zendesk"),
    ("intercom", "Intercom"), ("palantir", "Palantir"), ("shieldai", "Shield AI"),
    ("skydio", "Skydio"), ("aurora", "Aurora"), ("nuro", "Nuro"), ("zoox", "Zoox"),
    ("motional", "Motional"), ("mapbox", "Mapbox"), ("esri", "Esri"),
    ("garmin", "Garmin"), ("tomtom", "TomTom"), ("here", "HERE Technologies"),
    ("bosch", "Bosch"), ("harman", "Harman"), ("samsung", "Samsung"),
    ("arm", "Arm"), ("synopsys", "Synopsys"), ("cadence", "Cadence"),
    ("ansys", "Ansys"), ("mathworks", "MathWorks"), ("autodesk", "Autodesk"),
    ("trimble", "Trimble"), ("hexagon", "Hexagon"), ("hp", "HP"), ("lenovo", "Lenovo"),
    ("micron", "Micron"), ("western", "Western Digital"), ("seagate", "Seagate"),
    ("intel", "Intel"), ("amd", "AMD"), ("nvidia", "Nvidia"), ("qualcomm", "Qualcomm"),
    ("broadcom", "Broadcom"), ("marvell", "Marvell"), ("mediatek", "MediaTek"),
    ("siemens", "Siemens"), ("schneider", "Schneider Electric"), ("abb", "ABB"),
    ("ge", "GE"), ("honeywell", "Honeywell"), ("emerson", "Emerson"),
    ("rockwell", "Rockwell Automation"), ("ptc", "PTC"), ("aveva", "AVEVA"),
    ("dassault", "Dassault Systèmes"), ("bentley", "Bentley Systems"),
    ("rivian", "Rivian"), ("tesla", "Tesla"), ("spacex", "SpaceX"), ("waymo", "Waymo"),
    ("epicgames", "Epic Games"), ("unity", "Unity"),
]

ASHBY_ORGS = [
    ("openai", "OpenAI"), ("anthropic", "Anthropic"), ("perplexity", "Perplexity"),
    ("cohere", "Cohere"), ("scale", "Scale AI"), ("huggingface", "Hugging Face"),
    ("runway", "Runway"), ("character", "Character.AI"), ("together", "Together AI"),
    ("replicate", "Replicate"), ("modal", "Modal"), ("anyscale", "Anyscale"),
    ("weights-biases", "Weights & Biases"), ("langchain", "LangChain"),
    ("pinecone", "Pinecone"), ("neon", "Neon"), ("hasura", "Hasura"), ("prisma", "Prisma"),
    ("railway", "Railway"), ("sentry", "Sentry"), ("incident", "Incident.io"),
    ("rootly", "Rootly"), ("blameless", "Blameless"), ("cortex", "Cortex"),
    ("opslevel", "OpsLevel"), ("port", "Port"), ("humanitec", "Humanitec"),
    ("split", "Split"), ("pendo", "Pendo"), ("fullstory", "FullStory"),
    ("logrocket", "LogRocket"), ("bugsnag", "Bugsnag"), ("rollbar", "Rollbar"),
    ("coralogix", "Coralogix"), ("logz", "Logz.io"), ("mezmo", "Mezmo"),
    ("graylog", "Graylog"), ("opentelemetry", "OpenTelemetry"),
    ("victoriametrics", "VictoriaMetrics"), ("opensearch", "OpenSearch"),
]


@dataclass
class JobLead:
    title: str
    company_name: str
    location: str
    platform: str
    job_url: str
    snippet: str = ""
    source_type: str = "live"  # live | curated

    def key(self) -> str:
        return f"{self.company_name.lower().strip()}|{self.title.lower().strip()}"


def _get_json(url: str, timeout: int = 30) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _html_to_text(html: str, limit: int = 500) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"&nbsp;|&amp;|&lt;|&gt;|&#39;|&quot;", " ", text)
    return re.sub(r"\s+", " ", text).strip()[:limit]


def _is_bangalore(loc: str, title: str = "", snippet: str = "", *, location_only: bool = False) -> bool:
    if location_only:
        return bool(BANGALORE_PAT.search(loc))
    return bool(BANGALORE_PAT.search(f"{loc} {title} {snippet}"))


def _is_target_role(title: str, snippet: str = "") -> bool:
    blob = f"{title} {snippet}"
    return bool(ROLE_PAT.search(blob)) and not bool(EXCLUDE_PAT.search(blob))


def fetch_greenhouse(board: str, company_label: str) -> list[JobLead]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
    try:
        data = _get_json(url)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return []
    out: list[JobLead] = []
    for j in data.get("jobs") or []:
        title = j.get("title") or ""
        loc = (j.get("location") or {}).get("name") or ""
        snippet = _html_to_text(j.get("content") or "", 800)
        if not _is_target_role(title, snippet) or not _is_bangalore(loc, title, snippet, location_only=True):
            continue
        out.append(JobLead(title, company_label, loc or "Bangalore, India", "Greenhouse",
                           j.get("absolute_url") or "", snippet, "live"))
    return out


def fetch_lever(site: str, company_label: str) -> list[JobLead]:
    url = f"https://api.lever.co/v0/postings/{site}?mode=json"
    try:
        data = _get_json(url)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return []
    out: list[JobLead] = []
    for j in data or []:
        title = j.get("text") or ""
        cats = j.get("categories") or {}
        loc = cats.get("location") or ""
        if isinstance(cats.get("allLocations"), list):
            loc = loc or ", ".join(cats["allLocations"])
        snippet = (j.get("descriptionPlain") or "")[:800]
        if not _is_target_role(title, snippet) or not _is_bangalore(loc, title, snippet, location_only=True):
            continue
        out.append(JobLead(title, company_label, loc or "Bangalore, India", "Lever",
                           j.get("hostedUrl") or j.get("applyUrl") or "", snippet, "live"))
    return out


def fetch_ashby(org: str, company_label: str) -> list[JobLead]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{org}"
    try:
        data = _get_json(url)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return []
    out: list[JobLead] = []
    for j in data.get("jobs") or []:
        title = j.get("title") or ""
        loc = j.get("location") or ""
        snippet = (j.get("descriptionPlain") or j.get("description") or "")[:800]
        if not _is_target_role(title, snippet) or not _is_bangalore(loc, title, snippet, location_only=True):
            continue
        out.append(JobLead(title, company_label, loc or "Bangalore, India", "Ashby",
                           j.get("jobUrl") or j.get("applyUrl") or "", snippet, "live"))
    return out


# Curated Bangalore PM/TPM leads (career pages + known openings) — used to fill gaps
CURATED_JOBS: list[JobLead] = [
    JobLead("Group Product Manager, GenAI", "Intuit", "Bangalore, India", "LinkedIn",
            "https://www.linkedin.com/jobs/search/?keywords=Group%20Product%20Manager%20GenAI%20Intuit&location=Bangalore",
            "Martech/DXP GenAI; 12-17 yrs PM; people leadership.", "curated"),
    JobLead("Senior Product Manager - Healthcare SaaS", "Confidential (via recruiter)", "Bengaluru, India", "LinkedIn",
            "https://www.linkedin.com/jobs/search/?keywords=Senior%20Product%20Manager%20Healthcare%20SaaS&location=Bengaluru",
            "B2B SaaS PM; AI healthcare; 5-9 yrs; up to 70 LPA.", "curated"),
    JobLead("Product Manager", "Elfina Health", "Bengaluru, India", "LinkedIn",
            "https://www.linkedin.com/company/elfina-health/jobs/", "0-to-1 health-tech PM; Koramangala; 4+ yrs.", "curated"),
    JobLead("Product Manager - Hormone Insights", "Health-tech", "Bengaluru, India", "LinkedIn",
            "https://www.linkedin.com/jobs/search/?keywords=Product%20Manager%20Hormone%20Health%20Bangalore&location=Bengaluru",
            "Consumer health-tech; 5-8 yrs; 40-50 LPA.", "curated"),
    JobLead("Senior Product Manager - Payments", "PhonePe", "Bangalore, India", "PhonePe Careers",
            "https://www.phonepe.com/careers/", "Fintech PM; payments platform.", "curated"),
    JobLead("Product Manager - Merchant Platform", "Razorpay", "Bangalore, India", "Razorpay Careers",
            "https://razorpay.com/jobs/", "B2B payments & merchant products.", "curated"),
    JobLead("Senior Product Manager", "Flipkart", "Bangalore, India", "Flipkart Careers",
            "https://www.flipkartcareers.com/#!/jobsearch", "E-commerce PM; supply chain / OMS.", "curated"),
    JobLead("Group Product Manager", "Swiggy", "Bangalore, India", "Swiggy Careers",
            "https://careers.swiggy.com/", "Food delivery / quick commerce PM.", "curated"),
    JobLead("Senior Product Manager - Logistics", "Meesho", "Bangalore, India", "Meesho Careers",
            "https://careers.meesho.com/", "Supply chain & fulfillment PM.", "curated"),
    JobLead("Product Manager - Platform", "CRED", "Bangalore, India", "CRED Careers",
            "https://careers.cred.club/", "Fintech platform PM.", "curated"),
    JobLead("Technical Program Manager", "Google", "Bangalore, India", "Google Careers",
            "https://www.google.com/about/careers/applications/jobs/results/?location=Bangalore&q=technical%20program%20manager",
            "Cloud / ads / core TPM.", "curated"),
    JobLead("Product Manager II", "Microsoft", "Bangalore, India", "Microsoft Careers",
            "https://apply.careers.microsoft.com/careers?location=Bangalore&keywords=product%20manager",
            "Azure / M365 / enterprise PM.", "curated"),
    JobLead("Senior Product Manager", "Adobe", "Bangalore, India", "Adobe Careers",
            "https://careers.adobe.com/us/en/search-results?keywords=product%20manager&location=Bangalore",
            "Creative / experience cloud PM.", "curated"),
    JobLead("Product Manager - SaaS", "Freshworks", "Bangalore, India", "Freshworks Careers",
            "https://www.freshworks.com/company/careers/", "B2B SaaS CRM / ITSM PM.", "curated"),
    JobLead("Senior Product Manager", "SAP", "Bangalore, India", "SAP Careers",
            "https://jobs.sap.com/", "Enterprise ERP / cloud PM.", "curated"),
    JobLead("Technical Program Manager", "Cisco", "Bangalore, India", "Cisco Careers",
            "https://jobs.cisco.com/jobs/SearchJobs/?keyword=technical%20program%20manager",
            "Networking / security TPM.", "curated"),
    JobLead("Senior Product Manager - Order Management", "Dell", "Bangalore, India", "Dell Careers",
            "https://jobs.dell.com/en/search-jobs/Bangalore", "OMS / supply chain PM — alumni fit.", "curated"),
    JobLead("Program Manager", "IBM", "Bangalore, India", "IBM Careers",
            "https://www.ibm.com/careers/search?field_keyword_18[0]=Bangalore&field_keyword_05[0]=Program%20Manager",
            "Hybrid cloud program mgmt.", "curated"),
    JobLead("Product Manager - API Platform", "Postman", "Bangalore, India", "Postman Careers",
            "https://www.postman.com/company/careers/", "API developer tools PM.", "curated"),
    JobLead("Senior Product Manager", "Groww", "Bangalore, India", "Groww Careers",
            "https://groww.in/careers", "Investing / fintech PM.", "curated"),
    JobLead("Product Manager", "Zerodha", "Bangalore, India", "Zerodha Careers",
            "https://zerodha.com/careers/", "Capital markets PM.", "curated"),
    JobLead("Senior Product Manager", "Udaan", "Bangalore, India", "Udaan Careers",
            "https://careers.udaan.com/", "B2B marketplace PM.", "curated"),
    JobLead("Product Manager - Seller Experience", "Amazon", "Bangalore, India", "Amazon Jobs",
            "https://www.amazon.jobs/en/search?base_query=product%20manager&loc_query=Bangalore",
            "Marketplace seller PM.", "curated"),
    JobLead("Technical Program Manager", "Meta", "Bangalore, India", "Meta Careers",
            "https://www.metacareers.com/jobs?q=technical%20program%20manager&location=Bangalore",
            "WhatsApp / infra TPM.", "curated"),
    JobLead("Senior Product Manager", "Salesforce", "Bangalore, India", "Salesforce Careers",
            "https://careers.salesforce.com/en/jobs/?search=product%20manager&location=Bangalore",
            "CRM / platform PM.", "curated"),
    JobLead("Senior Program Manager", "Walmart Global Tech", "Bangalore, India", "Walmart Careers",
            "https://careers.walmart.com/", "Retail tech program mgmt.", "curated"),
    JobLead("Technical Product Manager", "Rubrik", "Bangalore, India", "Rubrik Careers",
            "https://www.rubrik.com/company/careers", "Data security TPM.", "curated"),
    JobLead("Senior Product Manager", "Ola", "Bangalore, India", "Ola Careers",
            "https://ola.careers/", "Mobility / EV PM.", "curated"),
    JobLead("Senior Product Manager", "ShareChat/Moj", "Bangalore, India", "ShareChat Careers",
            "https://sharechat.com/careers", "Social / short video PM.", "curated"),
    JobLead("Product Manager - Lending", "BharatPe", "Bangalore, India", "BharatPe Careers",
            "https://bharatpe.com/careers", "Fintech lending PM.", "curated"),
    JobLead("Senior Product Manager", "Slice", "Bangalore, India", "Slice Careers",
            "https://sliceit.com/careers", "Neobank / cards PM.", "curated"),
    JobLead("Product Manager - Insurance", "Acko", "Bangalore, India", "Acko Careers",
            "https://www.acko.com/careers/", "Insurtech PM.", "curated"),
    JobLead("Technical Program Manager", "Nvidia", "Bangalore, India", "Nvidia Careers",
            "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite", "AI / GPU platform TPM.", "curated"),
    JobLead("Senior Product Manager", "Qualcomm", "Bangalore, India", "Qualcomm Careers",
            "https://careers.qualcomm.com/", "Semiconductor / mobile PM.", "curated"),
    JobLead("Product Manager - Cloud", "Oracle", "Bangalore, India", "Oracle Careers",
            "https://www.oracle.com/careers/", "OCI / enterprise cloud PM.", "curated"),
    JobLead("Senior Program Manager", "Accenture", "Bangalore, India", "Accenture Careers",
            "https://www.accenture.com/in-en/careers", "Consulting program delivery.", "curated"),
    JobLead("Senior Product Manager", "Elastic", "Bangalore, India", "Elastic Careers",
            "https://jobs.elastic.co/", "Search / observability PM — skill match.", "curated"),
    JobLead("Product Manager - Splunk Observability", "Cisco Splunk", "Bangalore, India", "Splunk Careers",
            "https://www.splunk.com/en_us/careers.html", "Observability / log management PM.", "curated"),
    JobLead("Technical Program Manager", "Uber", "Bangalore, India", "Uber Careers",
            "https://www.uber.com/us/en/careers/list/?location=India-Bangalore", "Mobility / delivery TPM.", "curated"),
    JobLead("Senior Product Manager", "Myntra", "Bangalore, India", "Myntra Careers",
            "https://www.myntra.com/careers", "Fashion e-commerce PM.", "curated"),
    JobLead("Product Manager - Supply Chain", "Licious", "Bangalore, India", "Licious Careers",
            "https://www.licious.in/careers", "D2C / supply chain PM.", "curated"),
    JobLead("Senior Product Manager", "Dunzo", "Bangalore, India", "Dunzo Careers",
            "https://dunzo.com/careers", "Quick commerce PM.", "curated"),
    JobLead("Product Manager - B2B SaaS", "Chargebee", "Bangalore, India", "Chargebee Careers",
            "https://www.chargebee.com/careers/", "Subscription billing SaaS PM.", "curated"),
    JobLead("Senior Product Manager", "CleverTap", "Bangalore, India", "CleverTap Careers",
            "https://clevertap.com/careers/", "MarTech / analytics PM.", "curated"),
    JobLead("Product Manager - HR Tech", "Darwinbox", "Bangalore, India", "Darwinbox Careers",
            "https://darwinbox.com/careers", "HCM SaaS PM.", "curated"),
    JobLead("Technical Program Manager", "LinkedIn", "Bangalore, India", "LinkedIn Careers",
            "https://careers.linkedin.com/jobs/search?keywords=technical%20program%20manager&location=Bangalore",
            "Professional network TPM.", "curated"),
    JobLead("Product Manager - Kubernetes", "Red Hat", "Bangalore, India", "Red Hat Careers",
            "https://www.redhat.com/en/jobs", "OpenShift / platform PM.", "curated"),
    JobLead("Technical Program Manager", "PayPal", "Bangalore, India", "PayPal Careers",
            "https://careers.pypl.com/", "Payments platform TPM.", "curated"),
    JobLead("Senior Product Manager", "Visa", "Bangalore, India", "Visa Careers",
            "https://careers.visa.com/", "Payments network PM.", "curated"),
    JobLead("Product Manager - Cards", "Mastercard", "Bangalore, India", "Mastercard Careers",
            "https://careers.mastercard.com/", "Financial services PM.", "curated"),
    JobLead("Senior Product Manager", "Juspay", "Bangalore, India", "Juspay Careers",
            "https://juspay.io/careers", "Payments orchestration PM.", "curated"),
    JobLead("Product Manager - Checkout", "Cashfree", "Bangalore, India", "Cashfree Careers",
            "https://www.cashfree.com/careers", "Payments gateway PM.", "curated"),
    JobLead("Senior Program Manager", "Tekion", "Bangalore, India", "Tekion Careers",
            "https://www.tekion.com/careers", "Automotive retail SaaS.", "curated"),
    JobLead("Senior Product Manager", "InMobi", "Bangalore, India", "InMobi Careers",
            "https://www.inmobi.com/company/careers/", "Ad-tech PM.", "curated"),
    JobLead("Product Manager - Gaming", "Dream11", "Bangalore, India", "Dream Sports Careers",
            "https://www.dreamsports.group/careers", "Fantasy sports PM.", "curated"),
    JobLead("Technical Program Manager", "ServiceNow", "Bangalore, India", "ServiceNow Careers",
            "https://careers.servicenow.com/", "ITSM / workflow TPM.", "curated"),
    JobLead("Senior Product Manager", "Workday", "Bangalore, India", "Workday Careers",
            "https://www.workday.com/en-us/company/careers.html", "HCM / finance cloud PM.", "curated"),
    JobLead("Product Manager - Security", "Palo Alto Networks", "Bangalore, India", "Palo Alto Careers",
            "https://jobs.paloaltonetworks.com/", "Cybersecurity PM.", "curated"),
    JobLead("Senior Product Manager", "Zscaler", "Bangalore, India", "Zscaler Careers",
            "https://www.zscaler.com/careers", "Zero trust security PM.", "curated"),
    JobLead("Technical Program Manager", "Snowflake", "Bangalore, India", "Snowflake Careers",
            "https://careers.snowflake.com/", "Data cloud TPM.", "curated"),
    JobLead("Senior Product Manager", "Databricks", "Bangalore, India", "Databricks Careers",
            "https://www.databricks.com/company/careers", "Data / AI platform PM.", "curated"),
    JobLead("Product Manager - Observability", "Datadog", "Bangalore, India", "Datadog Careers",
            "https://careers.datadoghq.com/", "APM / monitoring PM — direct skill match.", "curated"),
    JobLead("Senior Product Manager", "New Relic", "Bangalore, India", "New Relic Careers",
            "https://newrelic.com/careers", "Observability PM.", "curated"),
    JobLead("Technical Program Manager", "Twilio", "Bangalore, India", "Twilio Careers",
            "https://www.twilio.com/company/jobs", "Communications API TPM.", "curated"),
    JobLead("Product Manager - API", "Kong", "Bangalore, India", "Kong Careers",
            "https://konghq.com/company/careers", "API gateway PM.", "curated"),
    JobLead("Senior Program Manager", "Confluent", "Bangalore, India", "Confluent Careers",
            "https://www.confluent.io/careers/", "Kafka / streaming PM.", "curated"),
    JobLead("Product Manager - Platform", "HashiCorp", "Bangalore, India", "HashiCorp Careers",
            "https://www.hashicorp.com/careers", "Terraform / infra PM.", "curated"),
    JobLead("Senior Product Manager", "MongoDB", "Bangalore, India", "MongoDB Careers",
            "https://www.mongodb.com/careers", "Database platform PM.", "curated"),
    JobLead("Technical Program Manager", "Stripe", "Bangalore, India", "Stripe Careers",
            "https://stripe.com/jobs/search?office_locations=South+Asia--Bengaluru", "Payments infra TPM.", "curated"),
    JobLead("Senior Product Manager", "Plaid", "Bangalore, India", "Plaid Careers",
            "https://plaid.com/careers/", "Fintech connectivity PM.", "curated"),
    JobLead("Product Manager - Lending", "Navi", "Bangalore, India", "Navi Careers",
            "https://navi.com/careers", "Fintech PM.", "curated"),
    JobLead("Senior Product Manager", "Pine Labs", "Bangalore, India", "Pine Labs Careers",
            "https://www.pinelabs.com/careers", "Merchant payments PM.", "curated"),
    JobLead("Technical Program Manager", "Goldman Sachs", "Bangalore, India", "Goldman Careers",
            "https://www.goldmansachs.com/careers/", "Finance tech TPM.", "curated"),
    JobLead("Product Manager - Travel", "MakeMyTrip", "Bangalore, India", "MakeMyTrip Careers",
            "https://careers.makemytrip.com/", "Travel tech — Expedia adjacent.", "curated"),
    JobLead("Technical Program Manager", "Booking.com", "Bangalore, India", "Booking Careers",
            "https://jobs.booking.com/", "Travel platform TPM.", "curated"),
    JobLead("Senior Product Manager", "Agoda", "Bangalore, India", "Agoda Careers",
            "https://careersatagoda.com/", "Travel / hospitality PM.", "curated"),
    JobLead("Senior Program Manager", "Practo", "Bangalore, India", "Practo Careers",
            "https://practo.com/careers", "Health-tech PM.", "curated"),
    JobLead("Senior Product Manager", "1mg", "Bangalore, India", "Tata 1mg Careers",
            "https://www.1mg.com/jobs", "E-pharmacy PM.", "curated"),
    JobLead("Senior Product Manager", "Urban Company", "Bangalore, India", "Urban Company Careers",
            "https://careers.urbancompany.com/", "Home services marketplace PM.", "curated"),
    JobLead("Product Manager - Logistics", "Delhivery", "Bangalore, India", "Delhivery Careers",
            "https://www.delhivery.com/careers/", "Logistics tech PM.", "curated"),
    JobLead("Product Manager - Fleet", "BlackBuck", "Bangalore, India", "BlackBuck Careers",
            "https://blackbuck.com/careers", "Trucking logistics PM.", "curated"),
    JobLead("Product Manager - EV", "Ather Energy", "Bangalore, India", "Ather Careers",
            "https://www.atherenergy.com/careers", "EV / mobility PM.", "curated"),
    JobLead("Senior Product Manager", "BrowserStack", "Bangalore, India", "BrowserStack Careers",
            "https://www.browserstack.com/careers", "Developer tools PM.", "curated"),
    JobLead("Product Manager - Testing", "LambdaTest", "Bangalore, India", "LambdaTest Careers",
            "https://www.lambdatest.com/careers", "DevTools / QA PM.", "curated"),
    JobLead("Senior Program Manager", "Hasura", "Bangalore, India", "Hasura Careers",
            "https://hasura.io/careers/", "GraphQL / data PM.", "curated"),
    JobLead("Product Manager - Analytics", "Amplitude", "Bangalore, India", "Amplitude Careers",
            "https://amplitude.com/careers", "Product analytics PM.", "curated"),
    JobLead("Senior Product Manager", "Mixpanel", "Bangalore, India", "Mixpanel Careers",
            "https://mixpanel.com/careers/", "Analytics PM.", "curated"),
    JobLead("Senior Product Manager", "MoEngage", "Bangalore, India", "MoEngage Careers",
            "https://www.moengage.com/careers/", "Customer engagement PM.", "curated"),
    JobLead("Product Manager - CRM", "LeadSquared", "Bangalore, India", "LeadSquared Careers",
            "https://www.leadsquared.com/careers/", "Sales CRM PM.", "curated"),
    JobLead("Senior Program Manager", "Zeta", "Bangalore, India", "Zeta Careers",
            "https://www.zeta.tech/careers", "Banking-as-a-service PM.", "curated"),
    JobLead("Senior Product Manager", "Perfios", "Bangalore, India", "Perfios Careers",
            "https://www.perfios.com/careers", "Credit analytics PM.", "curated"),
    JobLead("Technical Program Manager", "Nutanix", "Bangalore, India", "Nutanix Careers",
            "https://www.nutanix.com/company/careers", "Hyperconverged infra TPM.", "curated"),
    JobLead("Product Manager - Identity", "Okta", "Bangalore, India", "Okta Careers",
            "https://www.okta.com/company/careers/", "IAM PM.", "curated"),
    JobLead("Product Manager - SRE Tools", "PagerDuty", "Bangalore, India", "PagerDuty Careers",
            "https://careers.pagerduty.com/", "Incident response PM.", "curated"),
    JobLead("Senior Product Manager", "Grafana Labs", "Bangalore, India", "Grafana Careers",
            "https://grafana.com/about/careers/", "Observability / dashboards PM.", "curated"),
    JobLead("Technical Program Manager", "Honeycomb", "Bangalore, India", "Honeycomb Careers",
            "https://www.honeycomb.io/careers", "Observability TPM.", "curated"),
    JobLead("Senior Product Manager", "Chronosphere", "Bangalore, India", "Chronosphere Careers",
            "https://chronosphere.io/careers/", "Observability PM.", "curated"),
    JobLead("Product Manager - Logs", "Sumo Logic", "Bangalore, India", "Sumo Logic Careers",
            "https://www.sumologic.com/company/careers/", "Log analytics PM.", "curated"),
    JobLead("Senior Program Manager", "Dynatrace", "Bangalore, India", "Dynatrace Careers",
            "https://www.dynatrace.com/company/careers/", "APM program mgmt.", "curated"),
    JobLead("Senior Product Manager", "Mindtickle", "Bangalore, India", "Mindtickle Careers",
            "https://www.mindtickle.com/careers/", "Sales enablement SaaS PM.", "curated"),
    JobLead("Senior Product Manager", "Whatfix", "Bangalore, India", "Whatfix Careers",
            "https://whatfix.com/careers/", "Digital adoption PM.", "curated"),
    JobLead("Senior Product Manager", "Icertis", "Bangalore, India", "Icertis Careers",
            "https://www.icertis.com/company/careers/", "Contract lifecycle SaaS PM.", "curated"),
    JobLead("Technical Program Manager", "Coupa", "Bangalore, India", "Coupa Careers",
            "https://careers.coupa.com/", "Procurement SaaS TPM.", "curated"),
    JobLead("Senior Product Manager", "HighRadius", "Bangalore, India", "HighRadius Careers",
            "https://www.highradius.com/about/careers/", "FinOps SaaS PM.", "curated"),
    JobLead("Senior Program Manager", "Infosys", "Bangalore, India", "Infosys Careers",
            "https://www.infosys.com/careers.html", "Large-scale delivery PM.", "curated"),
    JobLead("Product Manager - Cloud", "HCLTech", "Bangalore, India", "HCL Careers",
            "https://www.hcltech.com/careers", "Cloud / digital PM.", "curated"),
    JobLead("Technical Program Manager", "Tech Mahindra", "Bangalore, India", "TechM Careers",
            "https://careers.techmahindra.com/", "Telecom / enterprise TPM.", "curated"),
    JobLead("Senior Product Manager - RazorpayX", "Razorpay", "Bangalore, India", "Razorpay Careers",
            "https://razorpay.com/jobs/", "Neobanking / payroll PM.", "curated"),
    JobLead("Product Manager - EdTech", "Unacademy", "Bangalore, India", "Unacademy Careers",
            "https://unacademy.com/careers", "EdTech PM.", "curated"),
    JobLead("Senior Product Manager", "Nykaa", "Bangalore, India", "Nykaa Careers",
            "https://www.nykaa.com/careers", "Beauty e-commerce PM.", "curated"),
    JobLead("Product Manager - Wealth", "Zerodha Coin", "Bangalore, India", "Zerodha Careers",
            "https://zerodha.com/careers/", "Mutual funds / wealth PM.", "curated"),
    JobLead("Senior Program Manager", "Deutsche Bank", "Bangalore, India", "Deutsche Bank Careers",
            "https://careers.db.com/", "Banking tech program mgmt.", "curated"),
    JobLead("Senior Product Manager", "Yatra", "Bangalore, India", "Yatra Careers",
            "https://www.yatra.com/careers", "OTA PM.", "curated"),
    JobLead("Product Manager - Diagnostics", "PharmEasy", "Bangalore, India", "PharmEasy Careers",
            "https://pharmeasy.in/careers", "Health-tech PM.", "curated"),
    JobLead("Product Manager - Hotels", "OYO", "Bangalore, India", "OYO Careers",
            "https://www.oyorooms.com/careers", "Hospitality tech PM.", "curated"),
    JobLead("Senior Product Manager", "Rivigo", "Bangalore, India", "Rivigo Careers",
            "https://www.rivigo.com/careers", "Logistics PM.", "curated"),
    JobLead("Technical Program Manager", "L&T Technology", "Bangalore, India", "LTTS Careers",
            "https://www.ltts.com/careers", "Engineering services TPM.", "curated"),
    JobLead("Senior Product Manager", "Siemens", "Bangalore, India", "Siemens Careers",
            "https://jobs.siemens.com/", "Industrial IoT PM.", "curated"),
    JobLead("Senior Program Manager", "Bosch", "Bangalore, India", "Bosch Careers",
            "https://www.bosch.com/careers/", "Automotive program mgmt.", "curated"),
    JobLead("Product Manager - ERP", "Ramco Systems", "Bangalore, India", "Ramco Careers",
            "https://www.ramco.com/careers/", "Enterprise ERP PM.", "curated"),
    JobLead("Senior Program Manager", "TCS", "Bangalore, India", "TCS Careers",
            "https://www.tcs.com/careers", "Large-scale delivery PM.", "curated"),
    JobLead("Product Manager - AI/ML", "Fractal Analytics", "Bangalore, India", "Fractal Careers",
            "https://fractal.ai/careers/", "AI product consulting.", "curated"),
    JobLead("Senior Product Manager", "MapmyIndia", "Bangalore, India", "MapmyIndia Careers",
            "https://www.mapmyindia.com/careers/", "Location / maps platform PM.", "curated"),
    JobLead("Product Manager", "Open Financial", "Bangalore, India", "Open Careers",
            "https://open.money/careers", "SMB fintech PM.", "curated"),
    JobLead("Senior Product Manager", "Open Financial", "Bangalore, India", "Open Careers",
            "https://open.money/careers", "SMB banking PM.", "curated"),
]


def discover_all(*, target: int = 100) -> list[JobLead]:
    seen: set[str] = set()
    results: list[JobLead] = []

    def add_batch(batch: list[JobLead]) -> None:
        for job in batch:
            if not job.title:
                continue
            k = job.key()
            if k in seen:
                continue
            seen.add(k)
            results.append(job)

    print("Fetching live jobs from Greenhouse...", file=sys.stderr)
    for board, label in GREENHOUSE_BOARDS:
        if len(results) >= target:
            break
        batch = fetch_greenhouse(board, label)
        if batch:
            print(f"  {label}: {len(batch)}", file=sys.stderr)
            add_batch(batch)
        time.sleep(0.12)

    print("Fetching live jobs from Lever...", file=sys.stderr)
    for site, label in LEVER_SITES:
        if len(results) >= target:
            break
        batch = fetch_lever(site, label)
        if batch:
            print(f"  {label}: {len(batch)}", file=sys.stderr)
            add_batch(batch)
        time.sleep(0.12)

    print("Fetching live jobs from Ashby...", file=sys.stderr)
    for org, label in ASHBY_ORGS:
        if len(results) >= target:
            break
        batch = fetch_ashby(org, label)
        if batch:
            print(f"  {label}: {len(batch)}", file=sys.stderr)
            add_batch(batch)
        time.sleep(0.12)

    live_count = len(results)
    print(f"Live postings: {live_count}. Filling with curated leads...", file=sys.stderr)
    add_batch(CURATED_JOBS)

    # Prioritize live postings first
    results.sort(key=lambda j: (0 if j.source_type == "live" else 1, j.company_name, j.title))
    return results[:target]


def write_csv(path: str, jobs: list[JobLead]) -> None:
    fields = ["title", "company_name", "location", "platform", "job_url", "snippet", "source_type"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for j in jobs:
            w.writerow({k: getattr(j, k) for k in fields})


def write_markdown(path: str, jobs: list[JobLead], candidate: str) -> None:
    live = sum(1 for j in jobs if j.source_type == "live")
    lines = [
        f"# Bangalore Jobs for {candidate} — Batch 2",
        "",
        f"**Generated:** 2026-08-21  ",
        f"**Total roles:** {len(jobs)}  ",
        f"**Live postings (direct apply links):** {live}  ",
        f"**Curated career-page leads:** {len(jobs) - live}  ",
        "",
        "## Profile fit",
        "",
        "Targeted for **Chitrakshi Mehta** — Program Manager III @ Expedia, ex-Dell PM/SDE, CSPO, ~10 yrs.",
        "Focus: Product Manager, Senior/GPM, Technical Program Manager, Platform/Observability/OMS PM roles in Bengaluru.",
        "",
        "## How to use",
        "",
        "1. Import `chitrakshi_bangalore_jobs_batch2.csv` into Job Search Copilot → Job Discovery → Import & JDs.",
        "2. Start with **live** postings (rows with `source_type=live`) — these have direct apply URLs.",
        "3. For curated rows, open the career page link and search the role title.",
        "",
        "## Top matches (observability / platform / OMS / travel)",
        "",
    ]
    keywords = ("observability", "platform", "order", "travel", "program", "api", "sre", "log", "monitoring", "payment")
    top = [j for j in jobs if any(k in j.title.lower() or k in j.snippet.lower() for k in keywords)][:15]
    for i, j in enumerate(top, 1):
        lines.append(f"{i}. **{j.title}** @ {j.company_name} — [{j.platform}]({j.job_url})")

    lines.extend(["", "## Full list", ""])
    for i, j in enumerate(jobs, 1):
        tag = "🟢" if j.source_type == "live" else "🔵"
        lines.append(f"{i}. {tag} **{j.title}** — {j.company_name} ({j.location})  ")
        lines.append(f"   - [{j.platform}]({j.job_url})")
        if j.snippet:
            lines.append(f"   - {j.snippet[:200]}...")
        lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> int:
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    out_csv = sys.argv[2] if len(sys.argv) > 2 else "bangalore_jobs.csv"
    out_md = sys.argv[3] if len(sys.argv) > 3 else out_csv.replace(".csv", ".md")
    candidate = sys.argv[4] if len(sys.argv) > 4 else "Chitrakshi Mehta"

    jobs = discover_all(target=target)
    write_csv(out_csv, jobs)
    write_markdown(out_md, jobs, candidate)
    live = sum(1 for j in jobs if j.source_type == "live")
    print(json.dumps({"count": len(jobs), "live": live, "curated": len(jobs) - live, "csv": out_csv, "md": out_md}))
    return 0 if len(jobs) >= target else 1


if __name__ == "__main__":
    raise SystemExit(main())
