import asyncio
import json
import os
import tarfile
import io
from datetime import datetime
from typing import Optional
import httpx
from web3 import Web3
try:
    from web3.middleware import geth_poa_middleware
except ImportError:
    geth_poa_middleware = None

from src.common.config import settings
from src.common.logging import setup_logging
from src.common.metrics import _metrics as metrics

logger = setup_logging("blockchain-service")

THREAT_LEDGER_ABI = [
    {"inputs": [], "stateMutability": "nonpayable", "type": "constructor"},
    {"inputs": [{"internalType": "address", "name": "_account", "type": "address"}], "name": "addAuthorizedAddress", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "_account", "type": "address"}], "name": "removeAuthorizedAddress", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "_eventHash", "type": "bytes32"}, {"internalType": "string", "name": "_threatClass", "type": "string"}, {"internalType": "string", "name": "_ipfsCid", "type": "string"}], "name": "recordEvent", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [], "name": "getEventCount", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "index", "type": "uint256"}], "name": "getEvent", "outputs": [{"components": [{"internalType": "bytes32", "name": "eventHash", "type": "bytes32"}, {"internalType": "uint256", "name": "timestamp", "type": "uint256"}, {"internalType": "string", "name": "threatClass", "type": "string"}, {"internalType": "string", "name": "ipfsCid", "type": "string"}, {"internalType": "address", "name": "submittedBy", "type": "address"}, {"internalType": "bytes32", "name": "previousHash", "type": "bytes32"}], "internalType": "struct ThreatLedger.ThreatEvent", "name": "", "type": "tuple"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "verifyChainIntegrity", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "view", "type": "function"},
]


class BlockchainService:
    def __init__(self):
        self.w3: Optional[Web3] = None
        self.ledger_contract: Optional[object] = None
        self.account: Optional[object] = None

    async def connect(self):
        try:
            self.w3 = Web3(Web3.HTTPProvider(settings.ethereum_rpc_url))
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            if self.w3.is_connected():
                logger.info("Connected to Ethereum node", extra={"rpc": settings.ethereum_rpc_url})
                if settings.ethereum_private_key:
                    self.account = self.w3.eth.account.from_key(settings.ethereum_private_key)
                    logger.info("Account loaded", extra={"address": self.account.address})
            else:
                logger.warning("Could not connect to Ethereum node")
        except Exception as e:
            logger.error("Blockchain connection error", extra={"error": str(e)})

    async def deploy_contract(self, contract_name: str) -> Optional[str]:
        try:
            contract_path = f"src/blockchain/contracts/{contract_name}.sol"
            if not os.path.exists(contract_path):
                logger.error("Contract file not found", extra={"path": contract_path})
                return None
            with open(contract_path) as f:
                source = f.read()
            compiled = self.w3.eth.compile_contract(source, contract_name)
            contract = self.w3.eth.contract(abi=compiled["abi"], bytecode=compiled["bin"])
            tx_hash = contract.constructor().transact({"from": self.account.address})
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            logger.info("Contract deployed", extra={"name": contract_name, "address": receipt.contractAddress})
            return receipt.contractAddress
        except Exception as e:
            logger.error("Contract deploy error", extra={"error": str(e)})
            return None

    def _init_contract(self, address: str):
        self.ledger_contract = self.w3.eth.contract(address=address, abi=THREAT_LEDGER_ABI)

    async def record_threat(self, threat_class: str, ipfs_cid: str, event_data: dict) -> Optional[str]:
        if not self.ledger_contract or not self.account:
            logger.warning("Blockchain not initialized, skipping record")
            return None
        try:
            event_json = json.dumps(event_data, default=str).encode("utf-8")
            event_hash = self.w3.keccak(event_json)
            tx = self.ledger_contract.functions.recordEvent(
                event_hash,
                threat_class,
                ipfs_cid,
            ).build_transaction({
                "from": self.account.address,
                "nonce": self.w3.eth.get_transaction_count(self.account.address),
                "gas": 200000,
                "gasPrice": self.w3.eth.gas_price,
            })
            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            logger.info("Threat recorded on blockchain", extra={"tx_hash": tx_hash.hex(), "threat_class": threat_class})
            return tx_hash.hex()
        except Exception as e:
            metrics.errors_total.labels(service="blockchain", error_type="record_threat").inc()
            logger.error("Blockchain record error", extra={"error": str(e)})
            return None

    async def verify_chain(self) -> bool:
        if not self.ledger_contract:
            return False
        try:
            return self.ledger_contract.functions.verifyChainIntegrity().call()
        except Exception as e:
            logger.error("Chain verification error", extra={"error": str(e)})
            return False


class IPFSEvidenceStore:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=settings.ipfs_rpc_url, timeout=60.0)

    async def store_incident(self, incident_id: str, data: dict) -> Optional[str]:
        try:
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w:gz") as tar:
                data_json = json.dumps(data, default=str)
                info = tarfile.TarInfo(name=f"{incident_id}.json")
                info.size = len(data_json.encode())
                tar.addfile(info, io.BytesIO(data_json.encode()))
            buf.seek(0)
            files = {"file": (f"{incident_id}.tar.gz", buf, "application/gzip")}
            resp = await self.client.post("/api/v0/add?pin=true", files=files)
            if resp.status_code == 200:
                result = resp.json()
                cid = result.get("Hash")
                logger.info("Evidence stored to IPFS", extra={"incident_id": incident_id, "cid": cid})
                return cid
            else:
                logger.error("IPFS upload error", extra={"status": resp.status_code})
                return None
        except Exception as e:
            metrics.errors_total.labels(service="ipfs", error_type="store").inc()
            logger.error("IPFS store error", extra={"error": str(e)})
            return None

    async def retrieve(self, cid: str) -> Optional[dict]:
        try:
            resp = await self.client.post(f"/api/v0/cat?arg={cid}")
            if resp.status_code == 200:
                return json.loads(resp.content)
            return None
        except Exception as e:
            logger.error("IPFS retrieve error", extra={"error": str(e), "cid": cid})
            return None
