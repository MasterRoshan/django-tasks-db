from django.conf import settings
from django.core.management.base import BaseCommand
from django_tasks_db.models import DBTaskResult
import zmq

class Command(BaseCommand):
    help = "Run a ZMQ worker to process tasks from the ZMQ broker"

    def handle(self, *args, **options):
        context = zmq.Context()
        socket = context.socket(zmq.PULL)
        with context, socket:
            socket.connect(getattr(settings, "ZMQ_WORKER_URL", "tcp://127.0.0.1:5556"))
            self.listen(socket)

    def listen(self, socket):
        self.stdout.write(self.style.SUCCESS("Worker listening for tasks..."))
        while True:
            if socket.poll(1000):
                task_id = socket.recv_string()
                db_task_result = DBTaskResult.objects.get(id=task_id)
                task = db_task_result.task
                task_result = db_task_result.task_result
                result = task.call(*task_result.args, **task_result.kwargs)
                self.stdout.write(self.style.SUCCESS(f"Task {task_id} completed with result: {result}"))