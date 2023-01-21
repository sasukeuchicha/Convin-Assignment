from django.shortcuts import redirect

from rest_framework.decorators import api_view
from rest_framework.response import Response

import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import os

# Insecure Transport error thing
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Google API service name
API_SERVICE_NAME = 'calendar'
API_VERSION = 'v3'

# Get credentials that contain ID and secret key of OAuth https://console.cloud.google.com/
OAUTH_CLIENT_ID_AND_SECRET = "cred.json"

# Scope parameters used to provide read and write access to account and redirect url
SCOPES = ['https://www.googleapis.com/auth/calendar',
          'https://www.googleapis.com/auth/userinfo.email',
          'https://www.googleapis.com/auth/userinfo.profile',
          'openid']

#Redirect URL
REDIRECT_URL = 'http://127.0.0.1:8000/calender/v1/calendar/redirect/'


@api_view(['GET'])
def GoogleCalendarInitView(request):
    # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(OAUTH_CLIENT_ID_AND_SECRET, scopes=SCOPES)
    flow.redirect_uri = REDIRECT_URL

    # Disable re-prompts from google for permission to access
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')

    # auth server response state verified
    request.session['state'] = state

    return Response({"Url_created": authorization_url})


@api_view(['GET'])
def GoogleCalendarRedirectView(request):
    # Specify the state when creating the flow in the callback so that it can
    # verified in the authorization server response.
    state = request.session['state']
    

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(OAUTH_CLIENT_ID_AND_SECRET, scopes=SCOPES, state=state)
    flow.redirect_uri = REDIRECT_URL

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response = request.get_full_path()
    flow.fetch_token(authorization_response=authorization_response)

    # Save credentials back to session in case access token was refreshed
    credentials = flow.credentials
    # add credentials to session
    request.session['credentials'] = credentials_to_dict(credentials)

    # Check if credentials are in session
    if 'credentials' not in request.session:
        return redirect('v1/calendar/init')

    # Load credentials from the session.
    credentials = google.oauth2.credentials.Credentials(
        **request.session['credentials'])

    # google api discovery
    service = googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

    # Returns the calendars on the user's calendar list
    calendar_list = service.calendarList().list().execute()

    # Get user ID 
    calendar_id = calendar_list['items'][0]['id']

    # Get events from id
    events  = service.events().list(calendarId=calendar_id).execute()

    event_list = []
    if events['items'] == None:
        print('No data found.')
        return Response({"message": "No data found or user credentials invalid."})
    else:
        for event in events['items']:
            event_list.append(event)
            return Response({"events": event_list})
    return Response({"error": "calendar event aren't here"})


def credentials_to_dict(credentials):
  return {'token': credentials.token,
          'refresh_token': credentials.refresh_token,
          'token_uri': credentials.token_uri,
          'client_id': credentials.client_id,
          'client_secret': credentials.client_secret,
          'scopes': credentials.scopes}
