import redis
import json
import os
from typing import Optional, Callable


class SSEManager:
    """
    Manages Server-Sent Events (SSE) communication via Redis pub/sub.
    Encapsulates progress updates and Redis connectivity.
    """

    def __init__(self, redis_host: str = None, redis_port: int = None):
        """
        Initialize the SSE manager with Redis connection parameters.

        :param redis_host: Redis host (defaults to env var REDIS_HOST or 'localhost')
        :param redis_port: Redis port (defaults to env var REDIS_PORT or 6379)
        """

        upstash_url = os.getenv("REDIS_URL")
        upstash_token = os.getenv("REDIS_TOKEN")

        if upstash_url and upstash_token:
            # --- Upstash Redis (Production) ---
            self.redis_client =  redis.Redis.from_url(
                upstash_url,
                password=upstash_token,
                decode_responses=True
                )

        else:
            # -- local Redis (Development) ---
            self.redis_host = redis_host or os.getenv("REDIS_HOST", "localhost")
            self.redis_port = redis_port or int(os.getenv("REDIS_PORT", 6379))
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True
            )

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
        :param channel: Redis channel name (typically a job_id)
        :param download_url: Optional download URL for completion
        """
        data = {
            "progress": progress,
            "message": message,
            "download_url": download_url
        }
        self.redis_client.publish(channel, json.dumps(data))

    def progress_callback(
        self,
        progress: int,
        message: str,
        channel: str,
        download_url: Optional[str] = None
    ) -> None:
        """
        Adjusted progress callback for PDF generation workflow.
        Maps raw progress (0-100) to adjusted range (10-90%) for UI presentation.

        :param progress: Raw progress percentage
        :param message: Status message
        :param channel: Job channel identifier
        :param download_url: Optional download URL
        """
        adjusted_progress = 10 + int(progress * 0.8)  # Maps to 10-90%
        self.publish_progress(adjusted_progress, message, channel, download_url)

    def get_stream_generator(self, channel: str):
        """
        Create a generator for streaming SSE messages from a channel.
        Used by Flask's Response to stream updates to the client.

        :param channel: Redis channel to subscribe to
        :return: Generator yielding SSE-formatted data
        """
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(channel)
        for message in pubsub.listen():
            if message['type'] == 'message':
                data = message['data']
                yield f"data: {data}\n\n"
