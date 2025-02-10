import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import yt_dlp
from datetime import datetime

# Constants
DOWNLOAD_FROM_FIRST = False  # Change to False to download from the last video
ADD_PREFIX = True  # Toggle filename prefix "00n_"
LOG_FILE = "download_log.txt"
OUTPUT_PATH = ""
FOLDER_NAME = ""

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
    if not isinstance(filename, str):  # Ensure it's a string
        return "Unknown_Title"
    return re.sub(r'[^A-Za-z0-9-_ ]', '_', filename)

def ensure_folder(folder_path, printit=False):
    """
    import os
    check if a folder exist, create it if not exist
    """
    # Check if the folder exists
    if not os.path.exists(folder_path):
        # If not, create the folder
        os.makedirs(folder_path)
        if printit:
            print(f"Folder '{folder_path}' created.")
    else:
        if printit:
            print(f"Folder '{folder_path}' already exists.")

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

def get_channel_playlists(channel_url):
    """
    When you pass a channel url: Extracts all video urls
    When you pass a channel playlists url: Extracts all playlist URLs from a given YouTube channel URL.
    """
    ydl_opts = {
        'quiet': True,
        'extract_flat': 'in_playlist',
        'force_generic_extractor': False
    }
    playlists = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(channel_url, download=False)
            if 'entries' in info:
                playlists = [
                    entry['url'] for entry in info['entries'] if 'url' in entry
                ]
        except Exception as e:
            print(f"❌ Error extracting playlists: {e}")
    return playlists
def extract_playlist_videos(url):
    """Extracts video URLs from a YouTube playlist"""
    ydl_opts = {
        'quiet': False,
        'extract_flat': 'in_playlist',
        'force_generic_extractor': False,
        'extractor_args': {'youtube:tab': {'skip': ['webpage']}}
    }
    urls = []
    items = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            global FOLDER_NAME
            FOLDER_NAME = info.get('title', 'Unknown Playlist')
            FOLDER_NAME = sanitize_filename(FOLDER_NAME)
            print(f"FOLDER NAME IS: {FOLDER_NAME}")
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
        print(f"{item['url']} \t {item['title']} \t\t {sanitize_filename(item['title'])}")
        # if is_in_completed(f'{title}'):
        #     print(f"✅ Item previously completed: {title}")
        # else:
        #     print(f"X Item not previously completed: {title}")
    return items

def get_video_title(video_url):
    ydl_opts = {'quiet': True}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(video_url, download=False)
            return info.get('title', 'Unknown_Title')
        except Exception as e:
            print(f"❌ Error fetching title: {e}")
            return "Unknown_Title"

def download_playlist(url):
    """
    :param url: playlist url
    :return:
    """
    RETRY_STEP = False
    def run_download():
        FAILED_FLAG = False
        nonlocal RETRY_STEP
        video_urls = extract_playlist_videos(url)
        global OUTPUT_PATH
        OUTPUT_PATH = folder_path.get()  # base download folder
        OUTPUT_PATH = f"{OUTPUT_PATH}/{FOLDER_NAME}"
        ensure_folder(OUTPUT_PATH)
        print(f"FOLDER NAME IS: {FOLDER_NAME}")
        print(f"OUTPUT PATH IS: {OUTPUT_PATH}")
        resolution = resolution_var.get()
        format_code = RESOLUTIONS.get(resolution, "best")
        log_message(f"📂 Downloading playlist to: {OUTPUT_PATH}")
        log_message(f"🎥 Selected resolution: {resolution}")
        folder = OUTPUT_PATH

        if not video_urls:
            log_message("❌ No videos found in the playlist!")
            return

        if not DOWNLOAD_FROM_FIRST:
            video_urls.reverse()

        video_urls_copy = video_urls.copy()
        for index, item in enumerate(video_urls_copy, start=1):
            title = item['title']
            video_url = item['url']
            prefix = f"{index:03d}_" if ADD_PREFIX else ""
            write_unique_line(f"{OUTPUT_PATH}/{FOLDER_NAME}_list_of_titles.txt", f"{prefix}{title}")

        for index, item in enumerate(video_urls, start=1):
            title = item['title']
            video_url = item['url']
            prefix = f"{index:03d}_" if ADD_PREFIX else ""

            if is_in_completed(f'{prefix}{title}'):
                print(f"✅ Item previously completed: {prefix}{title} \t {video_url}")
                continue

            title_sanitized = sanitize_filename(title)

            if RETRY_STEP:
                ydl_opts = {
                    'outtmpl': os.path.join(folder, prefix + title_sanitized + '.%(ext)s'),
                    'format': format_code,
                    'merge_output_format': 'mp4',
                    'progress_hooks': [progress_hook],
                    'noprogress': True,
                    'socket_timeout': 30,  # Increase timeout to 30 seconds, default is 10
                    'retries': 10,  # Increase retries to 10, default is 3
                    'fragment_retries': 10,  # Retries for fragmented downloads
                    # 'http_chunk_size': 10485760,  # Set chunk size to 10MB (optional, helps with slow connections)
                }
            else:
                ydl_opts = {
                    'outtmpl': os.path.join(folder, prefix + title_sanitized + '.%(ext)s'),
                    'format': format_code,
                    'merge_output_format': 'mp4',
                    'progress_hooks': [progress_hook],
                    'noprogress': True,
                }

            log_message(f"⬇️ Downloading: {video_url} ({index}/{len(video_urls)})")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    ydl.download([video_url])
                    log_message(f"✅ Completed: {video_url}")
                    log_to_completed(f'Completed: {prefix}{title},\t filename: {prefix}{title_sanitized},\t url: {video_url}')
                except Exception as e:
                    FAILED_FLAG = True
                    log_message(f"❌ Failed: {video_url} - {e}")
                    log_to_failed(f'Failed: {prefix}{title},\t filename: {prefix}{title_sanitized},\t url: {video_url}')
        if FAILED_FLAG:
            RETRY_STEP = True
            log_message("### LIST COMPLETED BUT SOMETHING FAILED, TRY AGAIN WITH OTHER OPTIONS ###")
            run_download()
        log_message("✅ Playlist download complete!")

    run_download()

def download_playlists():
    input_url = url_entry.get().strip()
    if not input_url:
        messagebox.showerror("Error", "Please enter a YouTube playlist URL")
        return

    global OUTPUT_PATH
    OUTPUT_PATH = folder_path.get()  # base download folder
    if not OUTPUT_PATH:
        messagebox.showerror("Error", "Please select a download folder")
        return

    def download_thread():
        playlists_list = []
        if ("playlists" not in input_url):
            playlists_list.append(input_url)
        else:
            playlists_list = get_channel_playlists(input_url)
        for playlist in playlists_list:
            global OUTPUT_PATH
            OUTPUT_PATH = folder_path.get()  # base download folder
            download_playlist(playlist)

    thread = threading.Thread(target=download_thread, daemon=True)
    thread.start()

def progress_hook(d):
    if d['status'] == 'downloading':
        log_message(f"⬇️ Downloading: {d.get('filename', 'Unknown')} - {d['_percent_str']}")


def choose_folder():
    folder_selected = filedialog.askdirectory()
    folder_path.set(folder_selected)

def gui_setup(root):
    global url_entry, folder_path, resolution_var, console_text

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
    resolution_dropdown = ttk.Combobox(root, textvariable=resolution_var, values=list(RESOLUTIONS.keys()),
                                       state="readonly")
    resolution_dropdown.pack(pady=5)

    # Download Button
    tk.Button(root, text="Download Playlist", command=download_playlists, bg="red", fg="white").pack(pady=10)

    # Console Output
    tk.Label(root, text="Download Console:").pack(pady=5)
    console_text = scrolledtext.ScrolledText(root, width=70, height=10, state="normal")
    console_text.pack(pady=5)

    # Status Label
    tk.Label(root, text="", fg="black").pack(pady=5)


if __name__ == "__main__":
    root = tk.Tk()
    gui_setup(root)
    root.mainloop()
