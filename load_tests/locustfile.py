from locust import HttpUser, TaskSet, task, between


class UserBehavior(TaskSet):
    @task(3)
    def view_posts(self):
        self.client.get('/api/foro/posts/')

    @task(1)
    def view_communities(self):
        self.client.get('/api/foro/communities/')

    @task(1)
    def try_post(self):
        # Attempt a post (likely fails unauthenticated) to exercise POST path
        self.client.post('/api/foro/posts/', json={'title': 'locust', 'content': 'load test'})


class WebsiteUser(HttpUser):
    tasks = [UserBehavior]
    wait_time = between(1, 3)
