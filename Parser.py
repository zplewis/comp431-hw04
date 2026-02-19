# Source - https://stackoverflow.com/a/287944
# Posted by joeld, modified by community. See post 'Timeline' for change history
# Retrieved 2026-02-08, License - CC BY-SA 4.0

import socket
import sys

def socket_is_connected(connection_socket: socket.socket = None, debug_mode: bool = False) -> bool:
    """
    Docstring for socket_is_connected

    :param connection_socket: Description
    :type connection_socket: socket
    :return: Description
    :rtype: bool
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

def socket_send_msg(connection_socket: socket.socket = None, msg: str = "", debug_mode: bool = False) -> bool:
    """
    Docstring for socket_send_msg

    :param connection_socket: Description
    :type connection_socket: socket
    :param msg: Description
    :type msg: str
    :param debug_mode: Description
    :type debug_mode: bool
    :return: Description
    :rtype: bool
    """

    if not connection_socket:
        DebugMode.print(debug_mode, "socket_send_msg(); connection_socket variable was invalid")
        return False

    if not msg:
        DebugMode.print(debug_mode, "socket_send_msg(); msg string variable was invalid")
        return False

    if not socket_is_connected(connection_socket, debug_mode):
        DebugMode.print(debug_mode, "socket_send_msg(); connection_socket is NOT connected")
        return False

    try:

        DebugMode.print(debug_mode, f"About to send message: '{msg}'", DebugMode.INFO)
        connection_socket.sendall(msg.encode())
        DebugMode.print(debug_mode, f"Sent message successfully.", DebugMode.SUCCESS)

    except OSError as e:
        DebugMode.print(debug_mode, e, DebugMode.ERROR)
    except Exception as e:
        DebugMode.print(debug_mode, e, DebugMode.ERROR)

    return False

def get_hostname(debug_mode: bool = False) -> str:
        """
        Returns the hostname of the server this code is running on. This works on
        the cs.unc.edu server even though this just prints "Mac" as my hostname.
        """

        try:

            return socket.gethostname()

        except Exception as e:
            DebugMode.print(debug_mode, f"get_hostname(); failed to get hostname: {e}", DebugMode.ERROR)
            return ""

def close_socket(connection_socket: socket.socket = None, debug_mode: bool = False) -> bool:
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

        connection_socket.shutdown()
        connection_socket.close()

        return True

    except Exception as e:
        connection_socket = None
        DebugMode.print(debug_mode, f"close_socket(); exception occurred: {e}")

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
        Returns the name of the command being parsed, e.g., "MAIL FROM", "RCPT TO", "DATA".
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

        return self.input_string.split(',')

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

        return parts[1]

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
        codes = ["250", "354", "500", "501", "503"]

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

        return (self.match_chars("From:") and self.whitespace() and self.reverse_path() and \
                self.nullspace() and self.crlf())

    def forwardfile_match_to_address(self) -> bool:
        """
        Matches the "To: <sender@domain.com>" from a forward file. From this line, we can
        recreate the "RCPT TO:" command.
        """

        return (self.match_chars("To:") and self.whitespace() and self.reverse_path() and \
                self.nullspace() and self.crlf())


    def is_at_end(self) -> bool:
        """
        Returns True if the parser has reached the end of the input string.
        """
        return self.position >= self.OUT_OF_BOUNDS

    def raise_parser_error(self, error_no: int, check_only: bool = False) -> bool:
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

        if not (self.whitespace() and self.domain() and self.nullspace() and self.crlf()):
            raise self.raise_parser_error(ParserError.SYNTAX_ERROR_IN_PARAMETERS)

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
        return self.print_success()

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
        return self.print_success()

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
            return self.raise_parser_error(ParserError.COMMAND_UNRECOGNIZED, check_only)

        # Flag that the command has been identified
        self.set_command_identified(cmd_name)

        # If we are only checking for command recognition, we can stop here and return
        if check_only:
            return True

        if not (self.nullspace() and self.crlf()):
            raise ParserError(ParserError.COMMAND_UNRECOGNIZED)

        # If we reach here, the line was successfully parsed
        self.set_command_parsed()

        if cmd_name == "DATA":
            return self.print_success(354)

        # TODO: See what you need to print, if anything, for QUIT.
        return True

    def quit_cmd(self, check_only: bool = False) -> bool:
        """
        The <quit-cmd> non-terminal handles the "QUIT" command.

        <quit-cmd> ::= "QUIT" <nullspace> <CRLF>
        """

        return self.word_only_commands("QUIT", check_only=check_only)

    def data_cmd(self, check_only: bool = False) -> bool:
        """
        The <data-cmd> non-terminal handles the "DATA" command.

        <data-cmd> ::= "DATA" <nullspace> <CRLF>
        """

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

            return self.print_success()

        # If we are not at the beginning of a new line, then we need to check for
        # <CRLF> "." <CRLF> from the current position.
        if not (self.crlf() and self.match_chars(".") and self.crlf()):
            self.rewind(start)
            return False

        return self.print_success()

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
