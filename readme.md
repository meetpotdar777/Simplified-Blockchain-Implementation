# Simplified Blockchain/Distributed Ledger ⛓️
## This project implements a basic blockchain from scratch in Python, demonstrating core concepts such as blocks, hashing, a simplified Proof-of-Work consensus mechanism, and peer-to-peer (P2P) networking. It provides a foundational understanding of how distributed ledgers operate.

# Features ✨
### Block Structure: Each block contains an index, timestamp, list of transactions, proof of work, and the hash of the previous block. 📦

### Hashing: Uses SHA-256 for cryptographic hashing to ensure data integrity and immutability. 🔐

### Proof-of-Work (PoW): A simplified PoW algorithm (finding a hash with leading zeros) is implemented to simulate mining and secure block creation. ⛏️

### Transactions: Supports basic transactions (sender, recipient, amount) that are added to blocks. 💰

### Flask API: Each blockchain node exposes an HTTP API (using Flask) for interaction, allowing users to mine new blocks, submit transactions, view the blockchain, register new nodes, and trigger conflict resolution. 🌐

### Peer-to-Peer (P2P) Communication: Nodes communicate directly via sockets to broadcast new blocks and transactions. 🤝

### Consensus Mechanism: Implements a "Longest Chain Wins" consensus algorithm (resolve_conflicts) to ensure all nodes maintain the most up-to-date and valid version of the blockchain. ⚖️

### Deterministic Genesis Block: Ensures all nodes start with an identical first block for consistent chain validation across the network. 🌟

# Technologies Used 🛠️
### Python 3.x: For the core blockchain logic and P2P communication. 🐍

### Flask: For creating the RESTful API endpoints for each node. 🧪

### hashlib: Python's built-in module for cryptographic hashing. 🔒

### requests: For making HTTP requests between nodes (used in consensus). 📡

### socket & threading: For implementing basic P2P communication between nodes. 🔌

# Setup and Installation 🚀
### Clone or Download: Save the blockchain.py code to your local machine. 💾

### Install Dependencies: Open your terminal or command prompt and install the required Python libraries:

### pip install Flask requests

# How to Run Multiple Nodes 🏃‍♂️🏃‍♀️🏃
### To simulate a distributed network, you need to run multiple instances of the blockchain.py script, each on a different port.

### Open separate terminal windows for each node you want to run.

### Terminal 1 (Node 1):

```bash
python blockchain.py 5000 6000

```
### (Flask API on port 5000, P2P on port 6000)

### Terminal 2 (Node 2):

```bash
python blockchain.py 5001 6001

```
### (Flask API on port 5001, P2P on port 6001)

### Terminal 3 (Node 3):

```bash
python blockchain.py 5002 6002

```
### (Flask API on port 5002, P2P on port 6002)

### Each terminal will show output indicating the Flask port, P2P port, and a unique node identifier. The "Deterministic genesis block created." message confirms the consistent starting point.

# How to Interact (using curl) 💬
### Once your nodes are running, you can interact with them using curl (or Postman, Insomnia, etc.). Remember to use double quotes and escape inner double quotes (\") for JSON data on Windows command prompt/PowerShell.

# 1. Register Nodes (Connect the Network): 🔗
### Nodes need to know about each other's Flask (HTTP) addresses to resolve conflicts. Run these commands from any terminal (e.g., your main one) after all nodes are started:

### Register Node 2 (Flask:5001) and Node 3 (Flask:5002) with Node 1 (Flask:5000):
```bash
curl -X POST -H "Content-Type: application/json" -d "{\"nodes\": [\"127.0.0.1:5001\", \"127.0.0.1:5002\"]}" http://127.0.0.1:5000/nodes/register

```    
### Register Node 1 (Flask:5000) and Node 3 (Flask:5002) with Node 2 (Flask:5001):
```bash    
curl -X POST -H "Content-Type: application/json" -d "{\"nodes\": [\"127.0.0.1:5000\", \"127.0.0.1:5002\"]}" http://127.0.0.1:5001/nodes/register

```
### Register Node 1 (Flask:5000) and Node 2 (Flask:5001) with Node 3 (Flask:5002):
```bash   
curl -X POST -H "Content-Type: application/json" -d "{\"nodes\": [\"127.0.0.1:5000\", \"127.0.0.1:5001\"]}" http://127.0.0.1:5002/nodes/register

```  
### You should see responses like `{"message":"New nodes have been added","total_nodes":["127.0.0.1:5000", ... ]}`

# 2. Mine a New Block: ⛏️
### Trigger the mining process on a node. This will create a new block, reward the miner, and broadcast the block to registered peers.

### Mine on Node 1 (Flask:5000):
```bash
curl http://127.0.0.1:5000/mine

```
### Observe the terminal outputs of other nodes; they should receive `NEW_BLOCK` messages and trigger conflict resolution.

# 3. Add a New Transaction: 💸
### Submit a transaction to a node. This transaction will be added to that node's pending transaction pool and broadcast. It will be included in the next block mined by any node.

### Add transaction to Node 2 (Flask:5001):
 ```bash
curl -X POST -H "Content-Type: application/json" -d "{\"sender\": \"alice\", \"recipient\": \"bob\", \"amount\": 5}" http://127.0.0.1:5001/transactions/new

 ```
### Observe `NEW_TRANSACTION` messages in other node terminals.
# 4. Mine a Block to Include Transactions: 🧱
### Mine another block on any node. This block will now include the pending transactions.

### Mine on Node 3 (Flask:5002):
 ```bash
 curl http://127.0.0.1:5002/mine

  ```
# 5. View the Full Blockchain: 👀
### Retrieve the entire blockchain from any node. After mining and synchronization, all nodes should have identical chains.

### View chain on Node 1 (Flask:5000):

```bash
curl http://127.0.0.1:5000/chain

```
### View chain on Node 2 (Flask:5001):

```bash
curl http://127.0.0.1:5001/chain

```
### View chain on Node 3 (Flask:5002):

```bash
curl http://127.0.0.1:5002/chain

```
### All nodes should report the same `length` and have identical block data.
# 6. Resolve Conflicts (Manual Consensus Trigger): 🔄
### If chains ever get out of sync (e.g., due to network delays or nodes starting at different times), you can manually trigger the consensus algorithm to force a node to adopt the longest valid chain from its peers.

### Resolve conflicts on Node 1 (Flask:5000):

```bash
curl http://127.0.0.1:5000/nodes/resolve

```
### Repeat for other nodes if necessary.
# Future Improvements 💡
### This implementation is a simplified model. Potential enhancements include:

### Persistence: Store the blockchain to disk to maintain state across restarts. 💾

### Transaction Validation: Implement more robust validation (e.g., checking sender balances, cryptographic signatures). ✅

### Wallet/Key Management: Generate and manage public/private key pairs for users. 🔑

### Error Handling: More comprehensive error handling for network issues and invalid data. ⚠️

### Advanced Consensus: Explore other consensus mechanisms like Proof-of-Stake. ⚡

### Peer Discovery: Implement more sophisticated methods for nodes to discover each other dynamically. 🗺️

### Scalability: Optimize for performance with a larger number of transactions and nodes. 📈

### User Interface: Develop a simple web interface for easier interaction. 🖥️
