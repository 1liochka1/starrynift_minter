import json
import random
import time
from web3 import Web3
from eth_account.messages import encode_defunct
import requests
from loguru import logger
from fake_useragent import UserAgent
import pandas as pd
from tqdm import tqdm

wallets = []
results = []
rpcs = ['https://rpc.ankr.com/bsc', 'https://bsc-dataseed2.ninicoin.io', 'https://bsc-dataseed1.ninicoin.io/']

def get_msg(address):
    ua = UserAgent()
    user_agent = ua.random

    headers = {
        'authority': 'starrynift.art',
        'accept': 'application/json',
        'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'authorization': 'Bearer null',
        'content-type': 'application/json;charset=UTF-8',
        'origin': 'https://starrynift.art',
        'referer': 'https://starrynift.art/',
        'sec-ch-ua': '"Google Chrome";v="113", "Chromium";v="113", "Not-A.Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': user_agent,
    }

    session = requests.session()
    session.headers.update(headers)

    json_data = {
        'address': address,
    }
    while True:
        try:
            response = session.post('https://starrynift.art/api/user/challenge', json=json_data)
            if response.status_code in [200, 201]:
                msg = json.loads(response.text)['data']['message']
                return msg, session
        except Exception as e:
            logger.error(f'{address} - {e}')
            time.sleep(3)


def check_status_tx(tx_hash,address,w3):

    logger.info(f'{address} - жду подтверждения транзакции...')
    while True:
        try:
            status = w3.eth.get_transaction_receipt(tx_hash)
            status = status['status']
            if status in [0, 1]:
                return status
            time.sleep(1)
        except Exception as error:
            time.sleep(1)

def sleep_indicator(secs):
    for i in tqdm(range(secs), desc='жду', bar_format="{desc}: {n_fmt}c / {total_fmt}c {bar}", colour='green'):
        time.sleep(1)


def get_auth_and_mint(pr,delay,rpc):
    w3 = Web3(Web3.HTTPProvider(rpc))
    account = w3.eth.account.from_key(pr)
    address = w3.eth.account.from_key(pr).address

    msg, session = get_msg(address)
    time.sleep(5)
    message = encode_defunct(text=msg)
    sign = w3.eth.account.sign_message(message, private_key=pr)
    signature = w3.to_hex(sign.signature)

    json_data = {
        'address': address,
        'signature': signature,
    }
    try:
        response = session.post('https://starrynift.art/api/user/login', json=json_data)
        auth = json.loads(response.text)['data']['token']
        if auth:
            headers = {
                'authorization': f'Bearer {auth}',
            }
            session.headers.update(headers)

    except Exception as e:
        logger.error(f'{address} - {e}')

    json_data = {
        'category': 1,
    }

    response = session.post('https://starrynift.art/api-v2/citizenship/citizenship-card/sign',json=json_data)
    signa = json.loads(response.text)['signature']
    data = f'0xf75e0384000000000000000000000000000000000000000000000000000000000000002' \
           f'0000000000000000000000000{address[2:]}' \
           f'0000000000000000000000000000000000000000000000000000000000000001' \
           f'0000000000000000000000000000000000000000000000000000000000000060' \
           f'0000000000000000000000000000000000000000000000000000000000000041' \
           f'{signa[2:]}' \
           f'00000000000000000000000000000000000000000000000000000000000000'

    while True:
        try:
            tx = {
                "from": address,
                "to": w3.to_checksum_address('0xc92df682a8dc28717c92d7b5832376e6ac15a90d'),
                "value": 0,
                "nonce": w3.eth.get_transaction_count(address),
                "chainId": w3.eth.chain_id,
                "gasPrice": w3.eth.gas_price,
                "data": data,
            }
            gasLimit = w3.eth.estimate_gas(tx)
            tx['gas'] = gasLimit
            logger.info(f'{address} - начинаю минтить...')
            signed_tx = account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            status = check_status_tx(tx_hash,address,w3)
            sleep_indicator(5)
            tt = random.randint(delay[0], delay[1])
            if status == 1:
                logger.success(f'{address} - успешно заминтил : https://bscscan.com/tx/{w3.to_hex(tx_hash)}...')
                sleep_indicator(tt)
                return address, 'success'
        except Exception as e:
            error = str(e)
            if 'Card already minted for this category' in error:
                logger.error(f'{address} - уже заминчено...')
                return address, 'already minted'
            logger.error(f'{address} - {e}...')
            return address, 'error'

def main():
    print(f'\n{" "*32}автор - https://t.me/iliocka{" "*32}\n')

    with open("keys.txt", "r") as f:
        keys = [row.strip() for row in f]
    delay = (0, 100)  # перерыв между кошельками
    for key in keys:
        rpc = random.choice(rpcs)
        mint = get_auth_and_mint(key,delay,rpc)
        wallets.append(mint[0]), results.append(mint[1])
    res = {'address': wallets, 'result': results}
    df = pd.DataFrame(res)
    df.to_csv('results.csv', index=False)
    logger.success('Минетинг закончен...')

if __name__ == '__main__':
    main()

