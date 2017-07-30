#!/usr/bin/env python3

from unittest.mock import MagicMock

import pytest

import tidy_includes
import comment_parser


class TestIncludeOrdering:
    @pytest.fixture
    def test_sequencer(self):
        seq = tidy_includes.IncludeSequencer()
        root = seq.add_root()
        root.insert('componentA', descendable=True)
        root.insert('componentB')
        root['componentA'].insert('subA0', descendable=True)
        root['componentA']['subA0'].insert('subA0a', descendable=False)
        root['componentA']['subA0'].insert('subA0b', descendable=True)  # Not clever
        root['componentA'].insert('subA1')
        root['componentA']['subA1'].insert('subA1a', descendable=True)
        return seq

    def test_group_id(self, test_sequencer):
        base_length = len(test_sequencer.invalid_id)
        assert 1 * base_length == len(test_sequencer.group_id('iostream'))
        assert 1 * base_length == len(test_sequencer.group_id('dep0.h'))
        assert 1 * base_length == len(test_sequencer.group_id('componentB/huhu/blah/moin.H')) # unknown
        assert 2 * base_length == len(test_sequencer.group_id('componentA/subA1/hans.H'))
        assert 2 * base_length == len(test_sequencer.group_id('componentA/subA1/subA1a/hans.H'))
        assert 3 * base_length == len(test_sequencer.group_id('componentA/subA0/hans.H'))
        assert 3 * base_length == len(test_sequencer.group_id('componentA/subA0/subA0a/hans.H'))
        assert 4 * base_length == len(test_sequencer.group_id('componentA/subA0/subA0b/hans.H'))

    def test_sort_id(self, test_sequencer):
        base_length = len(test_sequencer.invalid_id)
        id_stl = test_sequencer.sort_id('iostream')
        id_dep0 = test_sequencer.sort_id('dep0.h')
        idB  = test_sequencer.sort_id('componentB/huhu/blah/moin.H')
        id_subA00 = test_sequencer.sort_id('componentA/subA0/subA0a/hans.H')
        id_subA01 = test_sequencer.sort_id('componentA/subA1/subA1a/hans.H')

        expected = [id_subA00, id_subA01, idB, id_stl, id_dep0]
        assert sorted(expected) == expected

########################################################################################################################


class CommentParserMock(comment_parser.CommentParser):
    def __init__(self):
        comment_parser.CommentParser.__init__(self)
        self.code = []
        self.new_comments = []
        self.old_comments = []
        self.num_newlines = 0

    def clear(self):
        self.code.clear()
        self.new_comments.clear()
        self.old_comments.clear()
        self.num_newlines = 0

    def handle_code(self, code):
        self.code.append(code)

    def handle_old_comment(self, comment):
        self.old_comments.append(comment)

    def handle_new_comment(self, comment):
        self.new_comments.append(comment)

    def handle_end_of_line(self):
        self.num_newlines += 1


class TestCommentParsing:

    @pytest.fixture
    def comment_parser(self):
        return CommentParserMock()

    def test_comment_basics(self, comment_parser):
        comment_parser.feed('#include <huhu>')
        assert ['#include <huhu>'] == comment_parser.code
        assert not comment_parser.new_comments
        assert not comment_parser.old_comments
        assert comment_parser.num_newlines == 1

    def test_empty_comment(self, comment_parser):
        comment_parser.feed('')
        assert not comment_parser.code
        assert not comment_parser.new_comments
        assert not comment_parser.old_comments
        assert comment_parser.num_newlines == 1
        comment_parser.clear()

        comment_parser.feed('\n')
        assert not comment_parser.code
        assert not comment_parser.new_comments
        assert not comment_parser.old_comments
        assert comment_parser.num_newlines == 1
        comment_parser.clear()

        comment_parser.feed('//')
        assert not comment_parser.code
        assert [''] == comment_parser.new_comments
        assert not comment_parser.old_comments
        assert comment_parser.num_newlines == 1
        comment_parser.clear()

        comment_parser.feed('/**/')
        assert not comment_parser.code
        assert not comment_parser.new_comments
        assert [''] == comment_parser.old_comments
        assert comment_parser.num_newlines == 1

    def test_pure_new_style_comment(self, comment_parser):
        comment_parser.feed('// cmt')
        assert not comment_parser.code
        assert [' cmt'] == comment_parser.new_comments
        assert not comment_parser.old_comments
        assert comment_parser.num_newlines == 1

    def test_new_style_comment(self, comment_parser):
        comment_parser.feed('abc // cmt')
        assert ['abc '] == comment_parser.code
        assert [' cmt'] == comment_parser.new_comments
        assert not comment_parser.old_comments
        assert comment_parser.num_newlines == 1

    def test_pure_old_style_comment(self, comment_parser):
        comment_parser.feed('/* cmt */')
        assert not comment_parser.code
        assert not comment_parser.new_comments
        assert [' cmt '] == comment_parser.old_comments
        assert comment_parser.num_newlines == 1

    def test_old_style_comment(self, comment_parser):
        comment_parser.feed('abc /* cmt */')
        assert ['abc '] == comment_parser.code
        assert not comment_parser.new_comments
        assert [' cmt '] == comment_parser.old_comments
        assert comment_parser.num_newlines == 1


    def test_multiline_code(self, comment_parser):
        comment_parser.feed('abc /* cmt0 */')
        comment_parser.feed('def /* cmt1 */')
        assert ['abc ', 'def '] == comment_parser.code
        assert not comment_parser.new_comments
        assert [' cmt0 ', ' cmt1 '] == comment_parser.old_comments
        assert comment_parser.num_newlines == 2


    def test_multiline_comment(self, comment_parser):
        comment_parser.feed('abc /* cmt0')
        assert ['abc '] == comment_parser.code
        assert not comment_parser.new_comments
        assert not comment_parser.old_comments
        assert comment_parser.num_newlines == 0

        comment_parser.feed('cmt1 */ def')
        assert ['abc ', ' def'] == comment_parser.code
        assert not comment_parser.new_comments
        assert [' cmt0\ncmt1 '] == comment_parser.old_comments
        assert comment_parser.num_newlines == 1


    def test_nested_comments(self, comment_parser):
        comment_parser.feed('abc /* // cmt */')
        assert ['abc '] == comment_parser.code
        assert not comment_parser.new_comments
        assert [' // cmt '] == comment_parser.old_comments
        assert comment_parser.num_newlines == 1

        comment_parser.clear()
        comment_parser.feed('abc // /* cmt */')
        assert ['abc '] == comment_parser.code
        assert [' /* cmt */'] == comment_parser.new_comments
        assert not comment_parser.old_comments
        assert comment_parser.num_newlines == 1


########################################################################################################################


class TestIncludeArranging:

    @pytest.fixture
    def include_arranger(self):
        return tidy_includes.IncludeArranger('/home/john/work/', 'prjA/mom.C')

    def _assert_printed(self, capfd, subC0out='', subC0err=''):
        assert capfd.readouterr() == (subC0out, subC0err)

    def _feed_code(self, arranger, code):
        for line in code.splitlines():
            arranger.feed(line)
        arranger.empty_cache()

    def perform_test(self, arranger, capfd, code, expected):
        self._feed_code(arranger, code)
        self._assert_printed(capfd, expected)

    def test_arranging_nothing(self, capfd, include_arranger):
        code = '''
first line // blub
/* comment */

something
'''
        self.perform_test(include_arranger, capfd, code, code)

    def test_arrange_defaults(self, capfd, include_arranger):
        code = '''
#include <iostream>  // for subC0out

// This is a longer comment
// spreading over multiple
// lines
#include <componentA/real_header.H>

/*!Some other stuff*/
#include "array.H"
'''
        expected = '''
#include <iostream> // for subC0out

#include <componentA/real_header.H> // This is a longer comment spreading over multiple lines

#include "array.H" // !Some other stuff
'''
        self.perform_test(include_arranger, capfd, code, expected)

    def test_comment_concatenation(self, capfd, include_arranger):
        code = '''
/* This is the beginning */
#include <iostream>    //  and the end...

// A
// B
#include <componentA/real_header.H> // C

/* Some other stuff*/
/*!Some more stuff */
#include "array.H" //yo!

#include <iostream>  //finally!
'''
        expected = '''
#include <iostream> // This is the beginning and the end... finally!

#include <componentA/real_header.H> // A B C

#include "array.H" // Some other stuff !Some more stuff yo!
'''
        self.perform_test(include_arranger, capfd, code, expected)

    def test_comment_interrupt(self, capfd, include_arranger):
        code = '''
/* A fake start */

#include <iostream> // comment

// Fake it again

#include <componentA/real_header.H> // comment

/*comment*/
/**/
#include "real_array.H" //yo!

/*comment
*/
#include "real_array2.H"
'''

        expected = '''
/* A fake start */

#include <iostream> // comment

// Fake it again

#include <componentA/real_header.H> // comment

#include "real_array.H" // comment yo!
#include "real_array2.H" // comment
'''
        self.perform_test(include_arranger, capfd, code, expected)

    def test_code_interrupt(self, capfd, include_arranger):
        code = '''
#include <iostream> // comment

some code line

#include <iostream> // more
'''
        self.perform_test(include_arranger, capfd, code, code)

    def test_ugly(self, capfd, include_arranger):
        code = '''
/* A start */
#include <iostream> /* and some more,
*/ // what now?
'''

        expected = '''
#include <iostream> // A start and some more, what now?
'''
        self.perform_test(include_arranger, capfd, code, expected)

    def test_include_formatting(self, capfd, include_arranger):
        code = '''
#include <iostream>
#include <real_file.H>
#include <where/I/Am/at/real_more.H>
#include "real_even.H"
#include "string"
'''
        expected = '''
'''
        self.perform_test(include_arranger, capfd, code, expected)

    def test_block_arrangement(self, capfd, include_arranger):
        code = '''
#include <iostream>
#include <dep0>
#include <componentC/subC0/l0.H>
#include <componentA/subA0/subA0a/base.H>
#include <componentC/subC0/l1.H>
#include <componentA/subA0/subA0b/l2.H>
'''

        expected = '''
#include <iostream>

#include <dep0>

#include <componentC/subC0/l1.H>
#include <componentC/subC0/l0.H>

#include <componentA/subA0/subA0b/l2.H>
#include <componentA/subA0/subA0a/base.H>
'''
        self.perform_test(include_arranger, capfd, code, expected)

    def test_long_line_formatting(self, capfd, include_arranger):
        code = '''
// This is a very very very very very very very very very very very very very very very very very very long comment. . .
#include <componentA/some.H>
// This is a very very very very very very very very very very very very very very very very very very long comment. . .
#include <componentA/thing.H> // It even has to be split into several lines
#include <componentA/uber.H> // Maximally long inline commmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmment
#include <componentA/very_very_very_very_very_very_very_very_very_very_very_very_very_very_very_very_very_very_very_long.H>
'''
        expected = '''
// This is a very very very very very very very very very very very very very very very very very very long comment. . .
#include <componentA/some.H>
// This is a very very very very very very very very very very very very very very very very very very long comment. . .
// It even has to be split into several lines
#include <componentA/thing.H>
#include <componentA/uber.H> // Maximally long inline commmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmment
#include <componentA/very_very_very_very_very_very_very_very_very_very_very_very_very_very_very_very_very_very_very_long.H>
'''
        self.perform_test(include_arranger, capfd, code, expected)

    def test_line_limit_obeying(self, capfd, include_arranger):
        include_arranger.line_length = 79
        code = '''
// This is a very very very very very very very very very very long comment . .
#include <componentA/some.H>
// This is a very very very very very very very very very very long comment . .
#include <componentA/thing.H> // It even has to be split into several lines
#include <componentA/uber.H> // Maximally long inline commmmmmmmmmmmmmmmmmmmment
#include <componentA/very_very_very_very_very_very_very_very_very_very_very_long.H>
'''
        expected = '''
// This is a very very very very very very very very very very long comment . .
#include <componentA/some.H>
// This is a very very very very very very very very very very long comment . .
// It even has to be split into several lines
#include <componentA/thing.H>
#include <componentA/uber.H> // Maximally long inline commmmmmmmmmmmmmmmmmmmment
#include <componentA/very_very_very_very_very_very_very_very_very_very_very_long.H>
'''
        self.perform_test(include_arranger, capfd, code, expected)



# TODO: Test what happens on non-empty last line
# TODO: Test with include guards, multiple include sections and actual body code
# TODO: Comments output stripped on both sides
# TODO: Test mother stuff
