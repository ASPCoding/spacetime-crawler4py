from threading import Thread

from inspect import getsource
from utils.download import download
from utils import get_logger
from urllib.parse import urlparse
import scraper
import time


class Worker(Thread):
    def __init__(self, worker_id, config, frontier):
        self.logger = get_logger(f"Worker-{worker_id}", "Worker")
        self.config = config
        self.frontier = frontier
        # basic check for requests in scraper
        assert {getsource(scraper).find(req) for req in {"from requests import", "import requests"}} == {-1}, "Do not use requests in scraper.py"
        assert {getsource(scraper).find(req) for req in {"from urllib.request import", "import urllib.request"}} == {-1}, "Do not use urllib.request in scraper.py"
        super().__init__(daemon=True)

    def add_rule(self, url) -> None:
        try:
            parsed = urlparse(url)
        except:
            return
        with open("./Rules/" + parsed.hostname + "_robots.txt", "x") as file:
            resp = download(parsed.scheme + "://" + parsed.hostname + "/robots.txt", self.config, self.logger)
            # if Response object wrapper returns None or not 200, write nothing since there is no content
            if not resp.raw_response or resp.status != 200:
                return
            for line in resp.raw_response.content.decode("utf-8").splitlines(True):
                file.write(line)

    def follow_rules_of(self, url, file) -> bool:
        disallow = set()
        allow = set()
        for line in file:
            if line == "User-agent: *\n":
                while True:
                    new_line = file.readline()
                    if new_line == "\n" or new_line == "":
                        break
                    if new_line[-1] == "\n":
                        new_line = new_line[:-1]
                    if new_line[0] == "D":
                        disallow.add(new_line[10:])
                    if new_line[0] == "A":
                        allow.add(new_line[7:]) 
                break
        parsed = urlparse(url)
        for disallowed in disallow:
            if len(disallowed) <= len(parsed.path) and disallowed == parsed.path[:len(disallowed)]:
                if parsed.path in allow:
                    return True
                else:
                    return False
        return True
            
    
    def is_valid(self, url) -> bool:
        while True:
            try:
                with open("./Rules/" + urlparse(url).hostname + "_robots.txt") as file:
                    return self.follow_rules_of(url, file)
            except FileNotFoundError:
                self.add_rule(url)
        
    def run(self):
        while True:
            tbd_url = self.frontier.get_tbd_url()
            if not tbd_url:
                self.logger.info("Frontier is empty. Stopping Crawler.")
                break
            if not self.is_valid(tbd_url):
                self.frontier.mark_url_complete(tbd_url)
                time.sleep(self.config.time_delay)
                continue
            resp = download(tbd_url, self.config, self.logger)
            self.logger.info(
                f"Downloaded {tbd_url}, status <{resp.status}>, "
                f"using cache {self.config.cache_server}.")
            scraped_urls = scraper.scraper(tbd_url, resp)
            for scraped_url in scraped_urls:
                self.frontier.add_url(scraped_url)
            self.frontier.mark_url_complete(tbd_url)
            time.sleep(self.config.time_delay)
