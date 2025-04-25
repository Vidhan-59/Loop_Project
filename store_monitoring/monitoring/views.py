from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
import threading
import os

from .models import Report
from .utils import generate_report

@api_view(['POST'])
def trigger_report(request):
    """Trigger report generation."""
    # Create a new report object
    report = Report.objects.create()
    
    # Start report generation in background
    threading.Thread(target=generate_report, args=(report.id,)).start()
    
    return Response({'report_id': report.id}, status=status.HTTP_202_ACCEPTED)

@api_view(['GET'])
def get_report(request, report_id):
    """Get report status or download the completed report."""
    try:
        report = Report.objects.get(id=report_id)
        
        if report.status == Report.RUNNING:
            return Response({'status': 'Running'}, status=status.HTTP_200_OK)
        
        elif report.status == Report.COMPLETE:
            if request.query_params.get('download', 'false').lower() == 'true':
                # Return the CSV file
                if os.path.exists(report.file_path):
                    with open(report.file_path, 'rb') as file:
                        response = HttpResponse(file.read(), content_type='text/csv')
                        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(report.file_path)}"'
                        return response
                else:
                    return Response({'error': 'Report file not found'}, status=status.HTTP_404_NOT_FOUND)
            else:
                # Return status and link
                response_data = {
                    'status': 'Complete',
                }
                
                if report.google_drive_link:
                    response_data['google_drive_link'] = report.google_drive_link
                
                return Response(response_data, status=status.HTTP_200_OK)
        
        else:  # FAILED
            return Response({'status': 'Failed', 'error': 'Report generation failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except Report.DoesNotExist:
        return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)
