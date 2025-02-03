import tkinter as tk
from tkinter import messagebox
import subprocess
import requests
from PIL import Image, ImageTk
import io
import threading
import os
import glob

# Create the default download directory if it doesn't exist
default_download_dir = os.path.expanduser("~/Documents/Daily Motion Downloads")
if not os.path.exists(default_download_dir):
    os.makedirs(default_download_dir)

# Global variable to store the download process
download_process = None

def fetch_formats():
    video_url = video_url_entry.get()
    if not video_url:
        messagebox.showerror("Error", "Please enter a video URL")
        return

    # Use yt-dlp to get available formats
    result = subprocess.run(['yt-dlp', '-F', video_url], capture_output=True, text=True)
    if result.returncode != 0:
        messagebox.showerror("Error", f"Failed to fetch video formats:\n{result.stderr}\n{result.stdout}")
        return
    
    formats = result.stdout.splitlines()
    # Filter valid HLS links
    format_choices = [line for line in formats if 'hls' in line]

    if not format_choices:
        messagebox.showerror("Error", f"No HLS video formats found.\nComplete Output:\n{result.stdout}")
        return

    formats_listbox.delete(0, tk.END)
    for line in format_choices:
        formats_listbox.insert(tk.END, line)

    # Preview the video
    preview_video(video_url)

def download_video():
    global download_process
    selected_index = formats_listbox.curselection()
    if not selected_index:
        messagebox.showerror("Error", "No format selected")
        return

    selected_format = formats_listbox.get(selected_index).strip().split()[0]
    video_url = video_url_entry.get()
    if not selected_format or not video_url:
        messagebox.showerror("Error", "No format selected or invalid video URL")
        return

    # Extracting the video name to use for saving the file
    video_name_command = ['yt-dlp', '--get-filename', '-f', selected_format, video_url]
    video_name_result = subprocess.run(video_name_command, capture_output=True, text=True)
    video_name = video_name_result.stdout.strip()

    def run_download():
        global download_process
        # Set the download path to the default directory
        download_path = os.path.join(default_download_dir, video_name)
        
        download_command = [
            'yt-dlp', 
            '-f', selected_format, 
            '-o', download_path,
            '--external-downloader', 'aria2c',  # Use aria2c as the external downloader
            '--external-downloader-args', '-x 16 -s 16 -k 1M',  # Adjust aria2c settings for performance
            video_url
        ]

        download_process = subprocess.Popen(download_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        for line in download_process.stdout:
            print(line.strip())  # Print download progress in the cmd window
            if "%" in line:
                percentage = line.strip().split()[1]
                root.after(0, lambda: progress_var.set(f"Download Progress: {percentage}"))

        stdout, stderr = download_process.communicate()
        if download_process.returncode == 0:
            root.after(0, lambda: [messagebox.showinfo("Success", "Video downloaded successfully"), clear_all()])

    # Run download in a separate thread to prevent blocking the GUI
    download_thread = threading.Thread(target=run_download)
    download_thread.start()
    status_label.config(text="Download in progress...")

def stop_download():
    global download_process
    if download_process:
        download_process.terminate()
        download_process = None
        # Clear text fields and progress
        video_url_entry.delete(0, tk.END)
        formats_listbox.delete(0, tk.END)
        progress_var.set("")
        status_label.config(text="Download stopped.")
        # Delete part files from the download folder
        part_files = glob.glob(os.path.join(default_download_dir, '*.part'))
        for file in part_files:
            os.remove(file)

def preview_video(video_url):
    video_id = video_url.split('/')[-1]  # Extract video ID from URL
    api_url = f"https://api.dailymotion.com/video/{video_id}?fields=thumbnail_url,title"
    
    response = requests.get(api_url)
    if response.status_code != 200:
        messagebox.showerror("Error", f"Failed to fetch video details:\n{response.text}")
        return

    video_details = response.json()
    thumbnail_url = video_details.get('thumbnail_url')
    video_title = video_details.get('title')

    if not thumbnail_url:
        messagebox.showerror("Error", "Thumbnail URL not found")
        return

    response = requests.get(thumbnail_url)
    image_data = response.content
    image = Image.open(io.BytesIO(image_data))
    image.thumbnail((240, 135))  # Resize to a smaller thumbnail size
    img_tk = ImageTk.PhotoImage(image)

    preview_label.config(image=img_tk)
    preview_label.image = img_tk

    # Set the video title
    title_label.config(text=video_title)

def show_context_menu(event):
    context_menu.tk_popup(event.x_root, event.y_root)

def show_about():
    messagebox.showinfo("About", "Dailymotion Video Downloader\nVersion 1.0\nCreated by Washer.")

def show_help():
    messagebox.showinfo("Help", "1. Enter the Dailymotion video URL.\n2. Click 'Fetch Formats' to get available formats.\n3. Select a format from the list.\n4. Click 'Download Video' to start downloading. \n5. Files are downloaded to \nDocuments/Daily Motion Downloads. \n\n5. Some downloads are faster than others\ndepending on bandwidhth limits\nor just the volume of site traffic.")

def clear_all():
    video_url_entry.delete(0, tk.END)
    formats_listbox.delete(0, tk.END)
    progress_var.set("")
    status_label.config(text="")
    preview_label.config(image='')
    preview_label.image = None
    title_label.config(text="")

# Create the main window
root = tk.Tk()
root.title("Dailymotion Video Downloader")

# Set window size (width x height) and make it non-resizable
root.geometry("400x670")
root.resizable(False, False)  # Disable both horizontal and vertical resizing

# Create a menu bar
menu_bar = tk.Menu(root)

# Add an 'About' menu option
about_menu = tk.Menu(menu_bar, tearoff=0)
about_menu.add_command(label="About", command=show_about)
menu_bar.add_cascade(label="About", menu=about_menu)

# Add a 'Help' menu option
help_menu = tk.Menu(menu_bar, tearoff=0)
help_menu.add_command(label="Help", command=show_help)
menu_bar.add_cascade(label="Help", menu=help_menu)

# Add the menu bar to the main window
root.config(menu=menu_bar)

# Add a 'Clear' menu option
clear_menu = tk.Menu(menu_bar, tearoff=0)
clear_menu.add_command(label="Clear", command=clear_all)
menu_bar.add_cascade(label="Clear", menu=clear_menu)

# Create a context menu for the URL entry field
context_menu = tk.Menu(root, tearoff=0)
context_menu.add_command(label="Paste", command=lambda: video_url_entry.event_generate("<<Paste>>"))

# Add a text field for the video URL
video_url_label = tk.Label(root, text="Video URL:")
video_url_label.pack(pady=5)
video_url_entry = tk.Entry(root, width=50)
video_url_entry.pack(pady=5)
video_url_entry.bind("<Button-3>", show_context_menu)  # Bind right-click to show context menu

# Add a button to fetch formats
fetch_button = tk.Button(root, text="Fetch Formats", command=fetch_formats, bg="#4CAF50", fg="white", font=("Arial", 12))
fetch_button.pack(pady=10)

# Add a listbox to display available formats
formats_listbox = tk.Listbox(root, height=15, width=60, font=("Arial", 10))
formats_listbox.pack(pady=10)

# Add a frame to contain the download and stop buttons
button_frame = tk.Frame(root)
button_frame.pack(pady=10)

# Add a button to download the selected format within the button frame
download_button = tk.Button(button_frame, text="Download Video", command=download_video, bg="#2196F3", fg="white", font=("Arial", 12))
download_button.pack(side=tk.LEFT, padx=5)

# Add a button to stop the download within the button frame
stop_button = tk.Button(button_frame, text="Stop Download", command=stop_download, bg="#f44336", fg="white", font=("Arial", 12))
stop_button.pack(side=tk.LEFT, padx=5)

# Add a label to display download status
status_label = tk.Label(root, text="", font=("Arial", 10))
status_label.pack(pady=5)

# Add a variable and label to show download progress
progress_var = tk.StringVar()
progress_label = tk.Label(root, textvariable=progress_var, font=("Arial", 10))
progress_label.pack(pady=5)

# Add a label for the video title
title_label = tk.Label(root, text="", font=("Arial", 12))
title_label.pack(pady=5)

# Add a label for video preview
preview_label = tk.Label(root)
preview_label.pack(pady=10)

# Run the main loop
root.mainloop()
