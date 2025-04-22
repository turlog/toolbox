#!/opt/pyenv/versions/admin/bin/python3

import os
import sys
import json

import click

from paho.mqtt.client import Client, CallbackAPIVersion

from pydantic import BaseModel


class MQTTConnection(BaseModel):
    host: str
    port: int
    username: str
    password: str
    keepalive: int = 60


class RemoteConfiguration(BaseModel):
    mqtt: MQTTConnection
    actions: dict[str, str]

    @classmethod
    def load(cls, fn):
        stream = sys.stdin if fn == "-" else open(fn)
        try:
            return cls.model_validate(json.load(stream))
        except ValueError as error:
            raise click.UsageError(f"Invalid configuration file: {error}")


def action_handler(configuration):
    mqtt = Client(CallbackAPIVersion.VERSION1)
    mqtt.username_pw_set(configuration.mqtt.username, configuration.mqtt.password)

    actions = {
        "857E08": "L1",
        "857E04": "L2",
        "857E02": "L3",
        "857E01": "L4",
        "857E0C": "R1",
        "857E09": "R2",
        "857E05": "R3",
        "857E03": "R4",
    }

    def on_message(client, userdata, msg):
        payload = json.loads(msg.payload)
        data = payload.get("RfReceived", {}).get("Data")
        if data is not None:
            action = actions.get(data)
            if action is not None:
                print(f"ACTION: {action}")
                if (action := configuration.actions.get(action)) is not None:
                    if action.startswith("!"):
                        os.system(action[1:])

        raw = payload.get("RfRaw", {}).get("Data")
        if raw is not None:
            print(raw)

    def on_connect(client, userdata, flags, rc):
        print(userdata, flags, rc)
        client.subscribe("tele/rfbridge/RESULT", 2)
        # client.publish("cmnd/rfbridge/rfraw", "166")
        print("CONNECTED")

    def on_disconnect(client, userdata, rc):
        print("DISCONNECTED")

    def on_log(client, userdata, level, buf):
        print("NOTICE: ", buf)

    mqtt.on_log = on_log  # set client logging

    mqtt.on_connect = on_connect
    mqtt.on_message = on_message
    mqtt.on_disconnect = on_disconnect

    # mqtt.will_set("cmnd/rfbridge/rfraw", "0")

    mqtt.connect(
        configuration.mqtt.host,
        configuration.mqtt.port,
        keepalive=configuration.mqtt.keepalive,
    )

    mqtt.loop_forever()


@click.group()
def cli(): ...


@cli.command(
    "action-handler",
    context_settings={"max_content_width": 100, "help_option_names": ["-h", "--help"]},
)
@click.option(
    "--configuration",
    "-c",
    metavar="FILENAME",
    type=RemoteConfiguration.load,
    help="Configuration file (JSON).",
    default=os.environ.get(
        __spec__.name.upper().replace(".", "_") + "_CONFIGURATION", "-"
    ),
    show_default=True,
)
def action_handler_command(configuration):
    """
    Run the action handler that listens to MQTT messages.
    """
    action_handler(configuration)


if __name__ == "__main__":
    cli()
