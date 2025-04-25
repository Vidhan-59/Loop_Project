import pandas as pd
import pytz
from datetime import datetime, timedelta, time
from django.db.models import Avg, Count, Q, F, Min, Max
from .models import StoreStatus, BusinessHours, StoreTimezone

def get_store_business_hours(store_id, date):
    """
    Get business hours for a store on a specific date.
    Returns a list of (start_datetime, end_datetime) tuples in UTC.
    If no business hours are defined, assumes 24/7 operation.
    """
    # Get store timezone
    try:
        tz_str = StoreTimezone.objects.get(store_id=store_id).timezone_str
    except StoreTimezone.DoesNotExist:
        tz_str = 'America/Chicago'
    
    store_tz = pytz.timezone(tz_str)
    utc_tz = pytz.UTC
    
    # Get day of week (0=Monday, 6=Sunday)
    local_date = date.astimezone(store_tz).date()
    day_of_week = local_date.weekday()
    
    # Get business hours for this day
    business_hours = BusinessHours.objects.filter(store_id=store_id, day_of_week=day_of_week)
    
    if not business_hours.exists():
        # No business hours defined, assume 24/7
        start_dt = datetime.combine(local_date, time(0, 0))
        end_dt = datetime.combine(local_date, time(23, 59, 59))
        
        # Localize to store timezone, then convert to UTC
        start_dt = store_tz.localize(start_dt).astimezone(utc_tz)
        end_dt = store_tz.localize(end_dt).astimezone(utc_tz)
        
        return [(start_dt, end_dt)]
    
    # Process each business hours record
    result = []
    for bh in business_hours:
        start_dt = datetime.combine(local_date, bh.start_time_local)
        end_dt = datetime.combine(local_date, bh.end_time_local)
        
        # Handle business hours spanning midnight
        if bh.end_time_local < bh.start_time_local:
            end_dt += timedelta(days=1)
        
        # Localize to store timezone, then convert to UTC
        start_dt = store_tz.localize(start_dt).astimezone(utc_tz)
        end_dt = store_tz.localize(end_dt).astimezone(utc_tz)
        
        result.append((start_dt, end_dt))
    
    return result

def get_time_intervals_in_range(store_id, start_time, end_time):
    """
    Get all business hours intervals between start_time and end_time for a store.
    Returns a list of (start_datetime, end_datetime) tuples in UTC.
    """
    intervals = []
    
    # Get store timezone
    try:
        tz_str = StoreTimezone.objects.get(store_id=store_id).timezone_str
    except StoreTimezone.DoesNotExist:
        tz_str = 'America/Chicago'
    
    store_tz = pytz.timezone(tz_str)
    
    # Convert to timezone-aware UTC
    if start_time.tzinfo is None:
        start_time = pytz.UTC.localize(start_time)
    if end_time.tzinfo is None:
        end_time = pytz.UTC.localize(end_time)
    
    # Get local date ranges to check
    start_date_local = start_time.astimezone(store_tz).date()
    end_date_local = end_time.astimezone(store_tz).date()
    
    # Process each day in the range
    current_date = start_date_local
    while current_date <= end_date_local:
        # Get business hours for this date
        for bh_start, bh_end in get_store_business_hours(store_id, store_tz.localize(datetime.combine(current_date, time(12, 0)))):
            # Check if this business hours interval overlaps with our time range
            if bh_end > start_time and bh_start < end_time:
                # Calculate overlap
                overlap_start = max(bh_start, start_time)
                overlap_end = min(bh_end, end_time)
                intervals.append((overlap_start, overlap_end))
        
        current_date += timedelta(days=1)
    
    return intervals

def calculate_uptime_downtime(store_id, start_time, end_time):
    """
    Calculate uptime and downtime for a store between start_time and end_time.
    Only considers time within business hours.
    Uses interpolation to fill gaps between observations.
    """
    # Get all business hours intervals in the time range
    business_intervals = get_time_intervals_in_range(store_id, start_time, end_time)
    
    # Calculate total business hours
    total_business_seconds = sum((end - start).total_seconds() for start, end in business_intervals)
    
    # If no business hours in range, return zeros
    if total_business_seconds == 0:
        return 0, 0
    
    # Get observations within the time range
    observations = StoreStatus.objects.filter(
        store_id=store_id,
        timestamp_utc__gte=start_time,
        timestamp_utc__lte=end_time
    ).order_by('timestamp_utc')
    
    # If no observations, assume store was operating normally (uptime)
    if not observations.exists():
        total_business_minutes = total_business_seconds / 60
        return total_business_minutes, 0
    
    # Process observations
    uptime_seconds = 0
    downtime_seconds = 0
    
    for interval_start, interval_end in business_intervals:
        # Get observations within this business hours interval
        interval_obs = observations.filter(
            timestamp_utc__gte=interval_start,
            timestamp_utc__lte=interval_end
        )
        
        if not interval_obs.exists():
            # No observations in this interval, assume uptime
            uptime_seconds += (interval_end - interval_start).total_seconds()
            continue
        
        # Get first and last observation in this interval
        first_obs = interval_obs.first()
        last_obs = interval_obs.last()
        
        # Handle time before first observation
        if first_obs.timestamp_utc > interval_start:
            # For the first interval of the day, extrapolate from the first observation
            if first_obs.status == 'active':
                uptime_seconds += (first_obs.timestamp_utc - interval_start).total_seconds()
            else:
                downtime_seconds += (first_obs.timestamp_utc - interval_start).total_seconds()
        
        # Process pairs of observations
        prev_obs = None
        for obs in interval_obs:
            if prev_obs is not None:
                time_diff = (obs.timestamp_utc - prev_obs.timestamp_utc).total_seconds()
                if prev_obs.status == 'active':
                    uptime_seconds += time_diff
                else:
                    downtime_seconds += time_diff
            prev_obs = obs
        
        # Handle time after last observation
        if last_obs.timestamp_utc < interval_end:
            # Extrapolate from the last observation
            if last_obs.status == 'active':
                uptime_seconds += (interval_end - last_obs.timestamp_utc).total_seconds()
            else:
                downtime_seconds += (interval_end - last_obs.timestamp_utc).total_seconds()
    
    # Convert to minutes
    uptime_minutes = uptime_seconds / 60
    downtime_minutes = downtime_seconds / 60
    
    return uptime_minutes, downtime_minutes

def generate_store_report(store_id, current_time):
    """
    Generate uptime/downtime report for a single store.
    """
    # Define time intervals
    hour_ago = current_time - timedelta(hours=1)
    day_ago = current_time - timedelta(days=1)
    week_ago = current_time - timedelta(weeks=1)
    
    # Calculate metrics for different time intervals
    uptime_hour, downtime_hour = calculate_uptime_downtime(store_id, hour_ago, current_time)
    uptime_day, downtime_day = calculate_uptime_downtime(store_id, day_ago, current_time)
    uptime_week, downtime_week = calculate_uptime_downtime(store_id, week_ago, current_time)
    
    # Convert to hours for day and week metrics
    uptime_day_hours = uptime_day / 60
    downtime_day_hours = downtime_day / 60
    uptime_week_hours = uptime_week / 60
    downtime_week_hours = downtime_week / 60
    
    return {
        'store_id': store_id,
        'uptime_last_hour': round(uptime_hour, 2),
        'uptime_last_day': round(uptime_day_hours, 2),
        'uptime_last_week': round(uptime_week_hours, 2),
        'downtime_last_hour': round(downtime_hour, 2),
        'downtime_last_day': round(downtime_day_hours, 2),
        'downtime_last_week': round(downtime_week_hours, 2)
    }

def optimize_report_generation(report_id):
    """
    Optimized report generation that processes stores in batches
    to handle large datasets efficiently.
    """
    from .models import Report
    import time as time_module
    import pandas as pd
    
    try:
        report = Report.objects.get(id=report_id)
        
        # Get the current (max) timestamp
        current_time = StoreStatus.objects.aggregate(max_time=Max('timestamp_utc'))['max_time']
        if not current_time:
            current_time = datetime.now(pytz.UTC)
        
        # Get all unique store IDs
        store_ids = StoreStatus.objects.values_list('store_id', flat=True).distinct()
        
        # Process stores in batches
        batch_size = 100
        results = []
        total_stores = len(store_ids)
        
        for i in range(0, total_stores, batch_size):
            batch = list(store_ids)[i:i+batch_size]
            
            # Process each store in the batch
            for store_id in batch:
                try:
                    store_report = generate_store_report(store_id, current_time)
                    results.append(store_report)
                except Exception as e:
                    print(f"Error processing store {store_id}: {e}")
                    # Add a record with zeros for this store to ensure it's included in the report
                    results.append({
                        'store_id': store_id,
                        'uptime_last_hour': 0,
                        'uptime_last_day': 0,
                        'uptime_last_week': 0,
                        'downtime_last_hour': 0,
                        'downtime_last_day': 0,
                        'downtime_last_week': 0
                    })
            
            print(f"Processed {min(i+batch_size, total_stores)}/{total_stores} stores")
            
        # Create DataFrame and save to CSV
        df = pd.DataFrame(results)
        file_path = report.get_file_path()
        df.to_csv(file_path, index=False)
        
        # Upload to Google Drive
        from .utils import upload_to_google_drive
        drive_link = upload_to_google_drive(file_path, report.get_file_name())
        
        # Update report status
        report.status = Report.COMPLETE
        report.completed_at = datetime.now(pytz.UTC)
        report.file_path = file_path
        report.google_drive_link = drive_link
        report.save()
        
        return True
        
    except Exception as e:
        print(f"Error in optimize_report_generation: {e}")
        
        # Update report status to failed
        try:
            report.status = Report.FAILED
            report.save()
        except:
            pass
        
        return False