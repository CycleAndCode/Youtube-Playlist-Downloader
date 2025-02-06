import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import yt_dlp
from datetime import datetime

# Constants
DOWNLOAD_FROM_FIRST = True  # Change to False to download from the last video
ADD_PREFIX = True  # Toggle filename prefix "00n_"
LOG_FILE = "download_log.txt"
OUTPUT_PATH = ""

# Common YouTube resolutions
RESOLUTIONS = {
    "2160p (4K)": "bestvideo[height<=2160]+bestaudio/best",
    "1440p": "bestvideo[height<=1440]+bestaudio/best",
    "1080p (Full HD)": "bestvideo[height<=1080]+bestaudio/best",
    "720p (HD)": "bestvideo[height<=720]+bestaudio/best",
    "480p": "bestvideo[height<=480]+bestaudio/best",
    "360p": "bestvideo[height<=360]+bestaudio/best",
    "240p": "bestvideo[height<=240]+bestaudio/best"
}

def get_timestamp():
    """Returns the current timestamp in a log-friendly format."""
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

def write_unique_line(file_path, line):
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            lines = [l.strip() for l in lines]

            if line in lines:
                return
    except FileNotFoundError:
        pass

    with open(file_path, 'a') as file:
        file.write(line + '\n')

# Safe filename function
def sanitize_filename(filename):
    return re.sub(r'[^A-Za-z0-9-_ ]', '_', filename)


# Log function
def log_to_file(message):
    path = os.path.join(OUTPUT_PATH, LOG_FILE)
    with open(path, "a", encoding="utf-8") as log:
        log.write(message + "\n")

def log_to_completed(message):
    path = os.path.join(OUTPUT_PATH, "completed.txt")
    write_unique_line(path, message)

def is_in_completed(title):
    try:
        title.strip()
    except:
        pass
    path = os.path.join(OUTPUT_PATH, "completed.txt")
    try:
        with open(path, 'r') as file:
            lines = file.readlines()
            lines = [l.strip() for l in lines]
            for line in lines:
                # print(f'Test: {title} \t {line}')
                if title in line:
                    return True
    except FileNotFoundError:
        pass
    return False
def log_to_failed(message):
    path = os.path.join(OUTPUT_PATH, "failed.txt")
    with open(path, "a", encoding="utf-8") as log:
        message = f'{get_timestamp()}   {message}'
        log.write(message + "\n")


def log_message(message):
    console_text.insert(tk.END, message + "\n")
    console_text.see(tk.END)
    log_to_file(message)


def extract_playlist_videos(url):
    """Extracts video URLs from a YouTube playlist"""
    ydl_opts = {
        'quiet': False,
        'extract_flat': 'in_playlist',
        'force_generic_extractor': False
    }
    urls = []
    items = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:
                urls = [entry['url'] for entry in info['entries'] if 'url' in entry]
        except Exception as e:
            log_message(f"❌ Error extracting playlist: {e}")
    for video_url in urls:
        item = {}
        try:
            title = get_video_title(video_url)
        except:
            title = "Not available"
        item['url'] = video_url
        item['title'] = title
        items.append(item)
        print(f"{item['url']} \t {item['title']} \t {sanitize_filename(item['title'])}")
        # if is_in_completed(f'{title}'):
        #     print(f"✅ Item previously completed: {title}")
        # else:
        #     print(f"X Item not previously completed: {title}")
    return items

def get_video_title(video_url):
    """Fetches the title of a YouTube video given its URL."""
    ydl_opts = {'quiet': True}  # Suppress console output

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(video_url, download=False)
            return info.get('title', 'Unknown Title')
        except Exception as e:
            print(f"❌ Error fetching title: {e}")
            return None
def download_playlist():
    url = url_entry.get().strip()
    if not url:
        messagebox.showerror("Error", "Please enter a YouTube playlist URL")
        return

    global OUTPUT_PATH
    OUTPUT_PATH = folder_path.get()
    folder = OUTPUT_PATH
    if not folder:
        messagebox.showerror("Error", "Please select a download folder")
        return

    resolution = resolution_var.get()
    format_code = RESOLUTIONS.get(resolution, "best")
    log_message(f"📂 Downloading playlist to: {folder}")
    log_message(f"🎥 Selected resolution: {resolution}")

    def run_download():
        video_urls = extract_playlist_videos(url)
        if not video_urls:
            log_message("❌ No videos found in the playlist!")
            return

        if not DOWNLOAD_FROM_FIRST:
            video_urls.reverse()

        for index, item in enumerate(video_urls, start=1):
            title = item['title']
            video_url = item['url']
            prefix = f"{index:03d}_" if ADD_PREFIX else ""

            if is_in_completed(f'{prefix}{title}'):
                print(f"✅ Item previously completed: {prefix}{title} \t {video_url}")
                continue

            title_sanitized = sanitize_filename(title)

            ydl_opts = {
                'outtmpl': os.path.join(folder, prefix + title_sanitized + '.%(ext)s'),
                'format': format_code,
                'merge_output_format': 'mp4',
                'progress_hooks': [progress_hook],
                'noprogress': True
            }

            log_message(f"⬇️ Downloading: {video_url} ({index}/{len(video_urls)})")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    ydl.download([video_url])
                    log_message(f"✅ Completed: {video_url}")
                    log_to_completed(f'Completed: {prefix}{title},\t filename: {prefix}{title_sanitized},\t url: {video_url}')
                except Exception as e:
                    log_message(f"❌ Failed: {video_url} - {e}")
                    log_to_failed(f'Failed: {prefix}{title},\t filename: {prefix}{title_sanitized},\t url: {video_url}')

        log_message("✅ Playlist download complete!")

    threading.Thread(target=run_download, daemon=True).start()


def progress_hook(d):
    if d['status'] == 'downloading':
        log_message(f"⬇️ Downloading: {d.get('filename', 'Unknown')} - {d['_percent_str']}")


def choose_folder():
    folder_selected = filedialog.askdirectory()
    folder_path.set(folder_selected)


# GUI Setup
root = tk.Tk()
root.title("YouTube Playlist Downloader (yt-dlp)")
root.geometry("600x450")

# URL Input
tk.Label(root, text="YouTube Playlist URL:").pack(pady=5)
url_entry = tk.Entry(root, width=60)
url_entry.pack(pady=5)

# Folder Selection
tk.Label(root, text="Download Folder:").pack(pady=5)
folder_path = tk.StringVar()
folder_entry = tk.Entry(root, textvariable=folder_path, width=45, state="readonly")
folder_entry.pack(pady=5)
tk.Button(root, text="Choose Folder", command=choose_folder).pack(pady=5)

# Resolution Selection (Dropdown)
tk.Label(root, text="Select Video Resolution:").pack(pady=5)
resolution_var = tk.StringVar(value="1080p (Full HD)")
resolution_dropdown = ttk.Combobox(root, textvariable=resolution_var, values=list(RESOLUTIONS.keys()), state="readonly")
resolution_dropdown.pack(pady=5)

# Download Button
download_button = tk.Button(root, text="Download Playlist", command=download_playlist, bg="red", fg="white")
download_button.pack(pady=10)

# Console Output
tk.Label(root, text="Download Console:").pack(pady=5)
console_text = scrolledtext.ScrolledText(root, width=70, height=10, state="normal")
console_text.pack(pady=5)

# Status Label
status_label = tk.Label(root, text="", fg="black")
status_label.pack(pady=5)

# Run the GUI
root.mainloop()
