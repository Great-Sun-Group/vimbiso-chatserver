ACCOUNT_SELECTION = """
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
*{greeting}*

*_Which account would you like to_* 
*_view and manage?_*

{accounts}
 ⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

HOME = """
> *🏦 {account}*
{balance}
*👤 Account: _{handle}_*
 *1. 📥 Pending Offers ({pending_in})*
 *2. 🔀 Switch Account*
 *3. 📒 Review Ledger*
 *4. 💸 Offer Credex*
 *5. 💼 More Options*

 *What would you like to do ?*
 ⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

MANAGE_ACCOUNTS = """
> *💼 Manage Accounts*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
*👥 My Accounts*
 *1. 💼 Create Business*
 *2. 🗝️ Authorize Member*
 *3. 📤 Pending Outgoing ({pending_out})*

Send *'Menu'* to go back to Menu

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

INVALID_ACTION = """
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

*Invalid option selected*
"""

DELAY = """
Welcome to credex. 

Please hold a moment while 
we fetch your account data.
"""

BALANCE = """
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

*SECURED BALANCES*
{securedNetBalancesByDenom}
*USECURED BALANCES*
  Payables : {totalPayables}
  Receivables : {totalReceivables}
  PayRec : {netPayRec}

*CREDEX ASSETS*
  Credex Assets : {netCredexAssetsInDefaultDenom}
"""

BALANCE_FAILED = """
> *😞 Enquiry Failed*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Failed to perform balance
enquiry at the moment.
  
Send *'Menu'* to go back to Menu

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

CREDEX = """
> *💰 Credex*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

*Summary*

 Outstanding : {formattedOutstandingAmount}
 Party : {counterpartyDisplayname}
 Amount : {formattedInitialAmount}
 Date : {date}
 Type : {type}

Send *'Menu'* to go back to Menu

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

REGISTER = """
> *👤  Registration*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

*ℹ️  INSTRUCTIONS*
 To sign up for an account:

 - Click the *'Register'* button
   below and fill in the required
   fields and click submit.

Send *'Menu'* to go back to Menu

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

COMPANY_REGISTRATION = """
> *💼  Create New Account*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

*ℹ️  INSTRUCTIONS*
 To create a new account :

 - Click the *'Create Account'* 
   button below and fill in the 
   required fields and click submit.

{message}
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

OFFER_CREDEX = """
> *💰 Offer Credex*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

1.25=>CounterPartyHandle
to offer *secured* credex 
from your account

{message}
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

REGISTRATION_COMPLETE = """
> *🎉 Registered!*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Hello {full_name}

Welcome to Credex! We are 
excited to have you on board.

Send *'Menu'* and start 
exploring all the features 
we offer.

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

CONFIRM_SECURED_CREDEX = """
> *💰 Confirm*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Offer {secured} credex:
  ${amount} {currency} to {party}

Make offer from:
{accounts}
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

CONFIRM_UNSECURED_CREDEX = """
> *💰 Confirm*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Offer {secured} credex:
  ${amount} {currency} to {party}
  due {date}

Make offer from:
{accounts}
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

ACCEPT_CREDEX = """
> *💰 Accept Offer*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

*Accept {amount} offer*

  {type} credex from
- {party} 
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

OUTGOING_CREDEX = """
> *💰 Cancel Offer*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

*Cancel {amount} offer*

  {type} credex to
- {party} 
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

OFFER_SUCCESSFUL = """
> *✅ Success!*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

*Offered*

{amount} {currency} {secured} to
{recipient}

Send *'Menu'* to go back to Menu
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

OFFER_FAILED = """
> *😞 Failed*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Failed to perform transaction
at the moment.

{message}
Send *'Menu'* to go back to Menu

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

ADD_MERMBER = """
> *🗝️ Authorize Member*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Send member *handle* of the 
member you wish to allow to 
authorize transactions for 
*{company}*

{message}
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

CONFIRM_AUTHORIZATION = """
> *🗝️ Confirm Authorization*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Do you wish to allow member:

- *{member}*

to perform transactions for
*{company} ?*

*1. ✅ Authorize*
*2. ❌ Cancel*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

AUTHORIZATION_SUCCESSFUL = """
> *✅ Success*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️

Member authorization complete!

- *{member}*

can now transact on behalf of 
*{company}*
⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

AUTHORIZATION_FAILED = """
> *❌ Failed*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
Member authorization failed!

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""

AGENTS = """
> *👤 Agents*

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
Agents
1. Hre (+263 77 369 6227)
2. Byo (+263 77 369 6227)
3. Kwe (+263 77 369 6227)
4. Kdm (+263 77 369 6227)
5. Rspe (+263 77 369 6227)

⚠️⚠️⚠️ CREDEX DEMO ⚠️⚠️⚠️
"""
