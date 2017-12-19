import urllib3.contrib.pyopenssl
urllib3.contrib.pyopenssl.inject_into_urllib3()
from urlparse import urlparse, parse_qs
from locust import HttpLocust, TaskSet, task, events
import copy
import requests
from time import sleep, time
from gevent import spawn, joinall
from pyquery import PyQuery
import random
import json
import tinycss2


class AuctionAuthorizedTest(TaskSet):
    auction_id = "${options['auction_id']}"
    bidder_id = "${options['bidder_id']}"
    hash_value = "${options['hash_value']}"
    

    tender_src = None
    saved_cookies = None
    last_change = 0
    csses = []

    @task(1)
    def main_task(self):
        self.last_change = 0
        if not self.auction_id:
            self.auction_id = "111111111111111111111111111{0:05d}".format(random.randint(0, 100))
        params = {
            "bidder_id": self.bidder_id,
            "hash": self.hash_value
        }
        response = self.client.get('/tenders/{0}/login'.format(self.auction_id), params=params, name="Login", allow_redirects=False, catch_response=True)
        if response.ok and 'Location' in response.headers:
            if response.headers['Location'].startswith(self.client.base_url):
                sleep(10)
                return
            
            response = self.client.get(response.headers['Location'], name="Get EULA page")
            if not response.ok:
                return
            
            redirect_url = urlparse(response.request.url)
            query = parse_qs(redirect_url.query)


            params = {
                "client_id": query['client_id'][0],
                "scope": query['scope'][0],
                "bidder_id": query['bidder_id'][0],
                "response_type": query['response_type'][0],
                "redirect_uri": query['redirect_uri'][0],
                "confirm": "yes"
            }
            response = self.client.post(
                '{0.scheme}://{0.netloc}{0.path}'.format(redirect_url),
                data=params, name="Click yes on EULA"
            )
            if response.ok:
                self.saved_cookies = copy.copy(self.client.cookies)
                self.tender()
                self.css()
                self.js()
                self.auctions()
                self.auctions_db()
                self.time()
                self.changes()
                long_pool = spawn(self.changes_multiple)
                self.event_source(self.saved_cookies)
                joinall([long_pool])

        else:
            sleep(10)

    def event_source(self, cookies):
        start_time = time()
        response = self.client.get(
            "/tenders/{0}/event_source?lastEventId=&r={1}".format(
                self.auction_id, random.randint(1000000000000000, 9999999999999999)
            ),
            stream=True, cookies=requests.utils.dict_from_cookiejar(cookies),
            name="Get event_source stream"
        )
        response_length = 0
        try:
            if response.ok:
                for line in response.iter_lines():
                    response_length += len(line)
                    sleep(0.1)
        except:
            pass
        total_time = int((time() - start_time) * 1000)
        events.request_success.fire(request_type="GET", name="Get event_source stream (Finish read)", response_time=total_time, response_length=response_length)
        sleep(10)

    def tender(self):
        params = {"bidder_id": self.bidder_id,
                  "hash": self.hash_value,
                  "wait": 1}
        resp = self.client.get('/tenders/{0}'.format(self.auction_id), params=params, name="Get auction page")
        self.tender_src = resp.content

    def changes_multiple(self):
        for i in range(random.randint(8, 12)):
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
            '/get_current_server_time?_nonce={0}'.format(random.random()), name="Get current server time")

    def auctions_db(self):
        self.client.get('/database?_nonce={0}'.format(random.random()),
                        name="Get db info")

    def auctions(self):
        self.client.get('/database/{0}?_nonce={0}'.format(self.auction_id, random.random()),
                        name="Get document from couch")

    def changes(self):
        self.time()
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
            'doc_ids': '["{0}"]'.format(self.auction_id)
        }
        if self.last_change == 0:
            name = "Get first change from couch"
        else:
            name = "Get change from couch (longpoll)"

        resp = self.client.get('/database/_changes', params=params, name=name)
        if resp.status_code == 200:
            self.last_change = json.loads(resp.content)['last_seq']


class AuctionAuthorized(HttpLocust):
    host = "${options['host']}"
    min_wait = 0
    max_wait = 0
    task_set = AuctionAuthorizedTest
