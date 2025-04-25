import pandas as pd
from django.db import transaction
from django.core.management.base import BaseCommand
from monitoring.models import StoreStatus, BusinessHours, StoreTimezone

class Command(BaseCommand):
    help = 'Import data from CSV files into the database'

    def handle(self, *args, **options):
        self.import_data()
    
    @transaction.atomic
    def import_data(self):
        self.stdout.write(self.style.SUCCESS('Starting data import...'))
        
        # Import store status data
        try:
            self.stdout.write('Importing store status data...')
            status_df = pd.read_csv('store_status.csv')
            
            # Process in chunks to avoid memory issues
            chunk_size = 10000
            for i in range(0, len(status_df), chunk_size):
                chunk = status_df.iloc[i:i+chunk_size]
                
                status_objects = [
                    StoreStatus(
                        store_id=row['store_id'],
                        timestamp_utc=pd.to_datetime(row['timestamp_utc']),
                        status=row['status']
                    )
                    for _, row in chunk.iterrows()
                ]
                
                StoreStatus.objects.bulk_create(status_objects)
                self.stdout.write(f'Imported {i+len(chunk)}/{len(status_df)} status records')
            
            self.stdout.write(self.style.SUCCESS('Successfully imported store status data'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error importing store status data: {e}'))
        
        # Import business hours data
        try:
            self.stdout.write('Importing business hours data...')
            hours_df = pd.read_csv('business_hours.csv')
            
            hours_objects = [
                BusinessHours(
                    store_id=row['store_id'],
                    day_of_week=row['day_of_week'],
                    start_time_local=self.parse_time(row['start_time_local']),
                    end_time_local=self.parse_time(row['end_time_local'])
                )
                for _, row in hours_df.iterrows()
            ]
            
            BusinessHours.objects.bulk_create(hours_objects)
            self.stdout.write(self.style.SUCCESS('Successfully imported business hours data'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error importing business hours data: {e}'))
        
        # Import timezone data
        try:
            self.stdout.write('Importing timezone data...')
            timezone_df = pd.read_csv('timezones.csv')
            
            timezone_objects = [
                StoreTimezone(
                    store_id=row['store_id'],
                    timezone_str=row['timezone_str']
                )
                for _, row in timezone_df.iterrows()
            ]
            
            StoreTimezone.objects.bulk_create(timezone_objects)
            self.stdout.write(self.style.SUCCESS('Successfully imported timezone data'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error importing timezone data: {e}'))
        
        self.stdout.write(self.style.SUCCESS('Data import completed'))
    
    def parse_time(self, time_str):
        """Parse time string in HH:MM:SS format."""
        from datetime import datetime
        return datetime.strptime(time_str, '%H:%M:%S').time()