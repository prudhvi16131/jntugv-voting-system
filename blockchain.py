import hashlib
import json
import time

class MerkleTree:
    """
    Generates a Merkle Root from a list of transactions.
    This ensures that any change in a single vote will change the entire root hash.
    """
    def __init__(self, transactions):
        self.transactions = transactions
        self.root = self.build_tree(transactions)

    def build_tree(self, nodes):
        # Convert transactions to initial hashes (leaves)
        hashes = [hashlib.sha256(json.dumps(n, sort_keys=True).encode()).hexdigest() for n in nodes]
        
        if not hashes: 
            return hashlib.sha256(b"empty_block").hexdigest()
        
        while len(hashes) > 1:
            # If the number of hashes is odd, duplicate the last one to make it even
            if len(hashes) % 2 != 0:
                hashes.append(hashes[-1])
            
            new_level = []
            for i in range(0, len(hashes), 2):
                # Combine pairs of hashes to form the next level
                combined = hashes[i] + hashes[i+1]
                new_level.append(hashlib.sha256(combined.encode()).hexdigest())
            hashes = new_level
            
        return hashes[0] # The final Merkle Root

class Block:
    def __init__(self, index, transactions, timestamp, previous_hash, nonce=0):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce
        # Store the Merkle Root in the header for lightweight verification
        self.merkle_root = MerkleTree(transactions).root
        self.hash = self.compute_hash()

    def compute_hash(self):
        """
        Computes the SHA-256 hash of the block header.
        """
        block_string = json.dumps({
            "index": self.index,
            "merkle_root": self.merkle_root, 
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

class Blockchain:
    def __init__(self):
        self.unconfirmed_transactions = []
        self.chain = []
        self.create_genesis_block()

    def create_genesis_block(self):
        """
        Generates the first block of the chain.
        """
        genesis_block = Block(0, [], time.time(), "0")
        self.chain.append(genesis_block)

    def add_new_transaction(self, transaction):
        """
        Adds a new vote to the unconfirmed transaction list.
        """
        self.unconfirmed_transactions.append(transaction)

    def mine(self):
        """
        Mines a new block into the blockchain using Proof of Work.
        """
        if not self.unconfirmed_transactions:
            return False

        last_block = self.chain[-1]
        new_block = Block(index=last_block.index + 1,
                          transactions=self.unconfirmed_transactions,
                          timestamp=time.time(),
                          previous_hash=last_block.hash)
        
        # Difficulty adjustment: Block hash must start with '00'
        while not new_block.hash.startswith('00'):
            new_block.nonce += 1
            new_block.hash = new_block.compute_hash()
            
        self.chain.append(new_block)
        self.unconfirmed_transactions = []
        return True

    def is_chain_valid(self):
        """
        Validates the entire blockchain integrity.
        """
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            
            # Check if block hash is correct
            if current.hash != current.compute_hash():
                return False
            # Check if blocks are linked correctly
            if current.previous_hash != previous.hash:
                return False
        return True