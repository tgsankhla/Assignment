"""Test script to verify JIRA configuration."""
import os
from jira import JIRA
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

jira = JIRA(
    server=os.getenv("JIRA_INSTANCE_URL"),
    basic_auth=(os.getenv("JIRA_USER_EMAIL"), os.getenv("JIRA_API_TOKEN"))
)

issue_dict = {
    'project': {'key': os.getenv("JIRA_PROJECT_KEY")},
    'summary': 'Test issue via Python SDK',
    'description': 'Created using jira-python library',
    'issuetype': {'name': 'Task'},
}

new_issue = jira.create_issue(fields=issue_dict)
print("Created issue:", new_issue.key)
print("Issue URL:", f"{os.getenv('JIRA_INSTANCE_URL')}/browse/{new_issue.key}")
