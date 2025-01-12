import threading
import time
from collections import deque


class RequestCounter:
    _count = 0
    _lock = threading.Lock()
    _minute_start = time.time()
    _timestamps = deque()  # Timestamps of all requests
    _requests_in_minute = 0  # Number of requests in the current minute
    _timestamps_last_15_minutes = (
        deque()
    )  # Timestamps of requests in the last 15 minutes
    _last_minute_count = 0

    @classmethod
    def increment(cls):
        """Increment the global request counter and record the timestamp."""
        with cls._lock:
            current_time = time.time()
            cls._count += 1
            cls._timestamps.append(current_time)  # Append to all timestamps
            cls._timestamps_last_15_minutes.append(
                current_time
            )  # Append to 15-minute timestamps

            # Check if the current minute has changed
            if current_time - cls._minute_start >= 60:
                cls._reset_minute_window(current_time)

            cls._requests_in_minute += 1
            cls._remove_old_requests(current_time)

    @classmethod
    def get_count(cls):
        """Get the total number of requests made."""
        with cls._lock:
            return cls._count

    @classmethod
    def requests_per_last_minute(cls):
        """Calculate the number of requests made in the last 60 seconds."""
        with cls._lock:
            current_time = time.time()
            if current_time - cls._minute_start >= 60:
                cls._reset_minute_window(current_time)
            cls._remove_old_requests(current_time)
            return max(1, cls._requests_in_minute)

    @classmethod
    def requests_per_minute(cls):
        """Get the total requests made in the last 60 seconds."""
        with cls._lock:
            current_time = time.time()
            cls._remove_old_requests(current_time)
            return len(cls._timestamps)

    @classmethod
    def average_requests_last_15_minutes(cls):
        """Calculate the average requests per minute over the last 15 minutes."""
        with cls._lock:
            current_time = time.time()
            # Ensure old timestamps are removed
            cls._remove_old_requests(current_time)

            # Check if there are any valid timestamps left
            if not cls._timestamps_last_15_minutes:
                return 0

            # Calculate average based on timestamps
            first_timestamp = cls._timestamps_last_15_minutes[0]
            elapsed_time = current_time - first_timestamp
            elapsed_minutes = elapsed_time / 60
            total_requests = len(cls._timestamps_last_15_minutes)
            return round(total_requests / elapsed_minutes)

    @classmethod
    def get_last_minute_count(cls):
        """Get the request count for the last complete minute."""
        with cls._lock:
            return cls._last_minute_count

    @classmethod
    def seconds_elapsed_in_window(cls):
        """Calculate how many seconds are left in the current-minute window."""
        with cls._lock:
            current_time = time.time()
            if current_time - cls._minute_start >= 60:
                cls._reset_minute_window(current_time)
            cls._remove_old_requests(current_time)
            elapsed_time = current_time - cls._minute_start
            return max(0.1, elapsed_time)

    @classmethod
    def _remove_old_requests(cls, current_time):
        """Remove timestamps older than 60 seconds."""
        while cls._timestamps and current_time - cls._timestamps[0] >= 60:
            cls._timestamps.popleft()

        # Remove requests older than 15 minutes for the 15-minute window
        while (
            cls._timestamps_last_15_minutes
            and current_time - cls._timestamps_last_15_minutes[0] > 900
        ):
            cls._timestamps_last_15_minutes.popleft()

    @classmethod
    def _reset_minute_window(cls, current_time):
        """Reset the current-minute window."""
        cls._last_minute_count = cls._requests_in_minute
        cls._minute_start = current_time
        cls._requests_in_minute = 0
