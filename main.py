import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, Listbox, END

HOST = "127.0.0.1"
PORT = 5566
FORMAT = "utf-8"

class ChatGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Chat App")
        self.root.geometry("600x800")
        self.root.configure(bg="#0f1117")

        self.nickname = ""
        self.socket = None
        self.online_users = set()

        # Main (global) chat
        self.chat_area = scrolledtext.ScrolledText(
            self.root, state='disabled', bg="#1a1d26", fg="#e0e0ff",
            font=("Segoe UI", 12), wrap=tk.WORD
        )
        self.chat_area.pack(padx=15, pady=15, fill=tk.BOTH, expand=True)

        # Input for global
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

        # Sidebar users
        sidebar = tk.Frame(self.root, width=220, bg="#16181f")
        sidebar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0,15), pady=15)

        tk.Label(
            sidebar, text="Online Users", bg="#16181f", fg="#7289da",
            font=("Segoe UI", 13, "bold")
        ).pack(anchor="w", pady=(0,10))

        self.users_list = Listbox(
            sidebar, bg="#1a1d26", fg="#dcddde", font=("Segoe UI", 11),
            selectbackground="#5865f2", selectforeground="white",
            relief="flat", bd=0
        )
        self.users_list.pack(fill=tk.BOTH, expand=True)
        self.users_list.bind("<<ListboxSelect>>", self.open_private_chat)

        self.private_windows = {}   # nickname -> window

        self.connect_window()

        self.root.mainloop()

    def connect_window(self):
        win = tk.Toplevel(self.root)
        win.title("Join")
        win.geometry("400x300")
        win.configure(bg="#0f1117")
        win.grab_set()

        tk.Label(win, text="Server IP", bg="#0f1117", fg="white").pack(pady=10)
        ip_entry = tk.Entry(win, bg="#252a38", fg="white")
        ip_entry.insert(0, "127.0.0.1")
        ip_entry.pack(pady=5, padx=40, fill=tk.X)

        tk.Label(win, text="Port", bg="#0f1117", fg="white").pack(pady=10)
        port_entry = tk.Entry(win, bg="#252a38", fg="white")
        port_entry.insert(0, "5566")
        port_entry.pack(pady=5, padx=40, fill=tk.X)

        tk.Label(win, text="Nickname", bg="#0f1117", fg="white").pack(pady=10)
        nick_entry = tk.Entry(win, bg="#252a38", fg="white")
        nick_entry.insert(0, "")
        nick_entry.pack(pady=5, padx=40, fill=tk.X)

        def connect():
            global HOST, PORT
            HOST = ip_entry.get().strip() or "127.0.0.1"
            try:
                PORT = int(port_entry.get().strip() or "5566")
            except:
                PORT = 5566
            self.nickname = nick_entry.get().strip() or "User"
            win.destroy()
            self.start_connection()

        tk.Button(win, text="Connect", command=connect,
                  bg="#5865f2", fg="white", font=("Segoe UI", 12, "bold")).pack(pady=30)

    def start_connection(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((HOST, PORT))
            threading.Thread(target=self.receive, daemon=True).start()
            self.add_global("Connected.")
        except Exception as e:
            self.add_global(f"Connection failed: {e}")
            self.root.after(3000, self.root.quit)

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
                    self.online_users = set(users)
                    self.root.after(0, self.update_user_list)

                else:
                    # Normal message or PM
                    if msg.startswith("[PM]"):
                        # Example: [PM from sender] message
                        parts = msg.split(" ", 3)
                        if len(parts) >= 4 and parts[1] == "from":
                            sender = parts[2]
                            content = parts[3]
                            self.root.after(0, self.add_to_private, sender, f"{sender}: {content}")
                    else:
                        self.root.after(0, self.add_global, msg)

            except:
                self.root.after(0, self.add_global, "Disconnected.")
                break

    def update_user_list(self):
        self.users_list.delete(0, END)
        for user in sorted(self.online_users):
            if user != self.nickname:
                self.users_list.insert(END, user)

    def add_global(self, msg):
        self.chat_area.config(state='normal')
        self.chat_area.insert(END, msg + "\n")
        self.chat_area.config(state='disabled')
        self.chat_area.see(END)

    def send_global(self):
        text = self.msg_entry.get().strip()
        if not text:
            return
        try:
            self.socket.send(text.encode(FORMAT))
            self.add_global(f"You: {text}")
        except:
            self.add_global("Send failed.")
        self.msg_entry.delete(0, END)

    def open_private_chat(self, event):
        selection = self.users_list.curselection()
        if not selection:
            return
        target = self.users_list.get(selection[0])
        if target in self.private_windows and self.private_windows[target].winfo_exists():
            self.private_windows[target].lift()
            return

        self.create_private_window(target)

    def create_private_window(self, target):
        win = tk.Toplevel(self.root)
        win.title(f"Chat with {target}")
        win.geometry("400x350")
        win.configure(bg="#0f1117")

        chat = scrolledtext.ScrolledText(
            win, state='disabled', bg="#1a1d26", fg="#e0e0ff",
            font=("Segoe UI", 12)
        )
        chat.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        frame = tk.Frame(win, bg="#0f1117")
        frame.pack(fill=tk.X, padx=10, pady=(0,10))

        entry = tk.Entry(frame, bg="#252a38", fg="white", font=("Segoe UI", 12))
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0,10))
        entry.focus()

        def send_pm():
            text = entry.get().strip()
            if not text:
                return
            try:
                self.socket.send(f"/pm {target} {text}".encode(FORMAT))
                chat.config(state='normal')
                chat.insert(END, f"You: {text}\n")
                chat.config(state='disabled')
                chat.see(END)
            except:
                chat.config(state='normal')
                chat.insert(END, "Send failed.\n")
                chat.config(state='disabled')
            entry.delete(0, END)

        btn = tk.Button(frame, text="Send", command=send_pm,
                        bg="#5865f2", fg="white", font=("Segoe UI", 10, "bold"),
                        width=8)
        btn.pack(side=tk.RIGHT, ipadx=8, ipady=6)

        entry.bind("<Return>", lambda e: send_pm())

        self.private_windows[target] = win

        def on_close():
            del self.private_windows[target]
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_close)

    def add_to_private(self, target, msg):
        if target not in self.private_windows or not self.private_windows[target].winfo_exists():
            self.create_private_window(target)
        chat = self.private_windows[target].winfo_children()[0]
        chat.config(state='normal')
        chat.insert(END, msg + "\n")
        chat.config(state='disabled')
        chat.see(END)


if __name__ == "__main__":
    ChatGUI()
