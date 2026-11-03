import unittest

from tools.frontline import rich_mdx as rm


class Densify(unittest.TestCase):
    def test_a_sequence_without_keys_holds_the_rest_pose(self):
        # Death sinks (keys 3000-5999), Decay stays under (9000-12999); Birth/Work/Stand Work in
        # between have no keys of their own and must not slide toward the sunk pose (the dry dock
        # and new structures sank while producing or being built).
        windows=[(0,999),(3000,5999),(6000,6999),(7000,7999),(8000,8999),(9000,12999)]
        keys=[(3000,0,0,0),(5999,0,0,-60),(9000,0,0,-60),(12999,0,0,-90)]
        dense={k[0]:k[1:] for k in rm.densify(keys,windows)}
        for a,b in ((0,999),(6000,6999),(7000,7999),(8000,8999)):
            self.assertEqual(dense[a],(0,0,0),a);self.assertEqual(dense[b],(0,0,0),b)
        self.assertEqual(dense[5999],(0,0,-60));self.assertEqual(dense[12999],(0,0,-90))

    def test_keyed_sequences_still_interpolate_their_ends(self):
        windows=[(0,1000)]
        dense={k[0]:k[1:] for k in rm.densify([(200,0,0,0),(800,0,0,10)],windows)}
        self.assertEqual(dense[0],(0,0,0));self.assertEqual(dense[1000],(0,0,10))

if __name__=='__main__':unittest.main()
