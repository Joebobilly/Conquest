import socket
import threading
import time

clients = []

def handle_client(conn, addr):
    print(f"[+] Connected by {addr}")
    while True:
        try:
            data = conn.recv(1024).decode()
            if not data:
                break
            if data == "EXIT":
                print(f"[-] {addr} disconnected.")
                clients.remove(conn)
                conn.close()
                break
            if data == "RECV2":
                with open('Land.txt') as f:
                    conn.sendall(('..'+str(f.read())).encode())
            if data == "RECV":
                try:
                    with open('Buildings2.txt') as q:
                        q=str(q.read())
                        qu=''
                        y=-1
                        for i in q.split('\n'):
                            y+=1
                            x=-1
                            for i2 in i:
                                x+=1
                                if ord(i2)==0:
                                    continue
                                else:
                                    qu+=chr(x)+chr(y)+i2

                        nqu=''
                        ru=0
                        px=-2
                        py=-2
                        for i in range(int(len(qu)/3)):
                            if ord(qu[i*3])-px==1 and ord(qu[i*3+1])-py==0 and ru==0:
                                ru=1
                                nqu=list(nqu)
                                nqu[-3]=chr(ord(nqu[-3])+100)
                                nqu=''.join(nqu)
                                nqu+=qu[i*3+2]
                                px+=1
                                continue
                            elif ru and ord(qu[i*3])-px==1 and ord(qu[i*3+1])-py==0:
                                nqu+=qu[i*3+2]
                                px+=1
                                continue
                            elif ru:
                                nqu+=chr(0)
                                ru=0
                            px=ord(qu[i*3])
                            py=ord(qu[i*3+1])
                            nqu+=qu[i*3:i*3+3]
                        f='..'+nqu
                        conn.sendall(f.encode())
                        print('sent')
                except Exception as e:
                    print(e)
            print(f"[{addr}] {data}")
        except:
            clients.remove(conn)
            conn.close()
            break

def broadcast(message):
    for client in clients:
        try:
            client.sendall(message.encode())
        except:
            clients.remove(client)

def start_server(host='0.0.0.0', port=12345):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    print(f"[SERVER] Listening on {host}:{port}")
    while True:
        conn, addr = server.accept()
        clients.append(conn)
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

# Example usage of broadcasting
def broadcast_loop():
    while True:
        msg = input("[SERVER BROADCAST] > ")
        broadcast(msg)

if __name__ == "__main__":
    threading.Thread(target=start_server, daemon=True).start()
    broadcast_loop()
