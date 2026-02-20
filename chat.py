import socket
import threading
import sys
import time

def clear_screen():
    print("\n" * 80)

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

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()

    print("Server started")
    print("IP address →", get_ip())
    print("Port       →", PORT)
    print("Waiting for people to join...\n")

    clients = []
    nicknames = []

    def broadcast(message):
        for client in clients:
            try:
                client.send(message)
            except:
                pass

    def handle(client):
        while True:
            try:
                message = client.recv(1024)
                if not message:
                    break
                broadcast(message)
            except:
                index = clients.index(client)
                clients.remove(client)
                client.close()
                nickname = nicknames[index]
                broadcast(f"{nickname} left the chat.".encode("utf-8"))
                nicknames.remove(nickname)
                break

    while True:
        try:
            client, address = server.accept()
            print(f"Connected with {address}")

            client.send("NICK".encode("utf-8"))
            nickname = client.recv(1024).decode("utf-8").strip()

            nicknames.append(nickname)
            clients.append(client)

            print(f"Nickname is {nickname}")
            broadcast(f"{nickname} joined the chat!".encode("utf-8"))
            client.send("Connected to server!".encode("utf-8"))

            thread = threading.Thread(target=handle, args=(client,))
            thread.daemon = True
            thread.start()

        except:
            break

def client():
    clear_screen()
    print("Simple Chat Client")
    print("-------------------\n")

    HOST = input("Server IP: ").strip()
    if not HOST:
        HOST = "127.0.0.1"

    try:
        PORT = int(input("Port (usually 5566): ").strip() or "5566")
    except:
        PORT = 5566

    nickname = input("Choose your nickname: ").strip()
    if not nickname:
        nickname = "User" + str(int(time.time()) % 10000)

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client.connect((HOST, PORT))
    except:
        print("\nCannot connect. Is the server running?")
        print("Press Enter to exit...")
        input()
        sys.exit()

    def receive():
        while True:
            try:
                message = client.recv(1024).decode("utf-8")
                if message == "NICK":
                    client.send(nickname.encode("utf-8"))
                else:
                    print(message)
            except:
                print("Lost connection to server.")
                client.close()
                break

    receive_thread = threading.Thread(target=receive, daemon=True)
    receive_thread.start()

    print("\nYou are connected! Type messages and press Enter.")
    print("Type /quit to leave.\n")

    while True:
        message = input("")
        if message.lower() in ["/quit", "/exit", "quit", "exit"]:
            client.send(f"{nickname} left the chat.".encode("utf-8"))
            client.close()
            break
        if message.strip():
            client.send(f"{nickname}: {message}".encode("utf-8"))


if __name__ == "__main__":
    clear_screen()
    print("Simple LAN Chat 2025")
    print("1 = Run as SERVER")
    print("2 = Run as CLIENT")
    print("-------------------")

    choice = input("Choose (1 or 2): ").strip()

    if choice == "1":
        server()
    elif choice == "2":
        client()
    else:
        print("Wrong choice. Closing.")