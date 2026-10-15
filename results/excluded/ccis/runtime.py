"""Local multiprocess CPN-guided validation prototype.

Six TCP services at S=4 (one gateway, four workers, one root) plus a driver.
New design choices are documented in README.md; this is neither CPN Tools nor a
production blockchain. No real wallets, private keys, funds, or phone hardware.
Only trusted loopback RPC is supported. Do not expose these endpoints publicly.
"""
from __future__ import annotations
import asyncio
import copy
import json
import multiprocessing as mp
import os
import socket
import time
from typing import Any
from artifact import C, NP, MODEL, COSTS, TOTAL_B, TOTAL_C, deposit_tx, mk_block, hash_block
from artifact import proof_guard, make_proof, root_guard

LIMIT = 32 * 1024 * 1024


async def rpc(port: int, body: dict, timeout: float = 90.0) -> dict:
    async def call():
        reader, writer = await asyncio.open_connection('127.0.0.1', port, limit=LIMIT)
        try:
            writer.write(json.dumps(body, separators=(',', ':')).encode() + b'\n')
            await writer.drain()
            raw = await reader.readline()
            if not raw:
                raise RuntimeError(f'Empty response from {port}')
            result = json.loads(raw)
            if 'error' in result:
                raise RuntimeError(result['error'])
            return result
        finally:
            writer.close()
            await writer.wait_closed()
    return await asyncio.wait_for(call(), timeout)


class Gateway:
    def __init__(self, workers: list[int]):
        self.workers = workers
        self.reset({'devices': [], 'policy': 'stagewise', 'tau': .001})

    def reset(self, cfg):
        self.devices = {i: dict(d, held_b=0, held_c=0) for i, d in enumerate(cfg['devices'])}
        self.initial = copy.deepcopy(self.devices)
        self.policy, self.tau = cfg['policy'], cfg['tau']
        if self.policy not in ('stagewise', 'precheck', 'reserve'):
            raise ValueError('Unknown admission policy')
        self.requests, self.events = {}, []
        self.bid, self.prev = C['initBlockID'], 'genesisBlock'
        self.sbids = [1] * 4
        self.sprevs = [f'genesisShard{s}' for s in range(4)]
        self.deposit_balance = 0
        self.disconnect = set(cfg.get('disconnect', []))
        self.disconnected = set()

    def record(self, rid, event, **data):
        self.events.append({'ns': time.perf_counter_ns(), 'rid': rid, 'event': event, **data})

    def invariant(self):
        for uid, d in self.devices.items():
            assert min(d[k] for k in ('w', 'b', 'c', 'held_b', 'held_c')) >= 0
            if self.policy == 'reserve':
                assert d['b'] >= d['held_b'] and d['c'] >= d['held_c']
                active = [r for r in self.requests.values() if r.get('uid') == uid and r.get('admitted')]
                assert d['held_b'] == sum(r['hold_b'] for r in active)
                assert d['held_c'] == sum(r['hold_c'] for r in active)

    def admit(self, rid, uid, cid):
        # No await in this method: read/check/reserve/debit is one event-loop action.
        if rid in self.requests:
            raise ValueError('Duplicate request identifier')
        d = self.devices[uid]
        reason = ''
        if cid not in MODEL['mapping']:
            reason = 'unmapped'
        elif d['w'] < NP['minDeposit']:
            reason = 'wallet'
        elif self.policy != 'stagewise':
            hb, hc = (d['held_b'], d['held_c']) if self.policy == 'reserve' else (0, 0)
            if d['net'] == C['NET_OFF']:
                reason = 'offline'
            elif d['b'] - hb < TOTAL_B:
                reason = 'battery'
            elif d['c'] - hc < TOTAL_C:
                reason = 'cpu'
        r = {'uid': uid, 'cid': cid, 'sid': MODEL['mapping'].get(cid, -1), 'admitted': not reason,
             'hold_b': 0, 'hold_c': 0, 'spent_b': 0, 'spent_c': 0, 'phase': '', 'outcome': '',
             'reason': reason, 'bid': None}
        self.requests[rid] = r
        if reason:
            r['outcome'] = 'denied'
            self.record(rid, 'denied', reason=reason, uid=uid)
            return False
        d['w'] -= NP['minDeposit']
        if self.policy == 'reserve':
            d['held_b'] += TOTAL_B
            d['held_c'] += TOTAL_C
            r['hold_b'], r['hold_c'] = TOTAL_B, TOTAL_C
        self.record(rid, 'admitted', uid=uid, cid=cid, sid=r['sid'], w=d['w'],
                    b=d['b'], c=d['c'], held_b=d['held_b'], held_c=d['held_c'])
        self.invariant()
        return True

    def spend(self, rid, phase):
        r = self.requests[rid]
        d = self.devices[r['uid']]
        expect = {'block': '', 'proof': 'block', 'root': 'proof'}[phase]
        assert r['phase'] == expect and r['admitted'] and not r['outcome']
        cb, cc = COSTS[phase]
        reason = ('offline' if d['net'] == C['NET_OFF'] else
                  'battery' if d['b'] < cb else 'cpu' if d['c'] < cc else '')
        if reason:
            self.record(rid, 'guard_blocked', phase=phase, reason=reason)
            return {'ok': False, 'reason': reason}
        if self.policy == 'reserve':
            assert r['hold_b'] >= cb and r['hold_c'] >= cc
            r['hold_b'] -= cb
            r['hold_c'] -= cc
            d['held_b'] -= cb
            d['held_c'] -= cc
        d['b'] -= cb
        d['c'] -= cc
        r['spent_b'] += cb
        r['spent_c'] += cc
        r['phase'] = phase
        self.record(rid, phase, uid=r['uid'], b=d['b'], c=d['c'], net=d['net'],
                    held_b=d['held_b'], held_c=d['held_c'])
        ans = {'ok': True}
        if phase == 'block':
            # A chosen implementation binding uses the same logical owner in all stages.
            sid, uid = r['sid'], r['uid']
            tx = deposit_tx(r['cid'], uid)  # CPN routing surrogate: nested transaction ID.
            block = mk_block(self.bid, self.prev, tx, uid, sid, self.sbids[sid], self.sprevs[sid])
            r['bid'] = self.bid
            self.bid += 1
            self.prev += hash_block(block)
            self.sbids[sid] += 1
            self.sprevs[sid] = block['txList'][2]['txSig']
            self.deposit_balance += NP['minDeposit']
            ans['block'] = block
        self.invariant()
        return ans

    def terminal(self, rid, outcome, reason=''):
        r = self.requests[rid]
        assert r['admitted'] and not r['outcome']
        assert outcome in ('blocked', 'committed')
        if outcome == 'committed':
            assert r['phase'] == 'root' and (r['spent_b'], r['spent_c']) == (TOTAL_B, TOTAL_C)
        d = self.devices[r['uid']]
        d['held_b'] -= r['hold_b']
        d['held_c'] -= r['hold_c']
        r['hold_b'], r['hold_c'] = 0, 0
        r['outcome'], r['reason'] = outcome, reason
        self.record(rid, outcome, bid=r['bid'], reason=reason)
        self.invariant()
        return {'ok': True}

    async def handle(self, q):
        op = q['op']
        if op == 'health':
            return {'ok': True, 'role': 'gateway', 'pid': os.getpid()}
        if op == 'reset':
            self.reset(q)
            return {'ok': True}
        if op == 'spend':
            return self.spend(q['rid'], q['phase'])
        if op == 'terminal':
            return self.terminal(q['rid'], q['outcome'], q.get('reason', ''))
        if op == 'disconnect':
            uid = self.requests[q['rid']]['uid']
            if uid in self.disconnect and uid not in self.disconnected:
                self.devices[uid]['net'] = C['NET_OFF']
                self.disconnected.add(uid)
                self.record(q['rid'], 'disconnect', uid=uid)
            return {'ok': True}
        if op == 'snapshot':
            self.invariant()
            return {'devices': self.devices, 'initial': self.initial, 'requests': self.requests,
                    'events': self.events, 'deposit_balance': self.deposit_balance}
        if op == 'submit':
            rid, uid, cid = q['rid'], q['uid'], q['cid']
            if not self.admit(rid, uid, cid):
                return {'outcome': 'denied', 'reason': self.requests[rid]['reason']}
            await asyncio.sleep(C['EDGE_LAT'] * self.tau)
            sid = self.requests[rid]['sid']
            self.record(rid, 'routed', cid=cid, sid=sid)
            return await rpc(self.workers[sid], {'op': 'execute', 'rid': rid, 'uid': uid,
                                                'cid': cid, 'sid': sid, 'tau': self.tau})
        raise ValueError(f'Unknown operation: {op}')


class Shard:
    def __init__(self, sid, gateway, root):
        self.sid, self.gateway, self.root = sid, gateway, root
        self.lock = asyncio.Lock()

    async def handle(self, q):
        if q['op'] == 'health':
            return {'ok': True, 'role': 'shard', 'sid': self.sid, 'pid': os.getpid()}
        if q['op'] != 'execute' or q['sid'] != self.sid or MODEL['mapping'][q['cid']] != self.sid:
            raise ValueError('Incorrect worker route')
        rid = q['rid']
        async with self.lock:
            result = await rpc(self.gateway, {'op': 'spend', 'phase': 'block', 'rid': rid})
            if result['ok']:
                await asyncio.sleep(C['BLOCK_TIME'] * q['tau'])
        if not result['ok']:
            return await self.blocked(rid, 'block:' + result['reason'])
        block = result['block']
        await rpc(self.gateway, {'op': 'disconnect', 'rid': rid})
        if not proof_guard(block, q['uid']):
            return await self.blocked(rid, 'proof:binding')
        result = await rpc(self.gateway, {'op': 'spend', 'phase': 'proof', 'rid': rid})
        if not result['ok']:
            return await self.blocked(rid, 'proof:' + result['reason'])
        return await rpc(self.root, {'op': 'validate', 'rid': rid, 'uid': q['uid'],
                                    'block': block, 'proof': make_proof(block, q['uid']), 'tau': q['tau']})

    async def blocked(self, rid, reason):
        await rpc(self.gateway, {'op': 'terminal', 'rid': rid, 'outcome': 'blocked', 'reason': reason})
        return {'outcome': 'blocked', 'reason': reason}


class Root:
    def __init__(self, gateway):
        self.gateway = gateway
        self.candidates, self.decisions, self.commits = {}, {}, []

    async def handle(self, q):
        op = q['op']
        if op == 'health':
            return {'ok': True, 'role': 'root', 'pid': os.getpid()}
        if op == 'reset':
            self.candidates, self.decisions, self.commits = {}, {}, []
            return {'ok': True}
        if op == 'snapshot':
            return {'commits': self.commits, 'decisions': self.decisions}
        if op != 'validate':
            raise ValueError('Unknown root operation')
        rid, b, p = q['rid'], q['block'], q['proof']
        bid = b['ID']
        assert bid not in self.candidates and p['BlockID'] == bid
        self.candidates[bid] = b
        if not root_guard(p, q['uid']):
            reason = 'root:binding'
        else:
            result = await rpc(self.gateway, {'op': 'spend', 'phase': 'root', 'rid': rid})
            reason = '' if result['ok'] else 'root:' + result['reason']
        if reason:
            await rpc(self.gateway, {'op': 'terminal', 'rid': rid, 'outcome': 'blocked', 'reason': reason})
            return {'outcome': 'blocked', 'reason': reason}
        self.decisions[bid] = True
        decision_ns = time.perf_counter_ns()
        assert bid in self.candidates and self.decisions[bid] is True
        await asyncio.sleep(C['FINALITY'] * q['tau'])
        record = {'rid': rid, 'bid': bid, 'uid': q['uid'], 'decision_ns': decision_ns,
                  'commit_ns': time.perf_counter_ns()}
        self.commits.append(record)
        await rpc(self.gateway, {'op': 'terminal', 'rid': rid, 'outcome': 'committed'})
        return {'outcome': 'committed', 'bid': bid}


async def serve(role, port, cfg):
    service = (Gateway(cfg['workers']) if role == 'gateway' else
               Root(cfg['gateway']) if role == 'root' else
               Shard(cfg['sid'], cfg['gateway'], cfg['root']))
    async def handler(reader, writer):
        try:
            request = json.loads(await reader.readline())
            result = await service.handle(request)
        except Exception as exc:
            result = {'error': f'{type(exc).__name__}: {exc}'}
        writer.write(json.dumps(result, separators=(',', ':')).encode() + b'\n')
        try:
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()
    server = await asyncio.start_server(handler, '127.0.0.1', port, limit=LIMIT, backlog=2048)
    async with server:
        await server.serve_forever()


def process_main(role, port, cfg):
    asyncio.run(serve(role, port, cfg))


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class Deployment:
    def __init__(self):
        self.gateway, self.root = free_port(), free_port()
        self.workers = [free_port() for _ in range(4)]
        self.processes = []

    async def start(self):
        ctx = mp.get_context('spawn')
        roles = [('gateway', self.gateway, {'workers': self.workers}),
                 ('root', self.root, {'gateway': self.gateway})]
        roles += [('shard', p, {'sid': sid, 'gateway': self.gateway, 'root': self.root})
                  for sid, p in enumerate(self.workers)]
        for role, port, cfg in roles:
            process = ctx.Process(target=process_main, args=(role, port, cfg))
            process.start()
            self.processes.append(process)
        health = []
        for _, port, _ in roles:
            for attempt in range(200):
                try:
                    h = await rpc(port, {'op': 'health'}, timeout=2)
                    health.append(dict(h, port=port))
                    break
                except (OSError, asyncio.TimeoutError):
                    await asyncio.sleep(.05)
            else:
                raise RuntimeError('Service failed to start')
        return health

    def stop(self):
        for process in self.processes:
            if process.is_alive():
                process.terminate()
        for process in self.processes:
            process.join(timeout=5)
