from arcgis.gis import GIS

def arcgis_login(client_id: str, portal_url: str = "https://cmad.maps.arcgis.com"):
    """
    Prompts user for an OAuth login using out-of-band or local server flow.
    Returns an authenticated GIS object if successful, or None if login fails.
    """
    print("Opening browser for secure login...")
    gis = GIS(portal_url, client_id=client_id, authorize=True)

    if gis.users.me:
        print(f"✅ Login successful. Welcome, {gis.users.me.fullName} ({gis.users.me.username})")
        return gis
    else:
        print("❌ Login failed.")
        return None
