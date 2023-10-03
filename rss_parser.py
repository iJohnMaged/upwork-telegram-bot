import feedparser
import re
import html
import pytz
import timeago

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from storage import JobPostDB

jobs_db = JobPostDB()


@dataclass
class JobPost:
    url: str
    budget: str
    published: str
    title: str
    summary: str
    skills: List[str]
    budget_numeric: int
    country: str
    hourly: bool

    def to_str(self, show_summary):
        job_type = "Hourly" if self.hourly else "Fixed-price"
        if show_summary:
            return (
                f"<b>{self.title}</b>\n\n"
                f"{self.summary}\n\n"
                f"{self.url}\n\n"
                f"Budget: {self.budget}\n"
                f"Type: {job_type}\n"
                f"Published: {str(self.published)}\n"
                f"Country: {self.country}\n\n"
                f"<b>Keyword:</b>\n{', '.join(self.skills)}"
            )
        else:
            return (
                f"<b>{self.title}</b>\n\n"
                f"{self.url}\n\n"
                f"Budget: {self.budget}\n"
                f"Type: {job_type}\n"
                f"Published: {str(self.published)}\n"
                f"Country: {self.country}\n\n"
                f"<b>Keyword:</b>\n{', '.join(self.skills)}"
            )


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
            budget = re.search(r"<b>Hourly Range</b>:([^\n]+)", summary).group(1)
            budget = budget.strip()
            budget_no_dollar = budget.replace("$", "")
            return budget, float(budget_no_dollar.split("-")[0]), True
        try:
            budget = "$" + re.search(r"<b>Budget</b>: \$(\d[0-9,.]+)", summary).group(1)
            budget = re.sub("<[^<]+?>", "", budget)
        except AttributeError:
            budget = "N/A"
        try:
            return budget, int(budget[:-1]), False
        except:
            return budget, None, (budget == "N/A")

    def _parse_country(self, summary):
        try:
            return re.search(r"<b>Country</b>:([^\n]+)", summary).group(1)
        except:
            return "N/A"

    def _parse_skills(self, summary):
        try:
            return [
                item.strip()
                for item in (
                    re.search(r"<b>Skills</b>:([^\n]+)", summary).group(1).split(",")
                )
            ]
        except:
            return ["N/A"]

    def _clean_summary(self, summary):
        pattern = re.compile(r"<.*?>")
        return html.unescape(pattern.sub("", summary))

    def _parse_summary(self, summary):
        try:
            sep = re.search(r"(.*(<br\s*/>){2})<b>", summary).group(1)
            return self._clean_summary("".join([summary.split(sep)[0], sep]))
        except:
            return None

    def _parse_published(self, published_str):
        # Format Example: Sat, 24 Oct 2020 03:06:03 +0000
        user_timezone = self.user_settings.get("timezone", "UTC")
        published = (
            datetime.strptime(published_str, "%a, %d %b %Y %H:%M:%S %z")
            .replace(tzinfo=pytz.utc)
            .astimezone(pytz.timezone(user_timezone))
        )
        timenow = (
            datetime.utcnow()
            .replace(tzinfo=pytz.utc)
            .astimezone(pytz.timezone(user_timezone))
        )
        return timeago.format(published, timenow)

    def _filter_job(self, job: JobPost):
        excluded_countries = self.user_filters.get("exclude_countries", None)

        if excluded_countries is not None:
            for country in excluded_countries:
                if job.country.strip().lower() == country.lower():
                    return False

        return True

    def parse_rss(self):
        entries = self._load_rss().entries
        job_posts = []
        for entry in entries:
            if jobs_db.job_exits(entry["id"], self.user_id):
                continue
            budget, budget_numeric, hourly = self._parse_budget(entry["summary"])
            country = self._parse_country(entry["summary"])
            published = self._parse_published(entry["published"])
            job_post = JobPost(
                entry.get("id", "#"),
                budget,
                published,
                entry.get("title"),
                self._parse_summary(entry.get("summary")),
                self._parse_skills(entry.get("summary")),
                budget_numeric,
                country,
                hourly,
            )
            if self._filter_job(job_post):
                job_posts.append(job_post)
            jobs_db.insert_job(entry["id"], self.user_id)
        return job_posts
