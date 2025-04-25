import pandas as pd
import pytz
from datetime import datetime, timedelta
import os
import threading
from django.utils import timezone
from django.db.models import Max

from .models import StoreStatus, BusinessHours, StoreTimezone, Report
from .google_drive import GoogleDriveClient
from .report_utils import optimize_report_generation

def generate_report(report_id):
    """
    Start report generation in a background thread.
    """
    # Run report generation in a background thread
    thread = threading.Thread(target=optimize_report_generation, args=(report_id,))
    thread.daemon = True
    thread.start()

def upload_to_google_drive(file_path, file_name):
    """
    Upload a file to Google Drive using our GoogleDriveClient.
    """
    # Create a Google Drive client
    drive_client = GoogleDriveClient()
    
    # Upload the file
    result = drive_client.upload_file(file_path, file_name, mime_type='text/csv')
    
    if result:
        return result.get('link')
    
    return None

def get_current_timestamp():
    """
    Get the maximum timestamp from the database or current time if no data exists.
    """
    max_timestamp = StoreStatus.objects.aggregate(Max('timestamp_utc'))['timestamp_utc__max']
    if max_timestamp:
        return max_timestamp
    return timezone.now()

# Retry mechanism for uploading to Google Drive
def upload_with_retry(file_path, file_name, max_retries=3):
    """
    Upload a file to Google Drive with retry logic.
    """
    for attempt in range(max_retries):
        try:
            link = upload_to_google_drive(file_path, file_name)
            if link:
                return link
        except Exception as e:
            print(f"Upload attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                # Wait a bit before retrying (exponential backoff)
                time.sleep(2 ** attempt)
    
    return None