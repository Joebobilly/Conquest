import socket
import threading
import time

clients = []
global land_data
global building_data
land_data=[str(open('Land.txt').read())]
building_data=[str(open("Buildings2.txt").read())]
def landedit(data):
    tland=land_data[0].split('\n')
    tland[ord(data[1])]=list(tland[ord(data[1])])
    tland[ord(data[1])][ord(data[0])]=data[2]
    tland[ord(data[1])]=''.join(tland[ord(data[1])])
    tland='\n'.join(tland)
    land_data[0]=tland
def buildedit(data):
    tbuild=building_data[0].split('\n')
    tbuild[ord(data[1])]=list(tbuild[ord(data[1])])
    tbuild[ord(data[1])][ord(data[0])]=data[2]
    tbuild[ord(data[1])]=''.join(tbuild[ord(data[1])])
    tbuild='\n'.join(tbuild)
    building_data[0]=tbuild
def broadcast(message):
    for client in clients:
        try:
            client.sendall(message.encode())
        except:
            clients.remove(client)
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
            elif data == "RECV2":
                conn.sendall(('..'+land_data[0]).encode())
            elif data == "RECV":
                try:
                    qu=''
                    y=-1
                    for i in building_data[0].split('\n'):
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
            else:
                if data.startswith('T'):
                    data=data[1:]
                    landedit(data)
                    print("set_tile("+str(ord(data[0]))+","+str(ord(data[1]))+','+data[2]+')')
                    broadcast("set_tile_nosend("+str(ord(data[0]))+","+str(ord(data[1]))+',"'+data[2]+'")')
                    open("Land.txt",'w').write(land_data[0])
                elif data.startswith('B'):
                    data=data[1:]
                    buildedit(data)
                    if data[2]!='"':
                        print("set_building("+str(ord(data[0]))+","+str(ord(data[1]))+','+data[2]+')')
                        broadcast("set_building_nosend("+str(ord(data[0]))+","+str(ord(data[1]))+',"'+data[2]+'")')
                    else:
                        broadcast("set_building_nosend("+str(ord(data[0]))+","+str(ord(data[1]))+",'"+data[2]+"')")
                    open("Buildings2.txt",'w').write(building_data[0])
            print(f"[{addr}] {data}")
        except Exception as e:
            print(e)
            clients.remove(conn)
            conn.close()
            break



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
        if msg=="EXIT":
            break
        broadcast(msg)
    
    

if __name__ == "__main__":
    threading.Thread(target=start_server, daemon=True).start()
    broadcast_loop()
