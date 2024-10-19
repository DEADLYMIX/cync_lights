import logging
from homeassistant import config_entries
import voluptuous as vol
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv
from .const import DOMAIN
from .cync_hub import CyncUserData

_LOGGER = logging.getLogger(__name__)

class CyncConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Cync Room Lights."""

    def __init__(self):
        self.cync_hub = CyncUserData()
        self.data = {}
        self.options = {}

    VERSION = 1

    async def async_step_user(self, user_input=None):
        # Handle user step logic here...
        pass

    async def async_step_select_switches(self, user_input=None):
        """Step to allow selection of switches, sensors, etc."""
        try:
            # Log the entire entry object
            _LOGGER.debug(f"Entry Object: {getattr(self, 'entry', None)}")

            # Log all available data keys and values to identify missing or empty keys
            if hasattr(self, 'entry') and hasattr(self.entry, 'data'):
                _LOGGER.debug(f"Entry Data Keys: {list(self.entry.data.keys())}")
                _LOGGER.debug(f"Entry Data Values: {self.entry.data}")

            # Check if self.entry.data has expected key structure
            if 'cync_config' not in self.entry.data:
                _LOGGER.error(f"'cync_config' key is missing in self.entry.data: {self.entry.data}")
                raise KeyError("cync_config")

            cync_config = self.entry.data['cync_config']

            if 'rooms' not in cync_config:
                _LOGGER.error(f"'rooms' key is missing in cync_config: {cync_config}")
                raise KeyError("rooms")

            rooms = cync_config['rooms']

            if 'devices' not in cync_config:
                _LOGGER.error(f"'devices' key is missing in cync_config: {cync_config}")
                raise KeyError("devices")

            devices = cync_config['devices']

            # Log valid devices
            valid_devices = self._get_wifi_connected_devices()
            _LOGGER.debug(f"Valid WiFi Devices: {valid_devices}")

            if not valid_devices:
                raise InvalidCyncConfiguration(
                    "Invalid or unsupported Cync configuration, please ensure there is at least one WiFi connected Cync device in your Home(s)."
                )

            # Create schema for form selection
            switches_data_schema = vol.Schema(
                {
                    vol.Optional("rooms", description={"suggested_value": []}): cv.multi_select({
                        room: f"{room_info.get('parent_room', '')}: {room_info['home_name']}"
                        for room, room_info in rooms.items()
                        if room_info.get('isSubgroup', False)
                    }),
                    vol.Optional("switches", description={"suggested_value": []}): cv.multi_select({
                        switch_id: f"{sw_info.get('name', 'unknown')} ({sw_info.get('room_name', 'unknown')}: {sw_info.get('home_name', 'unknown')})"
                        for switch_id, sw_info in valid_devices.items()
                        if self._is_valid_device(sw_info, 'ONOFF')
                    }),
                    vol.Optional("motion_sensors", description={"suggested_value": []}): cv.multi_select({
                        device_id: f"{device_info.get('name', 'unknown')} ({device_info.get('room_name', 'unknown')}: {device_info.get('home_name', 'unknown')})"
                        for device_id, device_info in valid_devices.items()
                        if self._is_valid_device(device_info, 'MOTION')
                    }),
                    vol.Optional("ambient_light_sensors", description={"suggested_value": []}): cv.multi_select({
                        device_id: f"{device_info.get('name', 'unknown')} ({device_info.get('room_name', 'unknown')}: {device_info.get('home_name', 'unknown')})"
                        for device_id, device_info in valid_devices.items()
                        if self._is_valid_device(device_info, 'AMBIENT_LIGHT')
                    }),
                }
            )

        except KeyError as e:
            _LOGGER.error(f"KeyError: Missing or empty key '{e}' in device configuration.")
            _LOGGER.debug(f"self.entry.data at KeyError: {self.entry.data}")
            raise InvalidCyncConfiguration(f"Device configuration is missing or has an empty key: {e}")

        except Exception as e:
            _LOGGER.error(f"Unexpected error: {str(e)}")
            raise InvalidCyncConfiguration(f"Error in configuration: {str(e)}")

        return self.async_show_form(step_id="select_switches", data_schema=switches_data_schema)

    def _get_wifi_connected_devices(self):
        """Filter and return only devices that are connected via WiFi."""
        devices = self.entry.data.get("cync_config", {}).get("devices", {})
        valid_devices = {}

        for device_id, device_info in devices.items():
            _LOGGER.debug(f"Inspecting device: {device_info.get('name', 'unknown')}")
            _LOGGER.debug(f"WiFi MAC: {device_info.get('wifiMac')}, WiFi SSID: {device_info.get('wifiSsid')}, Online: {device_info.get('is_online')}")

            if device_info.get('wifiMac') and device_info.get('wifiSsid') and device_info.get('is_online', False):
                valid_devices[device_id] = device_info
            else:
                _LOGGER.warning(f"Device {device_info.get('name', 'unknown')} is missing WiFi configuration or is offline.")

        return valid_devices

    def _is_valid_device(self, device_info, property_key):
        """Check if the device has the required property."""
        return device_info.get(property_key, None)

class InvalidCyncConfiguration(HomeAssistantError):
    """Error to indicate invalid Cync configuration."""
