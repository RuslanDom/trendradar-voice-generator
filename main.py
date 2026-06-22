"""
TrendRadar Voice Generator — Edge TTS + Flet 0.90.0
Воспроизведение через локальный HTTP-сервер (работает на Android без pyjnius).
"""

import asyncio
import os
import socket
import sys
from pathlib import Path

import edge_tts
import flet as ft
from aiohttp import web

VOICES = {
    "en-US-EricNeural": "Eric — American male, confident (RECOMMENDED)",
    "en-US-AriaNeural": "Aria — American female, professional",
    "en-GB-RyanNeural": "Ryan — British male, solid",
    "en-US-GuyNeural": "Guy — American male, casual",
    "en-US-JennyNeural": "Jenny — American female, friendly",
    "en-GB-SoniaNeural": "Sonia — British female, warm",
    "en-AU-NatashaNeural": "Natasha — Australian female, bright",
}

debug_text = None
page_ref = None

# HTTP-сервер (одноразовый)
runner = None
server_site = None
server_port = None


def add_log(message):
    global debug_text, page_ref
    if debug_text and page_ref:
        debug_text.value = message
        page_ref.update()

async def start_server(file_path):
    global runner, server_site, server_port
    await stop_server()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        server_port = s.getsockname()[1]

    async def handle(request):
        return web.FileResponse(file_path)

    app = web.Application()
    app.router.add_get('/', handle)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', server_port)
    await site.start()
    server_site = site

async def stop_server():
    global runner, server_site, server_port
    if runner:
        await runner.cleanup()
        runner = None
    server_site = None
    server_port = None

def main(page: ft.Page):
    global debug_text, page_ref
    page_ref = page
    page.title = "TrendRadar Voice Generator"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 30
    page.window.width = 700
    page.window.height = 700

    if sys.platform not in ('android', 'ios'):
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            page.window.icon = icon_path

    last_output = {"path": ""}
    save_dir = {"path": str(Path.home() / "Downloads")}

    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    voice_dropdown = ft.Dropdown(
        label="Voice",
        value=list(VOICES.keys())[0],
        options=[ft.dropdown.Option(key=k, text=v) for k, v in VOICES.items()],
        expand=True,
    )

    text_field = ft.TextField(
        label="Enter your text here...",
        multiline=True,
        min_lines=6,
        max_lines=12,
        expand=True,
    )

    filename_field = ft.TextField(
        label="Filename (without .mp3)",
        value="trendradar_voice",
        expand=True,
    )

    save_dir_text = ft.Text(f"Save to: {save_dir['path']}", color=ft.Colors.GREY_400, size=12)

    async def choose_folder(e):
        result = await file_picker.get_directory_path()
        if result:
            save_dir["path"] = result
            save_dir_text.value = f"Save to: {result}"
            page.update()

    choose_dir_btn = ft.Button(
        "Choose Folder", on_click=choose_folder,
        style=ft.ButtonStyle(bgcolor=ft.Colors.YELLOW_700, color=ft.Colors.WHITE),
    )

    status_text = ft.Text("", color=ft.Colors.GREY_400)
    progress_bar = ft.ProgressBar(visible=False, expand=True)

    debug_text = ft.Text("", color=ft.Colors.GREY_400, size=12, selectable=True)

    is_mobile = page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)

    # --- Кнопка Listen через HTTP-сервер ---
    async def listen(e):
        if not last_output["path"]:
            status_text.value = "No file to play"
            status_text.color = ft.Colors.RED_400
            page.update()
            return

        src_path = Path(last_output["path"])
        if not src_path.exists():
            add_log(f"❌ File not found: {src_path}")
            status_text.value = "File not found"
            status_text.color = ft.Colors.RED_400
            page.update()
            return

        try:
            # Запускаем сервер
            await start_server(str(src_path))
            url = f"http://127.0.0.1:{server_port}/"
            add_log(f"🌐 Local server: {url}")
            await page.launch_url(url)
            add_log("📤 AudioPlayer")
            status_text.value = "Playing..."
            status_text.color = ft.Colors.GREEN_400

            # Остановим сервер через 10 секунд (достаточно для начала воспроизведения)
            async def delayed_stop():
                await asyncio.sleep(10)
                await stop_server()
                add_log("🛑 Server stop")
            asyncio.create_task(delayed_stop())

        except Exception as ex:
            add_log(f"❌ Error: {ex}")
            status_text.value = f"Error: {ex}"
            status_text.color = ft.Colors.RED_400
        page.update()

    listen_btn = ft.Button(
        "Listen",
        visible=False,
        on_click=lambda e: asyncio.create_task(listen(e)),
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.GREEN_700,
            color=ft.Colors.WHITE,
            padding=20,
        ),
        expand=True,
    )

    # --- Кнопка Open Folder (ПК) ---
    def on_open(e):
        if not last_output["path"]:
            return
        folder = os.path.dirname(last_output["path"])
        add_log(f"📂 Open folder: {folder}")
        if sys.platform == "win32":
            os.startfile(folder)
        elif sys.platform == "linux":
            import subprocess
            subprocess.Popen(["xdg-open", folder])

    open_folder_btn = ft.Button(
        "Open Folder",
        visible=False,
        on_click=on_open,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.GREEN_700,
            color=ft.Colors.WHITE,
            padding=20,
        ),
        expand=True,
    )

    # --- Генерация (Edge TTS) ---
    async def run_generation(text, voice, output_path, filename):
        try:
            add_log(f"🔄 Generation: '{text[:30]}...'")
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            last_output["path"] = output_path
            add_log(f"✅ Saved: {output_path}")
            status_text.value = f"Saved: {filename}.mp3"
            status_text.color = ft.Colors.GREEN_400
            listen_btn.visible = True
            if not is_mobile:
                open_folder_btn.visible = True
        except Exception as e:
            add_log(f"❌ Error generation: {e}")
            status_text.value = f"Error: {e}"
            status_text.color = ft.Colors.RED_400
        finally:
            progress_bar.visible = False
            generate_btn.disabled = False
            page.update()

    def on_generate(e):
        text = text_field.value.strip()
        if not text:
            add_log("⚠️ Void...")
            status_text.value = "Please enter some text."
            status_text.color = ft.Colors.RED_400
            page.update()
            return
        voice = voice_dropdown.value
        filename = filename_field.value.strip() or "output"
        output_path = str(Path(save_dir["path"]) / f"{filename}.mp3")
        add_log(f"🎤 Voice: {voice}, file: {filename}.mp3")

        progress_bar.visible = True
        status_text.value = "Generating audio..."
        status_text.color = ft.Colors.YELLOW_400
        generate_btn.disabled = True
        page.update()

        asyncio.create_task(run_generation(text, voice, output_path, filename))

    generate_btn = ft.Button(
        "Generate MP3", on_click=on_generate,
        style=ft.ButtonStyle(bgcolor=ft.Colors.PURPLE_700, color=ft.Colors.WHITE, padding=20),
        expand=True,
    )

    controls = [
        ft.Text("TrendRadar Voice Generator", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE_300),
        ft.Text("Free TTS using Microsoft Edge voices", color=ft.Colors.GREY_400),
        ft.Divider(height=20),
        voice_dropdown,
        ft.Text("Text to speak:", color=ft.Colors.GREY_300),
        text_field,
        filename_field,
        ft.Row([choose_dir_btn, save_dir_text], alignment=ft.MainAxisAlignment.START),
        generate_btn,
        progress_bar,
    ]

    controls.append(listen_btn)
    if not is_mobile:
        controls.append(open_folder_btn)

    controls.append(debug_text)
    controls.append(status_text)

    page.add(
        ft.Column(
            controls,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=15,
        )
    )

    add_log("🚀 App starting...")
    page.update()

if __name__ == "__main__":
    ft.run(main)