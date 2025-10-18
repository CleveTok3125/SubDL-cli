#!/usr/bin/python

import argparse
import json
import os
import re
from typing import List, Literal, Tuple, TypedDict
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    os.environ.get("API_KEY")

API = "https://api.subdl.com/api/v1/subtitles"
URL_BASE = "https://subdl.com/"
URL_DL = "https://dl.subdl.com/"


class CardInfo(TypedDict):
    sd_id: str
    name: str
    thumbnail_url: str


class APIResults(TypedDict):
    sd_id: int
    type: Literal["movie", "tv"]
    name: str
    imdb_id: str
    tmdb_id: int
    first_air_date: str
    slug: str
    release_date: str
    year: int


class APISubtitles(TypedDict):
    release_name: str
    name: str
    lang: str
    author: str
    url: str
    subtitlePage: str
    season: int
    episode: int
    language: str
    hi: bool
    episode_from: int
    episode_end: int
    full_season: bool


class APIResponse(TypedDict):
    status: bool
    results: List[APIResults]
    subtitles: List[APISubtitles]
    totalPages: int
    currentPage: int


class SearchEngine:
    def __get_search_content(self, query: str) -> str:
        url = urljoin(URL_BASE, f"search/{query}".rstrip("/") + "/")
        response: requests.Response = requests.get(url)
        html_content: str = response.text
        return html_content

    def __find_card_content(self, html_content: str) -> List[str]:
        card_contents: List[str] = re.findall(
            r"<a\s+href=\"\/subtitle.+?<\/a>", html_content
        )
        return card_contents

    def __find_card_info(self, card_content: List[str]) -> List[Tuple[str]]:
        raw_card_info: List[Tuple[str]] = re.findall(
            r"<a\s+href=\"\/subtitle\/sd(\d+).+?\">.+?title=\"(.+?)\"\s+src=\"(http.+?)\".+?<\/a>",
            card_content,
        )
        return raw_card_info

    def __parse_card_info(self, raw_card_info: List[Tuple[str]]) -> CardInfo:
        raw_card_info = raw_card_info[0]

        parsed_card_info: CardInfo = {
            "sd_id": raw_card_info[0],
            "name": raw_card_info[1],
            "thumbnail_url": raw_card_info[2],
        }
        return parsed_card_info

    def search(self, query: str) -> List[CardInfo]:
        html_content: str = self.__get_search_content(query)
        card_contents: List[str] = self.__find_card_content(html_content)

        search_results: List[CardInfo] = []
        for card_content in card_contents:
            raw_card_info: List[Tuple[str]] = self.__find_card_info(card_content)
            parsed_card_info: CardInfo = self.__parse_card_info(raw_card_info)
            search_results.append(parsed_card_info)

        return search_results


class SubtitleFetcher:
    def __matches(self, sub, filters: dict = None) -> bool:
        for key, pattern in filters.items():
            value = str(sub.get(key, ""))
            if not re.fullmatch(f"^{pattern}$", value):
                return False
        return True

    def get_subtitle_info(
        self,
        sd_id: str,
        languages: str = None,
        full_url: bool = False,
        filters: dict = None,
    ) -> APIResponse:
        params: dict = {
            "api_key": API_KEY,
            "sd_id": sd_id,
        }

        if languages:
            params.update(languages=languages)

        headers: dict = {"Accept": "application/json"}

        response: requests.Response = requests.get(API, params=params, headers=headers)
        data: APIResponse = response.json()

        if not data["status"]:
            print(data["error"])
            return

        if filters:
            data["subtitles"] = [
                s for s in data["subtitles"] if self.__matches(s, filters)
            ]

        if full_url:
            for subtitle in data["subtitles"]:
                subtitle["url"] = urljoin(URL_DL, subtitle["url"])
                subtitle["subtitlePage"] = urljoin(URL_BASE, subtitle["subtitlePage"])

        return data


class Display:
    def search_menu(self, search_results: List[CardInfo]):
        if not search_results:
            print("No results found.")
            return

        max_len: int = max(len(item["sd_id"]) for item in search_results)

        print(f"{'SD_ID':>{max_len}} Name")
        print(f"{'-'*max_len} {'-'*max_len}")

        for item in search_results:
            print(f"{item['sd_id']:>{max_len}} {item['name']}")

    def get_menu(
        self,
        get_result: APIResponse,
        *,
        compact: bool = False,
        subtitle_only: bool = False,
        needed_fields: set = None,
        needed_results_fields: set = None,
        needed_subtitles_fields: set = None,
    ):
        print_result = get_result

        if compact:
            needed_fields = (
                {"results", "subtitles"} if not needed_fields else needed_fields
            )
            needed_results_fields = (
                {"sd_id", "type", "name"}
                if not needed_results_fields
                else needed_results_fields
            )
            needed_subtitles_fields = (
                {
                    "release_name",
                    "lang",
                    "url",
                    "episode_from",
                    "episode_end",
                }
                if not needed_subtitles_fields
                else needed_subtitles_fields
            )

            print_result = {k: v for k, v in print_result.items() if k in needed_fields}
            print_result["results"] = [
                {k: v for k, v in f.items() if k in needed_results_fields}
                for f in print_result["results"]
            ]
            print_result["subtitles"] = [
                {k: v for k, v in f.items() if k in needed_subtitles_fields}
                for f in print_result["subtitles"]
            ]

        if subtitle_only:
            print_result = print_result["subtitles"]

        print(json.dumps(print_result, indent=4, ensure_ascii=False))


class ArgsHandler:
    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.subparsers = self.parser.add_subparsers(dest="command")

        self.search_parser = self.subparsers.add_parser("search")
        self.search_parser.add_argument("query", type=str)

        self.get_subtitle_parser = self.subparsers.add_parser("fetch")
        self.get_subtitle_parser.add_argument("sd_id", type=str)
        self.get_subtitle_parser.add_argument(
            "--language", type=str, default=None, required=False
        )
        self.get_subtitle_parser.add_argument(
            "--full-url", action="store_true", default=False, required=False
        )
        self.get_subtitle_parser.add_argument(
            "--filter",
            action="append",
            required=False,
            help='Filter results for subtitles containing a key (exact match) and a value (regex match). Eg: "--filter release_name=Inception.+" will filter for subtitles whose release_name value starts with "Inception"',
        )
        self.get_subtitle_parser.add_argument(
            "--compact", action="store_true", default=False, required=False
        )
        self.get_subtitle_parser.add_argument(
            "--subtitle-only", action="store_true", default=False, required=False
        )
        self.get_subtitle_parser.add_argument(
            "--data-struct",
            nargs="+",
            type=self.__parse_list,
            required=False,
            help='Works with --compact, only shows listed fields. Eg: "--data-struct fields=results,subtitles results=sd_id,name subtitles=name,lang,url"',
        )

        self.args = self.parser.parse_args()

    def __parse_list(self, s):
        key, val = s.split("=")
        val_list = [x.strip() for x in val.split(",")]
        return key, set(val_list)

    def listener(self):
        match self.args.command:
            case "search":
                search_results: List[CardInfo] = SearchEngine().search(self.args.query)
                Display().search_menu(search_results)
            case "fetch":
                if not API_KEY:
                    print(
                        "Action requires an API KEY, get it at https://subdl.com/panel/api"
                    )
                    return

                filters = {}
                if self.args.filter:
                    for f in self.args.filter:
                        key, value = f.split("=", 1)
                        filters[key] = value

                result = SubtitleFetcher().get_subtitle_info(
                    self.args.sd_id,
                    languages=self.args.language,
                    full_url=self.args.full_url,
                    filters=filters,
                )

                if not result:
                    return

                data_struct: dict = {}
                if self.args.data_struct:
                    data_struct = dict(self.args.data_struct)

                Display().get_menu(
                    result,
                    compact=self.args.compact,
                    subtitle_only=self.args.subtitle_only,
                    needed_fields=data_struct.get("fields"),
                    needed_results_fields=data_struct.get("results"),
                    needed_subtitles_fields=data_struct.get("subtitles"),
                )
            case _:
                self.parser.print_help()


if __name__ == "__main__":
    ArgsHandler().listener()
