#!/usr/bin/env python3
# THIS FILE IS PART OF THE CYLC SUITE ENGINE.
# Copyright (C) 2008-2019 NIWA & British Crown (Met Office) & Contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""The cylc terminal user interface (Tui)."""

TUI = """
                           _,@@@@@@.
                         <=@@@, `@@@@@.
                            `-@@@@@@@@@@@'
                               :@@@@@@@@@@.
                              (.@@@@@@@@@@@
                             ( '@@@@@@@@@@@@.
                            ;.@@@@@@@@@@@@@@@
                          '@@@@@@@@@@@@@@@@@@,
                        ,@@@@@@@@@@@@@@@@@@@@'
                      :.@@@@@@@@@@@@@@@@@@@@@.
                    .@@@@@@@@@@@@@@@@@@@@@@@@.
                  '@@@@@@@@@@@@@@@@@@@@@@@@@.
                ;@@@@@@@@@@@@@@@@@@@@@@@@@@@
               .@@@@@@@@@@@@@@@@@@@@@@@@@@.
              .@@@@@@@@@@@@@@@@@@@@@@@@@@,
             .@@@@@@@@@@@@@@@@@@@@@@@@@'
            .@@@@@@@@@@@@@@@@@@@@@@@@'     ,
          :@@@@@@@@@@@@@@@@@@@@@..''';,,,;::-
         '@@@@@@@@@@@@@@@@@@@.        `.   `
        .@@@@@@.: ,.@@@@@@@.            `
      :@@@@@@@,         ;.@,
     '@@@@@@.              `@'
    .@@@@@@;                ;-,
  ;@@@@@@.                   ...,
,,; ,;;                      ; ; ;
"""

from cylc.flow.task_state import (
    TASK_STATUSES_ORDERED,
    TASK_STATUS_DISPLAY_ORDER,
    TASK_STATUS_RUNAHEAD,
    TASK_STATUS_WAITING,
    TASK_STATUS_QUEUED,
    TASK_STATUS_EXPIRED,
    TASK_STATUS_READY,
    TASK_STATUS_SUBMIT_FAILED,
    TASK_STATUS_SUBMIT_RETRYING,
    TASK_STATUS_SUBMITTED,
    TASK_STATUS_RETRYING,
    TASK_STATUS_RUNNING,
    TASK_STATUS_FAILED,
    TASK_STATUS_SUCCEEDED
)

# default foreground and background colours
# NOTE: set to default to allow user defined terminal theming
FORE = 'default'
BACK = 'default'

# suite state colour
SUITE_COLOURS = {
    'running': ('light blue', BACK),
    'held': ('brown', BACK),
    'stopping': ('light magenta', BACK),
    'error': ('light red', BACK, 'bold')
}

# unicode task icons
TASK_ICONS = {
    f'{TASK_STATUS_WAITING}': '\u25cb',

    # TODO: remove with https://github.com/cylc/cylc-admin/pull/47
    f'{TASK_STATUS_READY}': '\u25cb',
    f'{TASK_STATUS_QUEUED}': '\u25cb',
    f'{TASK_STATUS_RETRYING}': '\u25cb',
    f'{TASK_STATUS_SUBMIT_RETRYING}': '\u25cb',
    # TODO: remove with https://github.com/cylc/cylc-admin/pull/47

    f'{TASK_STATUS_SUBMITTED}': '\u2299',
    f'{TASK_STATUS_RUNNING}': '\u2299',
    f'{TASK_STATUS_RUNNING}:0': '\u2299',
    f'{TASK_STATUS_RUNNING}:25': '\u25D4',
    f'{TASK_STATUS_RUNNING}:50': '\u25D1',
    f'{TASK_STATUS_RUNNING}:75': '\u25D5',
    f'{TASK_STATUS_SUCCEEDED}': '\u25CF',
    f'{TASK_STATUS_EXPIRED}': '\u25CF',
    f'{TASK_STATUS_SUBMIT_FAILED}': '\u2297',
    f'{TASK_STATUS_FAILED}': '\u2297'
}

# unicode modifiers for special task states
TASK_MODIFIERS = {
    'held': '\u030E'
}

# unicode job icon
JOB_ICON = '\u25A0'

# job colour coding
JOB_COLOURS = {
    'submitted': 'dark cyan',
    'running': 'light blue',
    'succeeded': 'dark green',
    'failed': 'light red',
    'submit-failed': 'light magenta',

    # TODO: update with https://github.com/cylc/cylc-admin/pull/47
    'ready': 'brown'
    # TODO: update with https://github.com/cylc/cylc-admin/pull/47
}


class Bindings:

    def __init__(self):
        self.bindings = []
        self.groups = {}

    def bind(self, keys, group, desc, callback):
        if group not in self.groups:
            raise ValueError(f'Group {group} not registered.')
        binding = {
            'keys': keys,
            'group': group,
            'desc': desc,
            'callback': callback
        }
        self.bindings.append(binding)
        self.groups[group]['bindings'].append(binding)

    def add_group(self, group, desc):
        self.groups[group] = {
            'name': group,
            'desc': desc,
            'bindings': []
        }

    def __iter__(self):
        return iter(self.bindings)

    def list_groups(self):
        for name, group in self.groups.items():
            yield (
                group,
                [
                    binding
                    for binding in self.bindings
                    if binding['group'] == name
                ]
            )


BINDINGS = Bindings()
