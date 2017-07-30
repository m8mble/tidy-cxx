__author__ = 'm8mble'
__email__ = 'm8mble@vivaldi.net'
__version__ = '0.1'

import comment_parser

import collections
import logging
import os.path
import re
import subprocess
import textwrap


class IncludeTreeNode(object):
    delimiter = '/'
    root_name = 'root'
    invalid_id = 9999

    def __init__(self, name=root_name, descendable=False, needs_remainder=True):
        self.name = name
        self.descendable = descendable
        self.children = []
        if needs_remainder:
            self.children.append(IncludeTreeNode('remainder', descendable=descendable, needs_remainder=False))

    def __getitem__(self, item):
        if not item:
            return self

        parts = item.split(self.delimiter)
        name = parts[0]

        try:
            idx = self.children.index(name)
            pos = self.children[idx][self.delimiter.join(parts[1:])]
        except ValueError:
            pos = self.children[-1]
        return pos

    def __str__(self):
        return '%s: %d@[%s]' % (str(self.name), len(self.children), ', '.join([str(c) for c in self.children]))

    def __eq__(self, other):
        if type(other) == str:
            return self.name == other
        elif type(other) == IncludeTreeNode:
            return self.name == other.name
        raise TypeError

    def insert(self, iterable, **kwargs):
        # Insert every iterable as direct child of self; return node inserted at last
        assert iterable
        if isinstance(iterable, str):
            iterable = iterable,
        self.children = self.children[:-1] + [IncludeTreeNode(i, **kwargs) for i in iterable] + [self.children[-1]]
        return self.children[-2]

    def id(self, item, group_only):
        assert isinstance(group_only, bool)
        if not item or (group_only and not self.descendable):
            return ''

        parts = item.split(self.delimiter)
        name = parts[0]
        try:
            idx = self.children.index(name)
            pos = self.children[idx]
            return ('{:0' + str(len(str(self.invalid_id))) + 'd}{:s}').format(
                idx, pos.id(item=self.delimiter.join(parts[1:]), group_only=group_only))
        except ValueError:
            return str(self.invalid_id)


class IncludeSequencer(object):
    def __init__(self):
        self._roots = []
        self.invalid_id = str(IncludeTreeNode().invalid_id)

    def add_root(self):
        self._roots.append(IncludeTreeNode(descendable=True))
        return self._roots[-1]

    def _find_include(self, include, respect_descendable):
        assert isinstance(respect_descendable, bool)
        for num, root in enumerate(self._roots):
            sid = root.id(include, respect_descendable)
            if sid != self.invalid_id:
                return sid, num
        else:
            return self.invalid_id, int(self.invalid_id)

    def _combine_ids(self, sid, num):
        return ('{:0'+str(len(str(self.invalid_id)))+'d}{:s}').format(num, sid)

    def sort_id(self, include):
        sid, num = self._find_include(include, respect_descendable=False)
        return self._combine_ids(sid, num)

    def group_id(self, include):
        sid, num = self._find_include(include, respect_descendable=True)
        ivl = len(self.invalid_id)
        length = max(ivl, len(sid) - ivl)
        return sid


########################################################################################################################


class _IncludeBuffer:
    def __init__(self):
        self.include = None
        self.comments = []  # List of comment strings
        # True for relative include (smae folder)
        # False for system and absolute includes (includes relative to -I compile settings)
        self.relative = None
        self.original = ''  # How the include line and its' description were formatted originally

    def clear(self):
        self.include = None
        self.comments = []
        self.relative = None
        self.original = ''

    def description(self):
        return ' '.join(self.comments)

    def add_comment(self, old, text):
        assert isinstance(old, bool) and isinstance(text, str)
        self.comments.append(text)
        self.original += (('/*%s*/' if old else '//%s') % text)


class IncludeArranger(comment_parser.CommentParser):

    def __init__(self, git_root, original_name, include_sequence=None, include_apply=None):
        """ Class for normalizing include structure for a single file of source code.

            TODO: Generalize git_root to project_root

        :param git_root:
        :param original_name: Full path to input file (abs. or relative to git_root).
        :param include_sequence:
        :param include_apply: Callback invoked on each include discovered. TODO: Document interface.
        """
        comment_parser.CommentParser.__init__(self)
        self.git_root = git_root  # Root folder of the managing git repository
        self.original_name = original_name  # Filename of the original input file
        self.abs_includes = set()
        self.rel_includes = set()
        self.sys_includes = set()
        self.icomments = collections.defaultdict(str)  # Mapping include files -> corr. comment_buffer in source code
        self.mother = None  # The header corresponding to this source file (ie. C file)
        self.line_length = 120

        # Variables realted to parsing
        self._buffer = _IncludeBuffer()
        self._line_with_code = False

        # Ordering of the include
        if not include_sequence:
            include_sequence = IncludeSequencer()
        self._include_sequence = include_sequence

        # Applier called ofr each include
        if not include_apply:
            def include_apply(include, absolute=True):
                return absolute, include
        self._include_apply = include_apply

    def _store_buffer(self):
        """ Save previously buffered data (comments, include path etc.) to the internal cache
        """
        assert self._buffer.include  # Otherwise no include statement got buffered

        if not self.num_cached_includes():
            # Directly print newlines here that precede a new block and otherwise would get lost
            matches = re.match('^(?P<preceding>\n*)', self._buffer.original)  # TODO: Only in the beginning
            if matches:
                print(matches.group('preceding'), end='')

        include = self._buffer.include
        if '/' in include:
            dest = self.abs_includes
        elif self._buffer.relative:
            dest = self.rel_includes
        else:
            dest = self.sys_includes
        dest.add(include)

        # Save description, ie. comments, if non-trivial
        description = self._buffer.description()
        if description:
            self.icomments[include] += ' ' + description

    def _prepare_include(self, include, absolute=True):
        """ Applier called on each discovered include once.

            The purpose of this standalone method is to allow / specify kwd-based calls.
        """
        assert isinstance(absolute, bool)
        return self._include_apply(include=include, absolute=absolute)

    def handle_code(self, code):
        matches = re.match('\s*#include\s*(?P<token>["<])(?P<incl>[^">]+)[">]\s*$', code)
        if matches:
            self._buffer.include = matches.group('incl')
            self._buffer.relative = (matches.group('token') == '"')
        else:
            self._buffer.original += code
            if code.strip():
                self._line_with_code = True

    def handle_old_comment(self, comment):
        self._buffer.add_comment(True, comment)

    def handle_new_comment(self, comment):
        self._buffer.add_comment(False, comment)

    def handle_end_of_line(self):
        if self._buffer.include:
            self._store_buffer()
            self._buffer.clear()
        else:
            in_empty_line = self._buffer.original and self._buffer.original[-1] == '\n'
            self._buffer.original += '\n'
            if in_empty_line or self._line_with_code:
                self.empty_cache()
        self._line_with_code = False

    def empty_cache(self):
        # Print cached data about include
        self._print_cached()
        self._reset()
        # Print remaining buffered code with a newline
        if self._buffer.original:
            assert self._buffer.original[-1] == '\n'
            print(self._buffer.original, end='')
        self._buffer.clear()

    def num_cached_includes(self):
        return len(self.abs_includes) + len(self.rel_includes) + len(self.sys_includes) + (1 if self.mother else 0)

    def _prepare_includes(self):
        verified_abs, verified_rel = [], []
        # Cope with absolute includes
        for i in self.abs_includes:
            absolute, p = self._prepare_include(include=i, absolute=True)
            if not p:
                logging.warning('Failed preparing %s. Removing it!' % i)
            elif absolute:  # p is indeed an absolute include
                verified_abs.append(p)
            else:  # p is in fact a relative include
                verified_rel.append(p)
            if p:
                self.icomments[p] = self.icomments[i]

        # Cope with relative includes
        # TODO: Do we really need this double copy pasta
        original_path, original_name = os.path.split(self.original_name)
        mother_re = re.compile('^' + original_name.split('.', 1)[0] + '\.[Hh]$') # TODO: Doesn't work with multiple '.' in filenames
        for i in self.rel_includes:
            abs, p = self._prepare_include(include=i, absolute=False)
            if not p or os.path.split(p)[0]:  # TODO: Second condition ?
                logging.warning('Failed to prepare %s. Removing it!' % i)
            elif not abs:
                p = os.path.split(p)[1]
                if mother_re.match(p):
                    self.mother = p
                    logging.info('Found mother %s' % self.mother)
                else:
                    verified_rel.append(p)
            elif abs:
                verified_abs.append(p)
            if p:
                self.icomments[p] = self.icomments[i]

        self.abs_includes = sorted(set(verified_abs), key=lambda x: self._include_sequence.sort_id(x) + x)
        self.rel_includes = sorted(set(verified_rel))
        self.sys_includes = sorted(self.sys_includes)

    def _include_text(self, ifile, pre='<', post='>'):
        include_stub = '#include ' + pre + str(ifile) + post
        comment = self.icomments[ifile].strip()

        # Compress whitespace, remove newline chars
        comment_text = re.sub('[\n\t ]+', ' ', comment)

        oneliner = include_stub + ((' // ' + comment_text) if comment_text else '')
        if len(oneliner) <= self.line_length:
            # Short comment that may be placed in a single line
            return oneliner + '\n'
        else:
            # Comment too long, split it apart
            lines = [('// %s' % line) for line in textwrap.wrap(comment_text, width=(self.line_length - len('// ')))]
            lines.append(include_stub)
            return '\n'.join(lines) + '\n'

    def _print_cached(self):
        logging.debug('Printing cache...')
        self._prepare_includes()
        prev_group_id = None
        data_to_print = []
        if self.mother:
            data_to_print.append(([self.mother], '"', '"'))
        data_to_print.append((self.sys_includes, '<', '>'))
        data_to_print.append((self.abs_includes, '<', '>'))
        data_to_print.append((self.rel_includes, '"', '"'))

        group_texts = []
        for data, pre, post in data_to_print:
            group_texts.append('')
            for include in data:
                new_group_id = self._include_sequence.group_id(include)
                if prev_group_id != new_group_id:
                    group_texts.append('')
                group_texts[-1] += self._include_text(include, pre, post)
                prev_group_id = new_group_id
        print('\n'.join([g for g in group_texts if g]), end='')

    def _reset(self):
        logging.debug('Resetting cached data..')
        self.sys_includes = set()
        self.abs_includes = set()
        self.rel_includes = set()
        self.mother = None
        self.icomments.clear()


def arrange_includes(src_file, git_root=None):
    if not git_root:
        git_root = subprocess.check_output('git rev-parse --show-toplevel'.split()).strip()
    arranger = IncludeArranger(git_root, src_file)
    # with fileinput.FileInput(sys.argv[1:], inplace=True, backup='.nwb')
    with open(src_file, 'r') as code:
        for line in code.readlines():
            arranger.feed(line)
    arranger.empty_cache()
