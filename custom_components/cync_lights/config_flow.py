import logging
from homeassistant.exceptions import HomeAssistantError
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
            valid_devices = self._get_wifi_connected_devices()

            # Debugging logs to help identify missing key issues
            _LOGGER.debug(f"Valid devices: {valid_devices}")
            _LOGGER.debug(f"Entry data: {self.entry.data}")

            # Add checks for missing keys with logging
            if not valid_devices:
                raise InvalidCyncConfiguration(
                    "Invalid or unsupported Cync configuration, please ensure there is at least one WiFi connected Cync device in your Home(s)."
                )

            # Ensure that self.entry is not None and contains valid data
            if not self.entry or not self.entry.data:
                _LOGGER.error(f"self.entry is None or empty. Entry data: {self.entry}")
                raise InvalidCyncConfiguration("self.entry is missing or has no data")

            # Ensure the 'cync_config' key exists before accessing it
            if 'cync_config' not in self.entry.data:
                _LOGGER.error(f"'cync_config' key missing from entry data: {self.entry.data}")
                raise InvalidCyncConfiguration("Missing 'cync_config' in entry data")

            # Log all keys in cync_config
            _LOGGER.debug(f"Keys in cync_config: {self.entry.data['cync_config'].keys()}")

            # Ensure the 'rooms' key exists in 'cync_config'
            if 'rooms' not in self.entry.data["cync_config"]:
                _LOGGER.error(f"'rooms' key missing in 'cync_config': {self.entry.data['cync_config']}")
                raise InvalidCyncConfiguration("Missing 'rooms' key in 'cync_config'")

            # Log keys in 'rooms' to identify potential issues
            _LOGGER.debug(f"Keys in rooms: {self.entry.data['cync_config']['rooms'].keys()}")

            # Now we access 'rooms' data safely
            switches_data_schema = vol.Schema(
                {
                    vol.Optional("rooms", description={"suggested_value": []}): cv.multi_select({
                        room: f"{room_info.get('parent_room', '')}: {room_info['home_name']}"
                        for room, room_info in self.entry.data["cync_config"]["rooms"].items()
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
            missing_key = str(e)
            _LOGGER.error(f"KeyError: Missing or empty key '{missing_key}' in device configuration at line 105")
            _LOGGER.debug(f"self.entry.data at KeyError: {self.entry.data}")
            raise InvalidCyncConfiguration(f"Device configuration is missing or has an empty key: {missing_key}")

        except Exception as e:
            _LOGGER.error(f"Unexpected error in configuration: {str(e)}")
            raise InvalidCyncConfiguration(f"Error in configuration: {str(e)}")

        return self.async_show_form(step_id="select_switches", data_schema=switches_data_schema)

    def _get_wifi_connected_devices(self):
        """Filter and return only devices that are connected via WiFi."""
        devices = self.entry.data.get("cync_config", {}).get("devices", {})
        valid_devices = {}

        for device_id, device_info in devices.items():
            # Log each device's WiFi properties
            _LOGGER.debug(f"Inspecting device: {device_info.get('name', 'unknown')}")
            _LOGGER.debug(f"WiFi MAC: {device_info.get('wifiMac')}, WiFi SSID: {device_info.get('wifiSsid')}, Online: {device_info.get('is_online')}")

            # Check for WiFi MAC, SSID, and if the device is online
            if device_info.get('wifiMac') and device_info.get('wifiSsid') and device_info.get('is_online', False):
                valid_devices[device_id] = device_info
            else:
                _LOGGER.warning(f"Device {device_info.get('name', 'unknown')} is missing WiFi configuration or is offline.")

        return valid_devices

    def _is_valid_device(self, device_info, property_key):
        """Check if the device has the required property and log missing ones."""
        if device_info.get(property_key, None):
            return True
        else:
            _LOGGER.warning(f"Device {device_info.get('name', 'unknown')} is missing property: {property_key}")
            return False

class InvalidCyncConfiguration(HomeAssistantError):
    """Error to indicate invalid Cync configuration."""
