#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patrick Lewis for COMP 431 Spring 2026
HW4: Building an SMTP Client/Server System Using Sockets
Server.py
Port number for your server is 800 + the last 4 digits of your PID.
"""

import argparse
import socket
from pathlib import Path
from Parser import Parser, ParserError, DebugMode, socket_is_connected, socket_send_msg, get_hostname

class SMTPServer:
    """
    Class that will operate like a state machine to keep track of what command
    is being handled next.
    """

    EXPECTING_CONNECTION = 0
    EXPECTING_HELO = 1
    EXPECTING_MAIL_FROM = 2
    EXPECTING_RCPT_TO = 3
    EXPECTING_RCPT_TO_OR_DATA = 4
    EXPECTING_DATA_END = 5
    EXPECTING_QUIT = 6

    def __init__(self, debug_mode: bool = False):
        self.state = self.EXPECTING_CONNECTION
        self.to_email_addresses = []
        self.email_text = []
        self.parser = None
        self.debug_mode = debug_mode
        self.connection_socket = None

    def set_parser(self, current_parser: Parser):
        """
        By the time the parser is set, the line has already been read. That means,
        what we do is check the current state and act accordingly.
        """
        self.parser = current_parser

        if not isinstance(current_parser, Parser):
            raise ValueError("parser must be an instance of Parser class.")

    def set_socket(self, connection_socket: socket = None):
        """
        Docstring for set_socket

        :param self: Description
        :param connection_socket: Description
        :type connection_socket: socket
        """

        self.connection_socket = connection_socket

        if not socket_is_connected(connection_socket, self.debug_mode):
            raise ValueError("connection_socket must be an instance of the socket class.")

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

        DebugMode.print(self.debug_mode, "About to check whether the parser object is valid...")

        if not isinstance(self.parser, Parser):
            raise ValueError("parser must be an instance of Parser class.")

        DebugMode.print(self.debug_mode, "About to check whether the socket object is valid...")

        if not socket_is_connected(self.connection_socket, self.debug_mode):
            raise ValueError("connection_socket must be an instance of the socket class.")

        # Syntax errors in the message name (type 500 errors) should take precedence over all other
        # errors.
        # Out-of-order (type 503 errors) should take precedence over parameter/argument errors
        # (type 501 errors). This means that we can no longer throw a 501 error until we have
        # verified that the command is in the correct sequence.

        DebugMode.print(self.debug_mode, f"evaluate_state(server): state: {self.state}")

        if self.state == self.EXPECTING_CONNECTION:
            socket_send_msg(self.connection_socket, f"220 {socket.gethostname()}", self.debug_mode)
            return self.advance()

        if self.state == self.EXPECTING_HELO:
            if not self.parser.match_helo_msg():
                raise ParserError(ParserError.COMMAND_UNRECOGNIZED)

            client_domain = self.parser.get_domain_from_helo()
            socket_send_msg(self.connection_socket, f"250 Hello {client_domain} pleased to meet you.", self.debug_mode)
            return self.advance()

        # We need to know if any command is recognized to be ready for 503 errors
        # We do not check for errors until after the SMTP "speaks" first.
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
            return self.advance()

        if self.state == self.EXPECTING_QUIT:
            if recognized_command != "QUIT" or not self.parser.quit_cmd():
                raise ParserError(ParserError.COMMAND_UNRECOGNIZED)

            # Otherwise, we can send a message to the client and close the connection and return
            # to its initial state
            socket_send_msg(self.connection_socket, f"221 {get_hostname()} closing connection", self.debug_mode)

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
        self.state = self.EXPECTING_CONNECTION
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

    def get_hostname(self) -> str:
        """
        Returns the hostname of the server this code is running on. This works on
        the cs.unc.edu server even though this just prints "Mac" as my hostname.
        """

        try:
            return self.connection_socket.gethostname()
        except:
            return ""




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



def close_socket(self):
    """
    Properly close the connection socket by calling .shutdown() then .close().
    Probably should use try...except.
    """

    if self.connection_socket is None:
        return

    if socket_is_connected():
        # https://docs.python.org/3.12/library/socket.html#socket.SHUT_RDWR
        self.connection_socket.shutdown(socket.SHUT_RDWR)

    self.connection_socket.close()


def main():
    """
    This code starts here.
    """

    # TODO: Print the hostname, delete this
    # print(f"220 {get_hostname()}")

    args = get_command_line_arguments()
    debug_mode = args.debug
    # 8000 + 4956 = 12956
    server_port = args.port_number

    # This is the maximum amount of data, in bytes, that can be received or sent via the socket.
    bufsize = 1024

    # Create an instance of the SMTPServer state machine
    smtp_server = SMTPServer(debug_mode)

    # https://docs.python.org/3.12/library/socket.html#socket.AF_INET
    # https://docs.python.org/3.12/library/socket.html#socket.SOCK_STREAM
    # SOCK_STREAM represents a socket type, one of the two the official documentation lists as
    # useful
    # By following the first example from the documentation here, it looks like you should use
    # "with" statements to properly close resources when they are done.
    # https://docs.python.org/3.12/library/socket.html#example
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:

        # The documentation provides a way to reuse a local socket in the TIME_WAIT state without
        # waiting for its natural timeout to expire
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # if debug_mode:
        #     server_socket.settimeout(4.0)

        connection_socket = None
        addr = None

        try:

            DebugMode.print(debug_mode, "whatever")

            # https://docs.python.org/3.12/library/socket.html#socket.socket.bind
            # This takes one parameter that is a 2-element tuple
            server_socket.bind(('', server_port))

            DebugMode.print(debug_mode, "called server_socket.bind()")

            # https://docs.python.org/3.12/library/socket.html#socket.socket.listen
            # The parameter specifies the number of unaccepted connections that the system will allow
            # before refusing new connections. This can help prevent multiple sockets and issues.
            server_socket.listen(1)

            DebugMode.print(debug_mode, "called server_socket.listen(1)...")

            # This outer
            while True:
                # TODO: What is "addr" for?
                # .accept() returns a tuple where the first element is a socket object
                # the second element is a return address
                # What is the difference between connection_socket and server_socket? It seems that
                # connection_socket represents an actual socket object when the client connects and is
                # spawned from the server_socket object.

                DebugMode.print(debug_mode, "about to create a new connection socket and listen for connections...", DebugMode.INFO)

                connection_socket, addr = server_socket.accept()

                with connection_socket:

                    if debug_mode:
                        connection_socket.settimeout(4.0)

                    DebugMode.print(debug_mode, f"socket_server.accept() received a new connection. addr: {addr}")

                    smtp_server.reset()

                    parser = Parser("", debug_mode)

                    smtp_server.set_parser(parser)
                    smtp_server.set_socket(connection_socket)

                    # Send a greeting message to the newly connected client
                    smtp_server.evaluate_state()

                    DebugMode.print(debug_mode, "should have sent an initial message to the client by now...")

                    try:

                        while True:

                            # https://docs.python.org/3.12/library/socket.html#socket.socket.recv
                            # The parameter is the maximum amount of data to be received at once
                            # TODO: A returned empty bytes object indicates that the client has
                            # disconnected. I think I should watch for that and break.

                            bytes_recv = connection_socket.recv(bufsize)

                            # If 0 bytes are received, that indicates that the client has sent anything yet.
                            if len(bytes_recv) == 0:
                                # DebugMode.print(debug_mode, "0 bytes was received from the client. closing the socket.", DebugMode.WARN)
                                continue

                            if bytes_recv is None:
                                DebugMode.print(debug_mode, "0 bytes was received from the client. closing the socket.", DebugMode.WARN)
                                break

                            # Reaching this point means we have data from the client
                            sentence = connection_socket.recv(bufsize).decode()

                            parser = Parser(sentence, debug_mode)
                            smtp_server.set_parser(parser)
                            smtp_server.set_socket(connection_socket)
                            smtp_server.evaluate_state()

                            # Note: close() releases the resource associated with a connection but does not
                            # necessarily close the connection immediately. If you want to close the connection in a
                            # timely fashion, call shutdown() before close().

                    except EOFError as e:
                        # Ctrl+D (Unix) or end-of-file from a pipe
                        # break
                        DebugMode.print(debug_mode, f"EOFError: {e}", DebugMode.ERROR)
                    except KeyboardInterrupt as e:
                        # Ctrl+C
                        # break
                        DebugMode.print(debug_mode, f"KeyboardInterrupt (error): {e}", DebugMode.ERROR)
                    except ParserError as e:
                        # All errors that should be handled according to the writeup are handled as ParserError
                        # objects. All other exceptions are ValueError or some other type. If a ParserError
                        # occurrs, the write up says "upon receipt of any erroneous SMTP message you should
                        # reset your state machine and return to the state of waiting for a valid MAIL FROM
                        # message".
                        DebugMode.print(debug_mode, f"ParserError: {e}", DebugMode.ERROR)
                    except OSError as e:
                        # This can be useful for catching errors related to sockets
                        DebugMode.print(debug_mode, f"OSError: {e}", DebugMode.ERROR)
                    except Exception as e:
                        # print(f"An unexpected error occurred: {e}")
                        # break
                        DebugMode.print(debug_mode, f"General Exception (connection_socket): {e}", DebugMode.ERROR)

                    if connection_socket:
                        # https://docs.python.org/3.12/library/socket.html#socket.SHUT_RDWR
                        connection_socket.shutdown(socket.SHUT_RDWR)
                        connection_socket.close()

                    return

            DebugMode.print(debug_mode, "about to close server socket and shutting down SMTP server...", DebugMode.WARN)

        except EOFError as e:
            # Ctrl+D (Unix) or end-of-file from a pipe
            # break
            DebugMode.print(debug_mode, f"EOFError: {e}", DebugMode.ERROR)
        except KeyboardInterrupt as e:
            # Ctrl+C
            # break
            DebugMode.print(debug_mode, f"KeyboardInterrupt (error): {e}", DebugMode.ERROR)
        except ParserError as e:
            # All errors that should be handled according to the writeup are handled as ParserError
            # objects. All other exceptions are ValueError or some other type. If a ParserError
            # occurrs, the write up says "upon receipt of any erroneous SMTP message you should
            # reset your state machine and return to the state of waiting for a valid MAIL FROM
            # message".
            DebugMode.print(debug_mode, f"ParserError: {e}", DebugMode.ERROR)
        except OSError as e:
            # This can be useful for catching errors related to sockets
            DebugMode.print(debug_mode, f"OSError: {e}", DebugMode.ERROR)
        except Exception as e:
            # print(f"An unexpected error occurred: {e}")
            # break
            DebugMode.print(debug_mode, f"General Exception (server_socket): {e}", DebugMode.ERROR)

        if server_socket:
            # TODO: How can you tell if a socket is connected? socket.getpeername()? socket.getsockname()?
            if socket_is_connected(server_socket):
                server_socket.close()

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

if __name__ == "__main__":
    main()
