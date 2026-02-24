#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patrick Lewis for COMP 431 Spring 2026
HW4: Building an SMTP Client/Server System Using Sockets
Client.py
"""

import argparse
import sys
from Parser import Parser, ParserError, DebugMode, socket_is_connected, socket_send_msg, get_hostname, close_socket
import socket

class SMTPClientSide:
    """
    Class that will operate like a state machine to keep track of what command
    is being handled next.
    """

    # All of these steps are just receiving user data
    EXPECTING_USER_MAIL_FROM_ADDRESS = 0
    EXPECTING_USER_TO_ADDRESSES = 1
    EXPECTING_USER_SUBJECT = 2
    EXPECTING_USER_MESSAGE = 3

    # After the user has entered a valid email message, your mail agent will create a TCP socket to
    # the SMTP server and forward the user's message to the server using the SMTP protocol.
    EXPECTING_SERVER_GREETING = 4 # Received 220

    EXPECTING_SERVER_HELLO = 5

    EXPECTING_MAIL_FROM = 6
    """
    Represents the "MAIL FROM:" command. Only occurs once.
    """
    EXPECTING_RCPT_TO = 7
    """
    Represents the "RCPT TO:" command, specifically this one time because at
    lease one "RCPT TO:" command is required for a well-formed email message.
    """
    EXPECTING_RCPT_TO_OR_DATA = 8
    """
    Represents 0 or more "RCPT TO:" commands or the first line of the email body
    inside a forward file.
    """
    EXPECTING_DATA_END = 9

    EXPECTING_QUIT_RESPONSE = 10
    """
    Before terminating the program, you must wait for a response from the server after you send
    the SMTP QUIT command.
    """

    def __init__(self, debug_mode: bool = False):
        self.state = self.EXPECTING_USER_MAIL_FROM_ADDRESS
        self.parser = None
        self.debug_mode = debug_mode
        self.generated_cmd = ""

        # I was doing this the hard way
        self.commands = []

        self.commands_index = -1
        self.forward_file_lines = []

        self.data_to_address_line = ""
        self.data_subject_line = ""

        self.connection_socket = None

        self.input_line = ""
        """
        This is the current line from the user. This will be useful
        in instances where the existence of a line signals the change in state
        but must be printed to standard out (stdout).
        """

    def set_parser(self, current_parser: Parser):
        """
        By the time the parser is set, the line has already been read. That means,
        what we do is check the current state and act accordingly.
        """
        if not isinstance(current_parser, Parser):
            raise ValueError("parser must be an instance of Parser class.")

        self.parser = current_parser

    def set_socket(self, connection_socket: socket.socket):
        """
        Docstring for set_socket
        """
        if not socket_is_connected(connection_socket, self.debug_mode):
            raise ValueError("client connection_socket must be an instance of the socket class.")

        self.connection_socket = connection_socket

    def get_generated_cmd(self) -> str:
        """
        This is the command, if any, that is generated when a line from the forward file is analyzed
        based on the current state.
        """

        return self.generated_cmd

    def get_state(self):
        """
        Get the current state of the SMTPClientSide.
        """

        return self.state

    def get_state_str(self, state: int) -> str:
        """
        Docstring for get_state_str

        :param self: Description
        :param state: Description
        :type state: int
        :return: Description
        :rtype: str
        """

        if state == self.EXPECTING_USER_MAIL_FROM_ADDRESS:
            return "EXPECTING_USER_MAIL_FROM_ADDRESS"
        if state == self.EXPECTING_USER_TO_ADDRESSES:
            return "EXPECTING_USER_TO_ADDRESSES"
        if state == self.EXPECTING_USER_SUBJECT:
            return "EXPECTING_USER_SUBJECT"
        if state == self.EXPECTING_USER_MESSAGE:
            return "EXPECTING_USER_MESSAGE"
        if state == self.EXPECTING_SERVER_GREETING:
            return "EXPECTING_SERVER_GREETING"
        if state == self.EXPECTING_SERVER_HELLO:
            return "EXPECTING_SERVER_HELLO"
        if state == self.EXPECTING_MAIL_FROM:
            return "EXPECTING_MAIL_FROM"
        if state == self.EXPECTING_RCPT_TO:
            return "EXPECTING_RCPT_TO"
        if state == self.EXPECTING_RCPT_TO_OR_DATA:
            return "EXPECTING_RCPT_TO_OR_DATA"
        if state == self.EXPECTING_DATA_END:
            return "EXPECTING_DATA_END"
        if state == self.EXPECTING_QUIT_RESPONSE:
            return "EXPECTING_QUIT_RESPONSE"

        return ""

    def advance_forward_file_line_pointer(self):
        """
        Docstring for advance_forward_file_line_pointer

        :param self: Description
        :return: Description
        :rtype: Any
        """

        if self.commands_index < len(self.commands) - 1:
            self.commands_index += 1

        self.self_update_parser()

    def self_update_parser(self):
        """
        Based on the user input, a list of lines was created that mimic a forward file. These will
        be fed to the Parser class so that SMTP commands can be sent to the server.
        """

        line = self.commands[self.commands_index]

        if not line.endswith("\n"):
            line += "\n"

        self.parser = Parser(line, debug_mode=self.debug_mode)

    def prompt_for_input(self, prompt: str) -> Parser:
        """
        Code for prompting the user for input. Since it is repeated multiple times, it could be
        its own function.
        """

        if not prompt:
            raise ValueError("A prompt must be shown to the user when asking for input.")

        print(prompt)
        line = sys.stdin.readline()
        return Parser(input_string=line, debug_mode=self.debug_mode)


    def collect_user_input(self):
        """
        Function specifically for prompting the user and collecting user information. This
        separates collecting user input from code that actually sends messages to the SMTP server.

        Technically, even recursion is not necessary if I do not use states for this part of the
        process, making the code even simpler.
        """

        if self.state == self.EXPECTING_USER_MAIL_FROM_ADDRESS:
            prompt = "From:"
            temp_parser = self.prompt_for_input(prompt)
            while not (temp_parser.mailboxes() and len(temp_parser.get_email_addresses()) == 1):
                temp_parser = self.prompt_for_input(prompt)

            # Add the one from address to the list of "forward file lines"
            self.forward_file_lines.append(f"{prompt} <{temp_parser.get_input_line()}>")
            self.commands.append(f"MAIL FROM: <{temp_parser.get_input_line()}>")

            self.advance()
            return self.collect_user_input()

        if self.state == self.EXPECTING_USER_TO_ADDRESSES:
            prompt = "To:"
            temp_parser = self.prompt_for_input(prompt)
            while not (temp_parser.mailboxes() and len(temp_parser.get_email_addresses()) >= 1):
                temp_parser = self.prompt_for_input(prompt)

            # Add all of the to addresses to the list of commands
            for email in temp_parser.get_email_addresses():
                self.commands.append(f"RCPT TO: <{email.strip()}>")

            # This will be helpful later when building the DATA message
            self.data_to_address_line = "To: " + ", ".join(f"<{e.strip()}>" for e in temp_parser.get_email_addresses())
            self.forward_file_lines.append(self.data_to_address_line)

            self.advance()
            return self.collect_user_input()

        if self.state == self.EXPECTING_USER_SUBJECT:
            prompt = "Subject:"
            temp_parser = self.prompt_for_input(prompt)
            while not (temp_parser.match_arbitrary_text()):
                temp_parser = self.prompt_for_input(prompt)

            # Add the subject to the forward_file_lines list
            self.data_subject_line = f"{prompt} {temp_parser.get_input_line()}"
            self.forward_file_lines.append(self.data_subject_line)
            # Add the blank line that is supposed to come after the subject
            # NOTE: Do NOT add a newline character to this blank element; when joined, a newline
            # character will be added to all lines.
            self.forward_file_lines.append("")

            self.advance()
            return self.collect_user_input()

        if self.state == self.EXPECTING_USER_MESSAGE:

            prompt = "Message:"
            temp_parser = self.prompt_for_input(prompt)
            while not (temp_parser.data_end_cmd()):
                self.forward_file_lines.append(temp_parser.get_input_line())
                DebugMode.print(self.debug_mode, temp_parser.get_input_line())
                line = sys.stdin.readline()
                temp_parser = Parser(input_string=line, debug_mode=self.debug_mode)

            self.forward_file_lines.append(temp_parser.get_input_line())
            DebugMode.print(self.debug_mode, temp_parser.get_input_line())

            # Returning True here should allow the main loop to continue and create a socket to
            # connect to the SMTP server
            self.advance()


        # Before leaving, complete the list of commands and add what is missing
        self.commands.append("DATA\n")
        # Combine the commands and forward file lines to one master list that contains all that
        # we need. No need to add "QUIT" as that is the only possible choice at the end.
        self.commands = self.commands + self.forward_file_lines

        if self.debug_mode:
            DebugMode.print(self.debug_mode, "\n***** forward file lines*****\n", DebugMode.WARN)
            for line in self.commands:
                DebugMode.print(self.debug_mode, line, DebugMode.WARN)

        # TODO: Remove this line
        # sys.exit(0)



    def evaluate_state(self, end_of_file: bool = False):
        """
        Based on the current state, print to standard output the appropriate SMTP message.
        Since we can assume that forward files are well-formed, we do not even have to validate and
        just get what we need.

        If an SMTP response message should be in sent by the user after this command, then
        return True.

        Only advance the state in this function if doing so is NOT determined by a server
        response!
        """

        # We only need self.parser after we have retrieved all of the user data
        if self.state < self.EXPECTING_SERVER_GREETING:
            raise ValueError(f"Client state must be EXPECTING_SERVER_GREETING ({self.EXPECTING_SERVER_GREETING}) or higher.")

        if not isinstance(self.parser, Parser):
            raise ValueError("self.parser must be an instance of Parser class.")

        DebugMode.print(self.debug_mode, "evaluate_state(client): parser is valid.")

        if not socket_is_connected(self.connection_socket, self.debug_mode):
            raise ValueError("client connection_socket must be an instance of the socket class.")

        DebugMode.print(self.debug_mode, "evaluate_state(client): socket is valid.")

        # generated_cmd is what is generated by the parser
        self.generated_cmd = ""
        self.input_line = self.parser.get_input_line()

        DebugMode.print(self.debug_mode, f"evaluate_state(client): state: {self.get_state_str(self.state)} ({self.state})", DebugMode.INFO)
        DebugMode.print(self.debug_mode, f"evaluate_state(client): input_string: '{self.parser.get_input_line()}'")

        if self.state == self.EXPECTING_QUIT_RESPONSE:
            if not socket_send_msg(self.connection_socket, "QUIT", self.debug_mode):
                self.quit_immediately(
                    msg=f'Failed to send SMTP QUIT in response to error code from SMTP server: "{self.parser.get_input_line()}'
                )

            # Returning True means that we are expecting a response from the server.
            return True

        if self.state == self.EXPECTING_SERVER_HELLO:
            DebugMode.print(self.debug_mode, "About to send HELO message to SMTP server...")
            if not socket_send_msg(self.connection_socket, f"HELO {get_hostname()}", self.debug_mode):
                self.quit_immediately(
                    msg='Failed to send HELO msg to SMTP server. Terminating program.'
                )

            return True

        if self.state == self.EXPECTING_MAIL_FROM:
            # self.parser.rewind(0)
            if not self.parser.mail_from_cmd():
                self.quit_immediately(
                    msg=f'Parser did not find a properly-formatted MAIL FROM SMTP command: "{self.parser.get_input_line()}"'
                )

            # print(self.parser.generate_mail_from_cmd())
            if not socket_send_msg(self.connection_socket, self.parser.get_input_line(), self.debug_mode):
                self.quit_immediately(
                    msg='Failed to send MAIL FROM command to SMTP server. Terminating program.'
                )

            return True

        if self.state == self.EXPECTING_RCPT_TO:
            if not self.parser.rcpt_to_cmd():
                self.quit_immediately(
                    msg=f"Parser did not find a properly-formatted RCPT TO SMTP command: '{self.parser.get_input_line()}'"
                )

            # print(self.parser.generate_rcpt_to_cmd())
            if not socket_send_msg(self.connection_socket, self.parser.get_input_line(), self.debug_mode):
                self.quit_immediately(
                    msg='Failed to send RCPT TO command to SMTP server. Terminating program.'
                )

            return True

        # This state allows either one of two things: "DATA" or "From: <email_address>"
        if self.state == self.EXPECTING_RCPT_TO_OR_DATA:
            DebugMode.print(self.debug_mode, f"About to check whether input string is the RCPT TO command: '{self.parser.get_input_line()}'", DebugMode.INFO)
            if self.parser.rcpt_to_cmd(check_only=True):
                self.generated_cmd = self.parser.get_command_name()

                if not socket_send_msg(self.connection_socket, self.parser.get_input_line(), self.debug_mode):
                    self.quit_immediately(
                        msg='Failed to send RCPT TO command to SMTP server. Terminating program.'
                    )

                # We do NOT advance the state machine because we have not encountered "DATA" yet.
                self.advance_forward_file_line_pointer()
                return True

            # If we made it here, that means that the text is NOT "To: <emailaddress>"
            # This text, then, is the first line of the body of the email.
            # We need to:
            # 1. Send the "DATA" command
            # 2. Prompt the user for an SMTP response
            self.parser.rewind(self.parser.BEGINNING_POSITION)
            DebugMode.print(self.debug_mode, f"About to check whether input string is the DATA command: '{self.parser.get_input_line()}'", DebugMode.INFO)
            if self.parser.data_cmd(check_only=True) and self.parser.get_command_name() == "DATA":
                if not socket_send_msg(self.connection_socket, self.parser.generate_data_cmd(), self.debug_mode):
                    self.quit_immediately(
                        msg='Failed to send DATA command to SMTP server. Terminating program.'
                    )

                # We do NOT advance the state machine in evaluate_state(); only in evaluate_response()
                self.advance_forward_file_line_pointer()
                return True


            self.quit_immediately(
                msg='Client failed to generate RCPT TO or DATA commands at appropriate time. Terminating program.'
            )

            return True

        if self.state == self.EXPECTING_DATA_END:
            # if self.parser.forwardfile_match_from_address():
            #     self.generated_cmd = "MAIL FROM"
            #     print(self.parser.generate_data_end_cmd())
            #     return True

            if end_of_file or self.parser.data_end_cmd():
                if not socket_send_msg(self.connection_socket, self.parser.generate_data_end_cmd(), self.debug_mode):
                    self.quit_immediately(
                        msg='Failed to send .\\n (DATA END) command to SMTP server. Terminating program.'
                    )
                return True

            # If we are here, that means the we are reading lines in the forward
            # file that are part of the body of the email message.
            if not socket_send_msg(self.connection_socket, self.parser.get_input_line(), self.debug_mode):
                self.quit_immediately(
                    msg='Failed to send text from body of the messaged to SMTP server. Terminating program.'
                )
                # We do NOT return here because no response is required from the SMTP server yet

            self.advance_forward_file_line_pointer()
            return self.evaluate_state()

        return False

    def debug_print(self, text: str):
        if not self.debug_mode:
            return

        print(text)

    def evaluate_response(self, end_of_file: bool = False) -> bool:
        """
        Based on the current state:
        1) Read the "server" response message, which could be either 250, 354, 500, 501, etc. If
        a success message is given (based on the context), then it is okay to advance to the
        next state (as appropriate). This comes from the user (standard input).
        2) Make sure to only validate the response message number only, as the text after the
        number can be anything.
        3) When echoing the response, print to standard error (stderr)!

        The return value here determines whether we need to process the input file again after
        advancing the state. This happens in 3 scenarios:

        1) Encountering the first line of the email body, switching to EXPECTING_DATA_END state
        2) Encountering the "From:" line of a new email, switching from EXPECTING_DATA_END to EXPECTING_MAIL_FROM
        3) Encountering the end-of-file (empty string), switching from EXPECTING_DATA_END to EXPECTING_MAIL_FROM
        """
        if not isinstance(self.parser, Parser):
            raise ValueError("parser must be an instance of Parser class.")

        # Stop here if the response is not properly formatted according to the provided
        # production rule; technically, some kind of error occurred
        if not self.parser.match_response_code():
            self.quit_immediately(f"The message from the SMTP server was NOT a response code: {self.parser.get_input_line()}")
            return False

        # Stop here if a properly formatted error message is received
        # If you get an error while expecting a quit response, then don't redirect to send another
        # QUIT command; make sure to prevent an endless loop!
        if self.state not in [self.EXPECTING_QUIT_RESPONSE]:
            if self.parser.match_response_code() and self.parser.is_error_smtp_response_code():
                self.state = self.EXPECTING_QUIT_RESPONSE
                return self.evaluate_state()

        # Based on the state, if the wrong message is received, then quit immediately
        resp_number = self.parser.get_smtp_response_code()

        self.debug_print(f"evaluate_response(); state: {self.get_state_str(self.state)} ({self.state}), resp_number: {resp_number}, generated_cmd: {self.generated_cmd}")

        if self.state in [self.EXPECTING_MAIL_FROM, self.EXPECTING_RCPT_TO, self.EXPECTING_DATA_END, self.EXPECTING_SERVER_HELLO] \
        and resp_number != '250':
            self.quit_immediately(f"Wrong response code for state '{self.get_state_str(self.state)}' ({self.state}): {resp_number}; Terminating program.")
            return False

        if self.state == self.EXPECTING_RCPT_TO_OR_DATA:
            if (self.generated_cmd == "DATA" and resp_number != '354') or \
            (self.generated_cmd != "DATA" and resp_number != '250'):
                self.quit_immediately(f"Wrong response code for state '{self.get_state_str(self.state)}' ({self.state}): {resp_number}; Terminating program.")
                return False

        if self.state == self.EXPECTING_QUIT_RESPONSE and resp_number != '221':
            self.quit_immediately(f"Wrong response code for state '{self.get_state_str(self.state)}' ({self.state}): {resp_number}; Terminating program.")

            return False

        if self.state == self.EXPECTING_SERVER_GREETING and resp_number != '220':
            self.quit_immediately(f"Wrong response code for state '{self.get_state_str(self.state)}' ({self.state}): {resp_number}; Terminating program.")
            return False

        # Handle the reasons to re-evaluate the current line from the forward file after
        # advancing the state
        # 1) Encountering the first line of the email body, switching to EXPECTING_DATA_END state
        if self.state == self.EXPECTING_RCPT_TO_OR_DATA and self.generated_cmd == "DATA":
            self.advance()
            return self.evaluate_state() # Return True

        # 2) Encountering the "From:" line of a new email, switching from EXPECTING_DATA_END to EXPECTING_MAIL_FROM
        if self.state == self.EXPECTING_DATA_END and self.generated_cmd == "MAIL FROM":
            self.advance()
            return self.evaluate_state() # Return True

        # 3) Encountering the end-of-file (empty string), switching from EXPECTING_DATA_END to EXPECTING_MAIL_FROM
        if self.state == self.EXPECTING_DATA_END and end_of_file:
            return self.quit_immediately("end-of-file was reached during state 'EXPECTING_DATA_END'.")

        # 4) # If the generated command is "RCPT TO:", then do NOT advance and there is NO need
        # to process the input string (most likely an email address) again.
        # Only advance if the "DATA" command has been determined to be needed by evaluate_state()
        # if self.state == self.EXPECTING_RCPT_TO_OR_DATA and self.generated_cmd != "DATA":
        #     return self.evaluate_state() # Return False

        # Do NOT advance yet; this represents the first message received after the connection (socket)
        # has been established. Now, the client has to send a HELO message to the SMTP server and
        # expect a response.
        if self.state == self.EXPECTING_SERVER_GREETING:
            self.advance()
            return True

        # Since you only reach this point if a valid response code is entered, then it is safe
        # to advance the state.
        self.advance()

        self.advance_forward_file_line_pointer()

        self.self_update_parser()

        return True

    def reset(self):
        """
        Resets the SMTP server state machine to expect a new email.

        NOTE: Do not clear the generated_cmd as we need to know when the email loops..
        """
        self.state = self.EXPECTING_USER_MAIL_FROM_ADDRESS
        # self.generated_cmd = ""
        self.parser = None
        self.input_line = ""
        self.commands = []
        self.commands_index = -1
        self.forward_file_lines = []

        self.data_to_address_line = ""
        self.data_subject_line = ""

    def advance(self):
        """
        Advances the state of the SMTP server by 1. If a message is completed,
        then it starts over and waits for the next one.
        """

        next_state = self.EXPECTING_USER_MAIL_FROM_ADDRESS if self.state == self.EXPECTING_QUIT_RESPONSE else self.state + 1

        self.debug_print(f"advancing state from '{self.get_state_str(self.state)}' ({self.state}) to '{self.get_state_str(next_state)}' ({next_state})")

        self.state = next_state
        if (next_state == self.EXPECTING_USER_MAIL_FROM_ADDRESS):
            self.reset()

    def quit_immediately(self, msg: str):
        """
        Upon receiving any error message from the SMTP "server" or otherwise encountering an error,
        you should stop processing email, emit the SMTP message "QUIT" to standard output, and
        terminate your program.

        When you reach the end of the forward file, send the SMTP message "QUIT".

        If you received an SMTP error response, write the response message received (the whole thing)
        to stderr before quitting. This still aligns with echoing the received SMTP response message
        to stderr, just with the extra step of quitting.
        """

        print(msg)
        close_socket(self.connection_socket, self.debug_mode)
        sys.exit(1)

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

    # Get debug_mode, hostname, and port_number
    args = get_command_line_arguments()
    debug_mode = args.debug
    server_name = args.hostname
    # 8000 + 4956 = 12956
    server_port = args.port_number

    # This is the maximum amount of data, in bytes, that can be received or sent via the socket.
    bufsize = 1024

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:

        # The documentation provides a way to reuse a local socket in the TIME_WAIT state without
        # waiting for its natural timeout to expire
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        DebugMode.print(debug_mode, "entered the with statement for client_socket...")

        # Even when the client quits, it must send a message to the server before terminating,
        # so this is a safe place to create the client
        smtp_client = SMTPClientSide(debug_mode)

        try:

            # Maybe to make it clean, this part, where we are asking for user input, should be its
            # own function separate from evaluate state? Techically, asking for user input is NOT
            # evaluating the state.
            smtp_client.collect_user_input()

            DebugMode.print(debug_mode, f"attempting to connect to SMTP server {server_name}:{server_port}...", DebugMode.INFO)

            # 1. When your program connects to the server, it must be prepared to
            # receive a correct greeting message. Your program will do nothing with the
            # greeting message other than receive it and confirm that it is a valid
            # greeting message (220 hostname.cs.unc.edu)
            # 1a. If the greeting message is not a valid greeting message, you should
            # print a 1-line error message to stdout and then terminate the program.
            # 1b. If the greeting message is valid, you should reply to the greeting
            # with the SMTP HELO message using the format from the non-terminal. It
            # will look like "HELO client-hostname.cs.unc.edu", where that is a
            # hostname of the server the client program is running on
            client_socket.connect((server_name, server_port))

            DebugMode.print(debug_mode, f"opened a socket to SMTP server {server_name}:{server_port}", DebugMode.SUCCESS)

            # I think this should be a loop:
            # First time is to read the valid greeting message (220)
            # The loop is used to "evaluate state", where state is talking about where in the
            # "conversation" between client and server you are in sending a message to the SMTP
            # server. You loop until:
            # An error is received from the SMTP server
            # An exception occurs
            # The SMTP server sends the response required after getting the SMTP QUIT command

            # I think this is better than while True
            while socket_is_connected(connection_socket=client_socket):

                # We have two functions: evaluate_state() which sends messages
                # evaluate_response() which is used to interpret messages from the SMTP server.
                # The flow should be like this:

                # Client establishes connection, server sends "220 domain" to client

                # state: EXPECTING_SERVER_GREETING
                    # evaluate_response() get 220 domain message
                # state: EXPECTING_SERVER_HELLO
                    # evaluate_state(): send HELO
                    # evaluate_response(): get 250 Hello message
                # state: EXPECTING_MAIL_FROM
                    # evaluate_state(): MAIL FROM
                    # evaluate_response(): 250
                # state: EXPECTING_RCPT_TO
                    # evaluate_state(): RCPT TO
                    # evaluate_response: 250
                # state: EXPECTING_RCPT_TO_OR_DATA
                    # evaluate_state(): DATA
                    # evaluate_response(): 354
                # state: EXPECTING_DATA_END
                    # evaluate_state(): message
                    # do not expect a response until ".\n:" from the SMTP server!
                    # evaluate_state(): .
                    # evaluate_response(): 250
                # state: EXPECTING_QUIT_RESPONSE
                    # evaluate_state(): QUIT
                    # evaluate_response(): 221
                while True:

                    # Perhaps, instead of returning False, any time that this function would return
                    # false, we can just have the function move forward and call itself. interesting.
                    # Keep in mind, a while loop is still needed, it just means that its return
                    # value no longer matters as recursion will handle when a response is not
                    # anticipated or requested from the server.
                    smtp_client.set_socket(client_socket)

                    # Attempt to receive the greeting message
                    # .decode() is required or the Python script hangs
                    data = client_socket.recv(bufsize).decode()

                    DebugMode.print(debug_mode, f"data received: {data}", DebugMode.WARN)

                    parser = Parser(input_string=data, debug_mode=debug_mode)
                    smtp_client.set_parser(current_parser=parser)
                    smtp_client.set_socket(client_socket)
                    smtp_client.evaluate_response()

                    # TODO: See if some of the evaluate_state() code can be simplified; the response
                    # from the server is sufficient for whether the command sent is valid
                    smtp_client.evaluate_state()


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

                    # After the user has entered a valid email message, this program will create a TCP socket to the
                    # SMTP server at the host and port number specified on the command line.
                    # Once the TCP socket has been created, forward the user's message to the server using the
                    # SMTP protocol.

                    # 1. When your program connects to the server, it must be prepared to
                    # receive a correct greeting message. Your program will do nothing with the
                    # greeting message other than receive it and confirm that it is a valid
                    # greeting message (220 hostname.cs.unc.edu)
                    # 1a. If the greeting message is not a valid greeting message, you should
                    # print a 1-line error message to stdout and then terminate the program.
                    # 1b. If the greeting message is valid, you should reply to the greeting
                    # with the SMTP HELO message using the format from the non-terminal. It
                    # will look like "HELO client-hostname.cs.unc.edu", where that is a
                    # hostname of the server the client program is running on.


                    # Four new operations:

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

        except EOFError as e:
            # Ctrl+D (Unix) or end-of-file from a pipe
            # break
            DebugMode.print(debug_mode, f"EOFError: {e}", DebugMode.ERROR)
            print("Program terminated by pressing CTRL+D or end-of-file.")
        except KeyboardInterrupt as e:
            # Ctrl+C
            # break
            DebugMode.print(debug_mode, f"KeyboardInterrupt: {e}", DebugMode.ERROR)
            print("Program terminated by pressing CTRL + C.")
        except ParserError as e:
            # All errors that should be handled according to the writeup are handled as ParserError
            # objects. All other exceptions are ValueError or some other type. If a ParserError
            # occurrs, the write up says "upon receipt of any erroneous SMTP message you should
            # reset your state machine and return to the state of waiting for a valid MAIL FROM
            # message".
            DebugMode.print(debug_mode, f"ParserError: {e}", DebugMode.ERROR)
        except Exception as e:
            # print(f"An unexpected error occurred: {e}")
            # break
            print(f"Exception: {e}")

        smtp_client.reset()

if __name__ == "__main__":
    main()
