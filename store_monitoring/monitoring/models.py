from django.db import models
import uuid
import os

class StoreStatus(models.Model):
    store_id = models.CharField(max_length=100, db_index=True)
    timestamp_utc = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=10)  # 'active' or 'inactive'
    
    class Meta:
        indexes = [
            models.Index(fields=['store_id', 'timestamp_utc']),
        ]

class BusinessHours(models.Model):
    store_id = models.CharField(max_length=100, db_index=True)
    day_of_week = models.IntegerField()  # 0=Monday, 6=Sunday
    start_time_local = models.TimeField()
    end_time_local = models.TimeField()
    
    class Meta:
        indexes = [
            models.Index(fields=['store_id', 'day_of_week']),
        ]

class StoreTimezone(models.Model):
    store_id = models.CharField(max_length=100, primary_key=True)
    timezone_str = models.CharField(max_length=100)

class Report(models.Model):
    RUNNING = 'running'
    COMPLETE = 'complete'
    FAILED = 'failed'
    
    STATUS_CHOICES = [
        (RUNNING, 'Running'),
        (COMPLETE, 'Complete'),
        (FAILED, 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=RUNNING)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    file_path = models.CharField(max_length=255, null=True, blank=True)
    google_drive_link = models.URLField(null=True, blank=True)
    
    def get_file_name(self):
        return f"report_{self.id}.csv"
    
    def get_file_path(self):
        from django.conf import settings
        return os.path.join(settings.REPORT_DIR, self.get_file_name())