#!/usr/bin/python

'''
    Copyright 2009, The Android Open Source Project

    Licensed under the Apache License, Version 2.0 (the "License"); 
    you may not use this file except in compliance with the License. 
    You may obtain a copy of the License at 

        http://www.apache.org/licenses/LICENSE-2.0 

    Unless required by applicable law or agreed to in writing, software 
    distributed under the License is distributed on an "AS IS" BASIS, 
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
    See the License for the specific language governing permissions and 
    limitations under the License.

    ----

    Akka log highlighter by partycoder (https://github.com/partycoder)
    Based on the logcat highlighter by Jeff Sharkey (http://jsharkey.org/)
    Piping detection and popen() added by other Android team
'''

import os
import sys
import re
import StringIO
import fcntl
import termios
import struct

import pprint

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

# modify these parameters to suit your needs
TIMESTAMP_WIDTH = 14
LOGLEVEL_WIDTH = 3
ACTOR_WIDTH = 30
DISPATCHER_WIDTH = 4  # 8 or -1
HEADER_SIZE = TIMESTAMP_WIDTH + LOGLEVEL_WIDTH + DISPATCHER_WIDTH + ACTOR_WIDTH

def format(fg=None, bg=None, bright=False, bold=False, dim=False, reset=False):
    # manually derived from http://en.wikipedia.org/wiki/ANSI_escape_code#Codes
    codes = []
    if reset:
        codes.append("0")
    else:
        if not fg is None:
            codes.append("3%d" % (fg))
        if not bg is None:
            if not bright:
                codes.append("4%d" % (bg))
            else:
                codes.append("10%d" % (bg))
        if bold:
            codes.append("1")
        elif dim:
            codes.append("2")
        else:
            codes.append("22")
    return "\033[%sm" % (";".join(codes))

resetChar = format(reset=True)
blackOverBlue = format(fg=BLACK, bg=BLUE, bright=True)
blackOverBlack = format(fg=BLACK, bg=BLACK, bright=True)
dimBlack = format(bg=BLACK, dim=True)

LOGLEVELS = {
    "NONE": "%s%s%s " % (format(fg=BLACK, bg=CYAN), "-".center(LOGLEVEL_WIDTH), resetChar),
    "DEBUG": "%s%s%s " % (format(fg=BLACK, bg=BLUE), "D".center(LOGLEVEL_WIDTH), resetChar),
    "INFO": "%s%s%s " % (format(fg=BLACK, bg=GREEN), "I".center(LOGLEVEL_WIDTH), resetChar),
    "WARNING": "%s%s%s " % (format(fg=BLACK, bg=YELLOW), "W".center(LOGLEVEL_WIDTH), resetChar),
    "ERROR": "%s%s%s " % (format(fg=BLACK, bg=RED), "E".center(LOGLEVEL_WIDTH), resetChar),
}

# add fixed colors for actors here
LAST_USED = [
    format(fg=RED, dim=False), \
    format(fg=GREEN, dim=False), \
    format(fg=YELLOW, dim=False), \
    format(fg=BLUE, dim=False), \
    format(fg=MAGENTA, dim=False), \
    format(fg=CYAN, dim=False), \
    format(fg=WHITE, dim=False)]
KNOWN_ACTORS = {}
KNOWN_ACTORS_FORMAT = {}

def allocate_color(actor):
    if not actor in KNOWN_ACTORS:
        KNOWN_ACTORS[actor] = LAST_USED[0]

    color = KNOWN_ACTORS[actor]
    LAST_USED.remove(color)
    LAST_USED.append(color)
    return color

def filter_actor_name(name):
    return name.replace("akka://", "").replace("akka.tcp://", "")


def format_actor_name(name):
    return filter_actor_name(name)[-ACTOR_WIDTH:].rjust(ACTOR_WIDTH)

header_re = re.compile("\[(\w+)\] \[(\d{2}/\d{2}/\d{4}) (\d{1,2}:\d{2}:\d{2}\.\d{3})\] \[([^\s]+)\] \[([^\s]+)\] (.*)$")
dead_letter_re = re.compile("Message \[([^\s]+)\] from Actor\[([^\s]+)\] to Actor\[([^\s]+)\] was not delivered")
stack_trace_re = re.compile("(\s+at )?([\w|\.|\$]+)\(([\w|\.]+.[java|scala]):(\d+)\)$")

nonAkkaHeader = ''.join([ \
    blackOverBlue, "--:--:--.---", resetChar, \
    blackOverBlack, " " * DISPATCHER_WIDTH, resetChar, \
    dimBlack, " " * ACTOR_WIDTH, resetChar, \
    LOGLEVELS["NONE"]])

def format_line(buffer, line):
    header_match = header_re.match(line)
    if header_match is None:
        # non-akka header
        buffer.write(nonAkkaHeader)

        # test for stack trace
        stack_trace_match = stack_trace_re.match(line)
        if not stack_trace_match is None:
            at_sign, scope, filename, line_no = stack_trace_match.groups()
            scope = scope.replace("$$", " ~~ ").replace("$", " ~ ")
            scope_header = "%s : %s" % (filename.rjust(30), line_no.rjust(6))
            buffer.write("%s @ %s" % (scope_header, scope))
        else:
            buffer.write(line)

        return

    loglevel, date, timestamp, dispatcher, actor, rest = header_match.groups()
    message = ""

    if not loglevel in LOGLEVELS:
        # invalid loglevel line
        buffer.write("- ignored line -")
        return

    dead_letter_match = dead_letter_re.match(rest)
    if dead_letter_match is None:
        # regular message
        message = rest
    else:
        # dead letter message
        msg, actor1, actor2 = dead_letter_match.groups()
        message = "Dead letter: [%s -> %s] %s" % (filter_actor_name(actor1), filter_actor_name(actor2), msg)

    dispatcher = dispatcher.split("-")[-1].rjust(DISPATCHER_WIDTH, "0")
    actor = format_actor_name(actor)

    # timestamp
    buffer.write( \
        ''.join([ \
            blackOverBlue, timestamp, resetChar, \
            blackOverBlack, dispatcher, resetChar, \
            allocate_color(actor), actor, resetChar, \
            LOGLEVELS[loglevel], message]))

try:
    output_buffer = StringIO.StringIO()
    for line in sys.stdin:
        format_line(output_buffer, line[:-1])
        print output_buffer.getvalue()
        output_buffer.seek(0)
        output_buffer.truncate()

except KeyboardInterrupt:
    sys.stdout.flush()
    pass
