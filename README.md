# novafos

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)

The `novafos`component is a Home Assistant custom component for monitoring your water metering data from Novafos (via KMD)

*This version 1.x is not backwards compatible with the 0.x versions.  If you use 0.x versions and is happy with this do not update before reading this README.  Please remove the integration and add it again after updating.  I recommend to try out this version in a test instance of Home Assistant first bevore deciding to upgrade.*

*If something stops working, downgrade and file a bug.*


## Installation
---
### Manual Installation
  1. Copy novafos folder into your custom_components folder in your hass configuration directory.
  2. Configure the `novafos` sensor.
  3. Restart Home Assistant.

### Installation with HACS (Home Assistant Community Store)
  1. Ensure that [HACS](https://hacs.xyz/) is installed.
  2. Search for and install the `novafos` integration.
  3. Configure the `novafos` sensor.
  4. Restart Home Assistant.

## Configuration
---
Fully configurable through config flow.
  1. Head to configuration --> integration
  2. Add new and search for novafos
  3. Enter email address and pasword as registered with Novafos.
     If you haven't done this before you need to login using NemId/MitId and
     setup email and password first.
  4. Enter the supplier ID as well.  Until a better way to get this automatically is identified, you can get the value from inspecting the browser network traffic. See the next section.<br>
  
### Get the supplier id
  1. In chrome press F12, and select the "Network" tab.
  2. Login on the https://minforsyning-2.kmd.dk webpage.
  3. Inspect the first few entries.  You should see something along the lines of: *https://<6-digit number>.webtools.kmd.dk/wts/...*  The 6 digit number is your `supplier ID`.

## State and attributes
---
!Note! Data is delayed in the data warehouse.  Data validity will range from 24h to 5 days ago from today's midnight.  This means the sensor data represents historical data.

The integration creates the following sensors:
* sensor.novafos_year_total
  * The total consumption until the last valid date
* sensor.novafos_month_total
  * The total consumption current until the last valid date
* sensor.novafos_day_total
  * The total consumtion on the last valid date
  * Attributes contain day data since the first day of the month at the correct dates
* sensor.novafos_hour_total
  * The hourly consumption on the last valid date. The sensor will return unknown if the valid date is older than 24h
  * Attributes contain data from the last 24 hours on the correct date
* sensor.novafos_valid_date
  * Just the date of the last valid data

All water sensors show their value in cubic meters (m3).  The sensors also have extended attributes as outlined above, which can be used by ex. apexchart-card to chart data at the correct date.  You can also create new sensors from these attributes to save them in the history database.  Attributes are not saved in the history.

## Debugging
It is possible to debug log the raw response from KMD API. This is done by setting up logging like below in configuration.yaml in Home Assistant. It is also possible to set the log level through a service call in UI. Be aware that a lot of information is dumped to the log, so only have this activated when reporting a bug.
```
logger: 
  default: info
  logs: 
    custom_components.novafos: debug
```

## Examples

### Entity card with latest sensor data
This example is just an entity card with the latest data of all sensors.  It shows when the latest data was valid as a reference.

![alt text](images/example_1.png "Bar graph Example")

## Apexchart card with data placed at the correct date
This is a configuratio for the apexchart card.  Because data retrieved today may be at least 24 hours old, graphing the sensor state will put values on the wrong date.
If this is not wanted, the sensors also provide attributes with the data and the correct dates.  Apexchart can graph this.

TBD:
One caveat though is that attributes are not saved in the sensor history.  So what the module does is to fetch daily use from the start of the month, and hourly data 7 days back or so.  Then from the attributes it is at least possible to put daily and hourly use at the correct date.

The sensors still save daily and hourly values but remember these values are only as valid as the latest data available from the API.

```
type: custom:apexcharts-card
graph_span: 7d
span:
  end: day
  offset: '-1d'
header:
  show: true
  title: Water year to date
  show_states: true
  colorize_states: true
yaxis:
  - id: left
    decimals: 3
  - id: right
    opposite: true
    decimals: 2
series:
  - entity: sensor.novafos_day_total
    extend_to_end: false
    type: column
    yaxis_id: left
    data_generator: |
      return entity.attributes.data.map((start, index) => {
        return [new Date(start["DateTo"]).getTime(), entity.attributes.data[index]["Value"]];
      });
  - entity: sensor.novafos_hour
    extend_to_end: false
    yaxis_id: left
    type: column
    data_generator: |
      return entity.attributes.data.map((start, index) => {
        return [new Date(start["DateTo"]).getTime(), entity.attributes.data[index]["Value"]];
      });
  - entity: sensor.novafos_year_total
    type: column
    yaxis_id: right
    data_generator: >
      return [[new Date(entity.attributes.last_valid_date).getTime(),
      entity.state]]
  - entity: sensor.novafos_month_total
    type: column
    yaxis_id: right
    data_generator: >
      return [[new Date(entity.attributes.last_valid_date).getTime(),
      entity.attributes.data[0]["Value"]]]
```



---
## What is new in v1.x

The v1.x version changes the API endpoint used and the authentication method.  The API used is vastly simplified which makes it much easier to retrieve the data.
The update was triggered mainly because my data fetched from Novafos stopped in early 2022.  Looking at the website and the data I discovered two things: The last valid data had holes in them and were even 5 days old.  The 0.x version of this module assumes laways that the last valid data is 24 hours delayed.  Secondly I saw that the endpoint for fetching data had changed and that the data looked a lot more intuitive.

One thing I wanted to change as well was to put the data at the right date.  Home assistant sensors do not allow setting historical data at the correct point in time. Looking at sensor attributes and apexchart-card, I saw an opportunity to use attributes to put data at the correct date.

Another thing was the many sensors for 1 hour data.  I do not find a use for saving a sensor which will show me how much water was used at 02:00 over time.  I would however like a single sensor showing me the water used hour by hour.

There is a price to this still because while the sensor will 'reveal' data hour by hour, the data will be revealed at the wrong time due to how sensors work in Home Assistant.

Charting the last valid day at the right date using attributes is now possible.

Charting the water use day-by-day using attributes (for the correct date) or the sensor value is possible.

Charting the water use current month and year total is also possible.

Also added a sensor signalling the last valid date for the data.