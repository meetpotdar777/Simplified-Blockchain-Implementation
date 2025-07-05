import hashlib
import json
import time
import requests
from urllib.parse import urlparse
import threading
import socket
import sys
import os

# --- 1. Blockchain Core Logic ---

class Blockchain:
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        # self.nodes will now store Flask (HTTP) addresses for conflict resolution
        self.nodes = set() # Set of unique network addresses of other nodes
        self.difficulty = '0000' # Target difficulty for Proof-of-Work

        # Create a deterministic genesis block if the chain is empty
        if not self.chain:
            self.create_deterministic_genesis_block()

    def create_deterministic_genesis_block(self):
        """
        Creates a fixed, deterministic genesis block to ensure consistency across all nodes.
        This block's hash will always be the same if the parameters are identical.
        """
        genesis_block = {
            'index': 1,
            'timestamp': 0, # Fixed timestamp for deterministic hash
            'transactions': [],
            'proof': 100,
            'previous_hash': '1', # Fixed previous hash
        }
        self.chain.append(genesis_block)
        print("Deterministic genesis block created.")

    def new_block(self, proof, previous_hash=None):
        """
        Creates a new Block and adds it to the chain
        :param proof: The proof given by the Proof-of-Work algorithm
        :param previous_hash: Hash of previous Block
        :return: New Block
        """
        # Ensure previous_hash is correctly derived from the last block
        # If previous_hash is not provided, calculate it from the last block in the chain.
        # This handles the case for the second block being mined, where previous_hash is the genesis hash.
        calculated_previous_hash = previous_hash or self.hash(self.chain[-1])

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time.time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': calculated_previous_hash,
        }

        # Reset the current list of transactions
        self.current_transactions = []
        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        """
        Adds a new transaction to the list of transactions to be included in the next mined Block
        :param sender: Address of the Sender
        :param recipient: Address of the Recipient
        :param amount: Amount
        :return: The index of the Block that will hold this transaction
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })
        return self.last_block['index'] + 1

    @property
    def last_block(self):
        """
        Returns the last block in the chain
        """
        return self.chain[-1]

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block
        :param block: Block
        :return: Hash string
        """
        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        # Create a copy of the block to avoid modifying the original when removing 'hash' if it exists.
        # This is crucial because the 'hash' field itself should not be part of the data being hashed.
        block_copy = block.copy()
        block_string = json.dumps(block_copy, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_proof):
        """
        Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains 4 leading zeros, where p is the previous p'
        :param last_proof:
        :return: <int>
        """
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        return proof

    def valid_proof(self, last_proof, proof):
        """
        Validates the Proof: Does hash(last_proof, proof) contain 4 leading zeros?
        :param last_proof: Previous Proof
        :param proof: Current Proof
        :return: True if correct, False otherwise.
        """
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:len(self.difficulty)] == self.difficulty

    def register_node(self, address):
        """
        Add a new node's HTTP (Flask) address to the list of nodes for conflict resolution.
        Ensures the address is stored as 'host:port'.
        :param address: HTTP Address of node. Eg. 'http://192.168.0.5:5000' or '192.168.0.5:5000'
        """
        # Prepend a dummy scheme if missing to ensure urlparse correctly identifies netloc
        if not (address.startswith('http://') or address.startswith('https://')):
            address = 'http://' + address

        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        else:
            raise ValueError(f'Invalid URL: Could not parse host and port from {address}. Ensure it includes host:port.')


    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid
        :param chain: a blockchain
        :return: True if valid, False if not
        """
        if not chain:
            return False # An empty chain is not valid

        # Start validation from the second block, as the first block (genesis)
        # is assumed to be deterministic and valid.
        # We only need to check if the incoming chain's genesis matches ours.
        if len(self.chain) > 0 and self.hash(chain[0]) != self.hash(self.chain[0]):
            print("Validation FAILED: Genesis block mismatch.")
            return False

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            # Added more detailed prints for debugging chain validation
            print(f"Validating block {block['index']} from peer chain:")
            print(f"  Current block's previous_hash: {block['previous_hash']}")
            calculated_previous_hash = self.hash(last_block)
            print(f"  Calculated hash of previous block ({last_block['index']}): {calculated_previous_hash}")

            # Check that the previous_hash of the current block is correct
            if block['previous_hash'] != calculated_previous_hash:
                print(f"  Validation FAILED: Previous hash mismatch for block {block['index']}")
                return False

            # Check that the Proof of Work is correct for the current block
            if not self.valid_proof(last_block['proof'], block['proof']):
                print(f"  Validation FAILED: Invalid proof for block {block['index']}")
                return False

            print(f"  Block {block['index']} passed validation.")
            last_block = block
            current_index += 1

        print("Chain is valid.")
        return True

    def resolve_conflicts(self):
        """
        This is our Consensus Algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.
        It fetches chains from nodes registered as HTTP addresses.
        :return: True if our chain was replaced, False if not
        """
        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node_http_address in neighbours:
            try:
                # Use the stored HTTP address to fetch the chain
                response = requests.get(f'http://{node_http_address}/chain')
                if response.status_code == 200:
                    length = response.json()['length']
                    chain = response.json()['chain']

                    print(f"Checking chain from {node_http_address}: length={length}, our_length={max_length}")
                    # Check if the length is longer and the chain is valid
                    if length > max_length and self.valid_chain(chain):
                        max_length = length
                        new_chain = chain
                else:
                    print(f"Failed to get chain from {node_http_address}. Status code: {response.status_code}")
            except requests.exceptions.ConnectionError as e:
                # This error is expected if a node is not running or the address is wrong
                print(f"Could not connect to node (HTTP): {node_http_address} - {e}")
                continue
            except Exception as e:
                print(f"Error fetching chain from {node_http_address}: {e}")
                continue

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            print("Chain replaced by a longer, valid chain from a peer.")
            return True

        print("Our chain is already the longest or no longer valid chain found.")
        return False

# --- 2. Flask API for Node Interaction ---

from flask import Flask, jsonify, request
import uuid

# Instantiate the Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid.uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()

# --- Flask Routes ---

@app.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work algorithm to find the next proof
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin.
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # Forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    # After forging a new block, broadcast it to P2P network
    global p2p_node # Access the P2PNode instance
    if p2p_node:
        p2p_node.broadcast_message({'type': 'NEW_BLOCK', 'payload': block}, exclude_port=p2p_node.port)

    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount']
    if not all(key in values for key in required):
        return 'Missing values', 400

    # Create a new Transaction
    transaction_data = {'sender': values['sender'], 'recipient': values['recipient'], 'amount': values['amount']}
    index = blockchain.new_transaction(transaction_data['sender'], transaction_data['recipient'], transaction_data['amount'])

    # Broadcast the new transaction to P2P network
    global p2p_node
    if p2p_node:
        p2p_node.broadcast_message({'type': 'NEW_TRANSACTION', 'payload': transaction_data}, exclude_port=p2p_node.port)

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values.get('nodes') # This list should now contain HTTP addresses

    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node_address in nodes:
        blockchain.register_node(node_address)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes), # This will list HTTP addresses
    }
    return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }
    return jsonify(response), 200

# --- 3. P2P Communication (Basic Socket Programming) ---

class P2PNode(threading.Thread):
    def __init__(self, host, port, blockchain_instance):
        super().__init__()
        self.host = host
        self.port = port
        self.blockchain = blockchain_instance
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = True
        print(f"P2P Node initialized on {self.host}:{self.port}")

    def run(self):
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            print(f"P2P Node listening on {self.host}:{self.port}")
            while self.running:
                conn, addr = self.socket.accept()
                threading.Thread(target=self.handle_client, args=(conn, addr)).start()
        except OSError as e:
            if self.running: # Only print error if not intentionally stopped
                print(f"P2P Server Error: {e}")
        finally:
            self.socket.close()
            print(f"P2P Node on {self.host}:{self.port} stopped.")

    def handle_client(self, conn, addr):
        with conn:
            print(f"Connected by {addr}")
            try:
                data = conn.recv(4096).decode('utf-8')
                if not data:
                    return

                message = json.loads(data)
                self.process_p2p_message(message)
            except json.JSONDecodeError:
                print(f"Received malformed JSON from {addr}")
            except Exception as e:
                print(f"Error handling client {addr}: {e}")

    def process_p2p_message(self, message):
        """
        Processes incoming P2P messages.
        """
        msg_type = message.get('type')
        payload = message.get('payload')

        if msg_type == 'NEW_BLOCK':
            print(f"P2P: Received NEW_BLOCK message: {payload['index']}")
            received_block = payload
            # Trigger conflict resolution to properly handle the new block
            # This is more robust than simple appending, as it validates the whole chain.
            print("P2P: Triggering conflict resolution due to new block from peer...")
            self.blockchain.resolve_conflicts()


        elif msg_type == 'NEW_TRANSACTION':
            print(f"P2P: Received NEW_TRANSACTION message: {payload}")
            # Add transaction to current_transactions
            self.blockchain.current_transactions.append(payload)
            print(f"P2P: Added new transaction from peer.")
            self.broadcast_message({'type': 'NEW_TRANSACTION', 'payload': payload}, exclude_port=self.port)

        elif msg_type == 'REQUEST_CHAIN':
            print("P2P: Received REQUEST_CHAIN message.")
            # Send back the current chain
            sender_host = message.get('sender_host')
            sender_port = message.get('sender_port')
            if sender_host and sender_port:
                self.send_message(sender_host, sender_port, {
                    'type': 'RESPOND_CHAIN',
                    'payload': {'chain': self.blockchain.chain, 'length': len(self.blockchain.chain)}
                })

        elif msg_type == 'RESPOND_CHAIN':
            print("P2P: Received RESPOND_CHAIN message.")
            # This is typically handled by the Flask /nodes/resolve endpoint
            # For P2P, you might use this to proactively update your chain
            # if you detect a longer one.
            received_chain = payload['chain']
            if len(received_chain) > len(self.blockchain.chain) and self.blockchain.valid_chain(received_chain):
                self.blockchain.chain = received_chain
                print("P2P: Updated chain from peer response.")

        else:
            print(f"P2P: Unknown message type: {msg_type}")

    def send_message(self, target_host, target_port, message):
        """
        Sends a P2P message to a specific target node.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((target_host, target_port))
                s.sendall(json.dumps(message).encode('utf-8'))
                print(f"P2P: Sent {message['type']} to {target_host}:{target_port}")
        except ConnectionRefusedError:
            print(f"P2P: Connection refused by {target_host}:{target_port}. Node might be down.")
        except Exception as e:
            print(f"P2P: Error sending message to {target_host}:{target_port}: {e}")

    def broadcast_message(self, message, exclude_port=None):
        """
        Broadcasts a P2P message to all known peers.
        Peers' P2P addresses are derived from the HTTP nodes in the blockchain instance
        using the convention: P2P_PORT = HTTP_PORT + 1000.
        """
        for http_node_address in list(self.blockchain.nodes): # Iterate over a copy to allow modification
            try:
                # Split host and HTTP port
                host, http_port_str = http_node_address.split(':')
                http_port = int(http_port_str)
                p2p_port = http_port + 1000 # Apply the convention

                if p2p_port == exclude_port: # Don't send back to the sender
                    continue

                self.send_message(host, p2p_port, message)
            except ValueError:
                print(f"P2P: Invalid HTTP node address format: {http_node_address}")
            except Exception as e:
                print(f"P2P: Error broadcasting to {http_node_address} (P2P:{p2p_port}): {e}")

    def stop(self):
        self.running = False
        self.socket.close() # This will cause the accept() call to raise an OSError, breaking the loop

# --- Main Execution ---

# Global variable to hold the P2PNode instance
p2p_node = None

if __name__ == '__main__':
    # Determine the port for Flask and P2P based on command line arguments
    # Usage: python blockchain.py <flask_port> <p2p_port>
    if len(sys.argv) < 3:
        print("Usage: python blockchain.py <flask_port> <p2p_port>")
        sys.exit(1)

    flask_port = int(sys.argv[1])
    p2p_port = int(sys.argv[2])
    p2p_host = '127.0.0.1' # Or '0.0.0.0' for external access

    # Start P2P Node in a separate thread
    p2p_node = P2PNode(p2p_host, p2p_port, blockchain)
    p2p_node.daemon = True # Allow main thread to exit even if P2P thread is running
    p2p_node.start()

    # Add this node's Flask (HTTP) address to its own list of nodes
    # This is important for the broadcast functionality to work correctly,
    # as it iterates over `blockchain.nodes` (which are now HTTP addresses).
    blockchain.register_node(f'{p2p_host}:{flask_port}')

    print(f"Flask App will run on port {flask_port}")
    print(f"P2P Node will run on {p2p_host}:{p2p_port}")
    print(f"Node Identifier: {node_identifier}")

    # Run the Flask app
    # Use host='0.0.0.0' to make it accessible externally if needed
    app.run(host='0.0.0.0', port=flask_port, debug=False)

    # When Flask app stops (e.g., Ctrl+C), stop the P2P node gracefully
    p2p_node.stop()
    p2p_node.join() # Wait for the P2P thread to finish
