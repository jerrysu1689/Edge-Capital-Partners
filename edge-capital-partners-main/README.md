# What does the project achieve?

This is a long polling script that monitors your inbox for new emails from the `SENDER_EMAIL` mentioned in your `.env` file.

# Dependencies

## IBKR TWS

Make sure TWS is running and configure Trusted IPs and port number you want the TWS to listen on from TWS's Global Configurations.
Change other API configuration settings on TWS, essentioal ones are:
- Enable ActiveX and Socket Clients should be selected
- Read-Only API should be unselected

# Setup

## `.env` file

Look at `sample.env` and create a new `.env` file with the assigned variables at the root of the project.

## Gmail password
The password you use to login to gmail will not work you need to generate an app password from google account management:
1. Go to [manage google account](https://myaccount.google.com/)
2. Ensure 2FA is enabled.
3. Look for `App passwords`. You can type in search bar.
4. Create an app password
5. Use that password for `EMAIL_PASS` variable's value in your `.env` file (remove white spaces if it has any).

## Add csv file containing the list of stocks to trade

Create csv file `config/trade_config_version_<SCRIPT_VERSION>.csv` with the following headers:
`ibkr_account,ticker,price,quantity`

## Add a json file containing the last checked email time

Create json file `last_checked_email_time.json` with the following content:
`{"last_checked_email_time": "2025-01-01 00:00:00+00:00"}`

You can adjust the date and time as you want.

# Running
From the root of the project run:
```bash
python main.py --version=<SCRIPT_VERSION>
```
