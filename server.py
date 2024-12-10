# to run in terminal: python server.py
from chatroom import ServerUDP, ServerTCP
server = ServerTCP(12345)
# server = ServerUDP(2020)
server.run()