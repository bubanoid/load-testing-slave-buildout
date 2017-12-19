import urllib3.contrib.pyopenssl
urllib3.contrib.pyopenssl.inject_into_urllib3()
from locust import HttpLocust, TaskSet, task
from pyquery import PyQuery
import random
import json
import tinycss2


class AuctionTest(TaskSet):
    tender_id = ""
    tender_src = None
    last_change = 0
    csses = []

    def index(self):
        resp = self.client.get("/")
        if resp.status_code == 200:
            pq = PyQuery(resp.content)
            links = pq('.list-group-item a')
            if links:
                tender_url = random.choice(links).get('href')
                self.tender_id = tender_url.split('/')[-1]

    def tender_event_source(self):
        path = '/tenders/{0}/event_source?_nonce={1}'.format(self.tender_id, random.random())
        self.client.get(path, name="event_source")

    def tender(self):
        resp = self.client.get('/tenders/{0}'.format(self.tender_id), name="GET auction page")
        if resp.status_code == 200:
            self.tender_src = resp.content

    @task(1)
    def reload_last_tender(self):
        self.index()
        if self.tender_id:
            self.tender()
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
        pq = PyQuery(self.tender_src)

        for style in pq('link[rel="stylesheet"]'):
            href = style.get('href')
            if href and href.startswith('/') and not href.startswith('//'):
                resp = self.client.get(href)
                if resp.status_code == 200:
                    css = resp.content
                    self.csses.append(tinycss2.parse_stylesheet_bytes(css, skip_comments=True))

    def js(self):
        pq = PyQuery(self.tender_src)

        for script in pq('script'):
            src = script.get('src')
            if src and src.startswith('/') and not src.startswith('//'):
                self.client.get(src)

    def time(self):
        self.client.get(
            '/get_current_server_time?_nonce={0}'.format(random.random()), name="get_current_server_time")

    def auctions_db(self):
        self.client.get('/database?_nonce={0}'.format(random.random()),
                        name="Get db info")

    def auctions(self):
        self.client.get('/database/{0}?_nonce={0}'.format(self.tender_id, random.random()),
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
            'doc_ids': '["{0}"]'.format(self.tender_id)
        }
        if self.last_change == 0:
            name = "Get first change from couch"
        else:
            name = "Get change from couch (longpoll)"

        resp = self.client.get('/database/_changes', params=params, name=name)
        if resp.status_code == 200:
            self.last_change = json.loads(resp.content)['last_seq']



class AuctionAnonymous(HttpLocust):
    host = "${options['host']}"
    min_wait = 0
    max_wait = 0
    task_set = AuctionTest

