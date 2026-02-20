import hashlib
import json
from time import time

class Block:
    def __init__(self, index, transactions, timestamp, previous_hash):
        self.index = index
        self.transactions = transactions  # Vote data
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.hash = self.compute_hash()

    def compute_hash(self):
        """Generates a cryptographic SHA-256 hash of the block's contents."""
        block_string = json.dumps(self.__dict__, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

class Blockchain:
    def __init__(self):
        self.unconfirmed_transactions = [] # Mempool
        self.chain = []
        self.create_genesis_block()

    def create_genesis_block(self):
        """Generates the first block in the chain."""
        genesis_block = Block(0, [], time(), "0")
        self.chain.append(genesis_block)

    @property
    def last_block(self):
        return self.chain[-1]

    def add_block(self, block):
        """Adds a block to the chain after verifying the previous_hash matches."""
        previous_hash = self.last_block.hash
        if previous_hash != block.previous_hash:
            return False
        self.chain.append(block)
        return True

    def add_new_transaction(self, transaction):
        """Adds a new vote to the pool of unconfirmed transactions."""
        self.unconfirmed_transactions.append(transaction)

    def mine(self):
        """Packages pending votes into a block instantly."""
        if not self.unconfirmed_transactions:
            return False

        last_block = self.last_block
        new_block = Block(
            index=last_block.index + 1,
            transactions=self.unconfirmed_transactions,
            timestamp=time(),
            previous_hash=last_block.hash
        )

        self.add_block(new_block)
        self.unconfirmed_transactions = []
        return new_block.index 