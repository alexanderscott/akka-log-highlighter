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

# unpack the current terminal width/height
data = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, '1234')
HEIGHT, WIDTH = struct.unpack('hh', data)
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

# Modify these parameters to suit your needs
TAGTYPE_WIDTH = 3
ACTOR_WIDTH = 30
DISPATCHER_WIDTH = 4  # 8 or -1
HEADER_SIZE = TAGTYPE_WIDTH + 1 + ACTOR_WIDTH + 1 + DISPATCHER_WIDTH + 1

LAST_USED = [RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE]

# Add fixed colors for actors here
KNOWN_ACTORS = {}

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

TAGTYPES = {
    "DEBUG": "%s%s%s " % (format(fg=BLACK, bg=BLUE), "D".center(TAGTYPE_WIDTH), format(reset=True)),
    "INFO": "%s%s%s " % (format(fg=BLACK, bg=GREEN), "I".center(TAGTYPE_WIDTH), format(reset=True)),
    "WARNING": "%s%s%s " % (format(fg=BLACK, bg=YELLOW), "W".center(TAGTYPE_WIDTH), format(reset=True)),
    "ERROR": "%s%s%s " % (format(fg=BLACK, bg=RED), "E".center(TAGTYPE_WIDTH), format(reset=True)),
}

def indent_wrap(message, indent=0, width=80):
    wrap_area = width - indent
    messagebuf = StringIO.StringIO()
    current = 0
    while current < len(message):
        next = min(current + wrap_area, len(message))
        messagebuf.write(message[current:next])
        if next < len(message):
            messagebuf.write("\n%s" % (" " * indent))
        current = next
    return messagebuf.getvalue()


def allocate_color(actor):
    # this will allocate a unique format for the given actor
    # since we dont have very many colors, we always keep track of the LRU
    if not actor in KNOWN_ACTORS:
        KNOWN_ACTORS[actor] = LAST_USED[0]
    color = KNOWN_ACTORS[actor]
    LAST_USED.remove(color)
    LAST_USED.append(color)
    return color

def filter_actor_name(name):
    return name.replace("akka://","").replace("akka.tcp://","")

reactor = re.compile("\[(\w+)\] \[(\d{2}/\d{2}/\d{4}) (\d{1,2}:\d{2}:\d{2}\.\d{3})\] \[(.*)\] \[(.*)\] (.*)$")

while True:
    try:
        line = sys.stdin.readline()
    except KeyboardInterrupt:
        break

    match = reactor.match(line)
    if not match is None:
        tagtype, date, timestamp, dispatcher, actor, message = match.groups()

        linebuf = StringIO.StringIO()

        linebuf.write("%s %s %s" % (
            format(fg=BLACK, bg=BLUE, bright=True), timestamp, format(reset=True)))

        # center process info
        if DISPATCHER_WIDTH > 0:
            dispatcher = dispatcher.split("-")[-1]
            dispatcher = dispatcher.strip().center(DISPATCHER_WIDTH)
            linebuf.write("%s%s%s" % (
                format(fg=BLACK, bg=BLACK, bright=True), dispatcher, format(reset=True)))

        # right-align actor title and allocate color if needed
        actor = filter_actor_name(actor.strip())
        color = allocate_color(actor)
        actor = actor[-ACTOR_WIDTH:].rjust(ACTOR_WIDTH)
        linebuf.write("%s%s %s" % (
            format(fg=color, bg=BLUE, bright=False), actor, format(reset=True)))

        # write out tagtype colored edge
        if not tagtype in TAGTYPES:
            break
        linebuf.write(TAGTYPES[tagtype])

        # insert line wrapping as needed
        message = indent_wrap(message, HEADER_SIZE, WIDTH)

        linebuf.write(message)
        line = linebuf.getvalue()

    print line
    if len(line) == 0:
        break
