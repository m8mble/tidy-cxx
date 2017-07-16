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

