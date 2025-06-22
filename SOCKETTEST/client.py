import socket
import threading
import time

def listen_for_messages(sock):
    while True:
        try:
            message = sock.recv(1024).decode()
            if message:
                print(f"[SERVER] {message}")
        except:
            print("[ERROR] Lost connection to server.")
            sock.close()
            break

def start_client(server_ip='127.0.0.1', server_port=12345):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server_ip, server_port))
    sock.sendall("JOIN".encode())

    threading.Thread(target=listen_for_messages, args=(sock,), daemon=True).start()

    try:
        while True:
            time.sleep(0.2)
            continue
            msg = input("> ")
            if msg.lower() == 'exit':
                sock.sendall("EXIT".encode())
                break
            sock.sendall(msg.encode())
    finally:
        sock.close()

if __name__ == "__main__":
    start_client()
