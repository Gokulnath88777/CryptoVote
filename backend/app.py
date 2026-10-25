from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import json
import os
import base64
from datetime import datetime
from blockchain import Blockchain

app = FastAPI(title="CryptoVote API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data directory path
DATA_DIR = "data"
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

# Initialize blockchain
blockchain = Blockchain()

# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str

class VoteRequest(BaseModel):
    voter_id: str
    candidate_id: str
    voter_name: str
    voter_address: str
    voter_phone: str
    id_proof_base64: str
    id_proof_filename: str

# Helper functions
def load_json(filename):
    """Load JSON file from data directory"""
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return {}

def save_json(filename, data):
    """Save data to JSON file"""
    filepath = os.path.join(DATA_DIR, filename)
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

def load_blockchain():
    """Load blockchain from file"""
    filepath = os.path.join(DATA_DIR, "blockchain.json")
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                content = f.read().strip()
                if content:  # Only load if file has content
                    chain_data = json.loads(content)
                    blockchain.from_json(chain_data)
                else:
                    print("⚠️  blockchain.json is empty, starting fresh")
        except json.JSONDecodeError as e:
            print(f"⚠️  Error reading blockchain.json: {e}")
            print("Starting with fresh blockchain")
        except Exception as e:
            print(f"⚠️  Unexpected error loading blockchain: {e}")
            print("Starting with fresh blockchain")

def save_blockchain():
    """Save blockchain to file"""
    save_json("blockchain.json", blockchain.to_json())

# Initialize data on startup
@app.on_event("startup")
async def startup_event():
    # Create data directory if it doesn't exist
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"✓ Data directory ready: {DATA_DIR}")
    
    # Initialize users.json if not exists or empty
    users_path = os.path.join(DATA_DIR, "users.json")
    if not os.path.exists(users_path) or os.path.getsize(users_path) == 0:
        users = {
            "user": {"password": "user123", "role": "voter"},
            "admin": {"password": "admin123", "role": "admin"}
        }
        save_json("users.json", users)
        print("✓ Initialized users.json")
    
    # Initialize candidates.json if not exists or empty
    candidates_path = os.path.join(DATA_DIR, "candidates.json")
    if not os.path.exists(candidates_path) or os.path.getsize(candidates_path) == 0:
        candidates = {
            "1": {"id": "1", "name": "Alice Johnson", "party": "Progressive Party", "image": "👩‍💼"},
            "2": {"id": "2", "name": "Bob Smith", "party": "Democratic Alliance", "image": "👨‍💼"},
            "3": {"id": "3", "name": "Carol Davis", "party": "Green Coalition", "image": "👩‍🎓"}
        }
        save_json("candidates.json", candidates)
        print("✓ Initialized candidates.json")
    
    # Initialize votes.json if not exists or empty
    votes_path = os.path.join(DATA_DIR, "votes.json")
    if not os.path.exists(votes_path) or os.path.getsize(votes_path) == 0:
        save_json("votes.json", [])
        print("✓ Initialized votes.json")
    
    # Load existing blockchain or start fresh
    load_blockchain()
    print(f"✓ Blockchain loaded: {len(blockchain.chain)} blocks")
    
    # Save initial blockchain if needed
    blockchain_path = os.path.join(DATA_DIR, "blockchain.json")
    if not os.path.exists(blockchain_path) or os.path.getsize(blockchain_path) == 0:
        save_blockchain()
        print("✓ Saved initial blockchain")
    
    print("\n" + "="*50)
    print("🗳️  CryptoVote Server Started Successfully!")
    print("="*50)
    print(f"API URL: http://localhost:8000")
    print(f"API Docs: http://localhost:8000/docs")
    print(f"Blockchain Blocks: {len(blockchain.chain)}")
    print("="*50 + "\n")

# Routes
@app.get("/")
async def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/index.html")
async def index_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/voter_dashboard.html")
async def voter_dashboard():
    return FileResponse(os.path.join(FRONTEND_DIR, "voter_dashboard.html"))

@app.get("/admin_dashboard.html")
async def admin_dashboard():
    return FileResponse(os.path.join(FRONTEND_DIR, "admin_dashboard.html"))

@app.get("/results.html")
async def results_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "results.html"))

@app.get("/api")
async def api_root():
    return {"message": "CryptoVote API is running", "blockchain_length": len(blockchain.chain)}

@app.post("/login")
async def login(request: LoginRequest):
    """Authenticate user"""
    users = load_json("users.json")
    
    if request.username not in users:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user = users[request.username]
    if user["password"] != request.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {
        "success": True,
        "role": user["role"],
        "username": request.username
    }

@app.get("/get_candidates")
async def get_candidates():
    """Fetch all candidates"""
    candidates = load_json("candidates.json")
    return {"candidates": list(candidates.values())}

@app.post("/submit_vote")
async def submit_vote(request: VoteRequest):
    """Submit a vote and add to blockchain"""
    try:
        # Check if voter has already voted
        if blockchain.has_voter_voted(request.voter_id):
            raise HTTPException(status_code=400, detail="You have already voted!")
        
        # Get candidate details
        candidates = load_json("candidates.json")
        if request.candidate_id not in candidates:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        candidate = candidates[request.candidate_id]
        
        # Add vote to blockchain
        new_block = blockchain.add_vote(
            voter_id=request.voter_id,
            candidate_id=request.candidate_id,
            candidate_name=candidate["name"]
        )
        
        # Save blockchain
        save_blockchain()
        
        # Save detailed vote information to votes.json
        votes = load_json("votes.json")
        vote_record = {
            "voter_id": request.voter_id,
            "voter_name": request.voter_name,
            "voter_address": request.voter_address,
            "voter_phone": request.voter_phone,
            "candidate_id": request.candidate_id,
            "candidate_name": candidate["name"],
            "candidate_party": candidate["party"],
            "timestamp": new_block.timestamp,
            "block_index": new_block.index,
            "block_hash": new_block.hash,
            "previous_hash": new_block.previous_hash,
            "id_proof_filename": request.id_proof_filename,
            "id_proof_base64": request.id_proof_base64,
            "vote_confirmed": True
        }
        votes.append(vote_record)
        save_json("votes.json", votes)
        
        return {
            "success": True,
            "message": "Vote recorded successfully!",
            "vote_details": {
                "voter_name": request.voter_name,
                "voter_id": request.voter_id,
                "voter_address": request.voter_address,
                "voter_phone": request.voter_phone,
                "candidate_name": candidate["name"],
                "candidate_party": candidate["party"],
                "block_index": new_block.index,
                "block_hash": new_block.hash,
                "previous_hash": new_block.previous_hash,
                "timestamp": new_block.timestamp,
                "id_proof_filename": request.id_proof_filename
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in submit_vote: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/get_results")
async def get_results():
    """Get voting results"""
    candidates = load_json("candidates.json")
    vote_count = blockchain.get_vote_count()
    
    results = []
    for candidate_id, candidate in candidates.items():
        results.append({
            "id": candidate_id,
            "name": candidate["name"],
            "party": candidate["party"],
            "image": candidate["image"],
            "votes": vote_count.get(candidate_id, 0)
        })
    
    # Sort by votes (descending)
    results.sort(key=lambda x: x["votes"], reverse=True)
    
    return {
        "results": results,
        "total_votes": sum(vote_count.values()),
        "blockchain_length": len(blockchain.chain)
    }

@app.get("/validate_chain")
async def validate_chain():
    """Validate blockchain integrity"""
    is_valid = blockchain.validate_chain()
    return {
        "valid": is_valid,
        "chain_length": len(blockchain.chain),
        "message": "Blockchain is valid ✓" if is_valid else "Blockchain has been tampered! ✗"
    }

@app.get("/blockchain")
async def get_blockchain():
    """Get entire blockchain (for debugging)"""
    return {
        "chain": blockchain.to_json(),
        "length": len(blockchain.chain)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)