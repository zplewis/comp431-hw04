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
    # there should be optional whitespace after the comma (using the same
    # definition as <nullspace>, meaning 0 or more spaces)
    # The non-terminal <mailbox> matches the email addresses.
    print("To:")
    email_to_addresses = sys.stdin.readline()

    print("Subject:")
    email_subject = sys.stdin.readline()

    # Assume users will terminate their message text by entering a period on an otherwise blank
    # line (data_end_cmd)
    print("Message:")
    email_body = ""
    email_line = ""
    while email_line != ".\n":
        email_line = sys.stdin.readline()
        email_body += email_line

    # After the user has entered a valid email message, this program will create a TCP socket to the
    # SMTP server at the host and port number specified on the command line.
    # Once the TCP socket has been created, forward the user's message to the server using the
    # SMTP protocol.

    # Four new operations:

    # 1. When your program connects to the server ,it must be prepared to
    # receive a correct greeting message. Your program will do nothing with the
    # greeting message other than receive it and confirm that it is a valid
    # greeting message (220 hostname.cs.unc.edu)
    # 1a. If the greeting message is not a valid greeting message, you should
    # print a 1-line error message to stdout and then terminate the program.
    # 1b. If the greeting message is valid, you should reply to the greeting
    # with the SMTP HELO message using the format from the non-terminal. It
    # will look like "HELO client-hostname.cs.unc.edu", where that is a
    # hostname of the server the client program is running on.

    # 2. It looks like you send the SMTP commands in order like before, MAIL
    # FROM, RCPT TO, DATA. This time, within the DATA message, you include
    # "From:", "To:", "Subject:", each on their own lines. After the "Subject:"
    # line, have a blank line before the start of the body of the email message.
    # When you send the message, the email addresses in "From:" and
    # "To:" should be wrapped in angle brackets (<>)
    # The message would include the data_end_cmd, which is a line with just
    # a period. The next line would be just "QUIT" for the quit command.
    # 2a. Note that the forward files are now named by domain and not email address
    # on the server.
    # 2b. What is added to the forward files on the server comes from the body
    # of the DATA message, not from the MAIL FROM and RCPT TO messages. For now,
    # don't worry about making them match unless the homework says to make sure
    # that they do.

    # 3. Your program will close its connection to the server, print to stdout
    # a meaningful 1-line error message, and terminate when:
    # end-of-file is reached
    # outgoing mail message has been successfully sent
    # when any SMTP or socket error is encountered
    # any SMTP protocol errors
    # errors opening the socket
    # keyboard quitting, like before

    # 4. When your client emits the QUIT message (which I imagine only happens
    # when sending SMTP messages to the server), the client has to wait and
    # expect the server's final 221 "connection closed" response. Do NOT
    # terminate until after receiving this message.
    # 4a. If the wrong message is given, I suppose you print a 1-line error
    # to standard out and terminate the client application.

if __name__ == "__main__":
    main()
