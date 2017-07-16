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
