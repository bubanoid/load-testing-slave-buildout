import urllib3.contrib.pyopenssl
urllib3.contrib.pyopenssl.inject_into_urllib3()
import random
import json
import tinycss2
import copy
import requests
from urlparse import urlparse, parse_qs
from locust import HttpLocust, TaskSet, task, events
from time import time
from gevent import spawn, joinall, sleep
from pyquery import PyQuery
from base64 import b64encode
from libnacl.sign import Signer
from urllib import quote
import os, io
from configparser import RawConfigParser
from math import ceil, log10

PWD = os.path.dirname(os.path.realpath(__file__.rstrip('cd')))

with open(PWD + '/../etc/locust.cfg', 'r') as f:
    sample_config = f.read()
config = RawConfigParser(allow_no_value=True)
config.read_file(io.BytesIO(sample_config))

section = os.path.basename(__file__.rstrip('cd'))
PARAMS = {}

for option in config.options(section):
    PARAMS[option] = config.get(section, option)

AUCTIONS_NUMBER = int(PARAMS['auctions_number'])
BIDDERS = [r.strip() for r in PARAMS['bidders'].split() if r.strip()]
SIGNATURE_KEY = PARAMS['signature_key']
tender_id_base = PARAMS['tender_id_base']
positions = int(ceil(log10(AUCTIONS_NUMBER)))
auction_id_template = \
    tender_id_base * (32 - positions) + '{{0:0{}d}}'.format(positions)
stages = int(PARAMS['stages'])


class AuctionInsiderAuthorizedTest(TaskSet):
    signer = Signer(SIGNATURE_KEY.decode('hex'))

    auction_src = None
    saved_cookies = None
    last_change = 0
    csses = []
    dutch_winner = ""
    dutch_winner_amount = 0

    def generate_auth_params(self):
        self.bidder_id = BIDDERS[random.randint(0, len(BIDDERS) - 1)]
        msg = '{}_{}'.format(self.auction_id, self.bidder_id)
        self.signature = quote(b64encode(self.signer.signature(str(msg))))

    def post_bid(self):
        current_phase = self.auction_doc['current_phase']
        inital_value = self.auction_doc['initial_value']
        params = {}
        if current_phase == 'dutch' and len(self.auction_doc['results']) == 0:
            stage = \
                self.auction_doc['stages'][self.auction_doc['current_stage']]
            params['bidder_id'] = self.bidder_id
            params['bid'] = stage['amount']
        elif current_phase == 'sealedbid':
            for result in self.auction_doc['results']:
                if 'dutch_winner' in result:
                    self.dutch_winner = result['bidder_id']
                    self.dutch_winner_amount = result['amount']
            params['bidder_id'] = self.bidder_id
            params['bid'] = random.randint(self.dutch_winner_amount,
                                           inital_value - 1)
        elif current_phase == 'bestbid' and \
                        self.bidder_id == self.dutch_winner:
            params['bidder_id'] = self.bidder_id
            params['bid'] = random.randint(self.dutch_winner_amount,
                                           inital_value - 1)
        if params:
            self.client.post(
                '/insider-auctions/{}/postbid'.format(self.auction_id),
                data=json.dumps(params),
                headers={'Content-Type': 'application/json'},
                name='Place bid to auction {}'.format(self.auction_id)
            )

    @task(1)
    def main_task(self):
        self.last_change = 0
        self.auction_id = \
            auction_id_template.format(random.randint(0, AUCTIONS_NUMBER - 1))
        self.generate_auth_params()
        params = {
            "bidder_id": self.bidder_id,
            "signature": self.signature
        }
        response = self.client.get(
            '/insider-auctions/{}/login'.format(self.auction_id),
            params=params, name="Login to auction", allow_redirects=False,
            catch_response=True
        )
        if response.ok and 'Location' in response.headers:
            if response.headers['Location'].startswith(self.client.base_url):
                sleep(10)
                return

            response = self.client.get(response.headers['Location'],
                                       name="Get EULA page")
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
                self.get_auction_page()
                self.load_all_css()
                self.load_all_js()
                self.get_auction_doc_from_couchdb()
                self.get_auctions_db_info()
                self.changes()
                self.get_current_time()
                long_pool = spawn(self.changes_multiple)
                self.read_event_source(self.saved_cookies)
                joinall([long_pool])
        else:
            sleep(10)

    def get_auction_page(self):
        resp = self.client.get('/insider-auctions/{}'.format(self.auction_id),
                               name='Get auction page')
        self.auction_page_src = resp.content

    def load_all_css(self):
        pq = PyQuery(self.auction_page_src)
        for style in pq('link[rel="stylesheet"]'):
            href = style.get('href')
            if href and href.startswith('/') and not href.startswith('//'):
                resp = self.client.get(href)
                if resp.status_code == 200:
                    css = resp.content
                    self.csses.append(
                        tinycss2.parse_stylesheet_bytes(
                            css, skip_comments=True)
                    )

    def load_all_js(self):
        pq = PyQuery(self.auction_src)

        for script in pq('script'):
            src = script.get('src')
            if src and src.startswith('/') and not src.startswith('//'):
                self.client.get(src)

    def get_auction_doc_from_couchdb(self):
        self.client.get(
            '/database/{0}?_nonce={0}'.format(self.auction_id,
                                              random.random()),
            name="Get document from couch")

    def get_auctions_db_info(self):
        self.client.get('/database?_nonce={0}'.format(random.random()),
                        name="Get db info")

    def read_event_source(self, cookies):
        start_time = time()
        response = self.client.get(
            "/insider-auctions/{0}/event_source?lastEventId=&r={1}".format(
                self.auction_id,
                random.randint(1000000000000000, 9999999999999999)
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
        events.request_success.fire(request_type="GET",
                                    name="Get event_source stream (Finish read)",
                                    response_time=total_time,
                                    response_length=response_length)
        sleep(10)

    def changes_multiple(self):
        while self.auction_doc['current_phase'] != u'announcement':
            self.changes()
            current_phase = self.auction_doc['current_phase']
            if current_phase == u'dutch' and \
                    self.auction_doc['current_stage'] == stages/2:
                self.post_bid()
            elif current_phase == u'sealedbid':
                self.post_bid()
            elif current_phase == u'bestbid':
                self.post_bid()

    def get_current_time(self):
        self.client.get(
            '/get_current_server_time?_nonce={0}'.format(random.random()),
            name="Get current server time")

    def changes(self):
        self.get_current_time()
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
            doc = json.loads(resp.content)
            if len(doc['results']) > 0:
                self.auction_doc = doc['results'][-1]['doc']
            self.last_change = doc['last_seq']


class AuctionAuthorized(HttpLocust):
    host = PARAMS['host']
    min_wait = 0
    max_wait = 0
    task_set = AuctionInsiderAuthorizedTest
