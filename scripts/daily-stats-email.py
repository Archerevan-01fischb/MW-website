#!/usr/bin/env python3
"""
Midwinter Website - Daily Stats Email
Fetches Cloudflare analytics and emails a daily summary.

Run via cron: 0 8 * * * /usr/bin/python3 /share/Web/scripts/daily-stats-email.py
"""

import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import json

# Configuration
CLOUDFLARE_API_TOKEN = "4ipjGhHGJbZaGPBgNPaFWueyXGIJBcPYUx_ZfFff"
CLOUDFLARE_ZONE_ID = "1d1f39d4951022f40f1e4a0a34a5cbe6"

GMAIL_USER = "lane01evan@gmail.com"
GMAIL_PASS = "onkojkqiecgkktbo"
RECIPIENT_EMAIL = "lane01evan@gmail.com"

SITE_NAME = "Midwinter Remaster"
SITE_URL = "midwinter-remaster.titanium-helix.com"


def get_cloudflare_stats():
    """Fetch analytics from Cloudflare GraphQL API"""

    # Get yesterday's date range
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    # GraphQL query for zone analytics
    query = """
    query {
      viewer {
        zones(filter: {zoneTag: "%s"}) {
          httpRequests1dGroups(
            limit: 1
            filter: {date_geq: "%s", date_leq: "%s"}
          ) {
            sum {
              requests
              pageViews
              bytes
              threats
              countryMap {
                clientCountryName
                requests
              }
            }
            uniq {
              uniques
            }
          }
        }
      }
    }
    """ % (CLOUDFLARE_ZONE_ID, start_date, end_date)

    response = requests.post(
        "https://api.cloudflare.com/client/v4/graphql",
        headers=headers,
        json={"query": query}
    )

    if response.status_code == 200:
        return response.json(), start_date
    else:
        return None, start_date


def format_bytes(bytes_val):
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} TB"


def build_email(stats, date):
    """Build the email content"""

    subject = f"[{SITE_NAME}] Daily Stats - {date}"

    if stats and 'data' in stats:
        try:
            zone_data = stats['data']['viewer']['zones'][0]['httpRequests1dGroups'][0]

            requests = zone_data['sum']['requests']
            page_views = zone_data['sum']['pageViews']
            bandwidth = format_bytes(zone_data['sum']['bytes'])
            unique_visitors = zone_data['uniq']['uniques']
            threats = zone_data['sum']['threats']

            # Top countries
            countries = zone_data['sum']['countryMap']
            countries_sorted = sorted(countries, key=lambda x: x['requests'], reverse=True)[:5]
            country_list = "\n".join([f"  - {c['clientCountryName']}: {c['requests']} requests" for c in countries_sorted])

            body = f"""
Daily Statistics for {SITE_NAME}
Date: {date}
URL: https://{SITE_URL}

====================================
TRAFFIC SUMMARY
====================================

Unique Visitors:  {unique_visitors:,}
Page Views:       {page_views:,}
Total Requests:   {requests:,}
Bandwidth Used:   {bandwidth}
Threats Blocked:  {threats:,}

====================================
TOP COUNTRIES
====================================
{country_list}

====================================

View full analytics:
https://dash.cloudflare.com/9504dae56d20fac3973b2b9d01c54daf/titanium-helix.com/analytics/web/overview

--
Automated report from Midwinter Website
"""
        except (KeyError, IndexError) as e:
            body = f"""
Daily Statistics for {SITE_NAME}
Date: {date}

Unable to parse analytics data.
Error: {str(e)}

Raw response:
{json.dumps(stats, indent=2)[:1000]}

View analytics directly:
https://dash.cloudflare.com/9504dae56d20fac3973b2b9d01c54daf/titanium-helix.com/analytics/web/overview
"""
    else:
        body = f"""
Daily Statistics for {SITE_NAME}
Date: {date}

Could not fetch Cloudflare analytics.
Please check your API token permissions.

View analytics directly:
https://dash.cloudflare.com/9504dae56d20fac3973b2b9d01c54daf/titanium-helix.com/analytics/web/overview
"""

    return subject, body


def send_email(subject, body):
    """Send email via Gmail SMTP"""

    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_PASS)
        server.sendmail(GMAIL_USER, RECIPIENT_EMAIL, msg.as_string())
        server.quit()
        print(f"Email sent successfully to {RECIPIENT_EMAIL}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def main():
    print(f"Fetching Cloudflare stats for {SITE_URL}...")
    stats, date = get_cloudflare_stats()

    print("Building email...")
    subject, body = build_email(stats, date)

    print("Sending email...")
    send_email(subject, body)


if __name__ == "__main__":
    main()
