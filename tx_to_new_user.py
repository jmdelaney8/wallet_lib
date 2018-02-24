from pycoin.key.BIP32Node import BIP32Node
from smtplib import SMTP_SSL
import sys

# using personal email for test
system_email = "jmdelaney8@gmail.com"

# This is a stand in test sender using a test wallet address
# test wallet master secret = 'password'
send_addr = '18tsPjLmtCWAAfF5c1gzZs4BEQLq6XN282'

# to make testing easier
if len(sys.argv) ! = 2:
    rec_email = input("pay to email: ")
else:
    rec_email = sys.argv[1]
# assuming email is not is user database
# creating wallet for new user
# TO DO:
# a better and more secure way to create wallets
password = 'random'
new_wallet = BIP32Node.from_master_secret(password.encode('utf-8'))
new_wif = new_wallet.wif()

# email wallet info to user
# TO DO:
# obviously bad security. This is a stand in for a system to on board users
standard_msg = ("Hello, \n You've got money. Retrieve with %s" % new_wif)
server = SMTP_SSL("smtp.gmail.com", 465)
server.login(system_email, "klcfkamvubxpcqit")
server.sendmail(system_email, rec_email, standard_msg)
server.quit()
