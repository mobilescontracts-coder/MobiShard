"""Typed Python projection of selected MSC CPN rules, not a CPN interpreter.

The original XML is unchanged. The exact snapshot digest pins these reviewed
transcriptions. The local runtime additionally introduces admission reservation,
FIFO worker queues, request diagnostics, and a selected same-owner role binding.
All keys/signatures and the polynomial hash remain SYMBOLIC.
"""
from __future__ import annotations
import hashlib
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

EXPECTED_SHA256 = 'f6cc604e1201393bfb720c43769a855ffec59ddc8a5926d3d1836ee843958f4f'
DEFAULT_MODEL = Path(__file__).resolve().parents[1] / 'model' / 'msc.cpn'


def load_model(path: Path = DEFAULT_MODEL) -> dict[str, Any]:
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError('Unreviewed CPN snapshot: recheck transcriptions before changing the digest.')
    root = ET.fromstring(data)
    declarations = '\n'.join(m.findtext('layout') or m.text or ''
                             for m in root.findall('.//globbox//ml'))
    constants = {k: int(v) for k, v in re.findall(
        r'val\s+(\w+)(?:\s*:\s*(?:int|INT))?\s*=\s*(\d+)\s*;', declarations)}
    p = re.search(r'val\s+initNP[^=]*=\s*\{([^}]+)\}', declarations).group(1)
    policy = {k: int(re.search(rf'\b{k}\s*=\s*(\d+)', p).group(1))
              for k in ('Difficulty', 'minBlockHeight', 'minDeposit')}
    policy['depositAddress'] = re.search(r'depositAddress\s*=\s*"([^"]+)"', p).group(1)
    modulus = int(re.search(r'val\s+hashtablesize\s*=\s*(\d+)', declarations).group(1))
    pages = root.findall('.//page')
    mapping = next(x for x in pages[0].findall('place') if x.findtext('text') == 'P_CID2SID')
    pairs = [(int(k), int(s)) for k, s in re.findall(r'\((\d+)\s*,\s*(\d+)\)',
                                                     mapping.findtext('initmark/text', ''))]
    assert pairs == [(k, k % 4) for k in range(64)]
    return {'sha256': digest, 'constants': constants, 'policy': policy, 'hash_modulus': modulus,
            'mapping': dict(pairs), 'pages': len(pages),
            'places': sum(len(p.findall('place')) for p in pages),
            'transitions': sum(len(p.findall('trans')) for p in pages),
            'arcs': sum(len(p.findall('arc')) for p in pages)}


MODEL = load_model()
C = MODEL['constants']
NP = MODEL['policy']
COSTS = {phase: (C[f'COST_{phase.upper()}_BATT'], C[f'COST_{phase.upper()}_CPU'])
         for phase in ('block', 'proof', 'root')}
TOTAL_B = sum(x[0] for x in COSTS.values())
TOTAL_C = sum(x[1] for x in COSTS.values())


def symhash(s: str) -> str:
    """String form of the CPN polynomial hash; NOT collision resistant."""
    h = 0
    for char in reversed(s):
        h = (ord(char) + 7 * h) % MODEL['hash_modulus']
    return str(h)


def wallet(uid: int) -> str:
    return f'wallet-{uid}'


def private_symbol(uid: int) -> str:
    return f'private-symbol-{uid}'


def deposit_tx(tid: int, uid: int) -> dict[str, Any]:
    return {'ID': tid, 'from': wallet(uid), 'to': NP['depositAddress'],
            'amount': NP['minDeposit'], 'pubkey': f'public-symbol-{uid}',
            'txSig': private_symbol(uid)}


def hash_block(b: dict[str, Any]) -> str:
    return symhash(str(b['ID']) + b['prevBlockHash'] + str(b['BlockchainDiffTarget'])
                   + str(b['txList'][0]['ID']))


def mk_block(bid: int, prev: str, tx: dict, uid: int, sid: int,
             sbid: int, sprev: str) -> dict:
    """mkMainBlock projection; original outer envelope ID is the auxiliary TXID."""
    shard = {'ID': sbid, 'prevBlockHash': sprev, 'BlockchainDiffTarget': C['initBlockchainDiffTarget'],
             'txList': [tx]}
    anchor = {'ID': sbid, 'from': f'Shard{sid}', 'to': 'MainChain', 'amount': 0,
              'pubkey': 'ANCHOR', 'txSig': hash_block(shard)}
    return {'ID': bid, 'prevBlockHash': prev, 'BlockchainDiffTarget': C['initBlockchainDiffTarget'],
            'txList': [deposit_tx(uid, uid), tx, anchor]}


def proof_guard(block: dict, uid: int) -> bool:
    head = block['txList'][0]
    return head['from'] == wallet(uid) and head['txSig'] == private_symbol(uid)


def make_proof(b: dict, uid: int) -> dict:
    bh = hash_block(b)
    tid = b['txList'][0]['ID']
    return {'BlockID': b['ID'], 'BlockHash': bh, 'BlockchainDiffTarget': b['BlockchainDiffTarget'],
            'TXID': tid, 'BlockTXList': b['txList'], 'proofID': symhash(bh + str(tid)),
            'proofSig': private_symbol(uid)}


def root_guard(p: dict, uid: int, policy: dict | None = None) -> bool:
    """Non-resource conjuncts of Root-block Validation; partial-list domain retained."""
    np = NP if policy is None else policy
    h = p['BlockTXList'][0]
    return (p['BlockchainDiffTarget'] >= np['Difficulty'] and h['amount'] >= np['minDeposit']
            and h['to'] == np['depositAddress'] and p['BlockID'] >= np['minBlockHeight']
            and p['TXID'] == h['ID'] and p['proofID'] == symhash(p['BlockHash'] + str(h['ID']))
            and h['from'] == wallet(uid) and h['txSig'] == private_symbol(uid))
