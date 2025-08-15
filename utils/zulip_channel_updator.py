#!/usr/bin/env python3

import zulip

def warn_zulip_user(message):
    client = zulip.Client(config_file= "C:/Users/lociuser/Documents/zuliprc")
    request = {
        "type": "stream",
        "to": "SLIM-acquisition-messages",
        "topic": "Acquisition status",
        "content": (message),
    }
    result = client.send_message(request)
    print(result)