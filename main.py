"""
TrendRadar Voice Generator — Edge TTS + Flet (новый API)
"""

import asyncio
import threading
import os
import sys
from pathlib import Path

import edge_tts
import flet as ft



VOICES = {
    "en-US-EricNeural": "Eric — American male, confident (RECOMMENDED)",
    "en-US-AriaNeural": "Aria — American female, professional",
    "en-GB-RyanNeural": "Ryan — British male, solid",
    "en-US-GuyNeural": "Guy — American male, casual",
    "en-US-JennyNeural": "Jenny — American female, friendly",
    "en-GB-SoniaNeural": "Sonia — British female, warm",
    "en-AU-NatashaNeural": "Natasha — Australian female, bright",
}

async def generate_tts(text, voice, output_path, callback):
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        callback(True, output_path)
    except Exception as e:
        callback(False, str(e))

def run_async(coro):
    asyncio.run(coro)

def main(page: ft.Page):
    page.title = "TrendRadar Voice Generator"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 30
    page.window.width = 700
    page.window.height = 700
    # Полный путь к иконке
    page.window.icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")


    last_output = {"path": ""}
    save_dir = {"path": str(Path.home() / "Downloads")}

    voice_dropdown = ft.Dropdown(
        label="Voice", value=list(VOICES.keys())[0],
        options=[ft.dropdown.Option(key=k, text=v) for k, v in VOICES.items()],
        width=700,
    )

    text_field = ft.TextField(label="Enter your text here...", multiline=True, min_lines=6, max_lines=12, width=700)
    filename_field = ft.TextField(label="Filename (without .mp3)", value="trendradar_voice", width=300)

    save_dir_text = ft.Text(f"Save to: {save_dir['path']}", color=ft.Colors.GREY_400, size=12)

    async def choose_folder(e):
        result = await ft.FilePicker().get_directory_path()
        if result:
            save_dir["path"] = result
            save_dir_text.value = f"Save to: {result}"
            page.update()


    choose_dir_btn = ft.Button(
        "Choose Folder", on_click=choose_folder,
        style=ft.ButtonStyle(bgcolor=ft.Colors.GREY_800, color=ft.Colors.WHITE),
    )

    status_text = ft.Text("", color=ft.Colors.GREY_400)
    progress_bar = ft.ProgressBar(width=700, visible=False)
    open_btn = ft.TextButton("Open Folder", visible=False)

    def on_generate(e):
        text = text_field.value.strip()
        if not text:
            status_text.value = "Please enter some text."
            status_text.color = ft.Colors.RED_400
            page.update()
            return
        voice = voice_dropdown.value
        filename = filename_field.value.strip() or "output"
        output_path = str(Path(save_dir["path"]) / f"{filename}.mp3")
        progress_bar.visible = True
        status_text.value = "Generating audio..."
        status_text.color = ft.Colors.YELLOW_400
        generate_btn.disabled = True
        page.update()

        def on_complete(success, result):
            progress_bar.visible = False
            generate_btn.disabled = False
            if success:
                last_output["path"] = result
                status_text.value = f"Saved: {filename}.mp3"
                status_text.color = ft.Colors.GREEN_400
                open_btn.visible = True
            else:
                status_text.value = f"Error: {result}"
                status_text.color = ft.Colors.RED_400
            page.update()

        threading.Thread(target=run_async, args=(generate_tts(text, voice, output_path, on_complete),), daemon=True).start()

    generate_btn = ft.Button(
        "Generate MP3", on_click=on_generate,
        style=ft.ButtonStyle(bgcolor=ft.Colors.PURPLE_700, color=ft.Colors.WHITE, padding=20),
    )

    def on_open(e):
        if last_output["path"]:
            os.startfile(os.path.dirname(last_output["path"]))

    open_btn.on_click = on_open

    page.add(
        ft.Text("TrendRadar Voice Generator", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE_300),
        ft.Text("Free TTS using Microsoft Edge voices", color=ft.Colors.GREY_400),
        ft.Divider(height=20),
        voice_dropdown,
        ft.Text("Text to speak:", color=ft.Colors.GREY_300),
        text_field,
        ft.Row([filename_field, generate_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Row([choose_dir_btn, save_dir_text]),
        progress_bar,
        ft.Row([open_btn]),
        status_text,
    )

if __name__ == "__main__":
    ft.app(target=main)