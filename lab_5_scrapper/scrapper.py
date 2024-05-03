"""
Crawler implementation.
"""
# pylint: disable=too-many-arguments, too-many-instance-attributes, unused-import, undefined-variable
import datetime
import json
import pathlib
import random
import re
import time
from typing import Pattern, Union

import requests
from bs4 import BeautifulSoup

from core_utils import constants
from core_utils.article.article import Article
from core_utils.article.io import to_meta, to_raw
from core_utils.config_dto import ConfigDTO



class IncorrectSeedURLError(Exception):
    """
    The seed url is not alike the pattern.
    """

    class NumberOfArticlesOutOfRangeError(Exception):
        """
        The number of articles is not in range of 1 to 150.
        """

    class IncorrectNumberOfArticlesError(Exception):
        """
        The article number is not integer.
        """

    class IncorrectHeadersError(Exception):
        """
        The headers are not stored in a dictionary.
        """

    class IncorrectEncodingError(Exception):
        """
        The encoding is not a string.
        """

        class IncorrectTimeoutError(Exception):
            """
            The timeout is not an integer or is not in the range.
            """

        class IncorrectVerifyError(Exception):
            """
            Verification check or Headless mode are not boolean.
            """


class Config:
    """
    Class for unpacking and validating configurations.
    """

    def __init__(self, path_to_config: pathlib.Path) -> None:
        """
        Initialize an instance of the Config class.

        Args:
            path_to_config (pathlib.Path): Path to configuration.
        """
        self.path_to_config = path_to_config
        self._validate_config_content()
        self.config = self._extract_config_content()
        self._seed_urls = self.config.seed_urls
        self._num_articles = self.config.total_articles
        self._headers = self.config.headers
        self._encoding = self.config.encoding
        self._timeout = self.config.timeout
        self._should_verify_certificate = self.config.should_verify_certificate
        self._headless_mode = self.config.headless_mode

    def _extract_config_content(self) -> ConfigDTO:
        """
        Get config values.

        Returns:
            ConfigDTO: Config values
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as file:
            config = json.load(file)
        return ConfigDTO(
            seed_urls=config["seed_urls"],
            total_articles_to_find_and_parse=config["total_articles_to_find_and_parse"],
            headers=config["headers"],
            encoding=config["encoding"],
            timeout=config["timeout"],
            should_verify_certificate=config["should_verify_certificate"],
            headless_mode=config["headless_mode"]
        )

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters are not corrupt.
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as file:
            config_data = json.load(file)

        if not (isinstance(config_data['seed_urls'], list)):
            raise IncorrectSeedURLError

        for url in config_data['seed_urls']:
            if not re.match("https?://(www.)?", url):
                raise IncorrectSeedURLError

        number = config_data["total_articles_to_find_and_parse"]
        if not isinstance(number, int) or number <= 0:
            raise IncorrectNumberOfArticlesError

        if not 0 < number < 150:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(config_data['headers'], dict):
            raise IncorrectHeadersError

        if not isinstance(config_data['encoding'], str):
            raise IncorrectEncodingError

        timeout = config_data['timeout']
        if not (isinstance(timeout, int) and (0 < timeout < 60)):
            raise IncorrectTimeoutError

        if not isinstance(config_data['should_verify_certificate'], bool) \
                or not isinstance(config_data['headless_mode'], bool):
            raise IncorrectVerifyError


    def get_seed_urls(self) -> list[str]:
        """
        Retrieve seed urls.

        Returns:
            list[str]: Seed urls
        """
        return self._seed_urls

    def get_num_articles(self) -> int:
        """
        Retrieve total number of articles to scrape.

        Returns:
            int: Total number of articles to scrape
        """
        return self._num_articles

    def get_headers(self) -> dict[str, str]:
        """
        Retrieve headers to use during requesting.

        Returns:
            dict[str, str]: Headers
        """
        return self._headers

    def get_encoding(self) -> str:
        """
        Retrieve encoding to use during parsing.

        Returns:
            str: Encoding
        """
        return self._encoding

    def get_timeout(self) -> int:
        """
        Retrieve number of seconds to wait for response.

        Returns:
            int: Number of seconds to wait for response
        """
        return self._timeout

    def get_verify_certificate(self) -> bool:
        """
        Retrieve whether to verify certificate.

        Returns:
            bool: Whether to verify certificate or not
        """
        return self._should_verify_certificate

    def get_headless_mode(self) -> bool:
        """
        Retrieve whether to use headless mode.

        Returns:
            bool: Whether to use headless mode or not
        """
        return self._headless_mode


def make_request(url: str, config: Config) -> requests.models.Response:
    """
    Deliver a response from a request with given configuration.

    Args:
        url (str): Site url
        config (Config): Configuration

    Returns:
        requests.models.Response: A response from a request
    """
    period = random.randrange(2)
    time.sleep(period)
    response = requests.get(url=url,
                            timeout=config.get_timeout(),
                            headers=config.get_headers(),
                            verify=config.get_verify_certificate()
                            )
    return response



class Crawler:
    """
    Crawler implementation.
    """

    url_pattern: Union[Pattern, str]

    def __init__(self, config: Config) -> None:
        """
        Initialize an instance of the Crawler class.

        Args:
            config (Config): Configuration
        """
        self.config = config
        self.urls = []
        self.url_pattern = self.config.get_seed_urls()[0].split('/mag')[0]

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Find and retrieve url from HTML.

        Args:
            article_bs (bs4.BeautifulSoup): BeautifulSoup instance

        Returns:
            str: Url from HTML
        """
        links = article_bs.find_all(class_="post-item__title")
        for link in links:
            url = self.url_pattern + str(link.find('a').get('href'))
            if url not in self.urls:
                break
        else:
            url = ''
        return url

    def find_articles(self) -> None:
        """
        Find articles.
        """
        seed_urls = self.get_search_urls()
        for seed_url in seed_urls:
            response = make_request(seed_url, self.config)
            if not response.ok:
                continue
            soup = BeautifulSoup(response.text, 'lxml')
            extracted_url = self._extract_url(soup)
            while extracted_url:
                if len(self.urls) == self.config.get_num_articles():
                    break
                self.urls.append(extracted_url)
                extracted_url = self._extract_url(soup)
                if len(self.urls) == self.config.get_num_articles():
                    break

    def get_search_urls(self) -> list:
        """
        Get seed_urls param.

        Returns:
            list: seed_urls param
        """


# 10
# 4, 6, 8, 10


class HTMLParser:
    """
    HTMLParser implementation.
    """

    def __init__(self, full_url: str, article_id: int, config: Config) -> None:
        """
        Initialize an instance of the HTMLParser class.

        Args:
            full_url (str): Site url
            article_id (int): Article id
            config (Config): Configuration
        """

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Find text of article.

        Args:
            article_soup (bs4.BeautifulSoup): BeautifulSoup instance
        """

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Find meta information of article.

        Args:
            article_soup (bs4.BeautifulSoup): BeautifulSoup instance
        """

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unify date format.

        Args:
            date_str (str): Date in text format

        Returns:
            datetime.datetime: Datetime object
        """

    def parse(self) -> Union[Article, bool, list]:
        """
        Parse each article.

        Returns:
            Union[Article, bool, list]: Article instance
        """


def prepare_environment(base_path: Union[pathlib.Path, str]) -> None:
    """
    Create ASSETS_PATH folder if no created and remove existing folder.

    Args:
        base_path (Union[pathlib.Path, str]): Path where articles stores
    """


def main() -> None:
    """
    Entrypoint for scrapper module.
    """


if __name__ == "__main__":
    main()
