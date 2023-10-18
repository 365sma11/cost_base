import streamlit as st
import asyncio
import requests
import pandas as pd
from json import JSONDecodeError
from datetime import datetime
import time

from moralis import evm_api

api_key = st.secrets["api_key"] 
moralis_api= st.secrets["moralis_api"] 

# Define the session state if it doesn't exist
if 'wallet_tokens' not in st.session_state:
    st.session_state['wallet_tokens'] = {}
if 'Tokens' not in st.session_state:
    st.session_state['Tokens'] = {}
if 'Transfers' not in st.session_state:
    st.session_state['Transfers'] = {}
if 'page_number' not in st.session_state:
    st.session_state['page_number'] = 0
if 'net_worth' not in st.session_state:
    st.session_state['net_worth'] = 0  # Initialize net_worth
if 'count' not in st.session_state:
    st.session_state['count'] = 1  
if 'pure_transactions' not in st.session_state:
    st.session_state['pure_transactions'] = {}  # unique transactions across all wallets



def handle_transfer_type(transaction, contract_address):
    #st.write(transaction)
    transfer_type = transaction['transfer_type']
    #st.write(transfer_type)
    delta = transaction['delta']
    #st.write(delta)
    delta_quote = transaction['delta_quote']
    #st.write(delta_quote)
    token_data = st.session_state['Tokens'][contract_address]
    #st.write(token_data)
    
    if transfer_type == 'IN':
        if delta != 0:
            #st.write(f"Current balance: {token_data['balance']}")
            token_data['balance'] += float(delta)
            #st.write(f"Updated balance: {token_data['balance']}")
        if isinstance(delta_quote, (int, float)):
            #st.write(f"Current cost base: {token_data['cost_base']}")
            token_data['cost_base'] += float(delta_quote)
            #st.write(f"Updated cost base: {token_data['cost_base']}")
    elif transfer_type == 'OUT':
        if delta != 0:
            #st.write(f"Current balance: {token_data['balance']}")
            portion = delta / token_data['balance']
            #st.write(f"Portion: {portion}")
            token_data['balance'] -= float(delta)
            #st.write(f"Updated balance: {token_data['balance']}")
        if isinstance(delta_quote, (int, float)):
            #st.write(f"Current cost base: {token_data['cost_base']}")
            cost_portion = portion * token_data['cost_base']
            token_data['cost_base'] -= cost_portion
            #st.write(f"Updated cost base: {token_data['cost_base']}")

def holdings_cost_base(wallet_list):
    #st.write("Holding Cost Calculations")
    #st.write(f"Wallet List: {wallet_list}")
    st.write('Processing transactions... this may take some time depending on how many transactions you have.')
    st.divider()

    # Organize transactions by date

    if 'Transfers' in st.session_state:
        sorted_transactions = sorted(st.session_state['Transfers'].values(), key=lambda x: x['block_signed_at'] if x else None)
    else:
        st.warning("No transactions found. 'Transfers' key not present.")
        sorted_transactions = []
    st.write("Transactions:")
    df = pd.DataFrame(sorted_transactions)
    st.dataframe(df)    

    # Loop through transactions
    for transaction in sorted_transactions:
        
        if isinstance(transaction, dict):
            #st.write(transaction)
            # Skip transactions involving other wallets in the list
            #st.write(f"From: {transaction['from_address']}")
            #st.write(f"To: {transaction['to_address']}")
            #st.write(f"Wallet List: {wallet_list}")

            lower_wallet_list = list(map(str.lower, wallet_list))

            if transaction['from_address'].lower() in lower_wallet_list and transaction['to_address'].lower() in lower_wallet_list:
                #st.divider()
                #st.write(f"transaction wallets shared, skipped: {transaction}")
                #st.divider()
                continue 
            else:
                contract_address = transaction['contract_address']
                #st.write(contract_address)
                #st.write(st.session_state['wallet_tokens'][contract_address])
                #st.write(transaction['tx_hash'])

                # Make sure the wallet and contract address exist in Tokens
                if contract_address in st.session_state['wallet_tokens']:
                    
                    
                    if contract_address in st.session_state['Tokens']:
                        handle_transfer_type(transaction, contract_address)
                    else:
                        #st.write('creating token')
                        #st.write(transaction['delta'])
                        #st.write(f"token balance {st.session_state['wallet_tokens'][contract_address]['balance']}")
                        st.session_state['Tokens'][contract_address] = {
                            'chain_name': st.session_state['wallet_tokens'][contract_address]['chain_name'],
                            'contract_address': st.session_state['wallet_tokens'][contract_address]['contract_address'],
                            'contract_name': st.session_state['wallet_tokens'][contract_address]['contract_name'],
                            'contract_ticker_symbol': st.session_state['wallet_tokens'][contract_address]['contract_ticker_symbol'],
                            'balance': st.session_state['wallet_tokens'][contract_address]['balance'],
                            'cost_base': 0,
                            'avg_cost_rate': 0,
                            'market_value': 0,
                            'market_rate': st.session_state['wallet_tokens'][contract_address]['market_rate'],
                            'profit_loss': 0,
                           
                        }
                        handle_transfer_type(transaction, contract_address)
                    #st.write(f"{st.session_state['wallet_tokens'][contract_address]['chain_name']} market rate: {st.session_state['wallet_tokens'][contract_address]['market_rate']}")







async def fetch_transactions(wallet, contract_address):
    counter = st.session_state['count']  # Initialize the counter
    has_more = True
    while has_more:
        #st.write(contract_address)
        #st.write(st.session_state['count'])
        response = requests.get(f"https://api.covalenthq.com/v1/eth-mainnet/address/{wallet}/transfers_v2/?key={api_key}&quote-currency=usd&contract-address={contract_address}")
        if response.status_code == 200:
            data = response.json()
            for res in data['data']['items']:
                for t in res['transfers']:
                    if t['delta'] is not None:
                        st.session_state['Transfers'][counter] = {  # Use counter as key
                            'contract_address': contract_address,
                            'block_signed_at': datetime.strptime(t['block_signed_at'], '%Y-%m-%dT%H:%M:%SZ'),
                            'tx_hash': t['tx_hash'],
                            'from_address': t['from_address'],
                            'to_address': t['to_address'],
                            'transfer_type': t['transfer_type'],
                            'delta': float(t['delta']) / (10 ** 18),
                            'delta_quote': t['delta_quote'],
                            'quote_rate': t['quote_rate']
                        }
                        #st.write(f"Transaction: {t['tx_hash']}")
                        #st.write(counter)
                        #st.write(st.session_state['Transfers'][counter])
                        counter += 1  # Increment the counter

            
            has_more = data['data']['pagination']['has_more']
            if has_more:
                st.session_state['page_number'] += 1
        else:
            handle_error(response)
    st.session_state['count'] = counter

def handle_error(response):
    error_message = 'Unknown error'
    try:
        error_message = response.json().get('error_message', 'Unknown error')
    except JSONDecodeError:
        pass
    st.write(f"Error fetching transactions: {error_message}")

        

def fetch_wallet_info(wallet_addresses):
    wallet_list = [wallet.strip() for wallet in wallet_addresses.split(",")]
    st.write("Checking Wallet List for coins with balances ... this may take some time")
    st.write(wallet_list)
    coin_decimal= 0
    counter=0
    for wallet in wallet_list:
        #st.write(f"Wallet: {wallet}")
        b = requests.get(f"https://api.covalenthq.com/v1/eth-mainnet/address/{wallet}/balances_v2/?key={api_key}&quote-currency=usd&no-spam=true")
        #st.write("API Response:", b.text)
        try:
            b_json = b.json()
        except Exception as e:
            st.write("Exception:", e)

        if b.status_code == 200:
            for item in b_json['data']['items']:
                #st.write(item['contract_address'])

                #Get contact Decimals
                #st.write(f'Count {counter}')
                if item['contract_address'] != "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
                    try:
                        params = {
                            "addresses": [item['contract_address']],
                            "chain": "eth"
                        }

                        result = evm_api.token.get_token_metadata(
                            api_key=moralis_api,
                            params=params,
                        )

                        #st.write(result)
                        #st.write(f"Decimal:{result[0]['decimals']}")
                        coin_decimal = float(result[0]['decimals'])
                    except Exception as e:
                        st.write(f"An error occurred: {e}. Setting coin_decimal to 18.")
                        coin_decimal = 18
                else:
                    #st.write('Ethereum contract')
                    coin_decimal= 18
                #st.write(coin_decimal) 

                if float(item['balance']) / (10 ** coin_decimal) > 0:
                    #st.write(f"Balance: {item['balance']}")
                    #st.write('adding contract')
                    if item['contract_address'] not in st.session_state['wallet_tokens']: ##checks to make sure duplicates don't get added
                        #st.write(item['contract_address'])    

                        #st.write(coin_decimal)
                        st.session_state['wallet_tokens'][item['contract_address']] = {
                            'chain_name': b_json['data']['chain_name'],
                            'contract_address': item['contract_address'],
                            'contract_name': item['contract_name'],
                            'contract_ticker_symbol': item['contract_ticker_symbol'],
                            'decimals': coin_decimal,
                            'balance': 0,
                            'cost_base': 0,
                            'avg_cost_rate': 0,
                            'market_value': item['quote'],
                            'market_rate': item['quote_rate'],
                            'profit_loss': 0,
                            
                        }

                        if item['quote'] is not None:  # Check to ensure quote is not None
                            st.session_state['net_worth'] += item['quote']  # Update net_worth
                        
        else:
            st.write(f"Error fetching data for wallet {wallet}: {b_json.get('error_message', 'Unknown error')}")

    st.write("Coins with Balances in Wallet(s)")
    df = pd.DataFrame(st.session_state['wallet_tokens'])
    st.dataframe(df)
    st.divider()

    for wallet in wallet_list:
        #get transactions for tokens in wallets
        for contract_address in st.session_state['wallet_tokens'].keys():
            #st.write(f'{wallet} Checking for transactions on contract: {contract_address}')
            if contract_address != "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
                #st.write(f'Checking {contract_address} for transactions')
                asyncio.run(fetch_transactions(wallet, contract_address))

        st.session_state['page_number'] = 0
        #st.divider()
    

    # Convert the dictionary to a DataFrame
    #df = pd.DataFrame.from_dict(st.session_state['Transfers'], orient='index')

    # Save the DataFrame to a CSV file
    #df.to_csv('Transfers.csv', index=False)

    # Display the DataFrame
    #st.write("Transactions:")
    #st.dataframe(df)

    holdings_cost_base(wallet_list)

    st.write("Done Processing, Ready to Go.  Select the token on the left and the in-game cost then hit calculate.")


def calculate(selected_option, usd_amount):
    selected_contract_address = selected_option.split(' (')[-1].strip(')')
    token_data = st.session_state['Tokens'][selected_contract_address]
    
    cost_base = token_data['cost_base'] / token_data['balance']
    current_price = token_data['market_rate']
    token_name= token_data['contract_ticker_symbol']
    token_data['market_value']= current_price* token_data['balance']
    token_data['profit_loss']= token_data['market_value'] - token_data['cost_base']
    token_data['avg_cost_rate']=cost_base
    st.write(token_data) 



    st.write(f"Your Average cost is {cost_base} USD")
    st.write(f"Current Market Price is {current_price} USD")
    st.write(f"Market value cost for ${usd_amount} USD would be: {float(usd_amount)/current_price} {token_name}")
    st.divider () 
    st.subheader("Your Best Option")
    if cost_base > current_price:

        st.write(f"Your Cost Base is higher than the current Market Price. Your best deal is using your Cost base. The purchase of ${usd_amount} in-game merch would cost you: {float(usd_amount) / cost_base} {token_name}")
    elif cost_base < current_price:
        st.write(f"Your Cost Base is lower than the current Market Price. Your best deal is using the Market Price. The purchase of ${usd_amount} in-game merch would cost you: {float(usd_amount) / current_price} {token_name}")
    st.divider ()

    st.subheader("How this works:")
    st.write("If you wanted to give your supporters the best 'deal' for an in-game purchase, one way you could go about it is maximize the value of their previous token purchase. ")
    st.write("You can do this 2 ways:")
    st.write("1. Use the current market price of the token to calculate the amount of tokens they would need to use for their purchase. This would be to their advantage if they bought at a lower price.")
    st.write("2. Use their cost base to calculate the amount of tokens to use for their purchase. This would be to their advantage if they bought at a higher price.")
    st.divider ()

    st.write(f"Example. I had previously purchased 1000 tokens. The current in-game purchase amount is equavalent to: $10 USD")
    col1,col2=st.columns(2)
    with col1:
        st.write("Example 1: Cost Base lower| Priced at Market")
        st.write("Cost Base: 0.01 USD")
        st.write("Market Price: 0.02 USD")
        st.write("The cost would be: 500 Tokens at Market")
        st.write("My actual cost: 500 x 0.01= $5")
    with col2:
        st.write("Example 2: Cost Base higher| Priced at Cost Base")
        st.write("Cost Base: 0.04 USD")
        st.write("Market Price: 0.02 USD")
        st.write("The cost would be: 250 Tokens at Cost Base")
        st.write("My actual cost: 250 x 0.04= $10")
    st.divider ()
    st.write("So, by getting in early at a lower price you save money. If you happen to buy it high and then it crashes, you are protected on the downside. It's a win/no-lose game where it potentially pays to get in early and there is no downside because the project has your back for the use of it's token for in-game purchases.")
    st.divider ()    

    st.subheader("Cost Base Calculation")
    
    col1,col2=st.columns(2)
    with col1:
        st.write("Example")
        st.markdown("Purchase 1- 500 \$Wild for \$125 (@\$0.25)")
        st.markdown("Transaction Cost Base= \$125 | My Cost Base= \$125")
        st.write("")
        st.markdown("Purchase 2- 500 \$Wild for \$100 (@\$0.20)")
        st.markdown("Transaction Cost Base= \$100 | My Cost Base= \$225")
        st.markdown("Total \$Wild= 1000")
        st.write("")
        st.markdown("Sell 500 \$Wild for Wheels upgrade")
        st.markdown("500 $Wild Remains")


    with col2:
        st.write("Calculation")
        st.markdown("\$125 / \$0.25= 500 \$Wild")
        st.markdown("It Cost me \$125")
        st.write("")
        st.markdown("\$100 / \$0.20= 500 \$Wild")
        st.markdown("It Cost me \$100 | Total spent so far \$225")
        st.markdown("Total Cost Base= /$225")
        st.write("")
        st.markdown("Cost Base= 500 sold/ 1000 total= 0.5 x \$225 Cost base= \$112.5 sold")
        st.markdown("Cost Base Remains= \$225 - \$112.5= \$112.5")
    st.write("")
    st.markdown("This Cost Base calculation for the In/Out transactions creates an average Cost Base.  In this case the Cost Base now is \$112.5 for 500 \$Wild which would give us an average cost of \$0.225 per remaining token (\$112.5/500)") 

    st.divider ()    
    st.subheader("Analyzer Assumptions")
    st.write("1. Transfers into the wallet are at market price. Thus, it does not account for purchases on CEX's at a different prices.")
    st.write("2. 'Your Best option' defaults to the best deal for the wallet owner")
    st.write("2. Cost base calculations are based off using an average cost base")

def populate_selectbox_options():
    options = [f"{value['contract_name']} ({key})" for key, value in st.session_state['Tokens'].items()]
    st.session_state['options'] = options

def main():
    st.title("ERC-20 Cost Base Analyzer")
    st.markdown("Determine based on $USD how many -**ERC-20 Tokens**- are required for In-Game token purchase")
    st.markdown("Note: wallet must have a balance of ERC-20 Tokens. Does not calculate Eth Coin cost base.")
    st.divider ()

    wallet_addresses = st.sidebar.text_input("Wallet addresses (separate by comma)", "")

    if st.sidebar.button("Fetch Wallet Info"):
        fetch_wallet_info(wallet_addresses)
        populate_selectbox_options()

    if st.sidebar.button("Reset"):
        st.session_state['wallet_tokens'] = {}
        st.session_state['Tokens'] = {}
        st.session_state['Transfers'] = {}
        st.session_state['page_number'] = 0
        st.session_state['net_worth'] = 0  # Initialize net_worth
        st.session_state['count'] = 1  # Initialize net_worth
        populate_selectbox_options()
        st.rerun()

    if 'options' in st.session_state:
        selected_option = st.sidebar.selectbox('Select a Token:', st.session_state['options'], key='selected_token')

        usd_amount = st.sidebar.text_input("Purchase cost in $USD", "")
        if st.sidebar.button("Calculate"):
            calculate(selected_option, usd_amount)
    st.sidebar.markdown("Step 1. Enter your Wallet(s)- Click Fetch")
    st.sidebar.markdown("Step 2. Select which token to use in Calculation")
    st.sidebar.markdown("Step 3. Enter the in-game purchase amount in USD")
    st.sidebar.markdown("Step 4. Click Calculate")
    st.sidebar.markdown("You can switch tokens and purchase amounts multiple times. Choose RESET before trying other wallet(s)")

if __name__ == "__main__":
    main()
