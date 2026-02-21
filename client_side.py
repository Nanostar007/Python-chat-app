import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, END
from datetime import datetime
import json
import os
import random
import tkinter.messagebox as msgbox

HOST = ""
PORT = 5566
FORMAT = "utf-8"
SETTINGS_FILE = "chat_settings.json"

class ChatGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Chat App")
        self.root.geometry("800x650")
        self.root.configure(bg="#0f1117")

        self.nickname = f"Chatter{random.randint(10000, 99999)}"
        self.socket = None
        self.muted_users = set()
        self.online_count = 0

        self.status_label = tk.Label(
            self.root, text="Disconnected", bg="#0f1117", fg="#ff5555",
            font=("Segoe UI", 10), anchor="w"
        )
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=(0,5))

        search_frame = tk.Frame(self.root, bg="#0f1117")
        search_frame.pack(fill=tk.X, padx=15, pady=(10,0))

        tk.Label(search_frame, text="Search:", bg="#0f1117", fg="#aaaaaa",
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)

        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                                     bg="#252a38", fg="white", font=("Segoe UI", 11))
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, ipady=4)
        self.search_var.trace("w", self.highlight_search)

        self.chat_area = scrolledtext.ScrolledText(
            self.root, state='disabled', bg="#1a1d26", fg="#e0e0ff",
            font=("Segoe UI", 12), wrap=tk.WORD
        )
        self.chat_area.pack(padx=15, pady=5, fill=tk.BOTH, expand=True)

        self.chat_area.tag_config("time", foreground="#888888")
        self.chat_area.tag_config("own", foreground="#00ff9d")
        self.chat_area.tag_config("other", foreground="#e0e0ff")
        self.chat_area.tag_config("system", foreground="#ffaa55", font=("Segoe UI", 11, "italic"))
        self.chat_area.tag_config("muted", foreground="#555566")
        self.chat_area.tag_config("highlight", background="#444466", foreground="white")

        self.chat_area.bind("<Double-Button-1>", self.copy_message)

        input_frame = tk.Frame(self.root, bg="#0f1117")
        input_frame.pack(fill=tk.X, padx=15, pady=(0,15))

        self.msg_entry = tk.Entry(
            input_frame, font=("Segoe UI", 13), bg="#252a38", fg="white",
            insertbackground="white"
        )
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0,10))
        self.msg_entry.bind("<Return>", lambda e: self.send_global())

        send_btn = tk.Button(
            input_frame, text="Send", command=self.send_global,
            bg="#5865f2", fg="white", font=("Segoe UI", 11, "bold"),
            width=10, relief="flat"
        )
        send_btn.pack(side=tk.RIGHT, ipadx=10, ipady=8)

        sidebar = tk.Frame(self.root, width=220, bg="#16181f")
        sidebar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0,15), pady=15)

        self.online_label = tk.Label(
            sidebar, text="Online: 0", bg="#16181f", fg="#7289da",
            font=("Segoe UI", 13, "bold")
        )
        self.online_label.pack(anchor="w", pady=(0,10))

        self.connect_window()

        self.root.mainloop()

    def connect_window(self):
        win = tk.Toplevel(self.root)
        win.title("Connect")
        win.geometry("400x280")
        win.configure(bg="#0f1117")
        win.grab_set()

        tk.Label(win, text="Server IP", bg="#0f1117", fg="white", font=("Segoe UI", 11)).pack(pady=10)
        ip_entry = tk.Entry(win, bg="#252a38", fg="white", font=("Segoe UI", 12))
        ip_entry.pack(pady=5, padx=40, fill=tk.X, ipady=6)

        tk.Label(win, text="Port", bg="#0f1117", fg="white", font=("Segoe UI", 11)).pack(pady=10)
        port_entry = tk.Entry(win, bg="#252a38", fg="white", font=("Segoe UI", 12))
        port_entry.pack(pady=5, padx=40, fill=tk.X, ipady=6)

        last_ip, last_port = self.load_settings()
        ip_entry.insert(0, last_ip)
        port_entry.insert(0, str(last_port))

        def connect():
            global HOST, PORT
            HOST = ip_entry.get().strip() or "127.0.0.1"
            try:
                PORT = int(port_entry.get().strip() or "5566")
            except:
                PORT = 5566
            self.save_settings(HOST, PORT)
            win.destroy()
            self.connect_to_server()

        tk.Button(win, text="Connect", command=connect,
                  bg="#5865f2", fg="white", font=("Segoe UI", 12, "bold")).pack(pady=30)

        win.bind("<Return>", lambda e: connect())

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    return data.get("last_ip", ""), data.get("last_port", 5566)
            except:
                pass
        return "", 5566

    def save_settings(self, ip, port):
        data = {"last_ip": ip, "last_port": port}
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f)

    def connect_to_server(self):
        self.status_label.config(text="Connecting...", fg="#ffaa00")
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((HOST, PORT))
            self.status_label.config(text=f"Connected as {self.nickname}", fg="#55ff55")
            threading.Thread(target=self.receive, daemon=True).start()
            self.add_global(f"Joined as {self.nickname}", tag="system")
        except Exception as e:
            self.status_label.config(text="Connection failed", fg="#ff5555")
            self.add_global(f"Connection failed: {e}", tag="system")
            self.root.after(4000, self.root.quit)

    def receive(self):
        while True:
            try:
                msg = self.socket.recv(1024).decode(FORMAT).strip()
                if not msg:
                    break

                if msg == "NICK":
                    self.socket.send(self.nickname.encode(FORMAT))

                elif msg.startswith("USERS:"):
                    users = [u.strip() for u in msg[6:].split(",") if u.strip()]
                    self.online_count = len([u for u in users if u != self.nickname])
                    self.root.after(0, self.update_online_count)

                else:
                    # Skip own message echoed back
                    if msg.startswith(self.nickname + ":") or "You:" in msg:
                        continue

                    if any(muted in msg for muted in self.muted_users):
                        continue

                    self.root.after(0, self.add_global, msg)

            except:
                self.root.after(0, lambda: self.status_label.config(text="Disconnected", fg="#ff5555"))
                self.root.after(0, self.add_global, "Disconnected from server.", tag="system")
                break

    def update_online_count(self):
        self.online_label.config(text=f"Online: {self.online_count}")

    def add_global(self, msg, is_own=False, tag=None):
        time_str = datetime.now().strftime("%H:%M")
        color_tag = tag if tag else ("own" if is_own else "other")

        self.chat_area.config(state='normal')
        self.chat_area.insert(END, f"[{time_str}] ", "time")
        self.chat_area.insert(END, f"{msg}\n", color_tag)
        self.chat_area.config(state='disabled')
        self.chat_area.see(END)

        self.highlight_search()

    def send_global(self):
        text = self.msg_entry.get().strip()
        if not text:
            return

        try:
            self.socket.send(text.encode(FORMAT))
            self.add_global(text, is_own=True)
        except:
            self.add_global("Send failed.", tag="system")
        self.msg_entry.delete(0, END)

    def copy_message(self, event):
        try:
            start = self.chat_area.index("current linestart")
            end = self.chat_area.index("current lineend")
            text = self.chat_area.get(start, end).strip()
            if text:
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                self.root.update()
        except:
            pass

    def highlight_search(self, *args):
        search_text = self.search_var.get().strip().lower()
        self.chat_area.tag_remove("highlight", "1.0", END)
        if not search_text:
            return

        self.chat_area.config(state='normal')
        pos = "1.0"
        while True:
            pos = self.chat_area.search(search_text, pos, stopindex=END, nocase=True)
            if not pos:
                break
            end = f"{pos}+{len(search_text)}c"
            self.chat_area.tag_add("highlight", pos, end)
            pos = end
        self.chat_area.config(state='disabled')


if __name__ == "__main__":
    ChatGUI()