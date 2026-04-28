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
import sys
from pathlib import Path
# from Parser import Parser, ParserError, DebugMode, socket_is_connected, socket_send_msg, get_hostname, close_socket

def socket_is_connected(connection_socket: socket.socket, debug_mode: bool = False) -> bool:
    """
    Docstring for socket_is_connected
    """

    if not connection_socket or connection_socket is None:
        DebugMode.print(debug_mode, "socket_is_connected(); connection_socket is empty")
        return False

    try:

        DebugMode.print(debug_mode, f"getpeername(): {connection_socket.getpeername()}", DebugMode.SUCCESS)

        return True

    except Exception as e:
        DebugMode.print(debug_mode, f"socket_is_connected(); exception occurred: {e}", DebugMode.ERROR)
        return False

def socket_send_msg(connection_socket: socket.socket, msg: str = "", debug_mode: bool = False) -> bool:
    """
    Shared function for using an existing socket for sending a message to the other end system.
    """

    if not connection_socket:
        DebugMode.print(debug_mode, "socket_send_msg(); connection_socket variable was invalid")
        return False

    # From the client, we need to be able to send empty messages to the server, like when
    # there is a blank line in the body of an email.
    # if not msg or msg is None:
    if msg is None:
        DebugMode.print(debug_mode, "socket_send_msg(); msg string variable was invalid")
        return False

    if not socket_is_connected(connection_socket, debug_mode):
        DebugMode.print(debug_mode, "socket_send_msg(); connection_socket is NOT connected")
        return False

    try:

        if not msg.endswith("\n"):
            msg += "\n"

        log_friendly_msg = msg[:-1] if msg.endswith("\n") else msg

        DebugMode.print(debug_mode, f"About to send message: '{log_friendly_msg.replace("\n","")}'", DebugMode.WARN)
        connection_socket.sendall(msg.encode())
        DebugMode.print(debug_mode, f"Sent message successfully.", DebugMode.SUCCESS)
        return True

    except OSError as e:
        DebugMode.print(debug_mode, str(e), DebugMode.ERROR)
    except Exception as e:
        DebugMode.print(debug_mode, str(e), DebugMode.ERROR)

    return False

def get_hostname(debug_mode: bool = False) -> str:
        """
        Returns the hostname of the server this code is running on. This works on
        the cs.unc.edu server even though this just prints "Mac" as my hostname.
        """

        try:

            # getfdqn() gives you the IP address
            domain = socket.gethostname()
            # if domain.casefold() == 'mac':
            #     domain = '127.0.0.1'

            return domain
            # return socket.gethostname()

        except Exception as e:
            DebugMode.print(debug_mode, f"get_hostname(); failed to get hostname: {str(e)}", DebugMode.ERROR)
            return ""

def close_socket(connection_socket: socket.socket|None, debug_mode: bool = False) -> bool:
    """
    Docstring for close_socket

    :param connection_socket: Description
    :type connection_socket: socket.socket
    :return: Description
    :rtype: bool
    """

    try:

        if connection_socket is None:
            return False

        if not socket_is_connected(connection_socket, debug_mode):
            connection_socket.close()
            return True

        # Note: close() releases the resource associated with a connection but does not
        # necessarily close the connection immediately. If you want to close the connection in a
        # timely fashion, call shutdown() before close().
        connection_socket.shutdown(socket.SHUT_RDWR)
        connection_socket.close()

        return True

    except Exception as e:
        # connection_socket = None
        DebugMode.print(debug_mode, f"close_socket(); exception occurred: {str(e)}")

    return False

class DebugMode():
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    INFO = 0 # Cyan
    WARN = 1 # YELLOW
    ERROR = 2 # Red
    SUCCESS = 3 # Green

    @staticmethod
    def get_color_from_type(log_type: int = 0) -> str:
        """
        Docstring for get_color_from_type
        """

        if log_type == DebugMode.INFO:
            return DebugMode.OKCYAN

        if log_type == DebugMode.WARN:
            return DebugMode.WARNING

        if log_type == DebugMode.ERROR:
            return DebugMode.FAIL

        if log_type == DebugMode.SUCCESS:
            return DebugMode.OKGREEN

        return DebugMode.ENDC

    @staticmethod
    def print(debug_mode: bool, text: str, log_type: int = 0):
        if not debug_mode:
            return

        start_color = DebugMode.get_color_from_type(log_type)

        # Apparently, print() was printing an extra line
        if debug_mode:
            text = f"{start_color}{text}{DebugMode.ENDC}"

        sys.stdout.write(text + "\n")
        sys.stdout.flush()


class ParserError(Exception):
    """
    Raised when a parsing error occurs. With HW2, whenver the first parsed
    token(s) on an input line do not match the literal string(s) in the
    production rule for any message in the grammar, a type 500 error message
    is generated. Operationally, a 500 error means that your parser could not
    uniquely recognize which SMTP message it should be parsing.

    If the correct message token(s) are recognized (i.e., your parser "knows"
    what message it's parsing), but some other error occurs on the line, a type
    501 error message is generated.
    """

    SERVER_GREETING = 220
    COMMAND_UNRECOGNIZED = 500
    SYNTAX_ERROR_IN_PARAMETERS = 501
    BAD_SEQUENCE_OF_COMMANDS = 503

    def __init__(self, error_no: int):
        self.error_no = error_no

        super().__init__(self.get_error_message())

    def get_error_message(self) -> str:
        """
        Returns the error message corresponding to the error number.
        """

        if self.error_no == self.SYNTAX_ERROR_IN_PARAMETERS:
            return "501 Syntax error in parameters or arguments"

        if self.error_no == self.BAD_SEQUENCE_OF_COMMANDS:
            return "503 Bad sequence of commands"

        # Assume 500 for anything else
        return "500 Syntax error: command unrecognized"


class Parser:
    """
    This will process a string and determine whether that string conforms to a
    particular grammar. Each function in this class corresponds to a
    non-terminal in the grammar.

    The professor said that this is a "context-free" grammar; what does that
    mean?

    This parser does NOT require backtracking. There won't be any ambiguities
    in this. This grammar will be LL(1). The "1" is the number of "lookahead",
    where "lookahead" represents the number of tokens (in this class,
    characters) that the parser will see in advance before making a decision.

    Based on the HW1 writeup,
    """

    def __init__(self, input_string: str, debug_mode: bool = False):
        """
        Constructor for the Parser class.

        :param input_string: String from stdin to be parsed as a "MAIL FROM:" command.
        """
        self.input_string = input_string


        self.BEGINNING_POSITION = 0
        self.position = self.BEGINNING_POSITION
        """
        The position of the "cursor", like in SQL, of the current character.
        """


        self.OUT_OF_BOUNDS = len(input_string)
        """
        A constant representing when the position has reached the end of the input string.
        """

        self.command_identified = False
        """
        A flag indicating whether the command has been identified. This does NOT mean that the
        command has been successfully parsed; it only means that the parser has gotten past the
        string literals at the beginning of the command line.
        """

        self.command_name = ""
        """
        The name of the command being parsed, e.g., "MAIL FROM", "RCPT TO", "DATA".
        """

        self.command_parsed = False
        """
        A flag indicating whether the command has been successfully parsed. To reiterate, a command
        can be identified but not successfully parsed.
        """

        self.debug_mode = debug_mode
        """
        If True, print additional statements that help with debugging. Turned off by default to
        prevent changing the output for grading.
        """

    def set_command_parsed(self):
        """
        Sets the command_parsed flag.
        """
        self.command_parsed = True

    def get_command_name(self) -> str:
        """
        Returns the name of the command being parsed, e.g., "MAIL FROM", "RCPT TO", "DATA", "HELO", "QUIT".
        """

        return self.command_name

    def is_command_identified(self) -> bool:
        """
        Returns True if the command has been identified.
        """

        return self.command_identified

    def set_command_identified(self, command_name: str = ""):
        """
        Sets the command_identified flag and command_name.
        """

        self.command_identified = True
        self.command_name = command_name

    def check_for_commands(self) -> bool:
        """
        Checks the input string for known commands and sets the command_identified
        flag and command_name accordingly. This function keeps up with the original position
        and restores it after the checks are performed so that non-terminals are identified
        correctly.
        """

        start = self.position
        self.reset()

        # Check for MAIL FROM
        # The second part is not needed; if this non-terminal function returns true with
        # check_only=True, that means either the command was identified or identified and parsed.
        if self.mail_from_cmd(check_only=True):
            self.rewind(start)
            return True

        self.reset()
        if self.rcpt_to_cmd(check_only=True):
            self.rewind(start)
            return True

        self.reset()
        if self.data_cmd(check_only=True):
            self.rewind(start)
            return True

        self.reset()
        if self.quit_cmd(check_only=True):
            self.rewind(start)
            return True

        # This means no commands have been identified, which can mean a number of things but not
        # necessarily a problem (depending on the state of the SMTP Server)
        self.rewind(start)
        return False

    def get_smtp_response_code(self) -> str:
        """
        Every SMTP response code, based on the grammar, starts with <resp-number>. Return this
        value.
        """

        if len(self.input_string) < 3:
            return ""

        # We need exactly three digit characters
        resp_number = self.input_string[:3]

        # https://docs.python.org/3/library/stdtypes.html#str.isdigit
        # Apparently, this works on an entire string, not just a single character.
        if not resp_number.isdigit():
            return ""

        return resp_number

    def is_error_smtp_response_code(self) -> bool:
        """
        Assuming that the input string matched on <response-code>, returns True if the error
        code >= 500.
        """

        resp_number_str = self.get_smtp_response_code()

        if not resp_number_str or len(resp_number_str) != 3:
            return False

        resp_number_int = int(resp_number_str)

        return resp_number_int >= 500


    def get_input_line_raw(self) -> str:
        """
        Get the exact string passed to the parser.
        """

        return self.input_string

    def get_input_line(self) -> str:
        """
        Retrieves the input line for printing to stdout or stderr without the
        last newline character.
        """

        # if self.debug_mode:
        #     print(f"original: {self.input_string}")
        #     print(f"sliced: {self.input_string[:-1]}")

        if not self.input_string or self.input_string is None:
            return ""

        if not self.input_string.endswith("\n"):
            return self.input_string

        return self.input_string[:-1]


    def get_email_address(self) -> str:
        """
        Extracts and returns the email address from the input string.
        """

        start_index = self.input_string.find("<") + 1
        end_index = self.input_string.find(">", start_index)
        return self.input_string[start_index:end_index].strip()

    def get_email_addresses(self) -> list:
        """
        For use with the <mailboxes> non-terminal, this returns a list of email addresses that
        have passed the production rule.
        """

        if not self.input_string:
            return []

        line = self.get_input_line()

        return line.split(',')

    def get_email_domain(self) -> str:
        """
        Extracts and returns the domain from the email address in the input
        string.
        """

        email_address = self.get_email_address()

        if not email_address or '@' not in email_address or '.' not in email_address:
            return ""

        parts = email_address.split('@')

        if not parts or len(parts) != 2:
            return ""

        return parts[1].casefold().strip()

    def get_domain_from_helo(self) -> str:
        """
        Extracts and returns the domain from the HELO msg.
        """

        if not self.command_parsed or self.command_name != "HELO":
            return ""

        return self.input_string.replace("HELO", "").strip()

    def get_address_line_for_email(self, string_literal: str) -> str:
        """
        Extracts and returns an address line for email based on the provided
        string literal ("FROM:" or "TO:") from a command line. This only works if the
        command has been successfully parsed (MAIL FROM or RCPT TO).
        """

        if not self.is_at_end() or not string_literal or string_literal not in self.input_string:
            raise ValueError(f"Input string does not contain '{string_literal}' literal.")

        start_index = self.input_string.find(string_literal) + len(string_literal)
        end_index = self.input_string.find(">", start_index) + 1
        return f"{string_literal[:-1].capitalize()}: {self.input_string[start_index:end_index].strip()}"

    def get_from_line_for_email(self) -> str:
        """
        Extracts and returns "From: <reverse-path>"from a "MAIL FROM:" command line.
        Assumes that the line has already been successfully parsed.
        """

        return self.get_address_line_for_email("FROM:")

    def get_to_line_for_email(self) -> str:
        """
        Extracts and returns "To: <forward-path-n>" from a "RCPT TO:" command line.
        """

        return self.get_address_line_for_email("TO:")

    def generate_mail_from_cmd(self) -> str:
        """
        Creates a "MAIL FROM:" command if the input string contains an email address.
        """

        email_address = self.get_email_address()
        return f"MAIL FROM: <{email_address}>"

    def generate_rcpt_to_cmd(self) -> str:
        """
        Creates a "RCPT TO:" command if the input string contains an email address.
        """

        email_address = self.get_email_address()
        return f"RCPT TO: <{email_address}>"

    def generate_data_cmd(self) -> str:
        """
        Creates a "DATA" command.
        """

        return "DATA"

    def generate_data_end_cmd(self) -> str:
        """
        Prints the ".<CRLF>" needed to indicate the end of the body of the email.
        """

        return "."

    def print_success(self, msg_no: int = 250) -> bool:
        """
        Prints the success message when a line is successfully parsed.
        """

        if msg_no == 250:
            print("250 OK")

        if msg_no == 354:
            print("354 Start mail input; end with <CRLF>.<CRLF>")

        return True

    def match_response_code(self) -> bool:
        """
        This is the non-terminal for both success and error codes.

        <response-code> ::= <resp-number> <whitespace> <arbitrary-text> <CRLF>
        """

        return self.match_resp_number() and self.whitespace() and self.match_arbitrary_text() and \
        self.crlf()

    def match_resp_number(self) -> bool:
        """
        Matches a string literal for any of the allowed error or success messages.
        """

        start = self.position
        codes = ["220", "221", "250", "354", "500", "501", "503"]

        for code in codes:
            if self.match_chars(code):
                return True

            self.rewind(start)

        return False

    def match_arbitrary_text(self) -> bool:
        """
        Matches any sequence of printable characters.
        """

        while self.match_ascii_printable():
            pass

        return True

    def current_char(self) -> str:
        """
        Returns the current character that the parser is looking at.
        """

        if self.is_at_end():
            return ""
        return self.input_string[self.position]

    def advance(self):
        """
        Advances the "cursor" for the parser forward by one character.
        """

        if self.is_at_end():
            return

        self.position += 1

    def forwardfile_match_from_address(self) -> bool:
        """
        Matches the "From: <sender@domain.com>" from a forward file. From this line, we can
        recreate the "MAIL FROM:" command.
        """

        self.position = self.BEGINNING_POSITION

        if not self.match_chars("From:"):
            DebugMode.print(self.debug_mode, "forwardfile_match_from_address failed on 'From:'")

        if not self.whitespace():
            DebugMode.print(self.debug_mode, "forwardfile_match_from_address failed on .whitespace()")

        if not self.reverse_path():
            DebugMode.print(self.debug_mode, "forwardfile_match_from_address failed on .reverse_path()")

        if not self.nullspace():
            DebugMode.print(self.debug_mode, "forwardfile_match_from_address failed on .nullspace()")

        if not self.crlf():
            DebugMode.print(self.debug_mode, "forwardfile_match_from_address failed on .crlf()", DebugMode.ERROR)

        self.position = self.BEGINNING_POSITION

        result = (self.match_chars("From:") and self.whitespace() and self.reverse_path() and \
                self.nullspace() and self.crlf())

        if result:
            self.command_identified = True
            self.command_parsed = True
            self.command_name = "MAIL FROM"

        return result

    def forwardfile_match_to_address(self) -> bool:
        """
        Matches the "To: <sender@domain.com>" from a forward file. From this line, we can
        recreate the "RCPT TO:" command.
        """

        self.position = self.BEGINNING_POSITION

        if not self.match_chars("To:"):
            DebugMode.print(self.debug_mode, "forwardfile_match_to_address failed on 'To:'", DebugMode.ERROR)

        if not self.whitespace():
            DebugMode.print(self.debug_mode, "forwardfile_match_to_address failed on .whitespace()", DebugMode.ERROR)

        if not self.reverse_path():
            DebugMode.print(self.debug_mode, "forwardfile_match_to_address failed on .reverse_path()", DebugMode.ERROR)

        if not self.nullspace():
            DebugMode.print(self.debug_mode, "forwardfile_match_to_address failed on .nullspace()", DebugMode.ERROR)

        if not self.crlf():
            DebugMode.print(self.debug_mode, "forwardfile_match_to_address failed on .crlf()", DebugMode.ERROR)

        self.position = self.BEGINNING_POSITION

        result = (self.match_chars("To:") and self.whitespace() and self.reverse_path() and \
                self.nullspace() and self.crlf())

        if result:
            self.command_identified = True
            self.command_parsed = True
            self.command_name = "RCPT TO"

        return result


    def is_at_end(self) -> bool:
        """
        Returns True if the parser has reached the end of the input string.
        """
        return self.position >= self.OUT_OF_BOUNDS

    def raise_parser_error(self, error_no: int, check_only: bool = False):
        """
        Raises a ParserError with the given error number if check_only is False.
        """
        if not check_only:
            raise ParserError(error_no)
        return False

    def match_helo_msg(self) -> bool:
        """
        This is the non-terminal for the HELO message.

        <helo-msg> ::= "HELO" <whitespace> <domain> <nullspace> <CRLF>
        """

        if self.match_chars("HELO"):
            self.set_command_identified("HELO")

        if not self.whitespace():
            DebugMode.print(self.debug_mode, f"match_helo_msg(); failed on whitespace: '{self.get_input_line()}'")
            raise ParserError(ParserError.SYNTAX_ERROR_IN_PARAMETERS)

        if not self.domain():
            DebugMode.print(self.debug_mode, f"match_helo_msg(); failed on domain: '{self.get_input_line()}'")
            raise ParserError(ParserError.SYNTAX_ERROR_IN_PARAMETERS)

        if not self.nullspace():
            DebugMode.print(self.debug_mode, f"match_helo_msg(); failed on nullspace: '{self.get_input_line()}'")
            raise ParserError(ParserError.SYNTAX_ERROR_IN_PARAMETERS)

        if not self.crlf():
            DebugMode.print(self.debug_mode, f"match_helo_msg(); failed on crlf '{self.get_input_line()}'")
            raise ParserError(ParserError.SYNTAX_ERROR_IN_PARAMETERS)

        self.set_command_parsed()
        return True

    def mail_from_cmd(self, check_only: bool = False) -> bool:
        """
        The <mail-from-cmd> non-terminal serves as the entry point for the
        parser. In other words, this non-terminal handles the entire
        "MAIL FROM:" command.

        <mail-from-cmd> ::= "MAIL" <whitespace> "FROM:" <nullspace> <reverse-path> <nullspace> <CRLF>
        """
        if not (self.match_chars("MAIL") and self.whitespace() and self.match_chars("FROM:")):
            return self.raise_parser_error(ParserError.COMMAND_UNRECOGNIZED, check_only)
        # Flag that the command has been identified
        self.set_command_identified("MAIL FROM")

        # If we are only checking for command recognition, we can stop here and return
        if check_only:
            return True


        if not (self.nullspace() and self.reverse_path() and self.nullspace() and self.crlf()):
            raise ParserError(ParserError.SYNTAX_ERROR_IN_PARAMETERS)

        # If we reach here, the line was successfully parsed
        self.set_command_parsed()
        return True

    def rcpt_to_cmd(self, check_only: bool = False) -> bool:
        """
        The <rcpt-to-cmd> non-terminal handles the "RCPT TO:" command.

        <rcpt-to-cmd> ::= "RCPT" <whitespace> "TO:" <nullspace> <forward-path> <nullspace> <CRLF>
        """

        if not (self.match_chars("RCPT") and self.whitespace() and self.match_chars("TO:")):
            return self.raise_parser_error(ParserError.COMMAND_UNRECOGNIZED, check_only)

        # Flag that the command has been identified
        self.set_command_identified("RCPT TO")

        # If we are only checking for command recognition, we can stop here and return
        if check_only:
            return True

        if not(self.nullspace() and self.forward_path() and self.nullspace() and self.crlf()):
            raise ParserError(ParserError.SYNTAX_ERROR_IN_PARAMETERS)

        # If we reach here, the line was successfully parsed
        self.set_command_parsed()
        return True

    def word_only_commands(self, cmd_name: str, check_only: bool = False) -> bool:
        """
        The <data-cmd> non-terminal handles the "DATA" command.
        The <quit-cmd> non-terminal handles the "QUIT" command.

        <data-cmd> ::= "DATA" <nullspace> <CRLF>
        <quit-cmd> ::= "QUIT" <nullspace> <CRLF>
        """

        allowed_cmds = ["QUIT", "DATA"]

        if not cmd_name or not isinstance(cmd_name, str) or not cmd_name in allowed_cmds:
            raise ValueError(f"word_only_commands(); must specify a valid command string literal ({','.join(allowed_cmds)})")

        # This is an example of a literal string in a production rule
        # If an error occurs here, it is a 500 error
        if not self.match_chars(cmd_name):
            DebugMode.print(self.debug_mode, f"{cmd_name}_cmd(); failed on match_chars({cmd_name}): '{self.get_input_line()}'")
            return self.raise_parser_error(ParserError.COMMAND_UNRECOGNIZED, check_only)

        # Flag that the command has been identified
        self.set_command_identified(cmd_name)

        # If we are only checking for command recognition, we can stop here and return
        if check_only:
            return True

        if not self.nullspace():
            DebugMode.print(self.debug_mode, f"{cmd_name}_cmd(); failed on nullspace: '{self.get_input_line()}'")
            return self.raise_parser_error(ParserError.COMMAND_UNRECOGNIZED, check_only)

        if not self.crlf():
            DebugMode.print(self.debug_mode, f"{cmd_name}_cmd(); failed on crlf: '{self.get_input_line()}'")
            return self.raise_parser_error(ParserError.COMMAND_UNRECOGNIZED, check_only)

        # If we reach here, the line was successfully parsed
        self.set_command_parsed()

        return True

    def quit_cmd(self, check_only: bool = False) -> bool:
        """
        The <quit-cmd> non-terminal handles the "QUIT" command.

        <quit-cmd> ::= "QUIT" <nullspace> <CRLF>
        """

        DebugMode.print(self.debug_mode, "reached quit_cmd()")
        return self.word_only_commands(cmd_name="QUIT", check_only=check_only)

    def data_cmd(self, check_only: bool = False) -> bool:
        """
        The <data-cmd> non-terminal handles the "DATA" command.

        <data-cmd> ::= "DATA" <nullspace> <CRLF>
        """

        DebugMode.print(self.debug_mode, "reached data_cmd()")
        return self.word_only_commands("DATA", check_only=check_only)

    def data_read_msg_line(self):
        """
        Handles the reading of mail input lines after a successful DATA command.
        """

        # This means to loop until we match <CRLF>.<CRLF>, or until we
        # encounter an invalid character.
        # I think this should work because data_end_cmd() rewinds the position
        # if it fails to match.
        while not self.data_end_cmd():
            # No need to continue if there are no more characters
            if self.is_at_end():
                break
            # What characters are allowed here?
            # There are no limits or constraints on what, how much text can be
            # entered after a correct DATA message other than we'll assume that
            # text is limited to printable text, whitespace, and newlines.
            if not (self.match_ascii_printable() or self.whitespace()
                or self.crlf()):
                # print(f"data_read_msg_line(); nothing matched...")
                return False

        return True

    def data_end_cmd(self):
        """
        The <data-end-cmd> non-terminal handles the end of mail input,
        represented by a line containing only a period. This non-terminal has
        to work with both keyboard input and reading a file.

        If reading from a file, the line will only contain a period and a newline.
        If reading from keyboard input, the user will type a period and press Enter.

        Maybe it goes like this:
        If the current position == 0 (beginning of a new line), and the next two characters are
        a period and a newline, then we have matched <data-end-cmd>.

        If the current position != 0, then we are not at the beginning of a new line. We can
        check whether <CRLF> "." <CRLF> matches from the current position.

        The reason this should work is because this function is not managing the state; it is
        only reading from the current position. This means that the code calling this function
        is responsible for calling it only after the "DATA" command has been successfully parsed.

        <data-end-cmd> ::= <CRLF> "." <CRLF>
        """

        # The line must begin with a period and nothing else
        # The beginning of a new line implies <CRLF> as defined by the
        # production rule.
        start = self.position

        if self.position == self.BEGINNING_POSITION:
            if not (self.match_chars(".") and self.crlf()):
                self.rewind(start)
                return False

            return True

        # If we are not at the beginning of a new line, then we need to check for
        # <CRLF> "." <CRLF> from the current position.
        if not (self.crlf() and self.match_chars(".") and self.crlf()):
            self.rewind(start)
            return False

        return True

    def is_ascii(self, char: str) -> bool:
        """
        Checks if a character is an ASCII character.
        """
        if self.is_at_end():
            return False

        return 0 <= ord(char) <= 127

    def is_ascii_printable(self, char: str) -> bool:
        """
        Checks if a character is an ASCII printable character.
        https://www.ascii-code.com/characters/printable-characters

        32 is space. <char> will omit space based on the rule.
        """
        if self.is_at_end():
            return False

        if not char:
            return False

        return 32 <= ord(char) <= 126

    def match_ascii_printable(self) -> bool:
        """
        Attempts to match a single ASCII printable character. If it matches,
        then advance the parser's position by one.
        """

        if self.is_at_end():
            # print(f"match_ascii_printable(); parser is at the end")
            return False

        if not self.is_ascii_printable(self.current_char()):
            # print(f"match_ascii_printable(); current char is not printable: (#{ord(self.current_char())}), input_string length: {len(self.input_string)}, position: {self.position}")
            return False

        self.advance()
        return True

    def rewind(self, new_position: int) -> bool:
        """
        Rewinds the parser's position to a specified index.

        :param self: Description
        :param new_position: The position to rewind to.
        """

        if not (self.BEGINNING_POSITION <= new_position <= self.OUT_OF_BOUNDS):
            raise ValueError(f"""new_position must be within the bounds of the input string.
                             actual: {new_position}, expected: [0, {self.OUT_OF_BOUNDS - 1}]""")

        self.position = new_position

        return True

    def fast_forward(self, new_position: int) -> bool:
        """
        Fast-forwards the parser's position to a specified index. Alias for "rewind".
        """

        return self.rewind(new_position)


    def reset(self):
        """
        Resets the parser's position to the beginning of the input string.
        """

        self.command_identified = False
        self.command_name = ""
        self.command_parsed = False
        return self.rewind(self.BEGINNING_POSITION)

    def match_chars(self, expected: str) -> bool:
        """
        Attempts to match a sequence of characters in the input string. This is
        good for matching fixed strings like "MAIL", "FROM:", "<", ">", etc.
        """

        if self.is_at_end():
            return False

        if not expected:
            raise ValueError("Expected must be a non-empty string.")

        for ch in expected:
            if not self.is_ascii(ch):
                raise ValueError("Expected character must be an ASCII character.")

            matched = self.is_ascii(self.current_char()) and self.current_char() == ch

            if not matched:
                return False

            self.advance()

        return True

    def whitespace(self) -> bool:
        """
        Matches one or more <sp> characters. Since this non-terminal does
        generate a ParserError upon failure, there is no need to return a
        value.
        """

        if not self.sp():
            return False

        while self.sp():
            pass

        return True

    def nullspace(self) -> bool:
        """
        Matches zero or more <sp> characters. Based on the video, because this
        non-terminal is in the starting rule (<i>mail-from-cmd</i>), it DOES
        generate a ParserError upon failure. After thinking about it, though,
        since this non-terminal can match zero characters, it will never fail.
        It is also NOT found in the list of non-terminals that DO generate an
        error in the HW1 writeup.

        :param self: Description
        """

        if self.is_at_end():
            return True

        while self.sp():
            pass

        return True

    def reverse_path(self):
        """
        The function that handles the <reverse-path> non-terminal.
        """

        return self.is_path()

    def forward_path(self) -> bool:
        """
        The function that handles the <forward-path> non-terminal. I imagine
        that this is a separate non-terminal in case it has to change later.

        <forward-path> ::= <path>
        """
        return self.is_path()

    def mailboxes(self) -> bool:
        """
        The function that handles the custom <mailboxes> non-terminal, which is:
        <mailboxes> ::= <mailbox> | <mailbox> "," <nullspace> <mailboxes>

        This is modeled after how <domain> works, recursively checking for
        <mailbox> in a comma-separated list.
        """

        start = self.position

        if not self.mailbox():
            self.rewind(start)
            return False

        start = self.position

        # Update the start position because we have a <mailbox>!
        if not self.match_chars(","):
            # Since there is no comma, rewind and stop here.
            self.rewind(start)
            return True

        # Since there is a comma, see if there is <nullspace> AND another
        # <mailbox>. If not, rewind again and return False. We are rewinding to
        # before the comma since the comma by itself is not enough for the
        # "right-side" of the "or" operator in the <mailboxes> non-terminal.
        # Calling this checks for another <nullspace> <mailboxes> after the
        # comma.
        if not (self.nullspace() and self.mailboxes()):
            self.rewind(start)
            return False

        return True

    def domain(self) -> bool:
        """
        The function that handles the <domain> non-terminal, which is:
        <domain> ::= <element> | <element> "." <domain>
        """

        start = self.position

        if not self.element():
            # print("Domain element failed")
            self.rewind(start)
            return False

        # Update the starting position since this succeeded!
        start = self.position

        if not self.match_chars("."):
            # Since there is no period, rewind and stop here
            self.rewind(start)
            return True

        # Since there is a period, see if there is another element. If not,
        # rewind again and return False. We are rewinding to before the period
        # since the period by itself is not enough for the "right-side" of the
        # "or" operator in the <domain> non-terminal. Calling this checks
        # for another element after the period.
        if not self.domain():

            self.rewind(start)
            # print(f"Rewinding after failed domain check; current position is {self.position}, start: {start}")
            return False

        return True


    def element(self) -> bool:
        """
        The function that handles the <element> non-terminal, which is:
        <letter> | <name>

        This means that an element can be a single letter. However, it is
        possible since <name> starts with <letter> that we check for <name>
        first to get the longest match possible. For this to work, I'll need
        to account for the possibility that <name> could fail.

        :param self: Description
        :return: Description
        :rtype: bool
        """

        start = self.position

        if self.name():
            return True

        # If name failed, that means there were only 0 or 1 letters. Rewind
        # the cursor so that we can check for <letter>.
        self.rewind(start)
        if not self.letter():
            return False

        return True

    def name(self) -> bool:
        """
        The function that handles the <name> non-terminal, which is:
        <letter> <let-dig-str>
        """

        return self.letter() and self.let_dig_str()

    def let_dig_str(self) -> bool:
        """
        The function that handles the <let-dig-str> non-terminal. This works
        just like the <whitespace> non-terminal, where at least 1 letter or
        digit is required.
        """

        if not self.let_dig():
            return False

        while self.let_dig():
            pass

        return True

    def let_dig(self) -> bool:
        """
        The function that handles the <let-dig> non-terminal.

        :param self: Description
        """

        return self.letter() or self.digit()

    def char_in_set(self, char_set: set) -> bool:
        """
        Reusable function that checks if the current character is in the
        provided set of characters. This helps reduce code duplication for a
        number of trivial non-terminals.
        """
        if self.is_at_end():
            return False

        if len(char_set) == 0:
            raise ValueError("char_set must be a non-empty set of characters.")

        if self.current_char() in char_set:
            self.advance()
            return True

        return False

    def is_path(self) -> bool:
        """
        Matches <user@domain.com>.
        """

        start = self.position

        if not self.match_chars("<"):
            self.rewind(start)
            return False

        if not self.mailbox():
            self.rewind(start)
            return False

        if not self.match_chars(">"):
            self.rewind(start)
            return False
        return True

    def mailbox(self) -> bool:
        """
        Function for <mailbox>. Is allowed to generate errors under the error detection rule
        defined in HW1 writeup.
        """

        start = self.position

        if not self.local_part():
            self.rewind(start)
            return False

        if not self.match_chars("@"):
            self.rewind(start)
            return False

        if not self.domain():
            self.rewind(start)
            return False

        return True

    def local_part(self) -> bool:
        """
        Seems to be an alias for <string>.
        """

        return self.is_string()


    def is_string(self) -> bool:
        """
        Function for the <string> non-terminal. This seems to mean
        "one or more <char> characters".
        """

        start = self.position
        if not self.is_char():
            self.rewind(start)
            return False

        while self.is_char():
            pass

        return True

    def is_char(self) -> bool:
        """
        Returns True if the current character is any ASCII character except
        those in <special> or those in <sp>.
        """

        start = self.position
        if self.special() or self.sp():
            self.rewind(start)
            return False

        if not self.is_ascii_printable(self.current_char()):
            return False

        self.advance()
        return True

    def sp(self) -> bool:
        """
        Matches a single space or tab (\t) character. This is one of the
        "non-trivial" non-terminals, so it would not generate a ParserError.

        :param self: Description
        :return: Description
        :rtype: bool
        """
        special_chars = set(" \t")
        return self.char_in_set(special_chars)

    def letter(self) -> bool:
        """
        Returns True if the current character is a letter (A-Z, a-z).

        :param self: Description
        :return: Description
        """

        special_chars = set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        )
        return self.char_in_set(special_chars)

    def digit(self) -> bool:
        """
        Returns True if the current character is a digit (0-9).
        """

        # WARNING: Do NOT use str.isdigit because it includes more than just 0-9!
        # https://docs.python.org/3/library/stdtypes.html#str.isdigit
        special_chars = set("0123456789")
        return self.char_in_set(special_chars)

    def crlf(self) -> bool:
        """
        According to the grammar, matches a single newline character, \n.
        I suppose we don't have to worry about \r.
        """
        if self.is_at_end():
            return False

        special_chars = set("\n")
        if self.char_in_set(special_chars):
            return True

        # 10 is carriage return in the ASCII table
        # technically, the code should never reach here.
        if ord(self.current_char()) == 10:
            return True

        return False

    def special(self) -> bool:
        """
        Matches a single "special" character as defined in the HW1 writeup.

        :param self: Description
        :return: Description
        :rtype: bool
        """
        # This is a cool trick: calling set() on a string creates a unique
        # list of characters in that string
        # The slash had to be escaped for this to work, just like the double
        # quote.
        special_chars = set("<>()[]\\.,;:@\"")
        return self.char_in_set(special_chars)


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
        self.to_domains = set()
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

    def set_socket(self, connection_socket: socket.socket):
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

        if not self.connection_socket or not socket_is_connected(self.connection_socket, self.debug_mode):
            raise ValueError("connection_socket must be an instance of the socket class.")

        # Syntax errors in the message name (type 500 errors) should take precedence over all other
        # errors.
        # Out-of-order (type 503 errors) should take precedence over parameter/argument errors
        # (type 501 errors). This means that we can no longer throw a 501 error until we have
        # verified that the command is in the correct sequence.

        DebugMode.print(self.debug_mode, f"evaluate_state(server): state: {self.state}")

        if self.state == self.EXPECTING_CONNECTION:
            if not socket_send_msg(self.connection_socket, f"220 {get_hostname()}", self.debug_mode):
                print("Failed to send initial 220 message to client upon establishing a connection.")
                return self.reset()
            return self.advance()

        if self.state == self.EXPECTING_HELO:
            if not self.parser.match_helo_msg():
                raise ParserError(ParserError.COMMAND_UNRECOGNIZED)

            client_domain = self.parser.get_domain_from_helo()
            if not socket_send_msg(self.connection_socket, f"250 Hello {client_domain} pleased to meet you", self.debug_mode):
                print('Failed to send 250 Hello message to client. Closing connection.')
                close_socket(self.connection_socket)
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
            # self.add_text_to_email_body(self.parser.get_from_line_for_email())

            if not socket_send_msg(self.connection_socket, f"250 OK", self.debug_mode):
                print('Failed to send 250 OK to client. Closing connection.')
                close_socket(self.connection_socket)
            return self.advance()

        if self.state == self.EXPECTING_RCPT_TO or \
            (self.state == self.EXPECTING_RCPT_TO_OR_DATA and recognized_command == "RCPT TO"):
            # if the command fails, that means a type 501 error occurred.
            if not self.parser.rcpt_to_cmd():
                raise ParserError(ParserError.SYNTAX_ERROR_IN_PARAMETERS)

            # If we made it here, the command was fully parsed successfully
            # Add the "To: <forward-path>" line to the list of email text lines
            # self.add_text_to_email_body(self.parser.get_to_line_for_email())

            # This is not used in HW4, domain is
            # self.to_email_addresses.append(self.parser.get_email_address())
            self.to_domains.add(self.parser.get_email_domain())

            # Only advance if this is the first time we are seeing a To: address
            if self.state == self.EXPECTING_RCPT_TO:
                self.advance()

            # Send the client a 250
            if not socket_send_msg(self.connection_socket, f"250 OK", self.debug_mode):
                print('Failed to send 250 OK to client. Closing connection.')
                close_socket(self.connection_socket)
            return

        if self.state == self.EXPECTING_RCPT_TO_OR_DATA:
            # This means that the recognized command must be "DATA", but we'll check anyway
            if recognized_command == "DATA" and not self.parser.data_cmd():
                raise ParserError(ParserError.COMMAND_UNRECOGNIZED)

            # If we made it here, the command was fully parsed successfully
            # Advance so that we can start reading the message
            if not socket_send_msg(self.connection_socket, f"354 Start mail input; end with <CRLF>.<CRLF>", self.debug_mode):
                print('Failed to send 354 message to client. Closing connection.')
                close_socket(self.connection_socket)
            return self.advance()

        if self.state == self.EXPECTING_DATA_END:
            # This is different because any text that does not create an error that is parsed
            # here is considered valid until the ending comes.
            DebugMode.print(self.debug_mode, "About to check for end of data...")
            if self.parser.data_end_cmd():
                DebugMode.print(self.debug_mode, "End of message confirmed. About to process the email message...")
                self.process_email_message()
                # Send the client a 250
                if not socket_send_msg(self.connection_socket, f"250 OK", self.debug_mode):
                    print('Failed to send 250 OK to client. Closing connection.')
                    close_socket(self.connection_socket)
                return self.advance()

            # if an error occurs while reading a line meant for the body of the message, then
            # throw an error. According to the writeup, "we'll assume that 'text' is limited to
            # printable text, whitespace, and newlines".
            DebugMode.print(self.debug_mode, "Checking for whether this is a valid line of text for the body of the email...")
            if not self.parser.data_read_msg_line():
                DebugMode.print(self.debug_mode, f"This line is not valid for the body of the email: {self.parser.get_input_line()}")
                raise ParserError(ParserError.SYNTAX_ERROR_IN_PARAMETERS)

            DebugMode.print(self.debug_mode, f"About to add this line to the email body: {self.parser.get_input_line()}")
            self.add_text_to_email_body(self.parser.get_input_line())
            # Make sure not to advance here, this was almost a mistake that was done right in HW3
            return False

        if self.state == self.EXPECTING_QUIT:
            DebugMode.print(self.debug_mode, "About to check for QUIT command...")

            # It is possible to encounter another MAIL FROM command at this stage.
            if self.parser.mail_from_cmd(check_only=True):
                self.state = self.EXPECTING_MAIL_FROM
                return self.evaluate_state()

            if not self.parser.quit_cmd(check_only=True):
                raise ParserError(ParserError.COMMAND_UNRECOGNIZED)

            # Otherwise, we can send a message to the client and close the connection and return
            # to its initial state
            socket_send_msg(self.connection_socket, f"221 {get_hostname()} closing connection", self.debug_mode)
            close_socket(self.connection_socket)
            self.reset()

    def command_id_errors(self) -> str:
        """
        If no command is recognized, then that results in a 500 error.
        If an unexpected command is recognized based on the current state, that results in a 503.
        Return the recognized command. This is helpful for when a state represents an option,
        RCPT TO or DATA.
        """

        if self.state not in [self.EXPECTING_MAIL_FROM, self.EXPECTING_RCPT_TO, self.EXPECTING_RCPT_TO_OR_DATA, self.EXPECTING_QUIT]:
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

        if self.state == self.EXPECTING_QUIT and recognized_command != "QUIT":
            raise ParserError(ParserError.BAD_SEQUENCE_OF_COMMANDS)

        return recognized_command

    def reset(self):
        """
        Resets the SMTP server state machine to expect a new email.
        """

        if self.state  < self.EXPECTING_MAIL_FROM:
            self.state = self.EXPECTING_CONNECTION
        else:
            self.state = self.EXPECTING_MAIL_FROM  # self.EXPECTING_CONNECTION

        self.to_email_addresses = []
        self.to_domains = set()
        self.email_text = []

        DebugMode.print(self.debug_mode, "SERVER state machine has been reset.", DebugMode.ERROR)

    def advance(self):
        """
        Advances the state of the SMTP server by 1. If a message is completed,
        then it starts over and waits for the next one.
        """
        if self.state != self.EXPECTING_QUIT:
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
        for domain in self.to_domains:
            forward_path = forward_folder / domain

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

            DebugMode.print(debug_mode, "about to call .bind() to create the server_socket...")

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

                    # if debug_mode:
                    #     connection_socket.settimeout(4.0)

                    DebugMode.print(debug_mode, f"socket_server.accept() received a new connection. addr: {addr}")

                    smtp_server.reset()

                    parser = Parser("", debug_mode)

                    smtp_server.set_parser(parser)
                    smtp_server.set_socket(connection_socket)

                    # Send a greeting message to the newly connected client
                    smtp_server.evaluate_state()

                    DebugMode.print(debug_mode, "should have sent an initial message to the client by now...")

                    try:

                        # This might be better than while True
                        while socket_is_connected(connection_socket):

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
                            sentence = bytes_recv.decode()

                            # 2026-03-22: I think it is possible that the client could send more
                            # than one line at a time, so we should compensate for that possibility.
                            # However, it is normal after .split() for Python to create an empty
                            # string token at the end, so we have to account for that apparently.
                            # This fix is actually a big deal.

                            lines = sentence.split("\n")

                            DebugMode.print(debug_mode, f"data received: {sentence}", DebugMode.WARN)
                            DebugMode.print(debug_mode, f"# of lines received: {len(lines)}", DebugMode.WARN)


                            for i, line in enumerate(lines):
                                is_last_token = (i == len(lines) - 1)
                                # Make sure it is:
                                # The last token
                                # Is empty
                                # And the string actually ends with "\n"
                                # If all three are true, only then can we truly discard it
                                if is_last_token and line == "" and sentence.endswith("\n"):
                                    continue

                                fixed_line = line
                                if not line.endswith("\n"):
                                    fixed_line += "\n"

                                DebugMode.print(debug_mode, f"line of sentence: {fixed_line}", DebugMode.WARN)
                                parser = Parser(fixed_line, debug_mode)
                                smtp_server.set_parser(parser)
                                smtp_server.set_socket(connection_socket)
                                smtp_server.evaluate_state()

                    # break is not needed in any of the exceptions because to reach the exceptions
                    # means that the loop is already broken. A new connection would have to be
                    # established anyway.
                    except EOFError as e:
                        # Ctrl+D (Unix) or end-of-file from a pipe
                        # close_socket(connection_socket)
                        # print(e)
                        DebugMode.print(debug_mode, f"EOFError: {e}", DebugMode.ERROR)
                    except KeyboardInterrupt as e:
                        # Ctrl+C
                        close_socket(connection_socket)
                        # print(e)
                        DebugMode.print(debug_mode, f"KeyboardInterrupt (error): {e}", DebugMode.ERROR)
                    except ParserError as e:
                        # All errors that should be handled according to the writeup are handled as ParserError
                        # objects. All other exceptions are ValueError or some other type. If a ParserError
                        # occurrs, the write up says "upon receipt of any erroneous SMTP message you should
                        # reset your state machine and return to the state of waiting for a valid MAIL FROM
                        # message".

                        # 2026/04/20 - it does NOT say close the connection.

                        socket_send_msg(connection_socket, str(e))
                        # close_socket(connection_socket)

                        input_line = ""
                        if smtp_server is not None and smtp_server.parser is not None:
                            input_line = smtp_server.parser.get_input_line()

                        DebugMode.print(debug_mode, f"ParserError: {e}, input_string: {input_line}", DebugMode.ERROR)
                    except OSError as e:
                        # This can be useful for catching errors related to sockets
                        close_socket(connection_socket)
                        # print(e)
                        DebugMode.print(debug_mode, f"OSError: {e}", DebugMode.ERROR)
                    except Exception as e:
                        # print(f"An unexpected error occurred: {e}")
                        close_socket(connection_socket)
                        # print(e)
                        DebugMode.print(debug_mode, f"General Exception (connection_socket): {e}", DebugMode.ERROR)

                    # attempt to shut down the connection socket anyway just in case
                    # close_socket(connection_socket)
                    smtp_server.reset()

                    should_close_socket = False

        except EOFError as e:
            # Ctrl+D (Unix) or end-of-file from a pipe
            # break
            DebugMode.print(debug_mode, f"EOFError: {e}", DebugMode.ERROR)

        except KeyboardInterrupt as e:
            # Ctrl+C
            # break
            DebugMode.print(debug_mode, f"KeyboardInterrupt (error): {e}", DebugMode.ERROR)
            should_close_socket = True
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
            should_close_socket = True
        except Exception as e:
            # print(f"An unexpected error occurred: {e}")
            # break
            DebugMode.print(debug_mode, f"General Exception (server_socket): {e}", DebugMode.ERROR)
            should_close_socket = True

        # Attempt to close the server socket just in case
        if should_close_socket:
            close_socket(server_socket)
        smtp_server.reset()


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
