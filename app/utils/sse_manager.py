from flask import Response
import queue
import threading
import json
from typing import Optional

# Global dictionary to store queues for each job_id
channels = {}

class SSEManager:
    def __init__(self):
        """
        Initialize the SSE manager with in-memory queues.
        """
        self.channels = channels

    def create_channel(self, job_id: str) -> None:
        """
        Create a new channel (queue) for the given job_id.
        :param job_id: Unique identifier for the job.
        """
        if job_id not in self.channels:
            self.channels[job_id] = queue.Queue()

    def publish_progress(
        self,
        progress: int,
        message: str,
        channel: str,
        download_url: Optional[str] = None
    ) -> None:
        """
        Publish a progress update to a specific channel.

        :param progress: Progress percentage (0-100, or adjusted as needed)
        :param message: Status message to display
        :param channel: Channel name (typically a job_id)
        :param download_url: Optional download URL for completion
        """
        if channel in self.channels:
            data = {
                "progress": progress,
                "message": message,
                "download_url": download_url
            }
            self.channels[channel].put(json.dumps(data))

    def progress_callback(
        self,
        progress: int,
        message: str,
        channel: str,
        download_url: Optional[str] = None
    ) -> None:
        """
        Adjusted progress callback for workflows like PDF generation.
        Maps raw progress (0-100) to adjusted range (10-90%) for UI presentation.

        :param progress: Raw progress percentage
        :param message: Status message
        :param channel: Job channel identifier
        :param download_url: Optional download URL
        """
        # Adjust progress to fit the UI range (e.g., 10-90%)
        adjusted_progress = 10 + int(progress * 0.8)
        self.publish_progress(adjusted_progress, message, channel, download_url)

    def stream(self, job_id: str) -> Response:
        """
        Stream messages from the queue for the given job_id.
        :param job_id: Unique identifier for the job.
        :return: A Flask Response object for SSE.
        """
        def generate():
            while True:
                if job_id not in self.channels:
                    break
                try:
                    # Get a message from the queue (timeout to prevent blocking indefinitely)
                    message = self.channels[job_id].get(timeout=10)
                    yield f"data: {message}\n\n"
                except queue.Empty:
                    # Timeout reached, send a keep-alive message
                    yield f": keep-alive\n\n"
                except GeneratorExit:
                    # Client disconnected
                    break

        return Response(generate(), content_type="text/event-stream")

    def delete_channel(self, job_id: str) -> None:
        """
        Delete the channel (queue) for the given job_id.
        :param job_id: Unique identifier for the job.
        """
        if job_id in self.channels:
            del self.channels[job_id]