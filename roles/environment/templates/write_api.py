# -*- coding: utf-8 -*-

from locust import HttpLocust, TaskSet, task
import json
from uuid import uuid4
from copy import copy, deepcopy
from datetime import datetime, timedelta
from test_load_data import test_tender_data, test_bid, test_lots, test_value, test_tender_data_with_lots

now = datetime.now()

tender_patch_count = 4
docs_posts_count = 3
bid_posts_count = 2
patch_bid_count = 2
bid_docs_posts_count = 4
bid_docs_patch_count = 1

api_auth = ("${options['api_key']}", '')


doc_url = "${options['doc_url']}"
doc_hash = "${options['doc_hash']}"


TEST_DOCUMENT = {
    'data': {
        'title': 'name.doc',
        'url': doc_url,
        'hash': doc_hash,
        'format': 'application/msword',
    }
}


class ApiTest(TaskSet):
    index = '/api/2.3/tenders'

    @task(1)
    def tender(self):
        self.client.head(self.index, name="Head tenders")
        create_tender_response = self.client.post(
            self.index, headers={'Content-Type': 'application/json'}, auth=api_auth,
            data=json.dumps({'data': copy(test_tender_data_with_lots)}),
            name="Create tender")

        if create_tender_response.ok:
            bids = {}
            data = create_tender_response.json()
            tender_id = data['data']['id']
            acc_token = data['access']['token']

            for i in xrange(tender_patch_count):
                patch_tender_response = self.client.patch(
                    '{}/{}'.format(self.index, tender_id), headers={'Content-Type': 'application/json'},
                    auth=api_auth, params={'acc_token': acc_token},
                    data=json.dumps({'data': {'description': 'new description'}}),
                    catch_response=True
                )

            for i in xrange(bid_posts_count):
                bid = deepcopy(test_bid)
                lots = [lot_id['id'] for lot_id in test_tender_data_with_lots['lots']]
                for lot_id in lots:
                    bid['lotValues'].append({'value': test_value, 'relatedLot': lot_id})
                create_bid_response = self.client.post('{}/{}/bids'.format(self.index, tender_id),
                                                       headers={'Content-Type': 'application/json'},
                                                       auth=api_auth,
                                                       data=json.dumps({'data': bid}),
                                                       name="Create draft bid"
                                                       )
                if not create_bid_response.ok:
                    return
                data = create_bid_response.json()
                bids[data['data']['id']] = data['access']['token']

            for bid_id, bid_acc_token in bids.items():
                for i in xrange(patch_bid_count):
                    patch_bid_response = self.client.patch(
                        '{}/{}/bids/{}?acc_token={}'.format(self.index, tender_id, bid_id, bid_acc_token),
                        headers={'Content-Type': 'application/json'}, auth=api_auth,
                        data=json.dumps({'data': {'status': 'pending'}}), name="Patch bid"
                    )

                for i in xrange(bid_docs_posts_count):
                    post_bid_document_response = self.client.post(
                        '{}/{}/bids/{}/documents?acc_token={}'.format(self.index, tender_id, bid_id, bid_acc_token),
                        headers={'Content-Type': 'application/json'}, auth=api_auth,
                        data=json.dumps(TEST_DOCUMENT), name="Post bid document")
                if post_bid_document_response.ok:
                    bid_document_id = post_bid_document_response.json()['data']['id']

                    for i in xrange(bid_docs_patch_count):
                        patch_bid_document_response = self.client.patch(
                            '{}/{}/bids/{}/documents/{}?acc_token={}'.format(
                                self.index, tender_id, bid_id, bid_document_id, bid_acc_token
                            ),
                            headers={'Content-Type': 'application/json'}, auth=api_auth,
                            data=json.dumps(TEST_DOCUMENT), name="Patch bid document")

            for i in xrange(docs_posts_count):
                post_document_response = self.client.post(
                    '{}/{}/documents'.format(self.index, tender_id), headers={'Content-Type': 'application/json'},
                    auth=api_auth, params={'acc_token': acc_token}, data=json.dumps(TEST_DOCUMENT),
                    name="Post document"
                )


class Api(HttpLocust):
    host = "${options['host']}"
    min_wait = 2000
    max_wait = 10000
    task_set = ApiTest
