#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patrick Lewis for COMP 431 Spring 2026
HW4: Building an SMTP Client/Server System Using Sockets
Server.py
Port number for your server is 800 + the last 4 digits of your PID.
"""

import argparse
from socket import *
from socket import SHUT_RDWR
from pathlib import Path
from Parser import Parser, ParserError, debugging

class SMTPServer:
    """
    Class that will operate like a state machine to keep track of what command
    is being handled next.
    """
    EXPECTING_MAIL_FROM = 0
    EXPECTING_RCPT_TO = 1
    EXPECTING_RCPT_TO_OR_DATA = 2
    EXPECTING_DATA_END = 3

    def __init__(self, debug_mode: bool = False):
        self.state = self.EXPECTING_MAIL_FROM
        self.to_email_addresses = []
        self.email_text = []
        self.parser = None
        self.debug_mode = debug_mode

    def set_parser(self, current_parser: Parser):
        """
        By the time the parser is set, the line has already been read. That means,
        what we do is check the current state and act accordingly.
        """
        self.parser = current_parser

        if not isinstance(current_parser, Parser):
            raise ValueError("parser must be an instance of Parser class.")

    def add_text_to_email_body(self, text: str):
        """
        Add the input string without the trailing newline character to the list of lines that
        will be appended to the message if the message parses correctly.

        Note to self: .strip() is too greedy and will remove trailing and leading spaces and tabs,
        changing the original content of each line passed to the parser.

        Another note to self: if this function is called, just do it; do not try to prevent an
        empty string from being sent to the email message.
        """

        self.email_text.append(text)


    def evaluate_state(self):
        """
        Determines what should happen
        """
        if not isinstance(self.parser, Parser):
            raise ValueError("parser must be an instance of Parser class.")

        # Syntax errors in the message name (type 500 errors) should take precedence over all other
        # errors.
        # Out-of-order (type 503 errors) should take precedence over parameter/argument errors
        # (type 501 errors). This means that we can no longer throw a 501 error until we have
        # verified that the command is in the correct sequence.

        # We need to know if any command is recognized to be ready for 503 errors
        recognized_command = self.command_id_errors()

        # STATE == 0
        if self.state == self.EXPECTING_MAIL_FROM:
            # if the command fails, that means a type 501 error occurred.
            if not self.parser.mail_from_cmd():
                raise ParserError(ParserError.SYNTAX_ERROR_IN_PARAMETERS)

            # If we made it here, the command was fully parsed successfully
            # Add the "From: <reverse-path>" line to the list of email text lines
            self.add_text_to_email_body(self.parser.get_from_line_for_email())
            return self.advance()

        if self.state == self.EXPECTING_RCPT_TO or \
            (self.state == self.EXPECTING_RCPT_TO_OR_DATA and recognized_command == "RCPT TO"):
            # if the command fails, that means a type 501 error occurred.
            if not self.parser.rcpt_to_cmd():
                raise ParserError(ParserError.SYNTAX_ERROR_IN_PARAMETERS)

            # If we made it here, the command was fully parsed successfully
            # Add the "To: <forward-path>" line to the list of email text lines
            self.add_text_to_email_body(self.parser.get_to_line_for_email())
            self.to_email_addresses.append(self.parser.get_email_address())

            # Only advance if this is the first time we are seeing a To: address
            if self.state == self.EXPECTING_RCPT_TO:
                self.advance()

            return

        if self.state == self.EXPECTING_RCPT_TO_OR_DATA:
            # This means that the recognized command must be "DATA", but we'll check anyway
            if recognized_command == "DATA" and not self.parser.data_cmd():
                raise ParserError(ParserError.COMMAND_UNRECOGNIZED)

            # If we made it here, the command was fully parsed successfully
            # Advance so that we can start reading the message
            return self.advance()

        if self.state == self.EXPECTING_DATA_END:
            # This is different because any text that does not create an error that is parsed
            # here is considered valid until the ending comes.
            if self.parser.data_end_cmd():
                self.process_email_message()
                return self.advance()

            # if an error occurs while reading a line meant for the body of the message, then
            # throw an error. According to the writeup, "we'll assume that 'text' is limited to
            # printable text, whitespace, and newlines".
            if not self.parser.data_read_msg_line():
                raise ParserError(ParserError.SYNTAX_ERROR_IN_PARAMETERS)

            self.add_text_to_email_body(self.parser.get_input_line())

    def command_id_errors(self) -> str:
        """
        If no command is recognized, then that results in a 500 error.
        If an unexpected command is recognized based on the current state, that results in a 503.
        Return the recognized command. This is helpful for when a state represents an option,
        RCPT TO or DATA.
        """

        if self.state not in [self.EXPECTING_MAIL_FROM, self.EXPECTING_RCPT_TO, self.EXPECTING_RCPT_TO_OR_DATA]:
            return ""

        if not isinstance(self.parser, Parser):
            raise ValueError("parser must be an instance of Parser class.")

        any_command_recognized = self.parser.check_for_commands()
        recognized_command = self.parser.get_command_name()

        if self.debug_mode:
            print(f"line: {self.parser.input_string.strip()}, state: {self.state}, recognized_command: {recognized_command}")

        if not any_command_recognized or not recognized_command:
            raise ParserError(ParserError.COMMAND_UNRECOGNIZED)

        if self.state == self.EXPECTING_MAIL_FROM and recognized_command != "MAIL FROM":
            raise ParserError(ParserError.BAD_SEQUENCE_OF_COMMANDS)

        if self.state == self.EXPECTING_RCPT_TO and recognized_command != "RCPT TO":
            raise ParserError(ParserError.BAD_SEQUENCE_OF_COMMANDS)

        if self.state == self.EXPECTING_RCPT_TO_OR_DATA and recognized_command not in ["RCPT TO", "DATA"]:
            raise ParserError(ParserError.BAD_SEQUENCE_OF_COMMANDS)

        return recognized_command

    def reset(self):
        """
        Resets the SMTP server state machine to expect a new email.
        """
        self.state = self.EXPECTING_MAIL_FROM
        self.to_email_addresses = []
        self.email_text = []

    def advance(self):
        """
        Advances the state of the SMTP server by 1. If a message is completed,
        then it starts over and waits for the next one.
        """
        if self.state != self.EXPECTING_DATA_END:
            self.state += 1
            return

        self.reset()

    def create_folder(self, folder_name: str) -> Path:
        """
        Create a folder with the specified name in the same location as this
        Python script.
        """

        if not folder_name:
            raise ValueError("create_folder(); must specify a folder name")

        # This is the folder that this Python script lives in.
        # I got this wrong the first time; this should be in the "current working directory" (p. 6)
        current_folder = Path.cwd()
        # This is the "forward" folder I want to create
        new_folder = current_folder / folder_name

        # it's okay if the folder already exists
        new_folder.mkdir(exist_ok=True)

        return new_folder

    def process_email_message(self):
        """
        Takes the lines that make up the email message and appends them to the mailbox files in
        the "forward" folder for each recipient of the current message (to_email_addresses).
        """

        # 1. Get the text of the message
        email_complete_text = "\n".join(self.email_text) + "\n"

        # 2. Create the "folder" folder
        forward_folder = self.create_folder("forward")

        # 3. For each recipient of the latest email message, append the text
        # of the email to a file with the email address as the name.
        for email_address in self.to_email_addresses:
            forward_path = forward_folder / email_address

            with forward_path.open("a", encoding="utf-8") as f:
                f.write(email_complete_text)

def get_command_line_arguments():
    """
    Handles command line arguments for the forward file and debug mode.
    """

    arg_parser = argparse.ArgumentParser(description="HW4: Building an SMTP Client/Server System Using Sockets")
    # https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_argument
    arg_parser.add_argument(
        "--debug",
        # https://docs.python.org/3/library/argparse.html#action
        action="store_true",
        help="Enable additional logging that is helpful for debugging without modifying code."
    )

    # Add an argument for reading the forward file
    arg_parser.add_argument(
        "port_number",
        # https://docs.python.org/3/library/argparse.html#action
        # 'store' - This just stores the argument's value. This is the default action.
        action="store",
        help="Incoming port number for connecting to the SMTP server",
        # https://docs.python.org/3/library/argparse.html#type
        # TODO: Make sure setting this does not create issues; the default is to store this value
        # as a "simple string"
        type=int
    )

    return arg_parser.parse_args()

def get_hostname() -> str:
    """
    Returns the hostname of the server this code is running on. This works on
    the cs.unc.edu server even though this just prints "Mac" as my hostname.
    """

    try:
        return socket.gethostname()
    except:
        return ""

def socket_is_connected(socket_obj: socket) -> bool:
    """
    Docstring for socket_is_connected

    :return: Description
    :rtype: bool
    """

    if not socket_obj:
        return False

    try:

        if not isinstance(socket_obj, (socket.socket, socket.SocketType)):
            return False

        print(f"getsockname(): {socket.getsockname()}")

        return True

    except Exception as e:
        return False

    return True

def main():
    """
    This code starts here.
    """

    # TODO: Print the hostname, delete this
    # print(f"220 {get_hostname()}")

    args = get_command_line_arguments()
    debug_mode = args.debug
    server_port = args.port_number

    # debugging.print(debug_mode, "whatever")

    # https://docs.python.org/3.12/library/socket.html#socket.AF_INET
    # https://docs.python.org/3.12/library/socket.html#socket.SOCK_STREAM
    # SOCK_STREAM represents a socket type, one of the two the official documentation lists as
    # useful
    serverSocket = socket(family=AF_INET, type=SOCK_STREAM)

    # debugging.print(debug_mode, "whatever")

    # print(f"getpeername(): {serverSocket.getpeername()}")


    connectionSocket = None
    addr = None

    try:

        debugging.print(debug_mode, "whatever")

        serverSocket.bind('', server_port)

        debugging.print(debug_mode, "called serverSocket.bind()")

        # https://docs.python.org/3.12/library/socket.html#socket.socket.listen
        # The parameter specifies the number of unaccepted connections that the system will allow
        # before refusing new connections. This can help prevent multiple sockets and issues.
        serverSocket.listen(1)

        debugging.print(debug_mode, "called serverSocket.listen(1)...")

        while True:
            # TODO: What is "addr" for?
            # .accept() returns a tuple where the first element is a socket object
            # the second element is a return address
            # What is the difference between connectionSocket and serverSocket? It seems that
            # connectionSocket represents an actual socket object when the client connects and is
            # spawned from the serverSocket object.
            connectionSocket, addr = serverSocket.accept()

            debugging.print(debug_mode, "called serverSocket.accept(). Maybe the code will listen?")

            sentence = connectionSocket.recv(1024).decode()

            capitalizedSentence = sentence.upper()

            connectionSocket.send(capitalizedSentence.encode())

            # Note: close() releases the resource associated with a connection but does not
            # necessarily close the connection immediately. If you want to close the connection in a
            # timely fashion, call shutdown() before close().


    except EOFError as e:
        # Ctrl+D (Unix) or end-of-file from a pipe
        # break
        debugging.print(debug_mode, f"EOFError: {e}")
    except KeyboardInterrupt as e:
        # Ctrl+C
        # break
        debugging.print(debug_mode, f"KeyboardInterrupt (error): {e}")
    except ParserError as pe:
        # All errors that should be handled according to the writeup are handled as ParserError
        # objects. All other exceptions are ValueError or some other type. If a ParserError
        # occurrs, the write up says "upon receipt of any erroneous SMTP message you should
        # reset your state machine and return to the state of waiting for a valid MAIL FROM
        # message".
        debugging.print(debug_mode, f"ParserError: {e}")
    except OSError as e:
        # This can be useful for catching errors related to sockets
        debugging.print(debug_mode, f"OSError: {e}")
    except Exception as e:
        # print(f"An unexpected error occurred: {e}")
        # break
        debugging.print(debug_mode, f"General Exception: {e}")

    if connectionSocket:
        # https://docs.python.org/3.12/library/socket.html#socket.SHUT_RDWR
        connectionSocket.shutdown(SHUT_RDWR)
        connectionSocket.close()

    if serverSocket:
        # TODO: How can you tell if a socket is connected? socket.getpeername()? socket.getsockname()?
        if socket_is_connected(serverSocket):
            serverSocket.shutdown(SHUT_RDWR)
        serverSocket.close()

    # 1. Upon starting this program, create a socket and wait for a connection.
    # By simply accepting a connection from a client, the SMTP server will send
    # a 220 hostname.cs.unc.edu message to the SMTP client.

    # 2. In response to the 220 message, expect an SMTP HELO message that must
    # be formatted correctly.

    # 3. When you receive the HELO message, read the domain from the SMTP HELO
    # message and send a 250 back with the following format:
    # 250 Hello client-domain pleased to meet you.

    # 4. Now enter the "email message processing loop", which means that you
    # begin processing SMTP messages until the QUIT message is received.
    # 4a. I suppose the same error messages would be generated, just now, they
    # will be sent to the client. They would NOT be printed to stdout.
    # 4b. If debug_mode = True, then print messages to stdout. Otherwise, DO NOT PRINT the 500+
    # error messages to standard out!

    # 5. Concerning the forward files, it may be easier to collect the
    # individual domains from the "RCPT TO" commands. Additionally, you add
    # only a single copy of the email to the forward file per domain, even if
    # that domain has multiple recipients. Just in case they are checking for
    # the existence of forward files, only create them once the entire message
    # has been created. You would be appending the message to the forward file.



    # TODO: What port should be used to create the socket to accept incoming requests?

if __name__ == "__main__":
    main()
