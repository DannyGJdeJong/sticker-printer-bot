# Sticker Printer Bot

This code creates a Telegram bot which allows users to interact with a Brother QL-650TD label printer, letting them print photos and Telegram stickers.

## Setup

Ensure you are using Python 3.11.

Create a venv and install dependencies:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy the example .env file and fill it:

```sh
cp .env.example .env
```

### Setup usb permissions

Find the correct idVendor and idProduct using `lsusb` and create an udev rule. For the Brother QL-650TD these are `04f9` and `20c0` respectively.

```sh
groupadd QL650TD
echo 'SUBSYSTEMS=="usb", ATTRS{idVendor}=="04f9", ATTRS{idProduct}=="20c0", GROUP="QL650TD", MODE="0666"' | sudo tee /etc/udev/rules.d/50-QL-650TD.rules
usermod -a -G QL650TD <user>
udevadm control --reload-rules && udevadm trigger
```

### Setup auto-start

Create a systemd unit with the following at `/etc/systemd/system/sticker-printer.service`:

```sh
[Unit]
Description=Sticker Printer Bot
After=network.target
After=systemd-user-sessions.service
After=network-online.target

[Service]
User=user
ExecStart=/path/to/run.sh
TimeoutSec=30
Restart=always

[Install]
WantedBy=multi-user.target
```

Run and enable it using the following command:

```sh
chmod +x run.sh
systemctl enable --now sticker-printer
```
