from locust import HttpUser, task, constant

class SignalUser(HttpUser):
    # ~100 QPS with 100 users if each sends ~1 request/second
    wait_time = constant(1.0)

    @task
    def get_signal(self):
        # Query a tracked symbol
        self.client.get("/signal", params={"symbol": "XYZ"})
