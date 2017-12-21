from locust import HttpLocust, TaskSet, task
import json


class ApiTest(TaskSet):
    index = '/api/0/tenders'

    tenders = []
    offset = None

    @task
    def tender(self):
        for id in self.next_id():
            self.client.get(self.index + '/' + id, name="get tender item")

    def start(self):
        content = json.loads(self.client.get(self.index, name="get tender listing", params={'descending': 1}).content)
        self.tenders = [data['id'] for data in content['data']]
        self.offset = content['next_page']['offset']

    def next_page(self):
        content = json.loads(self.client.get(self.index, name="get tender listing",
                                             params={'descending': 1, 'offset': self.offset}).content)
        self.tenders = [data['id'] for data in content['data']]
        self.offset = content['next_page']['offset']

    def next_id(self):
        self.start()

        while self.tenders:
            for id in self.tenders:
                yield id
            self.next_page()


class Api(HttpLocust):
    host = "${options['host']}"
    min_wait = 1000
    max_wait = 2000
    task_set = ApiTest