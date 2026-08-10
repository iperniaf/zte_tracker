"""Tests for H3640 WLAN configuration support."""

from unittest.mock import Mock

from zteclient.zte_client import zteClient


WLAN_XML = b"""<?xml version='1.0'?>
<ajax_response_xml_root>
  <IF_ERRORID>0</IF_ERRORID>
  <IF_ERRORPARAM>SUCC</IF_ERRORPARAM>
  <OBJ_WLANAP_ID>
    <Instance>
      <ParaName>_InstID</ParaName><ParaValue>DEV.WIFI.AP7</ParaValue>
      <ParaName>Enable</ParaName><ParaValue>1</ParaValue>
      <ParaName>Alias</ParaName><ParaValue>SSID7</ParaValue>
      <ParaName>ESSID</ParaName><ParaValue>RAWiFiP</ParaValue>
      <ParaName>WLANViewName</ParaName><ParaValue>DEV.WIFI.RD2</ParaValue>
    </Instance>
  </OBJ_WLANAP_ID>
  <OBJ_WLANSETTING_ID>
    <Instance>
      <ParaName>_InstID</ParaName><ParaValue>DEV.WIFI.RD2</ParaValue>
      <ParaName>Band</ParaName><ParaValue>5GHz</ParaValue>
    </Instance>
  </OBJ_WLANSETTING_ID>
  <OBJ_WLANPSK_ID>
    <Instance>
      <ParaName>_InstID</ParaName><ParaValue>DEV.WIFI.AP7.PSK1</ParaValue>
      <ParaName>KeyPassphrase</ParaValue><ParaValue>redacted</ParaValue>
    </Instance>
  </OBJ_WLANPSK_ID>
  <encode>KeyPassphrase</encode>
</ajax_response_xml_root>"""


def make_client() -> zteClient:
    client = zteClient("192.168.2.1", "admin", "password", "H3640")
    client.session = Mock()
    return client


def test_parse_h3640_wifi_configuration() -> None:
    client = make_client()
    response = Mock(content=WLAN_XML, request=None)
    client.session.get.return_value = response

    result = client.get_wifi_configuration()

    assert result == [
        {
            "ap_id": "DEV.WIFI.AP7",
            "enabled": True,
            "ssid": "RAWiFiP",
            "alias": "SSID7",
            "band": "5GHz",
            "radio_id": "DEV.WIFI.RD2",
            "psk_id": "DEV.WIFI.AP7.PSK1",
            "has_psk": True,
            "fields": {
                "_InstID": "DEV.WIFI.AP7",
                "Enable": "1",
                "Alias": "SSID7",
                "ESSID": "RAWiFiP",
                "WLANViewName": "DEV.WIFI.RD2",
            },
        }
    ]


def test_set_h3640_wifi_enabled_uses_minimal_signed_body() -> None:
    client = make_client()
    client.login = Mock(return_value=True)
    client.get_session_token = Mock(return_value="session-token")
    current = [{"ap_id": "DEV.WIFI.AP7", "enabled": True}]
    refreshed = [{"ap_id": "DEV.WIFI.AP7", "enabled": False}]
    client.get_wifi_configuration = Mock(side_effect=[current, refreshed])
    response = Mock(
        content=b"<ajax_response_xml_root><IF_ERRORID>0</IF_ERRORID>"
        b"<IF_ERRORPARAM>SUCC</IF_ERRORPARAM><IF_IRET>-9</IF_IRET>"
        b"</ajax_response_xml_root>",
        request=None,
    )
    client.session.post.return_value = response

    assert client.set_wifi_enabled("DEV.WIFI.AP7", False) == refreshed
    assert client.session.post.call_args.kwargs["data"] == (
        "IF_ACTION=Apply&Enable=0&_InstID=DEV.WIFI.AP7"
        "&_sessionTOKEN=session-token"
    )
    check = client.session.post.call_args.kwargs["headers"]["Check"]
    assert len(check) == 344
