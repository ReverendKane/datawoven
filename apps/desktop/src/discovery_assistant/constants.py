import os
from pathlib import Path

BASE_PATH = Path(__file__).parents[1].resolve()
TOOL_BASE_PATH = BASE_PATH.joinpath('discovery_assistant')
TABS_PATH = TOOL_BASE_PATH.joinpath('ui/tabs')
ICON_PATH = TOOL_BASE_PATH / 'assets/images/datawoven_icon.png'
LOGO_PATH = TOOL_BASE_PATH / 'assets/images/datawoven_headerLogo.png'

# Fonts
FONT_DIR = TOOL_BASE_PATH / "assets/fonts"
FONT_MONTSERRAT_SEMIBOLD = FONT_DIR / "Montserrat-SemiBold.ttf"
FONT_MONTSERRAT_REGULAR = FONT_DIR / "Montserrat-Regular.ttf"
FONT_ROBOTO_REGULAR = FONT_DIR / "Roboto-SemiBold.ttf"

# Logging
LOG_LEVEL = 20
FILE_LOG_LEVEL = 40
FRMT_LOG_LONG = "[%(name)s][%(levelname)s] >> %(message)s (%(asctime)s; %(filename)s:%(lineno)d)"

# Form Sections
SECTIONS = {
    "Instructions": "instructions_tab.py",
    "Respondent": "respondent_tab.py",
    "Org Map": "org_tab.py",
    "Processes": "processes_tab.py",
    "Pain Points": "painpoints_tab.py",
    "Data Sources": "datasources_tab.py",
    "Compliance": "compliance_tab.py",
    "Feature Ideas": "featureideas_tab.py",
    "Reference Library": "reference_library_tab.py",
    "Time && Resource Management": "time_resource_management_tab.py",
    "Review": "review_tab.py",
}

