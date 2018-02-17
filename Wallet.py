"""Wallet module pulls heavily from BIP32Node (of which it inherets)"""
from pycoin.key.BIP32Node import BIP32Node


class Wallet(BIP32Node):
    def do_nothing(self):
        """Stand in so class works"""
        return
