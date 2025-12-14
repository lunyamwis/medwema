import requests
import os

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "sk_test_xxxxxxx")  # Replace with your secret key
BASE_URL = os.getenv("PAYSTACK_BASE_URL", "https://api.paystack.co")
HEADERS = {
    "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
    "Content-Type": "application/json",
}

def get_last_n_subaccount_transactions(subaccount_code, n=6):
    """
    Fetches transactions from Paystack and returns the last n transactions
    for a specific subaccount code.

    Args:
        subaccount_code (str): The subaccount code to filter transactions by
        n (int): Number of most recent transactions to return (default 6)

    Returns:
        list: List of transaction dicts sorted by most recent first
    """
    per_page = 50  # Paystack max per page
    page = 1
    sub_txns = []

    while len(sub_txns) < n:
        params = {"perPage": per_page, "page": page}
        resp = requests.get(f"{BASE_URL}/transaction", headers=HEADERS, params=params)
        resp.raise_for_status()
        data = resp.json()["data"]

        if not data:
            break  # no more transactions

        # Filter for the given subaccount code
        for tx in data:
            sa = tx.get("subaccount")
            if sa and sa.get("subaccount_code") == subaccount_code:
                sub_txns.append(tx)
                if len(sub_txns) == n:
                    break

        # Stop if no more pages
        meta = resp.json().get("meta", {})
        if not meta.get("next_page"):
            break

        page += 1

    # Sort descending by creation date
    sub_txns.sort(
        key=lambda tx: tx.get("created_at") or tx.get("createdAt"),
        reverse=True
    )

    return sub_txns[:n]




def get_transaction_by_reference(reference, secret_key=PAYSTACK_SECRET_KEY):
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {
        "Authorization": f"Bearer {secret_key}",
    }
    response = requests.get(url, headers=headers)
    data = response.json()
    
    if data.get("status"):
        return data["data"]  # The transaction object
    else:
        return None  # Or handle errors accordingly
