import json
import secrets
import string

from web3 import Web3
from web3.gas_strategies.time_based import medium_gas_price_strategy
from web3.middleware import geth_poa_middleware
from web3.exceptions import TransactionNotFound

# bsc testnet
url = "https://data-seed-prebsc-2-s3.binance.org:8545"
web = Web3(Web3.HTTPProvider(url))
web.eth.set_gas_price_strategy(medium_gas_price_strategy)
web.middleware_onion.inject(geth_poa_middleware, layer=0)

# get StakeUp contract
address = "0xC0A2Db0E13e29141DCb7Da723eEEAE3c5517DB52"
abi = json.loads(
    '[{"inputs":[],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":true,"internalType":"address","name":"spender","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"from","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Transfer","type":"event"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"subtractedValue","type":"uint256"}],"name":"decreaseAllowance","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"addedValue","type":"uint256"}],"name":"increaseAllowance","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"from","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"}]')
stakeup_contract = web.eth.contract(address=address, abi=abi)


def create_wallet():
    return web.eth.account.create(
        ''.join(secrets.choice(string.ascii_uppercase + string.ascii_lowercase) for i in range(10)))


def create_encrypted_wallet(password):
    return encrypt_wallet(create_wallet(), password)


def get_wallet_from_key(priv):
    try:
        return web.eth.account.from_key(priv)
    except ValueError:
        return False


def encrypt_wallet(wallet, password):
    return wallet.encrypt(password)


def decrypt_wallet(keystore, password):
    try:
        return get_wallet_from_key(web.to_hex(web.eth.account.decrypt(keystore, password)))
    except ValueError:
        return False


def to_ether(amt):
    return web.from_wei(amt, 'ether')


def to_wei(amt):
    return web.to_wei(amt, 'ether')


def to_gwei(amt):
    return web.to_wei(amt, 'gwei')


def get_bnb_balance(addr):
    return to_ether(web.eth.get_balance(addr))


def get_stakeup_balance(addr):
    return to_ether(stakeup_contract.functions.balanceOf(addr).call())


def get_token_balance(wallet_addr, token_addr):
    contract = web.eth.contract(address=token_addr)
    return contract.functions.balanceOf(wallet_addr).call()


def transfer_stakeup(from_addr, from_priv_key, to_addr, amt):
    if int(get_stakeup_balance(from_addr)) < int(amt):
        return "StakeUp"

    tx = stakeup_contract.functions.transfer(
        to_addr,
        to_wei(amt)
    ).build_transaction({
        'gas': 200000,
        'gasPrice': web.eth.gas_price,
        'nonce': web.eth.get_transaction_count(from_addr)
    })

    signed_tx = web.eth.account.sign_transaction(tx, from_priv_key)
    try:
        hashed_tx = web.eth.send_raw_transaction(signed_tx.rawTransaction)
    except ValueError:
        return "BNB"
    return hashed_tx


def transfer_bnb(from_addr, from_priv_key, to_addr, amt):
    if float(get_bnb_balance(from_addr)) < float(amt):
        return "BNB"

    tx = {
        'nonce': web.eth.get_transaction_count(from_addr),
        'to': to_addr,
        'value': to_wei(amt),
        'gas': 2000000,
        'gasPrice': web.eth.gas_price,
        'from': from_addr
    }

    signed_tx = web.eth.account.sign_transaction(tx, from_priv_key)
    hashed_tx = web.eth.send_raw_transaction(signed_tx.rawTransaction)

    return hashed_tx


def get_status(tx_hash):
    try:
        return web.eth.get_transaction_receipt(tx_hash)['status']
    except TransactionNotFound:
        return False

def get_adress_from_encrypted_wallet(wallet):
    return web.to_checksum_address("0x" + json.loads(wallet)['address'])