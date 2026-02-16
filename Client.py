#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patrick Lewis for COMP 431 Spring 2026
HW4: Building an SMTP Client/Server System Using Sockets
Client.py
"""

import argparse
import sys

def get_command_line_arguments():
    """
    Your mail agent should take two command line arguments:
    a hostname followed by a port number
    Enables debug mode.
    """

    arg_parser = argparse.ArgumentParser(description="HW4: Building an SMTP Client/Server System Using Sockets")
    # https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_argument
    arg_parser.add_argument(
        "--debug",
        # https://docs.python.org/3/library/argparse.html#action
        action="store_true",
        help="Enable additional logging that is helpful for debugging without modifying code."
    )

    arg_parser.add_argument(
        "hostname",
        # https://docs.python.org/3/library/argparse.html#action
        # 'store' - This just stores the argument's value. This is the default action.
        action="store",
        help="hostname of the SMTP server to connect to",
        # https://docs.python.org/3/library/argparse.html#type
        # TODO: Make sure setting this does not create issues; the default is to store this value
        # as a "simple string"
        # type=default
    )

    arg_parser.add_argument(
        "port_number",
        # https://docs.python.org/3/library/argparse.html#action
        # 'store' - This just stores the argument's value. This is the default action.
        action="store",
        help="Port number of the SMTP server to connect to",
        # https://docs.python.org/3/library/argparse.html#type
        # TODO: Make sure setting this does not create issues; the default is to store this value
        # as a "simple string"
        type=int
    )

    return arg_parser.parse_args()

def main():
    """
    Docstring for main
    """

    # Print a "From:" prompt message (terminated with a newline)
    print("From:")
    email_from_address = sys.stdin.readline()

    # Users should be able to specify multiple email recipients by providing a list of
    # comma-separated email addresses (with optional whitespace after the comma)
    # Your program should confirm that data entered in response to both the From and To prompts
    # conforms to the syntax of the <forward-path> and <reverse-path> non-terminals in the SMTP
    # grammar (but without the angle brackets) for the SMTP MAIL FROM and RCPT TO messages.
    # If the data entered is erroneous, your client (this program) should print out a 1-line English
    # (not an SMTP) error message identifying the error (similar to what you did in HW1) and
    # re-prompt the user for the correct input.
    #
    # Make sure there is at least 1 valid email address
    # Make sure all email addresses are valid
    print("To:")
    email_to_addresses = sys.stdin.readline()

    print("Subject:")
    email_subject = sys.stdin.readline()

    # Assume users will terminate their message text by entering a period on an otherwise blank
    # line (data_end_cmd)
    print("Message:")
    email_body = sys.stdin.readline()




if __name__ == "__main__":
    main()
