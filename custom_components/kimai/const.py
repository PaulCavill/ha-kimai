"""Constants for the Kimai integration."""
from datetime import timedelta

DOMAIN = "kimai"

CONF_BASE_URL = "base_url"
CONF_API_TOKEN = "api_token"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=30)

SERVICE_ADD_TIMESHEET = "add_timesheet"

ATTR_PROJECT_ID = "project_id"
ATTR_ACTIVITY_ID = "activity_id"
ATTR_DATE = "date"
ATTR_START_TIME = "start_time"
ATTR_DURATION_MINUTES = "duration_minutes"
ATTR_END_TIME = "end_time"
ATTR_DESCRIPTION = "description"
ATTR_BILLABLE = "billable"

API_PATH_USERS_ME = "/api/users/me"
API_PATH_PROJECTS = "/api/projects"
API_PATH_ACTIVITIES = "/api/activities"
API_PATH_TIMESHEETS = "/api/timesheets"
API_PATH_TIMESHEETS_ACTIVE = "/api/timesheets/active"

TIMESHEET_PAGE_SIZE = 500
