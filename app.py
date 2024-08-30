import streamlit as st
from streamlit_js_eval import get_geolocation, streamlit_js_eval
import requests
from datetime import datetime, time
import overpy
from geopy.distance import geodesic

st.set_page_config(page_title="Azan Times", page_icon="🕌", layout="centered")

st.title("🕌 Azan Times")

# Function to find the nearest mosque
def find_nearest_mosque(lat, lon, radius=1000):
    api = overpy.Overpass()
    query = f"""
    [out:json];
    (
      node["amenity"="place_of_worship"]["religion"="muslim"](around:{radius},{lat},{lon});
      way["amenity"="place_of_worship"]["religion"="muslim"](around:{radius},{lat},{lon});
      relation["amenity"="place_of_worship"]["religion"="muslim"](around:{radius},{lat},{lon});
    );
    out center;
    """
    result = api.query(query)
    
    nearest_mosque = None
    min_distance = float('inf')
    
    for element in result.nodes + result.ways + result.relations:
        if hasattr(element, 'center_lat') and hasattr(element, 'center_lon'):
            mosque_lat, mosque_lon = element.center_lat, element.center_lon
        elif hasattr(element, 'lat') and hasattr(element, 'lon'):
            mosque_lat, mosque_lon = element.lat, element.lon
        else:
            continue
        
        distance = geodesic((lat, lon), (mosque_lat, mosque_lon)).meters
        if distance < min_distance:
            min_distance = distance
            nearest_mosque = element
    
    if nearest_mosque:
        name = nearest_mosque.tags.get('name', 'Unnamed Mosque')
        return name, min_distance
    return None, None

# Function to determine the current prayer time
def get_current_prayer(timings, current_time):
    prayer_times = {
        "Fajr": datetime.strptime(timings["Fajr"], "%H:%M").time(),
        "Sunrise": datetime.strptime(timings["Sunrise"], "%H:%M").time(),
        "Dhuhr": datetime.strptime(timings["Dhuhr"], "%H:%M").time(),
        "Asr": datetime.strptime(timings["Asr"], "%H:%M").time(),
        "Maghrib": datetime.strptime(timings["Maghrib"], "%H:%M").time(),
        "Isha": datetime.strptime(timings["Isha"], "%H:%M").time(),
    }
    
    current_prayer = "Isha"  # Default to Isha if it's after Isha but before Fajr
    for prayer, prayer_time in prayer_times.items():
        if current_time < prayer_time:
            return current_prayer
        current_prayer = prayer
    return current_prayer

# Get user's local time using JavaScript
user_time_str = streamlit_js_eval(js_expressions='new Date().toLocaleString()', key='current_time')
if user_time_str:
    user_time = datetime.strptime(user_time_str, "%m/%d/%Y, %I:%M:%S %p")
else:
    user_time = datetime.now()  # Fallback to server time if JS eval fails

# Use get_geolocation to obtain user's location
location = get_geolocation()

# Use session state to store location
if 'location' not in st.session_state:
    st.session_state.location = ''

if location:
    # Update session state with new location
    st.session_state.location = f"{location['coords']['latitude']},{location['coords']['longitude']}"

# Display and get the location coordinates
user_location = st.text_input("Your coordinates (latitude,longitude):", 
                              value=st.session_state.location, 
                              key="location_input")

# Update session state if user input changes
if user_location != st.session_state.location:
    st.session_state.location = user_location

# Fetch and display prayer times if location is available
if user_location and ',' in user_location:
    lat, lon = map(float, user_location.split(','))
    today = user_time.strftime("%d-%m-%Y")
    try:
        response = requests.get(
            f"http://api.aladhan.com/v1/timings/{today}",
            params={
                "latitude": lat,
                "longitude": lon,
                "method": 11,  # Majlis Ugama Islam Singapura, Singapore
            }
        )
        data = response.json()
        if data['code'] == 200:
            timings = data['data']['timings']
            date = data['data']['date']['readable']
            
            st.success(f"Prayer Times for {date}")
            
            current_prayer = get_current_prayer(timings, user_time.time())
            st.info(f"Current prayer time: {current_prayer}")
            
            col1, col2 = st.columns(2)
            
            prayer_icons = {
                "Fajr": "🌄", "Sunrise": "🌅", "Dhuhr": "☀️", 
                "Asr": "🌇", "Sunset": "🌆", "Maghrib": "🌙", "Isha": "🌠"
            }
            
            for i, (prayer, time) in enumerate(timings.items()):
                if prayer in prayer_icons:
                    if i % 2 == 0:
                        with col1:
                            st.metric(label=f"{prayer_icons[prayer]} {prayer}", value=time)
                    else:
                        with col2:
                            st.metric(label=f"{prayer_icons[prayer]} {prayer}", value=time)
            
            # Find nearest mosque
            st.write("Checking for nearby mosques...")
            progress_bar = st.progress(0)
            for i in range(100):
                progress_bar.progress(i + 1)
            
            mosque_name, distance = find_nearest_mosque(lat, lon)
            
            if mosque_name and distance:
                st.success(f"Nearest mosque: {mosque_name}")
                st.info(f"Distance: {distance:.2f} meters")
            else:
                st.info("No mosques found within 1km radius.")
            
        else:
            st.error(f"Failed to fetch prayer times. Error: {data.get('status', 'Unknown error')}")
    except requests.RequestException as e:
        st.error(f"An error occurred: {e}")
else:
    st.info("Click 'Allow' when prompted for location access, or enter coordinates manually.")

# Add a button to manually refresh the app
if st.button('Refresh'):
    st.rerun()

# Add a footer
st.markdown("---")
st.markdown("Made with ❤️ using Streamlit")
