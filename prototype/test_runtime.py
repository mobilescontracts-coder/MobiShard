"""Local rule and reservation tests; not native CPN or whole-net verification."""
import copy
import random
import unittest
from artifact import C, NP, COSTS, MODEL, TOTAL_B, TOTAL_C, symhash, deposit_tx, mk_block, make_proof, root_guard
from runtime import Gateway


class TestPrototype(unittest.TestCase):
    def gateway(self, policy='reserve', w=300, b=100, c=35, net=2):
        g = Gateway([1, 2, 3, 4])
        g.reset({'devices': [{'w': w, 'b': b, 'c': c, 'net': net}], 'policy': policy, 'tau': 0})
        return g

    def test_source_costs(self):
        self.assertEqual((TOTAL_B, TOTAL_C), (4, 7))
        self.assertEqual((NP['minDeposit'], NP['minBlockHeight']), (15, 0))
        self.assertEqual((C['EDGE_LAT'], C['BLOCK_TIME'], C['FINALITY']), (2, 5, 10))

    def test_source_hash(self):
        for s in ('', 'a', 'abc', 'wallet-1', 'genesisBlock'):
            expected = sum(ord(ch) * (7 ** j) for j, ch in enumerate(s)) % MODEL['hash_modulus']
            self.assertEqual(symhash(s), str(expected))

    def test_default_wallet_capacity(self):
        g = self.gateway(w=100, c=100)
        self.assertEqual(sum(g.admit(str(i), 0, i) for i in range(16)), 6)

    def test_reserved_cpu_capacity(self):
        g = self.gateway()
        self.assertEqual(sum(g.admit(str(i), 0, i) for i in range(16)), 5)

    def test_precheck_does_not_reserve(self):
        g = self.gateway('precheck')
        self.assertEqual(sum(g.admit(str(i), 0, i) for i in range(16)), 16)
        self.assertEqual(g.devices[0]['held_c'], 0)

    def test_stagewise_checks_wallet_only(self):
        g = self.gateway('stagewise', net=0)
        self.assertTrue(g.admit('a', 0, 0))
        self.assertFalse(g.spend('a', 'block')['ok'])

    def test_offline_denied_before_debit(self):
        g = self.gateway(net=0)
        self.assertFalse(g.admit('a', 0, 0))
        self.assertEqual(g.devices[0]['w'], 300)

    def test_exact_resource_boundary(self):
        g = self.gateway(b=4, c=7)
        self.assertTrue(g.admit('a', 0, 0))
        for stage in ('block', 'proof', 'root'):
            self.assertTrue(g.spend('a', stage)['ok'])
        g.terminal('a', 'committed')
        self.assertEqual((g.devices[0]['b'], g.devices[0]['c']), (0, 0))

    def test_concurrent_stage_orders(self):
        for seed in range(100):
            g = self.gateway()
            ids = [str(i) for i in range(5)]
            for i in ids:
                self.assertTrue(g.admit(i, 0, int(i)))
            progress = {i: 0 for i in ids}
            rng = random.Random(seed)
            while ids:
                i = rng.choice(ids)
                stage = ('block', 'proof', 'root')[progress[i]]
                self.assertTrue(g.spend(i, stage)['ok'])
                progress[i] += 1
                if progress[i] == 3:
                    g.terminal(i, 'committed')
                    ids.remove(i)
            self.assertEqual(g.devices[0]['c'], 0)

    def test_blocked_releases_unused_hold_not_wallet(self):
        g = self.gateway()
        g.admit('a', 0, 0)
        g.spend('a', 'block')
        g.devices[0]['net'] = 0
        self.assertFalse(g.spend('a', 'proof')['ok'])
        g.terminal('a', 'blocked')
        self.assertEqual((g.devices[0]['w'], g.devices[0]['held_c'], g.devices[0]['c']), (285, 0, 32))

    def test_commit_requires_root_spend(self):
        g = self.gateway()
        g.admit('a', 0, 0)
        with self.assertRaises(AssertionError):
            g.terminal('a', 'committed')

    def test_valid_root_and_mutations(self):
        b = mk_block(0, 'genesisBlock', deposit_tx(3, 1), 1, 3, 1, 'genesisShard3')
        p = make_proof(b, 1)
        self.assertTrue(root_guard(p, 1))
        for field, value in [('BlockchainDiffTarget', 9), ('BlockID', -1), ('TXID', 999), ('proofID', 'wrong')]:
            changed = copy.deepcopy(p)
            changed[field] = value
            self.assertFalse(root_guard(changed, 1))
        for field, value in [('amount', 14), ('to', 'wrong'), ('from', 'wrong'), ('txSig', 'wrong')]:
            changed = copy.deepcopy(p)
            changed['BlockTXList'][0][field] = value
            self.assertFalse(root_guard(changed, 1))

    def test_symbolic_coverage_limits_preserved(self):
        b = mk_block(0, 'genesisBlock', deposit_tx(3, 1), 1, 3, 1, 'genesisShard3')
        p = make_proof(b, 1)
        p['proofSig'] = 'unchecked'
        p['BlockTXList'][1]['amount'] = -123
        self.assertTrue(root_guard(p, 1))

    def test_empty_proof_list_is_outside_domain(self):
        with self.assertRaises(IndexError):
            root_guard({'BlockTXList': []}, 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
