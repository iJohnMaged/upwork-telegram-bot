import feedparser
import re
import pytz
import timeago

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict

from storage import JobPostDB

jobs_db = JobPostDB()


@dataclass
class JobPost:
    url: str
    budget: str
    published: str
    title: str
    summary: str
    budget_numeric: int
    country: str
    hourly: bool

    def __str__(self) -> str:
        job_type = "Hourly" if self.hourly else "Fixed-price"
        return f"Title: {self.title}\nURL: {self.url}\nBudget: {self.budget}\Type: {job_type}\nPublished: {str(self.published)}\nCountry: {self.country}"


class RSSParser:
    def __init__(self, url: str, user_obj: Dict[str, Any]) -> None:
        self.url = url
        self.user_settings = user_obj["settings"]
        self.user_filters = user_obj["filters"]
        self.user_id = user_obj["id"]

    def _load_rss(self):
        return feedparser.parse(self.url)

    def _parse_budget(self, summary):
        if "Hourly Range" in summary:
            budget = re.search(
                r'<b>Hourly Range</b>:([^\n]+)', summary).group(1)
            budget = budget.strip()
            budget_no_dollar = budget.replace('$', '')
            return budget, float(budget_no_dollar.split("-")[0]), True
        try:
            budget = '$' + re.search(
                r'<b>Budget</b>: \$(\d[0-9,.]+)',
                summary
            ).group(1)
            budget = re.sub('<[^<]+?>', '', budget)
        except AttributeError:
            budget = 'N/A'
        try:
            return budget, int(budget[:-1]), False
        except:
            return budget, None, (budget == "N/A")

    def _parse_country(self, summary):
        try:
            return re.search(
                r'<b>Country</b>:([^\n]+)', summary).group(1)
        except:
            return 'N/A'

    def _parse_published(self, published_str):
        # Format Example: Sat, 24 Oct 2020 03:06:03 +0000
        user_timezone = self.user_settings.get("timezone", "UTC")
        published = datetime.strptime(
            published_str, '%a, %d %b %Y %H:%M:%S %z'
        ).replace(tzinfo=pytz.utc).astimezone(pytz.timezone(user_timezone))
        timenow = datetime.utcnow().replace(
            tzinfo=pytz.utc).astimezone(pytz.timezone(user_timezone))
        return timeago.format(published, timenow)

    def _filter_job(self, job: JobPost):
        excluded_countries = self.user_filters.get("exclude_countries", None)
        minimum_budget = self.user_filters.get("minimum_budget", None)
        keywords = self.user_filters.get("keywords", None)

        if excluded_countries is not None:
            for country in excluded_countries:
                if job.country.strip().lower() == country.lower():
                    return False
        if job.budget != "N/A" and minimum_budget is not None:
            try:
                minimum_budget = int(minimum_budget)
                if job.budget_numeric < minimum_budget:
                    return False
            except:
                pass
        if keywords is not None:
            title = job.title.lower()
            def cb(x): return x.lower() in title
            if not any([cb(keyword) for keyword in keywords]):
                return False

        return True

    def parse_rss(self):
        entries = self._load_rss().entries
        job_posts = []
        for entry in entries:
            if jobs_db.job_exits(entry['id'], self.user_id):
                continue
            budget, budget_numeric, hourly = self._parse_budget(
                entry['summary'])
            country = self._parse_country(entry['summary'])
            published = self._parse_published(entry['published'])
            job_post = JobPost(
                entry.get("id", "#"),
                budget,
                published,
                entry.get("title"),
                entry.get("summary"),
                budget_numeric,
                country,
                hourly=hourly
            )
            if self._filter_job(job_post):
                job_posts.append(job_post)
            jobs_db.insert_job(entry["id"], self.user_id)
        return job_posts
