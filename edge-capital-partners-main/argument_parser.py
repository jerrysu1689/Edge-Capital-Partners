import argparse
from datetime import date, datetime

def get_cli_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--version", 
                        type=str, 
                        default='A', 
                        choices=['A', 'B'],
                        help="Version of the trade config to use")

    return parser.parse_args()