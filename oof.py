import flet as ft
from enum import Enum
from json import loads
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from base64 import b64encode
import threading
import time
import pyperclip  # 新增

AppEnum = Enum("AppEnum", "web, android, ios, linux, mac, windows, tv, alipaymini, wechatmini, qandroid")

def get_enum_name(val, cls):
    if isinstance(val, cls):
        return val.name
    try:
        if isinstance(val, str):
            return cls[val].name
    except KeyError:
        pass
    return cls(val).name

def get_qrcode_token(app):
    api = f"https://qrcodeapi.115.com/api/1.0/{app}/1.0/token/"
    return loads(urlopen(api).read())

def get_qrcode_status(payload):
    api = "https://qrcodeapi.115.com/get/status/?" + urlencode(payload)
    return loads(urlopen(api).read())

def post_qrcode_result(uid, app="web"):
    app = get_enum_name(app, AppEnum)
    payload = {"app": app, "account": uid}
    api = f"https://passportapi.115.com/app/1.0/{app}/1.0/login/qrcode/"
    return loads(urlopen(Request(api, data=urlencode(payload).encode("utf-8"), method="POST")).read())

def get_qrcode(uid, app):
    url = f"https://qrcodeapi.115.com/api/1.0/{app}/1.0/qrcode?uid={uid}"
    return urlopen(url).read()

def qr_login(page, app="web"):
    try:
        qrcode_token = get_qrcode_token(app)["data"]
        uid = qrcode_token["uid"]
        qr_image_data = get_qrcode(uid, app)
        qr_image_base64 = b64encode(qr_image_data).decode('utf-8')

        # Update QR code image
        image_control.src_base64 = qr_image_base64
        status_label.value = "Waiting for QR code scan..."
        cookies_label.value = ""
        page.update()

        def check_status():
            while True:
                try:
                    resp = get_qrcode_status(qrcode_token)
                    status = resp["data"].get("status")
                except Exception as e:
                    update_status(f"Error: {str(e)}")
                    break

                if status == 0:
                    update_status("Waiting for scan...")
                elif status == 1:
                    update_status("QR Code scanned. Please confirm login on your device.")
                elif status == 2:
                    update_status("Signed in successfully!")
                    try:
                        result = post_qrcode_result(uid, app)
                        cookies = result['data']['cookie']
                        cookies_text = "; ".join(f"{k}={v}" for k, v in cookies.items())
                        update_cookies(cookies_text)
                    except Exception as e:
                        update_cookies(f"Failed to retrieve cookies: {str(e)}")
                    break
                elif status == -1:
                    update_status("QR Code expired. Please try again.")
                    break
                elif status == -2:
                    update_status("Login canceled.")
                    break
                else:
                    update_status("Unknown status.")

                time.sleep(2)
                page.update()

        def update_status(message):
            status_label.value = message
            page.update()

        def update_cookies(message):
            cookies_label.value = message
            page.update()

        # Start checking the QR code status in a separate thread
        threading.Thread(target=check_status, daemon=True).start()

    except Exception as e:
        status_label.value = f"Initialization error: {str(e)}"
        page.update()

def copy_to_clipboard(e):
    pyperclip.copy(cookies_label.value)  # 使用 pyperclip 来复制到剪贴板

# Main Flet app entry point
def main(page: ft.Page):
    page.title = "115 QR Code Login"
    page.window_width = 400
    page.window_height = 600

    def on_app_selected(e):
        selected_app = app_dropdown.value
        qr_login(page, selected_app)

    # App selection dropdown
    app_dropdown = ft.Dropdown(
        options=[ft.dropdown.Option(app) for app in AppEnum._member_names_],
        value="web",
        on_change=on_app_selected
    )

    # Image control to display QR code
    global image_control
    image_control = ft.Image(width=200, height=200)
    # Status label
    global status_label
    status_label = ft.Text("Waiting for QR code scan...")
    # Cookies label
    global cookies_label
    cookies_label = ft.Text("")

    # Copy to clipboard button
    copy_button = ft.Button(text="Copy Cookies", on_click=copy_to_clipboard)

    # Add components to the page
    page.add(app_dropdown, image_control, status_label, cookies_label, copy_button)

# Start the Flet app
ft.app(target=main)