#!/usr/bin/env python3
"""Launch local TCP services, execute controlled workloads, retain measurements.

Example: python3 prototype/run_experiments.py --repetitions 20 --out results/deployment
No internet, real blockchain, CPN Tools, or third-party Python package required.
Use --extended to run all five controlled experimental suites.
Every experiment is a 256-request burst (16 logical devices x 16 requests), fresh
state, 4 FIFO shard workers, and randomised submission/policy order.
"""
from __future__ import annotations
import argparse
import asyncio
import csv
import gzip
import hashlib
import json
import math
import os
import platform
import random
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from artifact import MODEL, NP, TOTAL_B, TOTAL_C
from runtime import Deployment, rpc

POLICIES = ('stagewise', 'precheck', 'reserve', 'serial')
PROFILES = ('default', 'cpu', 'battery', 'mixed')


def profiles(name: str, rng: random.Random) -> list[dict]:
    def d(w, b, c, net=2):
        return {'w': w, 'b': b, 'c': c, 'net': net}
    if name == 'default':
        return [d(100, 100, 100) for _ in range(16)]
    if name == 'cpu':
        return [d(300, 100, 35) for _ in range(16)]
    if name == 'battery':
        return [d(300, 20, 100) for _ in range(16)]
    if name == 'mixed':
        items = [d(300, 100, 100), d(300, 100, 35), d(300, 20, 100), d(300, 100, 100, 0)] * 4
        rng.shuffle(items)
        return items
    if name == 'disconnect':
        return [d(300, 100, 100) for _ in range(16)]
    raise ValueError(name)


def quantile(items, p):
    if not items:
        return float('nan')
    x = sorted(items)
    v = (len(x) - 1) * p
    lo, hi = math.floor(v), math.ceil(v)
    return x[lo] + (x[hi] - x[lo]) * (v - lo)


def cpu_capacity(d):
    if d['net'] == 0:
        return 0
    return min(16, d['w'] // NP['minDeposit'], d['b'] // TOTAL_B, d['c'] // TOTAL_C)


async def one_run(dep, profile, policy, seed, tau, concurrency=16, arrival='burst', validation_mode='operational', suite='main'):
    rng = random.Random(100_000 + seed)
    ds = profiles(profile, rng)
    disconnect = rng.sample(range(16), 4) if profile == 'disconnect' else []
    workload = [{'op': 'submit', 'rid': f'{uid}:{j}', 'uid': uid, 'cid': (uid * 16 + j) % 64}
                for uid in range(16) for j in range(16)]
    rng.shuffle(workload)
    input_digest = hashlib.sha256(json.dumps({'devices': ds, 'workload': workload,
                                              'disconnect': disconnect, 'concurrency': concurrency, 'arrival': arrival}, sort_keys=True).encode()).hexdigest()
    await rpc(dep.root, {'op': 'reset'})
    await rpc(dep.gateway, {'op': 'reset', 'devices': ds, 'policy': policy, 'tau': tau,
                            'disconnect': disconnect, 'validation_mode': validation_mode})
    rows = []
    slots = {uid: asyncio.Semaphore(concurrency) for uid in range(16)}
    start_ns = time.perf_counter_ns()
    async def send(index, q):
        # Open-loop nominal arrivals: all burst at zero or 2 ms apart.
        due_ns = start_ns + (index * 2_000_000 if arrival == 'staggered' else 0)
        delay = (due_ns - time.perf_counter_ns()) / 1e9
        if delay > 0:
            await asyncio.sleep(delay)
        offered_ns = time.perf_counter_ns()
        async with slots[q['uid']]:
            rpc_ns = time.perf_counter_ns()
            response = await rpc(dep.gateway, q)
        stop = time.perf_counter_ns()
        rows.append(dict(q, scheduled_ns=due_ns, start_ns=offered_ns,
                         rpc_ns=rpc_ns, stop_ns=stop, **response))
    await asyncio.gather(*(send(i, q) for i, q in enumerate(workload)))
    stop_ns = time.perf_counter_ns()
    snapshot = await rpc(dep.gateway, {'op': 'snapshot'})
    root = await rpc(dep.root, {'op': 'snapshot'})
    request_map = snapshot['requests']
    admitted = sum(r['admitted'] for r in request_map.values())
    committed = sum(r['outcome'] == 'committed' for r in request_map.values())
    blocked = sum(r['outcome'] == 'blocked' for r in request_map.values())
    denied = sum(r['outcome'] == 'denied' for r in request_map.values())
    assert len(rows) == len(request_map) == committed + blocked + denied == 256
    assert admitted == committed + blocked
    assert len(root['commits']) == committed
    assert len({r['bid'] for r in root['commits']}) == committed
    events_by_rid = {}
    for e in snapshot['events']:
        events_by_rid.setdefault(e['rid'], []).append(e['event'])
    for c in root['commits']:
        events = events_by_rid[c['rid']]
        assert events.index('block') < events.index('proof') < events.index('root') < events.index('committed')
        assert root['decisions'][str(c['bid'])] is True
        assert c['commit_ns'] - c['decision_ns'] >= int(10 * tau * 1e9)
    for uid, d in snapshot['devices'].items():
        ours = [r for r in request_map.values() if r['uid'] == int(uid)]
        initial = ds[int(uid)]
        assert d['w'] == initial['w'] - sum(r['admitted'] for r in ours) * NP['minDeposit']
        assert d['b'] == initial['b'] - sum(r['spent_b'] for r in ours)
        assert d['c'] == initial['c'] - sum(r['spent_c'] for r in ours)
        assert d['held_b'] == d['held_c'] == 0
        assert min(d['w'], d['b'], d['c']) >= 0
    assert snapshot['deposit_balance'] == sum(r['phase'] != '' for r in request_map.values()) * NP['minDeposit']
    if profile != 'disconnect' and policy in ('reserve', 'serial'):
        assert committed == sum(cpu_capacity(d) for d in ds)
        assert blocked == 0
    lat = [(r['stop_ns'] - r['start_ns']) / 1e6 for r in rows if r['outcome'] == 'committed']
    elapsed = (stop_ns - start_ns) / 1e9
    rec = {'suite': suite, 'profile': profile, 'concurrency': concurrency, 'arrival': arrival,
           'validation_mode': validation_mode, 'policy': policy, 'seed': seed, 'tau_ms': tau * 1000,
           'input_sha256': input_digest, 'submitted': 256, 'admitted': admitted,
           'committed': committed, 'blocked': blocked, 'denied': denied,
           'completion_pct': 100 * committed / 256,
           'admitted_completion_pct': 100 * committed / admitted if admitted else float('nan'),
           'elapsed_s': elapsed, 'throughput_rps': committed / elapsed,
           'mean_latency_ms': statistics.mean(lat) if lat else float('nan'), 'p95_latency_ms': quantile(lat, .95),
           'wasted_cpu': sum(r['spent_c'] for r in request_map.values() if r['outcome'] == 'blocked'),
           'wasted_battery': sum(r['spent_b'] for r in request_map.values() if r['outcome'] == 'blocked'),
           'blocked_deposit_units': blocked * NP['minDeposit'],
           'budget_bound': sum(cpu_capacity(d) for d in ds),
           'invariant_violations': 0, 'trace_events': len(snapshot['events'])}
    return rec, {'summary': rec, 'config': {'devices': ds, 'workload': workload, 'disconnect': disconnect,
                                      'concurrency': concurrency, 'arrival': arrival, 'validation_mode': validation_mode},
                 'responses': rows, 'gateway': snapshot, 'root': root}


def read_optional(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


async def main(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    dep = Deployment()
    env = {'started_utc': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(),
           'platform': platform.platform(), 'logical_cpu_count': os.cpu_count(),
           'affinity_count': len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None,
           'cpu_max': read_optional('/sys/fs/cgroup/cpu.max'),
           'memory_max': read_optional('/sys/fs/cgroup/memory.max'), 'model': MODEL,
           'code_sha256': {f.name: hashlib.sha256(f.read_bytes()).hexdigest()
                           for f in Path(__file__).parent.glob('*.py')},
           'command': vars(args), 'driver_pid': os.getpid()}
    try:
        env['services'] = await dep.start()
        (out / 'environment.json').write_text(json.dumps(env, indent=2))
        # Warm all policies. Warm-up observations are explicitly excluded from results.csv.
        warm = []
        for policy in POLICIES:
            rec, _ = await one_run(dep, 'default', policy, 0, .001)
            warm.append(rec)
        (out / 'warmup.json').write_text(json.dumps(warm, indent=2))
        jobs = []
        for seed in range(1, args.repetitions + 1):
            batch = [(p, policy, seed, .001, 16, 'burst', 'operational', 'main')
                     for p in PROFILES for policy in POLICIES]
            if args.extended:
                batch += [('cpu', policy, seed, .001, cap, 'burst', 'operational', 'concurrency')
                          for cap in (1, 2, 4, 8) for policy in POLICIES]
                batch += [('cpu', policy, seed, .001, 16, 'staggered', 'operational', 'arrival')
                          for policy in POLICIES]
                batch += [('cpu', policy, seed, .001, 16, 'burst', 'full', 'instrumentation')
                          for policy in POLICIES]
                batch += [('disconnect', policy, seed, .001, 16, 'burst', 'operational', 'disconnect')
                          for policy in POLICIES]
            random.Random(900_000 + seed).shuffle(batch)
            jobs += batch
        with (out / 'results.csv').open('w', newline='') as csvfile, gzip.open(out / 'traces.jsonl.gz', 'wt') as tracefile:
            writer = None
            for idx, job in enumerate(jobs, 1):
                rec, trace = await one_run(dep, *job)
                if writer is None:
                    writer = csv.DictWriter(csvfile, fieldnames=list(rec))
                    writer.writeheader()
                writer.writerow(rec)
                csvfile.flush()
                tracefile.write(json.dumps(trace, separators=(',', ':')) + '\n')
                tracefile.flush()
                print(f"{idx}/{len(jobs)} {rec['profile']:10s} {rec['policy']:9s} s={rec['seed']:2d} "
                      f"{rec['suite']} cap={rec['concurrency']} admitted={rec['admitted']:3d} committed={rec['committed']:3d} "
                      f"blocked={rec['blocked']:3d} runtime={rec['elapsed_s']:.3f}s", flush=True)
        env['ended_utc'] = datetime.now(timezone.utc).isoformat()
        env['retained_runs'] = len(jobs)
        (out / 'environment.json').write_text(json.dumps(env, indent=2))
    finally:
        dep.stop()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repetitions', type=int, default=20)
    p.add_argument('--out', default='results/deployment')
    p.add_argument('--extended', action='store_true', help='Concurrency, arrivals, instrumentation, and disconnection studies')
    a = p.parse_args()
    if not 1 <= a.repetitions <= 1000:
        p.error('--repetitions must be between 1 and 1000')
    asyncio.run(main(a))
