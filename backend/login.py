import urllib.parse
import getpass
from arcgis.gis import GIS

def generate_oauth_url(client_id: str, portal_url: str = "https://cmad.maps.arcgis.com") -> str:
    redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": "my_state",  # In production, use a randomly generated state
        "allow_verification": "false"
    }
    base_url = f"{portal_url}/sharing/rest/oauth2/authorize"
    url = base_url + "?" + urllib.parse.urlencode(params)
    return url

def arcgis_login(client_id: str, code: str = None, portal_url: str = "https://cmad.maps.arcgis.com"):
    print("Starting OAuth login process...")
    if code:
        print(f"Using provided code: {code}")
        # Monkey-patch getpass.getpass so it returns the provided code
        getpass.getpass = lambda prompt='': code
    else:
        print("No approval code provided; launching browser for OAuth.")
    gis = GIS(portal_url, client_id=client_id, authorize=True)
    if gis.users.me:
        print(f"✅ Login successful. Welcome, {gis.users.me.fullName} ({gis.users.me.username})")
        return gis
    else:
        print("❌ Login failed.")
        return None
