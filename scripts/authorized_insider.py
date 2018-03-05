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
from iso8601 import parse_date
from datetime import timedelta
from dateutil import parser


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
positions = 4
auction_id_template = \
    tender_id_base * (32 - positions) + '{{0:0{}d}}'.format(positions)
dutch_steps = int(PARAMS['dutch_steps'])


class AuctionInsiderAuthorizedTest(TaskSet):
    signer = Signer(SIGNATURE_KEY.decode('hex'))

    auction_src = None
    auction_id = None
    saved_cookies = None
    last_change = 0
    csses = []
    dutch_winner = ''
    dutch_winner_amount = 0
    auction_doc = {}
    ind = False
    current_phase = None
    current_stage = None
    initial_value = 0
    current_time = '2000-01-01T00:00:00.000000+02:00'
    next_stage_start = '2000-01-01T00:00:00+02:00'

    def __init__(self, parent):
        self.auction_id = \
            auction_id_template.format(random.randint(0, AUCTIONS_NUMBER - 1))
        self.bidder_id = BIDDERS[random.randint(0, len(BIDDERS) - 1)]
        msg = '{}_{}'.format(self.auction_id, self.bidder_id)
        self.signature = quote(b64encode(self.signer.signature(str(msg))))
        self.auth_params = {
            "bidder_id": self.bidder_id,
            "signature": self.signature
        }
        super(AuctionInsiderAuthorizedTest, self).__init__(parent)

    def post_bid(self, params):
        self.client.post(
            '/insider-auctions/{}/postbid'.format(self.auction_id),
            data=json.dumps(params),
            headers={'Content-Type': 'application/json'},
            name='Place bid to auction. Phase: {}, id: {}'.
                format(self.current_phase, self.auction_id)
        )

    @task(1)
    def main_task(self):
        self.get_auction_doc_from_couchdb()

        if self.current_phase != u'announcement':  # and self.current_stage >= 0:
            response = self.client.get(
                '/insider-auctions/{}/login'.format(self.auction_id),
                params=self.auth_params, name="Login to auction",
                allow_redirects=False, catch_response=True
            )
            if response.ok and 'Location' in response.headers:
                if response.headers['Location'].\
                        startswith(self.client.base_url):
                    sleep(10)
                    return

                response = self.client.get(response.headers['Location'],
                                           name="Get EULA page")
                if not response.ok:
                    raise Exception('Client could not get EULA page')

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
                    self.get_auctions_db_info()
                    long_pool = spawn(self.changes_multiple)
                    self.read_event_source(self.saved_cookies)
                    joinall([long_pool])
                else:
                    raise Exception('Client could not click yes on EULA')
        sleep(10)

    def get_auction_page(self):
        resp = self.client.get('/insider-auctions/{}'.format(self.auction_id),
                               name='Get auction page')
        self.auction_src = resp.content

    def load_all_css(self):
        pq = PyQuery(self.auction_src)
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
        resp = self.client.get(
            '/database/{0}?_nonce={0}'.format(self.auction_id,
                                              random.random()),
            name="Get document from couch")
        doc = json.loads(resp.content)

        self.current_stage = doc['current_stage']
        self.current_phase = doc['current_phase']
        self.initial_value = doc['initial_value']

        if len(doc['stages']) > int(doc['current_stage']) + 1:
            self.next_stage_start = \
                doc['stages'][doc['current_stage'] + 1]['start']

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
        events.request_success.fire(
            request_type="GET",
            name="Get event_source stream (Finish read)",
            response_time=total_time,
            response_length=response_length
        )
        sleep(3)

    def changes_multiple(self):
        while self.current_phase != u'announcement':
            params = {}
            self.changes()
            self.get_current_server_time()

            if self.current_phase == u'dutch' and \
                    self.auction_doc['current_stage'] >= dutch_steps/2 and \
                    not self.dutch_winner and \
                    self.before_time(self.current_time,
                                     parse_date(self.next_stage_start)):

                stage = self.auction_doc['stages'][
                    self.auction_doc['current_stage']]
                params['bidder_id'] = self.bidder_id
                params['bid'] = stage['amount']

            elif self.current_phase == u'sealedbid' and \
                    self.bidder_id != self.dutch_winner and \
                    self.before_time(self.current_time,
                                     parse_date(self.next_stage_start)):

                params['bidder_id'] = self.bidder_id
                params['bid'] = random.randint(self.dutch_winner_amount,
                                               99*self.initial_value/100 - 2)

            elif self.current_phase == u'bestbid' and \
                    self.bidder_id == self.dutch_winner and \
                    self.before_time(self.current_time,
                                     parse_date(self.next_stage_start)):
                params['bidder_id'] = self.bidder_id
                params['bid'] = int(self.initial_value - 1)

            if params:
                self.post_bid(params)

    def get_current_server_time(self):
        resp = self.client.get(
            '/get_current_server_time?_nonce={0}'.format(random.random()),
            name="Get current server time")
        if resp.status_code == 200:
            current_time_str = resp.headers['date']
            self.current_time = parser.parse(current_time_str)

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
                self.current_phase = self.auction_doc['current_phase']
                self.current_stage = self.auction_doc['current_stage']

                if not self.dutch_winner:
                    for result in self.auction_doc['results']:
                        if 'dutch_winner' in result:
                            self.dutch_winner = result['bidder_id']
                            self.dutch_winner_amount = result['amount']

            self.last_change = doc['last_seq']

    @staticmethod
    def before_time(time1, time2):
        return time1 < time2 - timedelta(seconds=3)


class AuctionAuthorized(HttpLocust):
    host = PARAMS['host']
    min_wait = 0
    max_wait = 0
    task_set = AuctionInsiderAuthorizedTest
