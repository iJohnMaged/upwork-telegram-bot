from pyairtable import Api
from rss_parser import JobPost
from typing import List


class AirTable:
    def __init__(
        self,
        app_id: str,
        table_id: str,
        table_country_id: str,
        table_skill_id: str,
        token: str,
    ):
        self.api = Api(token)
        self.app_id = app_id
        self.table = self.get_table(table_id)
        self.tbl_country = self.get_table(table_country_id)
        self.tbl_skill = self.get_table(table_skill_id)

    def item_insert(self, jobpost: JobPost):
        jobpost = jobpost.to_dict()
        data = {
            "Title": jobpost.get("title"),
            "Text": jobpost.get("summary"),
            "Keyword": self.get_skill_id(jobpost.get("skills")),
            "Country": self.get_country_id(jobpost.get("country")),
            "Type": "Hourly" if jobpost.get("hourly") else "Fixed-price",
            "Start": jobpost.get("budget_min"),
            "Until": jobpost.get("budget_max"),
            "Published": jobpost.get("published_date"),
            "Link": jobpost.get("url"),
        }
        return self.table.create(data)

    def item_add(self, data: dict):
        for item in data.copy().keys():
            if item == "Country":
                data[item] = self.get_country_id(data[item])
            if item == "Keyword":
                data[item] = self.get_skill_id(data[item])
        return self.table.create(data)

    def item_update(self, item_id: str, data: dict):
        return self.table.update(item_id, data)

    def item_get(self, item_id: str = None):
        if item_id is not None:
            return self.table.get(item_id)
        else:
            return self.table.all()

    def item_delete(self, item_id: str):
        return self.table.delete(item_id)

    def get_table(self, table_id: str):
        return self.api.table(self.app_id, table_id)

    def get_country_id(self, country: str):
        country = country.strip()
        countries = self.tbl_country.all()
        if country in (item["fields"]["Name"] for item in countries):
            return [
                item["id"] for item in countries if country == item["fields"]["Name"]
            ]
        else:
            new_country = self.tbl_country.create({"Name": country})
            if new_country:
                return [new_country["id"]]

    def get_skill_id(self, keys: List):
        skills = self.tbl_skill.all()
        data = list()
        for key in keys:
            if key in (item["fields"]["Name"] for item in skills):
                data.extend(
                    [item["id"] for item in skills if key == item["fields"]["Name"]]
                )
            else:
                new_skill = self.tbl_skill.create({"Name": key})
                if new_skill:
                    data.append(new_skill["id"])
        if len(data) == len(keys):
            return data
