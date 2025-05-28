```python
import requests
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import json
import html

# Configuration from provided inputs
api_base_url = "https://api.heygen.com"
api_endpoints = {
    'list_videos': '/v1/videos',
    'video_status': '/v1/video_status.get'
}
refresh_interval_seconds = 5 * 60  # "Every 5 minutes" converted to seconds

# Dashboard template parts from dashboard_template input
html_template_sentinel = 'html_template_sentinel'
html_template_content = '</html>'
# The model schema JSON is not directly used for rendering but defines data structure

# Global variable to hold the latest generated dashboard HTML
dashboard_html = ""
dashboard_html_lock = threading.Lock()

# Function to fetch list of videos from HeyGen API
def fetch_videos():
    """
    Fetches the list of videos from the HeyGen API.
    Returns a list of video dicts as returned by the API.
    """
    url = api_base_url + api_endpoints['list_videos']
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # Assuming the API returns a JSON object with a list of videos under a key, e.g. 'videos'
        # Since no exact API response format is given, assume the response itself is a list of videos
        # or contains 'videos' key. Adjust accordingly.
        if isinstance(data, dict) and 'videos' in data:
            return data['videos']
        elif isinstance(data, list):
            return data
        else:
            return []
    except Exception as e:
        print(f"Error fetching videos: {e}")
        return []

# Function to transform API video data to VideoStatus objects as per dashboard_data_model
def transform_video_data(api_videos):
    """
    Transforms raw API video data into a list of VideoStatus dicts matching the dashboard model.
    Each VideoStatus object must have:
    - id (string)
    - title (string)
    - template_name (string)
    - voice_name (string)
    - status (string)
    - created_at (string)
    - completed_at (string or null)
    - thumbnail_url (string or null)
    - video_url (string or null)
    - duration (string or null)
    
    Since the exact API response fields are unknown, this function maps common fields and
    uses placeholders or nulls where data is missing.
    """
    video_status_list = []
    for v in api_videos:
        video_status = {
            "id": str(v.get("id", "")),
            "title": v.get("title", "Untitled"),
            "template_name": v.get("template_name", "Unknown Template"),
            "voice_name": v.get("voice_name", "Unknown Voice"),
            "status": v.get("status", "unknown"),
            "created_at": v.get("created_at", ""),
            "completed_at": v.get("completed_at") if v.get("completed_at") is not None else None,
            "thumbnail_url": v.get("thumbnail_url") if v.get("thumbnail_url") is not None else None,
            "video_url": v.get("video_url") if v.get("video_url") is not None else None,
            "duration": v.get("duration") if v.get("duration") is not None else None,
        }
        video_status_list.append(video_status)
    return video_status_list

# Function to compute API usage stats from video list
def compute_api_usage_stats(videos):
    """
    Computes ApiUsageStats object from the list of videos.
    Fields:
    - total_videos (int)
    - completed_videos (int)
    - processing_videos (int)
    - failed_videos (int)
    - monthly_quota (int) - unknown, set to 1000 as example
    - remaining_quota (int) - monthly_quota - total_videos
    - usage_percentage (float) - (total_videos / monthly_quota) * 100
    
    Since no API usage endpoint or quota info is provided, this is a mock calculation.
    """
    total = len(videos)
    completed = sum(1 for v in videos if v.get("status") == "completed")
    processing = sum(1 for v in videos if v.get("status") == "processing")
    failed = sum(1 for v in videos if v.get("status") == "failed")
    monthly_quota = 1000
    remaining = max(monthly_quota - total, 0)
    usage_percentage = (total / monthly_quota) * 100 if monthly_quota > 0 else 0.0

    return {
        "total_videos": total,
        "completed_videos": completed,
        "processing_videos": processing,
        "failed_videos": failed,
        "monthly_quota": monthly_quota,
        "remaining_quota": remaining,
        "usage_percentage": round(usage_percentage, 2)
    }

# Function to generate dashboard HTML from data model
def generate_dashboard_html(dashboard_data):
    """
    Generates an HTML dashboard page string from the dashboard_data dict.
    The dashboard_data contains:
    - videos: list of VideoStatus dicts
    - api_usage: ApiUsageStats dict
    - last_updated: timestamp string
    
    The HTML includes:
    - API usage summary
    - Table of videos with key info
    - Auto-refresh meta tag based on refresh_interval_seconds
    """
    # Escape all text to prevent HTML injection
    def esc(text):
        return html.escape(str(text)) if text is not None else ""

    api_usage = dashboard_data['api_usage']
    videos = dashboard_data['videos']
    last_updated = dashboard_data['last_updated']

    refresh_seconds = refresh_interval_seconds

    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "  <meta charset='UTF-8'>",
        f"  <meta http-equiv='refresh' content='{refresh_seconds}'>",
        "  <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
        "  <title>HeyGen Video Dashboard</title>",
        "  <style>",
        "    body { font-family: Arial, sans-serif; margin: 20px; background: #f9f9f9; }",
        "    h1 { color: #333; }",
        "    table { border-collapse: collapse; width: 100%; background: white; }",
        "    th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }",
        "    th { background-color: #eee; }",
        "    tr:nth-child(even) { background-color: #f2f2f2; }",
        "    .status-completed { color: green; font-weight: bold; }",
        "    .status-processing { color: orange; font-weight: bold; }",
        "    .status-failed { color: red; font-weight: bold; }",
        "  </style>",
        "</head>",
        "<body>",
        "  <h1>HeyGen Video Dashboard</h1>",
        f"  <p>Last Updated: {esc(last_updated)}</p>",
        "  <h2>API Usage Stats</h2>",
        "  <ul>",
        f"    <li>Total Videos: {esc(api_usage['total_videos'])}</li>",
        f"    <li>Completed Videos: {esc(api_usage['completed_videos'])}</li>",
        f"    <li>Processing Videos: {esc(api_usage['processing_videos'])}</li>",
        f"    <li>Failed Videos: {esc(api_usage['failed_videos'])}</li>",
        f"    <li>Monthly Quota: {esc(api_usage['monthly_quota'])}</li>",
        f"    <li>Remaining Quota: {esc(api_usage['remaining_quota'])}</li>",
        f"    <li>Usage Percentage: {esc(api_usage['usage_percentage'])}%</li>",
        "  </ul>",
        "  <h2>Videos</h2>",
        "  <table>",
        "    <thead>",
        "      <tr>",
        "        <th>Title</th>",
        "        <th>Template</th>",
        "        <th>Voice</th>",
        "        <th>Status</th>",
        "        <th>Created At</th>",
        "        <th>Completed At</th>",
        "        <th>Duration</th>",
        "        <th>Thumbnail</th>",
        "        <th>Video Link</th>",
        "      </tr>",
        "    </thead>",
        "    <tbody>"
    ]

    for v in videos:
        status_class = ""
        status_lower = v.get("status", "").lower()
        if status_lower == "completed":
            status_class = "status-completed"
        elif status_lower == "processing":
            status_class = "status-processing"
        elif status_lower == "failed":
            status_class = "status-failed"

        thumbnail_html = (f"<img src='{esc(v['thumbnail_url'])}' alt='Thumbnail' width='120'>" 
                          if v.get("thumbnail_url") else "N/A")
        video_link_html = (f"<a href='{esc(v['video_url'])}' target='_blank'>Watch</a>" 
                           if v.get("video_url") else "N/A")

        html_parts.extend([
            "      <tr>",
            f"        <td>{esc(v['title'])}</td>",
            f"        <td>{esc(v['template_name'])}</td>",
            f"        <td>{esc(v['voice_name'])}</td>",
            f"        <td class='{status_class}'>{esc(v['status'])}</td>",
            f"        <td>{esc(v['created_at'])}</td>",
            f"        <td>{esc(v['completed_at']) if v['completed_at'] else 'N/A'}</td>",
            f"        <td>{esc(v['duration']) if v['duration'] else 'N/A'}</td>",
            f"        <td>{thumbnail_html}</td>",
            f"        <td>{video_link_html}</td>",
            "      </tr>"
        ])

    html_parts.extend([
        "    </tbody>",
        "  </table>",
        html_template_content  # '</html>'
    ])

    return "\n".join(html_parts)

# Background thread function to periodically refresh dashboard data and HTML
def refresh_dashboard_periodically():
    """
    Periodically fetches video data, transforms it, generates dashboard HTML,
    and updates the global dashboard_html variable.
    Runs every refresh_interval_seconds.
    """
    global dashboard_html
    while True:
        try:
            # Step 1: Fetch videos from API
            api_videos = fetch_videos()

            # Step 2: Transform API response to dashboard data model
            videos = transform_video_data(api_videos)
            api_usage = compute_api_usage_stats(videos)
            last_updated = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

            dashboard_data = {
                "videos": videos,
                "api_usage": api_usage,
                "last_updated": last_updated
            }

            # Step 3: Generate dashboard HTML
            new_html = generate_dashboard_html(dashboard_data)

            # Step 4: Update global dashboard HTML safely
            with dashboard_html_lock:
                dashboard_html = new_html

            print(f"[{datetime.utcnow().isoformat()}] Dashboard refreshed successfully.")
        except Exception as e:
            print(f"Error during dashboard refresh: {e}")

        time.sleep(refresh_interval_seconds)

# HTTP request handler to serve the dashboard HTML
class DashboardRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """
        Handles GET requests by serving the latest dashboard HTML.
        """
        if self.path == "/" or self.path == "/index.html":
            with dashboard_html_lock:
                content = dashboard_html or "<html><body><h1>Loading dashboard...</h1></body></html>"
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        else:
            # For any other path, respond with 404 Not Found
            self.send_response(404)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"404 Not Found")

def run_server(host="0.0.0.0", port=8000):
    """
    Starts the HTTP server to serve the dashboard.
    """
    server_address = (host, port)
    httpd = HTTPServer(server_address, DashboardRequestHandler)
    print(f"Serving dashboard at http://{host}:{port}/")
    httpd.serve_forever()

if __name__ == "__main__":
    # Initial dashboard HTML to show while first fetch completes
    with dashboard_html_lock:
        dashboard_html = "<html><body><h1>Loading dashboard data, please wait...</h1></body></html>"

    # Start background thread to refresh dashboard periodically
    refresh_thread = threading.Thread(target=refresh_dashboard_periodically, daemon=True)
    refresh_thread.start()

    # Start HTTP server (blocking call)
    run_server()
```