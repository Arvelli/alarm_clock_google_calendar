# SPDX-FileCopyrightText: 2021 Brent Rubell, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
# SPDX-FileCopyrightText: 2021 Brent Rubell, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
import time
from adafruit_oauth2 import OAuth2
from adafruit_display_shapes.line import Line
from adafruit_pyportal import PyPortal
import rtc
from adafruit_bitmap_font import bitmap_font
import adafruit_datetime



# Set up the RTC
rtc_r = rtc.RTC()

# Calendar ID
CALENDAR_ID = "arvin.fazeli051214@gmail.com"

# Maximum amount of events to display
MAX_EVENTS = 5

# Amount of time to wait between refreshing the calendar, in minutes
REFRESH_TIME = 15

MONTHS = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}

# Dict. of day names for pretty-printing the header
WEEKDAYS = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}

# Add a secrets.py to your filesystem that has a dictionary called
# "password" keys with your WiFi credentials. DO NOT share that file
# source control.
# pylint: disable=no-name-in-module,wrong-import-order
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Create the PyPortal object
pyportal = PyPortal()

# Connect to the network
pyportal.network.connect()

# Initialize an OAuth2 object with GCal API scope
scopes = ["https://www.googleapis.com/auth/calendar.readonly"]
google_auth = OAuth2(
    pyportal.network.requests,
    secrets["google_client_id"],
    secrets["google_client_secret"],
    scopes,
    secrets["google_access_token"],
    secrets["google_refresh_token"],
)

# fetch calendar events!
print("fetching local time...")
pyportal.get_local_time(secrets["timezone"])

# Play a WAV file
def play_alarm():
    print("Playing WAV file...")
    pyportal.play_file("Iphone Alarm Sound Effect.wav", wait_to_finish=False)

def get_current_time(time_max=False):
    """Gets local time from the real-time clock and converts to  timestamp."""
    # Get local time from the real-time clock

    # Get local time from Adafruit IO
    #pyportal.get_local_time(secrets["timezone"])

    cur_time = rtc_r.datetime

    if time_max:
     
        cur_datetime = adafruit_datetime.datetime(*cur_time[:6]) # Convert cur_time tuple to datetime object
        
        cur_datetime += adafruit_datetime.timedelta(days=1) # Add 1 day to the current datetime
        
        cur_time_max = cur_datetime.timetuple()  # Convert back to struct_time
        
        cur_time = cur_time_max

    cur_time = "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}{:s}".format(
        cur_time[0],
        cur_time[1],
        cur_time[2],
        cur_time[3],
        cur_time[4],
        cur_time[5],
        "Z",
    )
    return cur_time




def get_calendar_events(calendar_id, max_events, time_min):
    """Returns events on a specified calendar.
    Response is a list of events ordered by their start date/time in ascending order.
    """
    time_max = get_current_time(time_max=True)
    print("Fetching calendar events from {0} to {1}".format(time_min, time_max))

    headers = {
        "Authorization": "Bearer " + google_auth.access_token,
        "Accept": "application/json",
        "Content-Length": "0",
    }
    url = (
        "https://www.googleapis.com/calendar/v3/calendars/{0}"
        "/events?maxResults={1}&timeMin={2}&timeMax={3}&orderBy=startTime"
        "&singleEvents=true".format(calendar_id, max_events, time_min, time_max)
    )
    resp = pyportal.network.requests.get(url, headers=headers)
    resp_json = resp.json()

    if "error" in resp_json:
        raise RuntimeError("Error:", resp_json)
    resp.close()

    # Parse events
    events = resp_json.get("items", [])


    # Extract start time of the first event
    first_event_start_time = None
    if events:
        first_event_start_time = events[0].get("start", {}).get("dateTime")
        print("first_event::",first_event_start_time)


    # Log events
    print("Number of events:", len(events))
    for event in events:
        print("Event Summary:", event.get("summary"))
        print("Event Start Time:", event.get("start", {}).get("dateTime"))

    return first_event_start_time, events

def get_wakeup_time(calendar_id, max_events, time_min):
    first_event_start_time, _ = get_calendar_events(calendar_id, max_events, time_min)

    if first_event_start_time:
        # Given timestamp
        timestamp = adafruit_datetime.datetime.fromisoformat(first_event_start_time)

        # Create a timedelta object representing 60 minutes
        delta = adafruit_datetime.timedelta(minutes=60)

        # Subtract the timedelta from the timestamp
        wakeup_time = timestamp - delta
        print("wakeup_time:", wakeup_time)

        return wakeup_time
    else:
        return None  # Return None if no events found or if first_event_start_time is None


def format_datetime(datetime, pretty_date=False):
    """Formats ISO-formatted datetime returned by Google Calendar API into_time."""
    # Example datetime format from Google Calendar API: "2024-02-01T12:34:56Z"
    year, month, day = map(int, datetime[:10].split("-"))
    hours, minutes, seconds = map(int, datetime[11:19].split(":"))

    formatted_time = "{:01d}:{:02d}{:s}".format(
        hours % 12 or 12,  # Convert hours to 12-hour format
        minutes,
        "am" if hours < 12 else "pm"  # Determine AM/PM
    )

    if pretty_date:
        formatted_date = "{} {}. {:02d}, {:04d} ".format(
            WEEKDAYS[rtc_r.datetime[6]], MONTHS[month], day, year
        )  # Fixed 'r' to 'rtc_r' here
        return formatted_date

    return formatted_time



def create_event_labels():
    for event_idx in range(MAX_EVENTS):
        event_start_label = pyportal.add_text(
            text_font=font_events,
            text_position=(7, 70 + (event_idx * 40)),
            text_color=0x000000,
        )
        event_text_label = pyportal.add_text(
            text_font=font_events,
            text_position=(88, 70 + (event_idx * 40)),
            text_color=0x000000,
            line_spacing=0.75,
        )
        event_labels.append((event_start_label, event_text_label))


def display_calendar_events(events_tuple):
    first_event_start_time, events = events_tuple  # Unpack the tuple

    # Display all calendar events
    for event_idx in range(len(events)):
        event = events[event_idx]
        # wrap event name around second line if necessary
        event_name = PyPortal.wrap_nicely(event["summary"], 25)
        event_name = "\n".join(event_name[0:2])  # only wrap 2 lines, truncate third..
        event_start = event["start"]["dateTime"]
        print("-" * 40)
        print("Event Description: ", event_name)
        print("Event Time:", format_datetime(event_start))
        print("-" * 40)
        pyportal.set_text(format_datetime(event_start), event_labels[event_idx][0])
        pyportal.set_text(event_name, event_labels[event_idx][1])

    # Clear any unused labels
    for event_idx in range(len(events), MAX_EVENTS):
        pyportal.set_text("", event_labels[event_idx][0])
        pyportal.set_text("", event_labels[event_idx][1])


pyportal.set_background(0xFFFFFF)

# Set up calendar event fonts
font_events = "fonts/Nunito-Black-17.bdf"

# Add the header
line_header = Line(0, 50, 320, 50, color=0x000000)
pyportal.splash.append(line_header)

label_header = pyportal.add_text(
    text_font="fonts/Nunito-Black-17.bdf",
    text_position=(10, 30),
    text_color=0x000000,
)
event_labels = []
create_event_labels()

if not google_auth.refresh_access_token():
    raise RuntimeError("Unable to refresh access token - has the token been revoked?")
access_token_obtained = int(time.monotonic())
print("acc token obt",access_token_obtained)
# Add the header
line_header = Line(0, 50, 320, 50, color=0x000000)
pyportal.splash.append(line_header)

label_header = pyportal.add_text(
    text_font="fonts/Nunito-Black-17.bdf",
    text_position=(10, 30),
    text_color=0x000000,
)
event_labels = []
create_event_labels()

clock_label = pyportal.add_text(
    text_font="fonts/Nunito-Black-17.bdf",
    text_position=(325, 30),  # Adjust the position as needed
    text_anchor_point=(1, 0),  # Top-right corner
    text_color=0x000000,
)

events = []
last_second = None



while True:
    current_time = time.monotonic()
    # Check if a second has passed
    if int(current_time) != last_second:
        # Update the clock display every second
        last_second = int(current_time)

        # Display real-time clock
        rtc_time = rtc_r.datetime
        clock_str = "{:02d}:{:02d}".format(rtc_time[3], rtc_time[4])
        pyportal.set_text(clock_str, clock_label)

        # Convert timestamp to ISO format
        correct_clock = "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
        rtc_time[0], rtc_time[1], rtc_time[2], rtc_time[3], rtc_time[4], rtc_time[5]
        )

    # check if we need to refresh token
    # print("google acc token exp",google_auth.access_token_expiration)
    
    if (int(time.monotonic()) - access_token_obtained >= google_auth.access_token_expiration):
        print("Access token expired, refreshing...")
        if not google_auth.refresh_access_token():
            raise RuntimeError(
                "Unable to refresh access token - has the token been revoked?"
            )
        access_token_obtained = int(current_time)

    # fetch calendar events!
    print("fetching local time...")
    now = get_current_time()

    # setup header label
    pyportal.set_text(format_datetime(now, pretty_date=True), label_header)

    print("fetching calendar events...")
    events = get_calendar_events(CALENDAR_ID, MAX_EVENTS, now)

    print("displaying events")
    display_calendar_events(events)

    print("clock_str", clock_str)
    
    print("correct_clock", correct_clock)
    

    # Check if the current time matches the wake-up time
    wakeup_time = get_wakeup_time(CALENDAR_ID, MAX_EVENTS, now)

    if wakeup_time is not None and correct_clock == wakeup_time:
        # Play the WAV file
        pyportal.play_file("alarm.wav", wait_to_finish=False)


    print("Sleeping for %d seconds" % 30)  # Sleep for 1 second
    time.sleep(30)

