import urllib3.contrib.pyopenssl
urllib3.contrib.pyopenssl.inject_into_urllib3()
import random
import json
import tinycss2
from datetime import datetime
from time import mktime
from locust import HttpLocust, TaskSet, task
from pyquery import PyQuery
import os, io
from configparser import RawConfigParser

PWD = os.path.dirname(os.path.realpath(__file__))

with open(PWD + '/../etc/locust.cfg', 'r') as f:
    sample_config = f.read()
config = RawConfigParser(allow_no_value=True)
config.read_file(io.BytesIO(sample_config))

section = os.path.basename(__file__)
PARAMS = {}

for option in config.options(section):
    PARAMS[option] = config.get(section, option)

AUCTIONS_NUMBER = int(PARAMS['auctions_number'])


class AuctionTest(TaskSet):
    auction_id = ""
    auction_src = None
    last_change = 0
    csses = []

    def index(self):
        today = mktime(datetime.now().date().timetuple()) * 1000
        resp = self.client.get("/")
        if resp.status_code == 200:
            pq = PyQuery(resp.content)
            links = pq('.list-group-item a')
            if links:
                resp = self.client.get(
                    "/database/_design/auctions/_view/by_endDate?"
                    "include_docs=true&startkey={0}".format(int(today)))
                rows = resp.json().get('rows', [])
                if rows:
                    self.auction_id = random.choice(rows).get('id')

    def auction_event_source(self):
        path = '/insider-auctions/{}/event_source?_nonce={}'.format(
            self.auction_id, random.random())
        self.client.get(path, name="event_source")

    def auction(self):
        resp = self.client.get(
            '/insider-auctions/{}'.format(self.auction_id),
            name="GET auction page")
        if resp.status_code == 200:
            self.auction_src = resp.content

    @task(1)
    def reload_last_auction(self):
        self.index()
        if self.auction_id:
            self.auction()
            self.css()
            self.js()
            self.auctions()
            self.auctions_db()
            self.time()
            self.changes()
            self.time()
            for i in range(random.randint(1, 5)):
                self.changes()

    def css(self):
        pq = PyQuery(self.auction_src)

        for style in pq('link[rel="stylesheet"]'):
            href = style.get('href')
            if href and href.startswith('/') and not href.startswith('//'):
                resp = self.client.get(href)
                if resp.status_code == 200:
                    css = resp.content
                    self.csses.append(
                        tinycss2.parse_stylesheet_bytes(css,
                                                        skip_comments=True))

    def js(self):
        pq = PyQuery(self.auction_src)

        for script in pq('script'):
            src = script.get('src')
            if src and src.startswith('/') and not src.startswith('//'):
                self.client.get(src)

    def time(self):
        self.client.get(
            '/get_current_server_time?_nonce={}'.format(
                random.random()), name="get_current_server_time")

    def auctions_db(self):
        self.client.get('/database?_nonce={}'.format(random.random()),
                        name="Get db info")

    def auctions(self):
        self.client.get('/database/{}?_nonce={}'.format(self.auction_id,
                                                        random.random()),
                        name="Get document from couch")

    def changes(self):
        params = {
            'timeout': 25000,
            'style': 'main_only',
            'heartbeat': 10000,
            'include_docs': 'true',
            'feed': 'longpoll',
            'filter': '_doc_ids',
            'since': self.last_change,
            'limit': 25,
            '_nonce': random.random(),
            'doc_ids': '["{}"]'.format(self.auction_id)
        }
        if self.last_change == 0:
            name = "Get first change from couch"
        else:
            name = "Get change from couch (longpoll)"

        resp = self.client.get('/database/_changes', params=params, name=name)
        if resp.status_code == 200:
            self.last_change = json.loads(resp.content)['last_seq']


class AuctionAnonymous(HttpLocust):
    host = PARAMS['host']
    min_wait = 0
    max_wait = 0
    task_set = AuctionTest
