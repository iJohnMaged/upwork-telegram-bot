import pytz
from datetime import datetime, timedelta

ALLOWED_SETTINGS = {
    "timezone": {
        "values": [tz.lower() for tz in pytz.all_timezones],
        "type": str
    },
    "show_summary": {
        "values": ["yes", "no"],
        "type": str
    }
}

ALLOWED_FILTERS = [
    "exclude_countries",
    "minimum_budget",
    "keywords",
]

ITERABLE_FILTERS = [
    "exclude_countries",
    "keywords"
]

REPEAT_PERIOD = 5  # minutes

HELP_TEXT = f"""
Hey! Get your Upwork feed delivered and customized to your needs while focusing on work/learning!

Commands available:

- RSS Feeds:
*/add_rss* <rss_url> <rss_name>: adds a new RSS feed
*/list_rss*: Lists your current saved RSS feeds

- Settings:
*/set* <key> <value>: Set settings to value (Currently only timezone!)
*/settings*: Displays your current settings

- Filters
Available filters:
exclude_countries, minimum_budget, keywords
for *exclude_countries* and *keywords* input is comma separated for multiple inputs

*/add_filter* <filter> <value>: sets filter's value
*/filters*: Displays your current filter settings

Notifications are sent out every {REPEAT_PERIOD} minutes!
New features like removing RSS feed/settings will be out soon!

*PS* Buy me coffee at: https://www.buymeacoffee.com/iJohnMaged :)
"""


def round_time(dt=None, delta=timedelta(minutes=REPEAT_PERIOD)):
    if dt is None:
        dt = datetime.now()
    return dt + (datetime.min - dt) % delta
