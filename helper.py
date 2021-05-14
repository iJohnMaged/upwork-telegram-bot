import pytz
from datetime import datetime, timedelta

ALLOWED_SETTINGS = {
    "timezone": {
        "values": [tz.lower() for tz in pytz.all_timezones],
        "type": str,
        "error": "Allowed timezone values are listed here: https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568"
    },
    "show_summary": {
        "values": ["yes", "no"],
        "type": str,
        "error": "Allowed show_summary values are yes/no."
    }
}

ALLOWED_FILTERS = [
    "exclude_countries",
]

ITERABLE_FILTERS = [
    "exclude_countries",
]

REPEAT_PERIOD = 5  # minutes

HELP_TEXT = f"""
Hey! Get your Upwork feed delivered while focusing on work/learning!

Commands available:

- RSS Feeds:
<b>/add_rss</b> &lt;rss url&gt; &lt;rss name&gt;: adds a new RSS feed
<b>/delete_rss</b> &lt;rss name&gt;: Deletes RSS given a name
<b>/list_rss</b>: Lists your current saved RSS feeds

- Settings:
<b>/set</b> &lt;key&gt; &lt;value&gt;: Set settings to value
<b>/settings</b>: Displays your current settings

- Filters
Available filters:
exclude_countries
for <b>exclude_countries</b> input is comma separated for multiple inputs

<b>/add_filter</b> &lt;filter&gt; &lt;value&gt;: sets filter's value
<b>/clear_filter</b> &lt;filter&gt; clears filter's value
<b>/filters</b>: Displays your current filter settings

- Notifications
<b>/pause</b>: Pauses sending notifications
<b>/resume</b>: Resumes sending notifications

Notifications are sent out every {REPEAT_PERIOD} minutes!
New features will be out soon!

<b>PS</b> You can support me at: https://www.buymeacoffee.com/iJohnMaged :)
"""

INITIAL_TUTORIAL = f"""
Hello! Thanks for using my bot.. this bot allows you to get your Upwork RSS feed delivered to you!

Here's a quick tutorial on how to use the bot:

- First things first, I suggest modifying the settings
<b>/set</b> timezone &lt;your timezone&gt; ex: /set timezone Egypt
<b>/set</b> show_summary &lt;yes/no&gt; ex: /set show_summary yes -- This setting shows/hides job posts summary

- Add your RSS feeds:
<b>/add_rss</b> &lt;rss url&gt; &lt;rss name&gt; ex: /add_rss https://url.com my_feed

You can add multiple RSS feeds, once done, you'll be receiving notifications ever {REPEAT_PERIOD} minutes!

Use <b>/help</b> for more info!
New features will be out soon!

<b>PS</b> You can support me at: https://www.buymeacoffee.com/iJohnMaged :)
"""


def round_time(dt=None, delta=timedelta(minutes=REPEAT_PERIOD)):
    if dt is None:
        dt = datetime.now()
    return dt + (datetime.min - dt) % delta
