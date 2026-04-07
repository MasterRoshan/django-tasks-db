from django.conf import settings
from django.core.management.base import BaseCommand
import zmq
import threading
import time

class Command(BaseCommand):
    help = "Run a ZMQ broker to receive task IDs and push them to workers"

    def handle(self, *args, **options):
        with (
            zmq.Context() as context,
            context.socket(zmq.PULL) as frontend,
            context.socket(zmq.PUSH) as backend,
            context.socket(zmq.PAIR) as ctrl_recv,
            context.socket(zmq.PAIR) as ctrl_send,
        ):
            frontend.bind(getattr(settings, "ZMQ_BROKER_URL", "tcp://127.0.0.1:5555"))
            backend.bind(getattr(settings, "ZMQ_WORKER_URL", "tcp://127.0.0.1:5556"))

            ctrl_endpoint = "inproc://proxy-control"
            ctrl_recv.bind(ctrl_endpoint)
            ctrl_send.connect(ctrl_endpoint)

            proxy_thread = threading.Thread(
                target=zmq.proxy_steerable,
                args=(frontend, backend, None, ctrl_recv),
                daemon=True,
            )
            proxy_thread.start()
            self.stdout.write(self.style.SUCCESS("ZMQ broker started..."))

            try:
                while proxy_thread.is_alive():
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING("Shutting down ZMQ broker..."))
                ctrl_send.send(b"TERMINATE")
                proxy_thread.join(timeout=5)
                if proxy_thread.is_alive():
                    self.stdout.write(self.style.ERROR("ZMQ broker did not terminate in time"))