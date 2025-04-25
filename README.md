# Take Home Interview - Store Monitoring

This project implements a backend system to monitor restaurant uptime and downtime based on business hours and periodic status logs. It allows restaurant owners to generate reports that help them understand how often their stores were offline during business hours.

## 📦 Features

- Store and process CSV data related to store statuses, business hours, and timezones.
- Dynamically compute uptime and downtime for:
  - Last hour
  - Last day
  - Last week
- Handle timezone conversions and local time business hour logic.
- Extrapolate uptime/downtime using polling-based interpolation.
- Expose APIs to:
  - Trigger report generation
  - Retrieve report status or download results

## 🗂️ Data Sources

The project uses three CSV files (from [this ZIP file](https://storage.googleapis.com/hiring-problem-statements/store-monitoring-data.zip)):

1. **Store Status Logs**: `store_id, timestamp_utc, status`
2. **Business Hours**: `store_id, dayOfWeek, start_time_local, end_time_local`
3. **Timezones**: `store_id, timezone_str`

> 📌 Missing business hours are assumed to be 24/7.  
> 📌 Missing timezones default to `America/Chicago`.

## 🛠️ Technologies Used

- Python
- Django REST Framework
- PostgreSQL
- pandas
- pytz, datetime
- Celery + Redis (for background task simulation)
- Docker (optional for setup)
- Postman (API testing)

## 📑 API Documentation

Available here:  
📄 [Postman Documentation](https://documenter.getpostman.com/view/34400094/2sB2izEDvG)
