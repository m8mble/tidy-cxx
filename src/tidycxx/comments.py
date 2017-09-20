import re


class CommentParser(object):

    def __init__(self):
        self.in_old_comment = False
        self.old_comment_buffer = ''

    def _handle_code(self, code):
        if code:  # if there is no code to handle, don't handle it!
            self.handle_code(code)

    def feed(self, input_line):
        """ Split one line of source code into its pieces and call appropriate handlers on the respective code parts

            The input_line is expected to resemble one single line of source code, ie. no newline charaters in the
            middle and whatever is fed next is assumed to be placed on a consecutive line. The trailing '\n' is
            optional.

            :param input_line: Next line to digest
            :return: None
        """
        input_line = input_line.strip('\n')
        while True:
            matches = re.match(r'(?P<text>.*?)(?P<delimiter>' + ('\*/' if self.in_old_comment else '//|/\*')
                               + r')(?P<else>.*)', input_line)
            if not matches:
                break

            input_line = matches.group('else')
            if self.in_old_comment:
                self.handle_old_comment(self.old_comment_buffer + matches.group('text'))
                self.old_comment_buffer = ''
                self.in_old_comment = False
            else:
                self._handle_code(matches.group('text'))
                if matches.group('delimiter') == '/*':
                    self.in_old_comment = True
                else:
                    self.handle_new_comment(input_line)  # Input line contains else matching group; see above
                    self.handle_end_of_line()
                    return  # this line needs no further analysis

        # Handle stuff at end of line, ie. block not delimited by (eg. '*/') in this line
        if self.in_old_comment:
            self.old_comment_buffer += input_line + '\n'
        else:
            self._handle_code(input_line)
            self.handle_end_of_line()


    def handle_code(self, code):
        print('CPP', '_%s_' % code)

    def handle_old_comment(self, comment):
        """
        Handle code documentation given within a /* ... */ block. Method expects comment not to contain line breaks.
        :param comment: code documentation feed in the above form.
        :return: None
        """
        print('ILC', '_%s_' % comment)

    def handle_new_comment(self, comment):
        print('ELC', '_%s_' % comment)

    def handle_end_of_line(self):
        print('EOL')
