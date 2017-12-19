from locust import HttpLocust, TaskSet, task
from hashlib import md5

class DSBehavior(TaskSet):
    content = 'a' * ${options['size']}
    md5hash = md5(content).hexdigest()
    auth = ('${options['username']}', '${options['password']}')

    @task
    def upload_with_registration(self):
        hashdata = {'hash': 'md5:' + self.md5hash}
        r = self.client.post('/register', json={'data': hashdata}, auth=self.auth, name="/register")
        if r.status_code == 201:
            json = r.json()
            upload_url = json['upload_url']
        else:
            return

        r = self.client.post(upload_url, files={'file': ('file.txt', self.content, 'text/plain')}, auth=self.auth, name="/upload")
        if r.status_code == 200:
            json = r.json()
            get_url = json['get_url']
        else:
            return
        for _ in xrange(5):
            self.client.get(get_url, name="/get")

    @task
    def upload_wo_registration(self):
        r = self.client.post('/upload', files={'file': ('file.txt', self.content, 'text/plain')}, auth=self.auth, name="/upload")
        if r.status_code == 200:
            json = r.json()
            get_url = json['get_url']
        else:
            return
        for _ in xrange(5):
            self.client.get(get_url, name="/get")

class ${options['class']}(HttpLocust):
    host = "${options['host']}"
    task_set = DSBehavior
    max_wait = 10000
