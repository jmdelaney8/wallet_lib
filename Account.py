"""
Contains the class Account to represent an account with one email.
Also contains functions to work with keys and such.
"""

# fixme: move create_key to Wallet?

from pycoin.key.BIP32Node import BIP32Node
from pycoin.tx.Tx import Tx
from pycoin.tx.tx_utils import create_tx, sign_tx
from pycoin.key.validate import is_address_valid
from pycoin.cmds import ku
import Wallet

from smtplib import SMTP_SSL
import sqlite3

# FIX ME -- there is probably a much better way to do this
WALLET_KEYS = 'var/wallet_keys.sqlite3'


def set_wallet_keys_location(file_path):
    """Set the wallet_keys location to file_path"""
    global WALLET_KEYS
    WALLET_KEYS = file_path


# returns true if the email is not in the database, else false
def known_email(email):
    """If email is in wallet_key database, return True"""
    # FIXME: test that 'with sqlite3.connect(WALLET_KEYS) as conn'
    conn = sqlite3.connect(WALLET_KEYS)
    c = conn.cursor()
    query = (email, )
    c.execute('SELECT email FROM wallet_keys WHERE email=?', query)
    # print("output: ",c.fetchall())
    known_emails = c.fetchall()
    conn.close()
    if known_emails == []:
        return False
    return True


# EFFECTS: Creates a new **PRIVATE** wallet key and returns key
def create_wallet_key():
    wallet = BIP32Node.from_master_secret(ku.get_entropy())
    wallet_key = wallet.hwif(as_private=True)
    return wallet_key


# EFFECTS: Returns an address from the account associate with email
# fixme: make this pull from some database of public addresses
def get_address_for_account(email):
    """Retrieve one wallet for email. Return its address"""
    query = (email, )
    conn = sqlite3.connect(WALLET_KEYS)
    c = conn.cursor()
    c.execute('SELECT wallet_key from wallet_keys WHERE email=?', query)
    wallet_key = c.fetchone()[0]
    wallet = Wallet.Wallet.from_wallet_key(wallet_key)
    return wallet.address()


class Account:
    """Object to represent a one email account"""
    def __init__(self, email, import_key=None):
        self.email = email
        self.wallet_keys = []
        if known_email(email):
            self.wallet_keys = self.get_keys()
            return
        self.create_account()
        if import_key:
            self.add_wallet_key(import_key)
            self.wallet_keys.append(import_key)
            return
        new_key = self.new_wallet_key()
        self.wallet_keys.append(new_key)

    # EFFECTS: Returns wallet keys associated with account
    def get_wallet_keys(self):
        """Return wallet keys of account."""
        return self.wallet_keys

    # REQUIRES: email be associated with an account
    # EFFECTS: Returns the account information associated with this email
    def get_keys(self):
        """Return wallet keys from wallet_keys database for account"""
        conn = sqlite3.connect(WALLET_KEYS)
        c = conn.cursor()
        query = (self.email, )
        c.execute('SELECT wallet_key FROM wallet_keys WHERE email=?', query)
        results = c.fetchall()
        wallet_keys = []
        for result in results:
            if result:
                wallet_keys.append(result[0])
        conn.close()
        return wallet_keys
        # return ['xprv9s21ZrQH143K2cZXLUxwnVuc1Yt5uXEXGqP1xbei7...
        # rXEooe26rcf91gC7yMhFfGuBXHu5rwoXtf69fd2GCPHNY6cE5MFcbVAizwQ2vxoNDx']

    # REQUIRES: email associated with known account
    # MODIFIES: wallet_keys database
    # EFFECTS: Creates a new wallet key and adds it to account
    def new_wallet_key(self):
        """Create a new wallet key and add it to this account."""
        new_key = create_wallet_key()
        query = [(new_key, self.email), ]
        conn = sqlite3.connect(WALLET_KEYS)
        c = conn.cursor()
        c.executemany("""INSERT INTO wallet_keys(wallet_key, email)
                      VALUES (?, ?) """,
                      query)
        conn.commit()
        conn.close()
        self.wallet_keys.append(create_wallet_key())
        return new_key

    # REQUIRES: email not be associated with another account
    # MODIFIES: wallet_keys
    # EFFECTS: creates a new account with email and no wallet keys
    def create_account(self):
        """Add email to database without an wallet keys."""
        conn = sqlite3.connect(WALLET_KEYS)
        c = conn.cursor()
        query = (self.email, )
        c.execute('INSERT INTO wallet_keys(email) VALUES (?)', query)
        conn.commit()
        conn.close()

    # REQUIRES: email be in database
    # MODIFIES: wallet_keys database
    # EFFECTS: removes all the wallets from the database associated with email
    def delete_account(self):
        """Remove account from database."""
        conn = sqlite3.connect(WALLET_KEYS)
        c = conn.cursor()
        query = (self.email,)
        assert known_email(self.email)
        c.execute('DELETE FROM wallet_keys WHERE email=?', query)
        conn.commit()
        assert not known_email(self.email)
        conn.close()

    # REQUIRES: email corresponds to an account
    # EFFECTS: Returns true if account of email
    #          owns a wallet with key wallet_key
    def contains_wallet(self, wallet_key):
        """If account owns wallet, return true."""
        conn = sqlite3.connect(WALLET_KEYS)
        c = conn.cursor()
        query = (self.email, )
        c.execute('SELECT wallet_key from wallet_keys where email= ?', query)
        results = c.fetchall()
        wallet_keys = []
        for result in results:
            wallet_keys.append(result[0])
        return wallet_key in wallet_keys

    # REQUIRES: wallet_key be associated with the account owned by email.
    #           email is a known account
    # MODIFIES: wallet_keys
    # EFFECTS: Removes wallet_key from account associated with email
    def remove_wallet(self, wallet_key):
        """Remove wallet_key from account."""
        conn = sqlite3.connect(WALLET_KEYS)
        c = conn.cursor()
        query = (wallet_key,)
        assert self.contains_wallet(wallet_key)
        c.execute('DELETE FROM wallet_keys WHERE wallet_key=?', query)
        conn.commit()
        conn.close()

    # REQURIES: email associated with known account.
    #           wallet_key not already in account (wallet_key db)
    # MODIFIES: wallet_keys db
    # EFFECTS: Adds wallet_key to account associate with this object email
    def add_wallet_key(self, wallet_key):
        """Add wallet_key to account."""
        assert known_email(self.email)
        assert not self.contains_wallet(wallet_key)
        conn = sqlite3.connect(WALLET_KEYS)
        c = conn.cursor()
        query = [(wallet_key, self.email), ]
        c.executemany("""INSERT INTO wallet_keys(wallet_key, email)
                      VALUES (?,?)""", query)
        conn.commit()
        conn.close()

    # REQUIRES: email not be an email already in the database
    # EFFECTS: Sends the standard new user email to email
    def send_new_account_email(self):
        """Send the standard new user email to this account."""
        # system_email =
        standard_msg = """Hello, you have received money.
                       You can retrieve it at my website"""
        # fixme: fill with correct test email info
        # server = SMTP_SSL("smtp.gmail.com", 465)
        # server.login(system_email,  )
        server.sendmail(system_email, self.email, standard_msg)
        server.quit()

    # TO DO: add amount paid and function to look up utxos that
    #        will add to amount paid
    def send_payment(self, rec_email, amount):
        """
        Still in flux
        """
        # TO DO: a database with emails and addresses would
        #        be far better than this
        receive_address = get_address_for_account(rec_email)
        # create input from prior transaction
        tx_hex, index = self.utxo(amount)
        tx = Tx.from_hex(tx_hex)
        spendable = tx.tx_outs_as_spendable()[index]
        # create unsigned transaction
        tx = create_tx([spendable], [receive_address])
        print("usigned %s" % tx.as_hex())
        wallet = Wallet.Wallet.from_wallet_key(self.get_wallet_keys()[0])
        sign_tx(tx, [wallet.wif()])
        print("signed %s" % tx.as_hex())

    # EFFECTS: Returns the utxo hex and index of a utxo greater than or
    #          equal to amount, else None.
    def utxo(self, amount):
        """
        Find utxo owned by this account that are greater than or equal to
        amount. Return list of utxo hexes
        """
        query = (self.email,)
        conn = sqlite3.connect(WALLET_KEYS)
        c = conn.cursor()
        c.execute('SELECT tx_hex, tx_index from utxos WHERE email=?', query)
        # TO DO: include ability to cipher by value
        # (probably possible to get value from Tx onject)
        results = c.fetchone()
        conn.close()
        return results

    # EFFECTS: returns true if tx_hex is associated with account
    def is_utxo(self, tx_hex):
        """If a utxo of this account, return True."""
        query = (tx_hex, self.email)
        conn = sqlite3.connect(WALLET_KEYS)
        c = conn.cursor()
        c.execute('SELECT tx_hex from utxos WHERE tx_hex=? AND email=?', query)
        results = c.fetchall()
        conn.close()
        return len(results) != 0
