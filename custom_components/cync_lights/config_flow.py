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
            if not valid_devices:
                raise InvalidCyncConfiguration(
                    "Invalid or unsupported Cync configuration, please ensure there is at least one WiFi connected Cync device in your Home(s)."
                )

            switches_data_schema = vol.Schema(
                {
                    vol.Optional("rooms", description={"suggested_value": []}): cv.multi_select({
                        room: f"{room_info.get('parent_room', '')}: {room_info['home_name']}"
                        for room, room_info in self.entry.data["cync_config"]["rooms"].items()
                        if room_info.get('isSubgroup', False)
                    }),
                    vol.Optional("switches", description={"suggested_value": []}): cv.multi_select({
                        switch_id: f"{sw_info['name']} ({sw_info['room_name']}: {sw_info['home_name']})"
                        for switch_id, sw_info in valid_devices
                        if self._is_valid_device(sw_info, 'ONOFF')
                    }),
                    vol.Optional("motion_sensors", description={"suggested_value": []}): cv.multi_select({
                        device_id: f"{device_info['name']} ({device_info['room_name']}: {device_info['home_name']})"
                        for device_id, device_info in valid_devices
                        if self._is_valid_device(device_info, 'MOTION')
                    }),
                    vol.Optional("ambient_light_sensors", description={"suggested_value": []}): cv.multi_select({
                        device_id: f"{device_info['name']} ({device_info['room_name']}: {device_info['home_name']})"
                        for device_id, device_info in valid_devices
                        if self._is_valid_device(device_info, 'AMBIENT_LIGHT')
                    }),
                }
            )

        except KeyError as e:
            _LOGGER.error(f"Missing device property: {str(e)}")
            raise InvalidCyncConfiguration(f"Device missing property: {str(e)}")

        except Exception as e:
            _LOGGER.error(f"Unexpected error in configuration: {str(e)}")
            raise InvalidCyncConfiguration(f"Error in configuration: {str(e)}")

        return self.async_show_form(step_id="select_switches", data_schema=switches_data_schema)

    def _get_wifi_connected_devices(self):
        """Filter and return only devices that are connected via WiFi."""
        devices = self.entry.data["cync_config"]["devices"]
        valid_devices = {}
        
        for device_id, device_info in devices.items():
            if device_info.get('wifiMac') and device_info.get('wifiSsid'):
                valid_devices[device_id] = device_info
            else:
                _LOGGER.warning(f"Device {device_info.get('name', 'unknown')} is missing WiFi configuration.")
        
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
