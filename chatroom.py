
import socket
import threading
import select
import sys
import time

#############################################################################################################
#TCP Server & Client

class ServerTCP:
    def __init__(self, server_port):

        #Address and Port
        """
        ServerTCP constructor

        Parameters
        ----------
        server_port : int
            The port number to listen on

        Attributes
        ----------
        server_port : int
            The port number to listen on
        addr : str
            The IPv4 address of the server
        server_socket : socket
            The socket listening for incoming connections
        clients : dict
            Mapping of client sockets to client names
        run_event : threading.Event
            Event to signal when the server should shut down
        handle_event : threading.Event
            Event to signal when the server should start accepting new clients
        """

        self.server_port = server_port
        server_addr = socket.gethostbyname(socket.gethostname())

        #Init Socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((server_addr, server_port))
        self.server_socket.listen(9)
        print(f'Server listening on {server_addr}:{server_port}')
        self.clients = {}

        #Threading
        self.run_event = threading.Event()
        self.handle_event = threading.Event()

    def accept_client(self):
        """
        Accept new clients and create a new thread to handle each client connection
        Continuously listen for new connections until the server is shut down

        Parameters
        ----------
        None

        Attributes
        ----------
        None

        Returns
        -------
        None
        """
        print("Waiting for clients to connect...")
        try:
            read_sockets, _, _ = select.select([self.server_socket], [], [], 1)
            if read_sockets:
                connection_socket, client_addr = self.server_socket.accept()
                print(f"Accepted connection from {client_addr}")
                name = connection_socket.recv(1024).decode()

                if name in self.clients.values():
                    connection_socket.send("Name already taken".encode())
                    connection_socket.close()
                    print(f"Connection closed for {client_addr}: Name already taken")
                    return False

                else:
                    connection_socket.send("Welcome".encode())
                    self.broadcast(connection_socket, f"join")
                    self.clients[connection_socket] = name
                    return True
        except Exception as e:
            print(f"Error Occurred Accepting Client: {e}")
        return False




    def close_client(self, client_socket):
        """
        Close a client connection and broadcast the exit message to all other clients

        Parameters
        ----------
        client_socket : socket
            The socket object for the client connection to be closed

        Attributes
        ----------
        None

        Returns
        -------
        bool
            True if the client connection was closed successfully, False otherwise
        """

        if client_socket in self.clients:
            try:
                name = self.clients.pop(client_socket)
                client_socket.close()
                print(f"{name} has left the chat.")
                return True
                
            except Exception as e:
                print(f"Error closing the client: {e}")
        return False


    def broadcast(self, client_socket_sent, message):
        """
        Broadcast a message to all other clients

        Parameters
        ----------
        client_socket_sent : socket
            The socket object for the client that sent the message
        message : str
            The message to be broadcast

        Attributes
        ----------
        None

        Returns
        -------
        None
        """
        msg=""
        name = self.clients.get(client_socket_sent, "Unknown")
        if message.lower() == "exit":
            msg = f"User {name} left"
        elif message.lower() == "join":
            msg = f"User {name} joined"
        else:msg = f"{name}: {message}"
        try:
            for client_iter in self.clients:
                if client_iter != client_socket_sent:
                    client_iter.send(msg.encode())
        except Exception as e:
            print(e)
    def shutdown(self):
        """
        Shut down the server

        Parameters
        ----------
        None

        Attributes
        ----------
        None

        Returns
        -------
        None
        """
        
        print("Shutting down the server...")
        
        try:
            self.run_event.set()
            self.handle_event.set()

            for socket_iter in list(self.clients.keys()):
                
                socket_iter.send("server-shutdown".encode())
                self.close_client(socket_iter)

        
            
            self.server_socket.close()
            print("Server has been shut down.")

        except Exception as e:
            print(f"Error at ServerTCP shutdown: {e}")
    def get_clients_number(self):
        """
        Get the number of connected clients

        Parameters
        ----------
        None

        Returns
        -------
        int
            The number of clients currently connected to the server
        """
        return len(self.clients)
        

    def handle_client(self, client_socket):
        """
        Handle a single client connection.

        Parameters
        ----------
        client_socket : socket
            The socket object for the client connection

        Attributes
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        This function is run in a separate thread for each client connection.
        It listens for incoming messages, broadcasts them to all other clients,
        and closes the client connection when it is done.
        """
        name = self.clients[client_socket]
        while not self.handle_event.is_set():
            try:
                if select.select([client_socket], [], [], 1)[0]:
                    message = client_socket.recv(1024).decode()
                    self.broadcast(client_socket, message)
                    if message.lower() == f"exit":
                        break
            except Exception as e:
                print(f"Error handling client: {e}")
                break

        self.close_client(client_socket)


    def run(self):
        """
        Start the server and begin listening for incoming connections

        Parameters
        ----------
        None

        Attributes
        ----------
        None

        Returns
        -------
        None
        """
        
        while not self.run_event.is_set():
            try:

                if self.accept_client():
                    client_socket = list(self.clients.keys())[-1]
                    print(f'Server started on port {self.server_port}')
                    threading.Thread(target=self.handle_client, args=(client_socket,)).start()
            except KeyboardInterrupt:break
            except Exception as e:
                print(f"Error at ServerTCP run: {e}")
                break
        self.shutdown()

#############################################################################################################

class ClientTCP:

    def __init__(self, client_name, server_port):
        """
        Initialize a new ClientTCP instance.

        Parameters
        ----------
        client_name : str
            The name of the client.
        server_port : int
            The port number to connect to on the server.

        Attributes
        ----------
        server_port : int
            The port number to connect to on the server.
        client_name : str
            The name of the client.
        server_addr : str
            The server's IPv4 address resolved from the hostname.
        client_socket : socket
            The TCP socket for the client's connection.
        exit_run : threading.Event
            Event to signal when the client should stop running.
        exit_receive : threading.Event
            Event to signal when the client should stop receiving messages.
        """
        self.server_port = server_port
        self.client_name = client_name
        self.server_addr = socket.gethostbyname(socket.gethostname())
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.exit_run = threading.Event()
        self.exit_receive = threading.Event()


    def connect_server(self):
        """
        Attempt to connect to the server using the client name.

        This method attempts to establish a TCP connection to the server using
        the client's socket. It sends the client's name to the server and waits
        for a response indicating whether the connection was successful.

        Returns
        -------
        bool
            True if the connection is successful and the server responds with
            "Welcome", False if the name is already taken or an error occurs
            during the connection process.
        """
        try:
            self.client_socket.connect((self.server_addr, self.server_port))
            print(f"Connecting to server at {self.server_addr}...")
            self.client_socket.send(self.client_name.encode())
            return_message = self.client_socket.recv(1024).decode()
            if return_message == "Welcome":
                print("Successfully connected to the server.")
                return True
        except Exception as e:
            print(f"Error connecting to server: {e}")
        return False


    def send(self, text):
        """
        Send a message to the server

        Parameters
        ----------
        text : str
            The message to be sent

        Returns
        -------
        None
        """
        try:
            self.client_socket.send(text.encode())
        except Exception as e:
            print(f"Client-side sending error: {e}")

    def receive(self):
        """
        Receive messages from the server and print them to the console.

        This method continuously receives messages from the server and prints them
        to the console. It also handles the case where the server shuts down by
        printing a message and setting the exit flags.

        Parameters
        ----------
        None

        Attributes
        ----------
        None

        Returns
        -------
        None
        """
        while not self.exit_receive.is_set():
            try:
                if select.select([self.client_socket], [], [], 1)[0]:
                    message = self.client_socket.recv(1024).decode()
                    if message == "server-shutdown":
                        print("Server is shutting down.")
                        break
                print(f"Message: {message}")

            except Exception as e:
                print(f"Client-side receive error: {e}")
                break

        self.exit_run.set()
        self.exit_receive.set()



    def run(self):
        con_stat = self.connect_server()
        print(f"Connection Status: {con_stat}")
        if con_stat:
            print("Connected to server")
            print("TCP CLIENT RUN METHOD")
            thread = threading.Thread(target=self.receive)
            thread.start()
            while not self.exit_run.is_set():
                try:
                    user_message = input()
                    self.send(user_message)

                    if user_message.lower() == "exit":
                        break

                except KeyboardInterrupt:
                    break

                except Exception as error:
                    print(f"Error in the ClientTCP Run method: {error}")
                    break
            self.exit_receive.set()
            self.send("exit")
            self.client_socket.close()

#############################################################################################################
#############################################################################################################
# UDP Server & Client         

class ServerUDP:
    def __init__(self, server_port):
        self.server_port = server_port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.clients= dict()
        self.messages = []
        self.addr = socket.gethostbyname(socket.gethostname())
        self.server_socket.bind((self.addr, self.server_port))
        
        
    def accept_client(self, client_addr, message):
        name = message.split(":")[0]
        try:
            if name not in self.clients.values():
                self.clients[client_addr] = name
                self.server_socket.sendto("Welcome".encode(), client_addr)
                self.messages.append((client_addr,f"User {name} joined"))
                self.broadcast()
                return True
            self.server_socket.sendto("Name already taken".encode(), client_addr)
        except Exception as e:
            print(f"Error at ServerUDP accept_client: {e}")
        return False

    def close_client(self, client_addr):
        try:
            name = self.clients.pop(client_addr)
            self.messages.append((client_addr,f"User {name} left"))
            self.broadcast()
            return True
        except Exception as e:
            print(f"Error at ServerUDP close_client: {e}")
        return False
        
    def broadcast(self):
        try:
            recent_msg = self.messages[-1]
            name = self.clients[recent_msg[0]]
            msg= recent_msg[1]
            for client_iter in self.clients.keys():
                if recent_msg[0] != client_iter:
                    self.server_socket.sendto(msg.encode(), client_iter)
        except Exception as e:
            print(f"Error at ServerUDP broadcast: {e}")

    def shutdown(self):
        try:
            all_clients = list(self.clients.keys())
            for client_iter in all_clients:
                self.server_socket.sendto("server-shutdown".encode(), client_iter)
                self.clients.pop(client_iter)
            self.server_socket.close()
        except Exception as e:
            print(f"Error at ServerUDP shutdown: {e}")
            
    def get_clients_number(self):
        return len(self.clients)
    
    def run(self):
        while True:
            try:
                if select.select([self.server_socket],[],[],1)[0]:
                    message, client_addr = self.server_socket.recvfrom(1024)
                    print(f"Received from {client_addr}: {message.decode()}")
                    message = message.decode()
                    if "join" in message.split(":")[1].strip():
                        self.accept_client(client_addr, message)
                    if  "exit" in message.split(":")[1].strip():
                        self.close_client(client_addr)
                    else:
                        self.messages.append((client_addr, message))
                        self.broadcast()            
            except KeyboardInterrupt:break
            except Exception as e:
                print(f"Error at ServerUDP run: {e}")
                break
        self.shutdown()

#############################################################################################################

class ClientUDP:
    def __init__(self, client_name, server_port):
        """
        ClientUDP constructor

        Parameters
        ----------
        client_name : str
            The name of the client
        server_port : int
            The port number to connect to on the server

        Attributes
        ----------
        server_addr : str
            The IPv4 address of the server
        client_socket : socket
            The UDP socket for the client's connection
        server_port : int
            The port number to connect to on the server
        client_name : str
            The name of the client
        exit_run : threading.Event
            Event to signal when the client should stop running
        exit_receive : threading.Event
            Event to signal when the client should stop receiving messages
        """
        self.server_addr = socket.gethostbyname(socket.gethostname())
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_port = server_port
        self.client_name = client_name

        self.exit_run = threading.Event()
        self.exit_receive = threading.Event()


    
    def connect_server(self):
        """
        Attempt to connect to the server by sending a "join" message to the
        server and waiting for a response. If the response is "Welcome", the
        connection is successful.

        Returns
        -------
        bool
            True if the connection is successful, False if an error occurs
        """
        
        
        try:
            self.send("join")
            data, _ = self.client_socket.recvfrom(1024)
            response = data.decode()
            print( response)

            if response == "Welcome":
                print("Successful!")
                return True
            return False

        except Exception as e:
            print(f"Error during connection: {e}")
        return False
        
        
    def send(self, text):
        """
        Send a message to the server

        Parameters
        ----------
        text : str
            The message to be sent

        Returns
        -------
        None
        """
        try:
            message = f"{self.client_name}:{text}"
            self.client_socket.sendto(message.encode(), (self.server_addr, self.server_port))
        except Exception:
            print("Client-side sending error")


    def receive(self):
        """
        Receive messages from the server and print them to the console.

        This method continuously receives messages from the server and prints them
        to the console. It also handles the case where the server shuts down by
        printing a message and setting the exit flags.

        Parameters
        ----------
        None

        Attributes
        ----------
        None

        Returns
        -------
        None
        """
        while not self.exit_receive.is_set():
            try:
                if select.select([self.client_socket], [], [], 1)[0]:
                        
                    message = self.client_socket.recv(1024).decode()

                    if message.strip() == "server-shutdown":
                        self.exit_receive.set()
                        self.exit_run.set()
                        print("Shutting Down")
                        break
                    print(message)

            except Exception as e:
                print(f"Client-side receive error: {e}")



    def run(self):
        con_stat=self.connect_server()
        if not con_stat: return

        recv_thread = threading.Thread(target=self.receive)
        recv_thread.start()
        while not self.exit_run.is_set():
            try:
                user_input = input()
                self.send(user_input)

                if user_input.lower() == 'exit':
                    break
                
            except KeyboardInterrupt:
                break

            except Exception as e:
                print(f"Error at ClientUDP run: {e}")
                break

        self.send("exit")
        self.exit_receive.set()
        recv_thread.join()

