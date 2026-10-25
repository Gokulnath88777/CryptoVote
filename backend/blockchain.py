import hashlib
import json
import time
from datetime import datetime

class Block:
    def __init__(self, index, timestamp, data, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()
    
    def calculate_hash(self):
        """Generate SHA-256 hash of block contents"""
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def to_dict(self):
        """Convert block to dictionary for JSON storage"""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "hash": self.hash
        }

class Blockchain:
    def __init__(self):
        self.chain = []
        self.create_genesis_block()
    
    def create_genesis_block(self):
        """Create the first block in the chain"""
        genesis_block = Block(0, str(datetime.now()), {
            "type": "genesis",
            "message": "CryptoVote Blockchain Initialized"
        }, "0")
        self.chain.append(genesis_block)
    
    def get_latest_block(self):
        """Return the most recent block"""
        return self.chain[-1]
    
    def add_vote(self, voter_id, candidate_id, candidate_name):
        """Add a new vote as a block to the chain"""
        vote_data = {
            "type": "vote",
            "voter_id": voter_id,
            "candidate_id": candidate_id,
            "candidate_name": candidate_name,
            "timestamp": str(datetime.now())
        }
        
        new_block = Block(
            index=len(self.chain),
            timestamp=str(datetime.now()),
            data=vote_data,
            previous_hash=self.get_latest_block().hash
        )
        
        self.chain.append(new_block)
        return new_block
    
    def validate_chain(self):
        """Check if the blockchain is valid"""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            # Check if current block's hash is correct
            if current_block.hash != current_block.calculate_hash():
                return False
            
            # Check if previous hash matches
            if current_block.previous_hash != previous_block.hash:
                return False
        
        return True
    
    def get_vote_count(self):
        """Count votes per candidate"""
        vote_count = {}
        for block in self.chain:
            if block.data.get("type") == "vote":
                candidate_id = block.data.get("candidate_id")
                if candidate_id:
                    vote_count[candidate_id] = vote_count.get(candidate_id, 0) + 1
        return vote_count
    
    def has_voter_voted(self, voter_id):
        """Check if a voter has already cast a vote"""
        for block in self.chain:
            if block.data.get("type") == "vote" and block.data.get("voter_id") == voter_id:
                return True
        return False
    
    def to_json(self):
        """Convert entire chain to JSON format"""
        return [block.to_dict() for block in self.chain]
    
    def from_json(self, chain_data):
        """Load chain from JSON data"""
        self.chain = []
        for block_data in chain_data:
            block = Block(
                block_data["index"],
                block_data["timestamp"],
                block_data["data"],
                block_data["previous_hash"]
            )
            block.hash = block_data["hash"]
            self.chain.append(block)