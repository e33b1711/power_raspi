import socket, time, sys
import threading
import pprint

TCP_IP = 'localhost'
TCP_PORT = 7777
BUFFER_SIZE = 1024

clientCount = 0

class server():

    def __init__(self):
        self.CLIENTS = []        


    def startServer(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind((TCP_IP,TCP_PORT))
            s.listen(10)
            while 1:
                client_socket, addr = s.accept()
                print ('Connected with ' + addr[0] + ':' + str(addr[1]))
                global clientCount
                clientCount = clientCount+1
                print (clientCount)
                # register client
                self.CLIENTS.append(client_socket)
                threading.Thread(target=self.playerHandler, args=(client_socket,)).start()
            s.close()
        except socket.error as msg:
            print ('Could Not Start Server Thread. Error Code : ') #+ str(msg[0]) + ' Message ' + msg[1]
            sys.exit()


   #client handler :one of these loops is running for each thread/player   
    def playerHandler(self, client_socket):
        #send welcome msg to new client
        client_socket.send(bytes('{"type": "bet","value": "1"}', 'UTF-8'))
        while 1:
            data = client_socket.recv(BUFFER_SIZE)
            if not data: 
                break
            #print ('Data : ' + repr(data) + "\n")
            #data = data.decode("UTF-8")
            # broadcast
            for client in self.CLIENTS.values():
                client.send(data)

         # the connection is closed: unregister
        self.CLIENTS.remove(client_socket)
        #client_socket.close() #do we close the socket when the program ends? or for ea client thead?

    def broadcast(self, message):

        for c in self.CLIENTS:
            c.send(message.encode("utf-8"))

    def _broadcast(self):        
        for sock in self.CLIENTS:           
            try :
                self._send(sock)
            except socket.error:                
                sock.close()  # closing the socket connection
                self.CLIENTS.remove(sock)  # removing the socket from the active connections list

    def _send(self, sock):        
        # Packs the message with 4 leading bytes representing the message length
        #msg = struct.pack('>I', len(msg)) + msg
        # Sends the packed message
        sock.send(bytes('{"type": "bet","value": "1"}', 'UTF-8'))


if __name__ == '__main__':
    s = server() #create new server listening for connections
    threading.Thread(target=s.startServer).start()

    while 1:       
        s._broadcast()
        pprint.pprint(s.CLIENTS)
        print(len(s.CLIENTS)) #print out the number of connected clients every 5s
        time.sleep(5) 