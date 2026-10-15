"""Regression tests for controlled accounting and serialization changes."""
import asyncio
import unittest
from runtime import Gateway

class RevisionTests(unittest.TestCase):
    def gateway(self, mode='operational', policy='reserve'):
        g=Gateway([1,2,3,4])
        g.reset({'devices':[{'w':300,'b':100,'c':35,'net':2}],
                 'policy':policy,'tau':0,'validation_mode':mode})
        return g

    def test_full_scan_detects_inconsistent_hold(self):
        g=self.gateway()
        g.admit('x',0,0)
        g.requests['x']['hold_c']-=1
        with self.assertRaises(AssertionError): g.invariant()

    def test_modes_preserve_deterministic_accounting(self):
        states=[]
        for mode in ('operational','full'):
            g=self.gateway(mode)
            for j in range(5): self.assertTrue(g.admit(str(j),0,j))
            for phase in ('block','proof','root'):
                for j in range(5): self.assertTrue(g.spend(str(j),phase)['ok'])
            for j in range(5): g.terminal(str(j),'committed')
            g.invariant()
            states.append((g.devices,g.requests))
        self.assertEqual(states[0],states[1])

    def test_serial_precheck_does_not_create_holds(self):
        g=self.gateway(policy='serial')
        self.assertTrue(g.admit('x',0,0))
        self.assertEqual(g.devices[0]['held_c'],0)
        for phase in ('block','proof','root'): g.spend('x',phase)
        g.terminal('x','committed')
        g.invariant()

class SerialSchedulingTests(unittest.IsolatedAsyncioTestCase):
    async def test_one_owner_enters_only_once(self):
        g=Gateway([1,2,3,4])
        g.reset({'devices':[{'w':300,'b':100,'c':35,'net':2}],
                 'policy':'serial','tau':0})
        active=0; maximum=0
        async def fake(q):
            nonlocal active,maximum
            active+=1; maximum=max(maximum,active)
            await asyncio.sleep(.001)
            active-=1
            return {'outcome':'test'}
        g.execute_submission=fake
        await asyncio.gather(*(g.handle({'op':'submit','uid':0,'rid':str(i),'cid':i}) for i in range(8)))
        self.assertEqual(maximum,1)

    async def test_different_owners_can_overlap(self):
        g=Gateway([1,2,3,4])
        g.reset({'devices':[{'w':300,'b':100,'c':35,'net':2}]*2,
                 'policy':'serial','tau':0})
        active=0; maximum=0
        async def fake(q):
            nonlocal active,maximum
            active+=1; maximum=max(maximum,active)
            await asyncio.sleep(.001)
            active-=1
            return {'outcome':'test'}
        g.execute_submission=fake
        await asyncio.gather(*(g.handle({'op':'submit','uid':u,'rid':str(u),'cid':u}) for u in range(2)))
        self.assertEqual(maximum,2)

if __name__=='__main__': unittest.main(verbosity=2)
