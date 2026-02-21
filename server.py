import socket
import threading
import sys
import time
import os
from datetime import datetime

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def server():
    HOST = "0.0.0.0"
    PORT = 5566

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen()
    except Exception as e:
        print(f"Bind/listen failed: {e}")
        sys.exit(1)

    clear_screen()
    print("Server started")
    print("IP address →", get_ip())
    print("Port       →", PORT)
    print("\nAdmin commands (type in this console):")
    print("  clear          - clear console")
    print("  list           - show online nicknames")
    print("  kick <name>    - kick user by nickname")
    print("  msgall <text>  - send message to everyone")
    print("  whois <name>   - show detailed info about user")
    print("  restart        - close all clients, keep server running")
    print("  help           - show this list again")
    print("  shutdown       - stop server")
    print("-" * 60)
    print("Waiting for connections...\n")

    clients = []
    nicknames = []
    addresses = []
    join_times = []  # new: store join datetime for each client

    def broadcast(message, exclude_client=None):
        for client in clients:
            if client != exclude_client:
                try:
                    client.send(message)
                except:
                    pass

    def handle(client):
        index = clients.index(client)
        nickname = nicknames[index]

        while True:
            try:
                message = client.recv(1024)
                if not message:
                    break
                broadcast(message, client)
            except:
                break

        # Cleanup
        try:
            clients.remove(client)
            nicknames.remove(nickname)
            addresses.pop(index)
            join_times.pop(index)
            client.close()
            broadcast(f"{nickname} left the chat.".encode("utf-8"))
            print(f"{nickname} disconnected")
        except:
            pass

    def accept_connections():
        while True:
            try:
                client, address = server_socket.accept()
                print(f"New connection from {address}")

                client.send("NICK".encode("utf-8"))
                nickname_raw = client.recv(1024).decode("utf-8").strip()

                if not nickname_raw:
                    client.close()
                    continue

                nickname = nickname_raw

                clients.append(client)
                nicknames.append(nickname)
                addresses.append(address)
                join_times.append(datetime.now())  # record join time

                print(f"{nickname} joined")
                broadcast(f"{nickname} joined the chat!".encode("utf-8"))
                client.send("Connected to server!".encode("utf-8"))

                thread = threading.Thread(target=handle, args=(client,))
                thread.daemon = True
                thread.start()

            except Exception as e:
                print(f"Accept error: {e}")
                break

    accept_thread = threading.Thread(target=accept_connections, daemon=True)
    accept_thread.start()

    while True:
        try:
            cmd_input = input("").strip()
            if not cmd_input:
                continue

            cmd_parts = cmd_input.split(" ", 1)
            cmd = cmd_parts[0].lower()
            arg = cmd_parts[1] if len(cmd_parts) > 1 else ""

            if cmd == "clear":
                clear_screen()
                print("Console cleared\n")

            elif cmd == "help":
                print("\nAdmin commands:")
                print("  clear          - clear console")
                print("  list           - show online nicknames")
                print("  kick <name>    - kick user by nickname")
                print("  msgall <text>  - send message to everyone")
                print("  whois <name>   - show detailed info about user")
                print("  restart        - close all clients, keep server running")
                print("  shutdown       - stop server")
                print()

            elif cmd == "list":
                if nicknames:
                    print("Online users:")
                    for nick in nicknames:
                        print(f"  {nick}")
                else:
                    print("No users online")
                print()

            elif cmd == "kick" and arg:
                target = arg.strip()
                if target in nicknames:
                    index = nicknames.index(target)
                    client = clients[index]
                    try:
                        client.send("You were kicked by admin.".encode("utf-8"))
                        client.close()
                    except:
                        pass
                    nicknames.pop(index)
                    clients.pop(index)
                    addresses.pop(index)
                    join_times.pop(index)
                    broadcast(f"{target} was kicked by admin.".encode("utf-8"))
                    print(f"Kicked {target}")
                else:
                    print(f"User '{target}' not found")

            elif cmd == "msgall" and arg:
                message = f"[SERVER] {arg}"
                broadcast(message.encode("utf-8"))
                print(f"Sent to all: {arg}")

            elif cmd == "whois" and arg:
                target = arg.strip()
                if target in nicknames:
                    index = nicknames.index(target)
                    addr = addresses[index]
                    join_time = join_times[index]
                    time_online = datetime.now() - join_time
                    hours, remainder = divmod(time_online.seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    online_str = f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"

                    print(f"User: {target}")
                    print(f"  IP: {addr[0]}")
                    print(f"  Port: {addr[1]}")
                    print(f"  Joined: {join_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"  Time online: {online_str}")
                    print(f"  Socket active: {client.fileno() if client.fileno() != -1 else 'closed'}")
                else:
                    print(f"User '{target}' not found")

            elif cmd == "restart":
                print("Restarting connections...")
                broadcast("Server is restarting connections...".encode("utf-8"))
                for client in clients[:]:
                    try:
                        client.close()
                    except:
                        pass
                clients.clear()
                nicknames.clear()
                addresses.clear()
                join_times.clear()
                print("All clients disconnected. Accepting new connections.")

            elif cmd == "shutdown":
                print("Shutting down...")
                broadcast("Server is shutting down.".encode("utf-8"))
                for client in clients:
                    try:
                        client.close()
                    except:
                        pass
                server_socket.close()
                print("Server stopped.")
                sys.exit(0)

            else:
                print("Unknown command. Type 'help' for list.")

        except KeyboardInterrupt:
            print("\nCtrl+C detected. Shutting down...")
            broadcast("Server stopped.".encode("utf-8"))
            for client in clients:
                try:
                    client.close()
                except:
                    pass
            server_socket.close()
            sys.exit(0)
        except Exception as e:
            print(f"Command error: {e}")

if __name__ == "__main__":
    server()
