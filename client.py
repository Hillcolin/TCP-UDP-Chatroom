# to run in terminal: python client.py --name 
from chatroom import ClientTCP, ClientUDP
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--name', '-n', type=str, help='Client name')
args = parser.parse_args()
client = ClientTCP(args.name, 12345)
# client = ClientUDP(args.name, 2020)
client.run()