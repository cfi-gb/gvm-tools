# -*- coding: utf-8 -*-
# Copyright (C) 2018 Greenbone Networks GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later
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

import argparse
import code
import configparser
import logging
import os
import sys

from gmp import get_version
from gmp.connections import (SSHConnection,
                             TLSConnection,
                             UnixSocketConnection,
                             DEFAULT_UNIX_SOCKET_PATH,
                             DEFAULT_TIMEOUT,
                             DEFAULT_GVM_PORT)
from gmp.protocols.latest import Gmp
from gmp.transforms import EtreeCheckCommandTransform


__version__ = get_version()

logger = logging.getLogger(__name__)

HELP_TEXT = """
    gvm-pyshell {version} (C) 2017 Greenbone Networks GmbH

    This program is a command line tool to access services
    via Greenbone Management Protocol (GMP) and
    Open Scanner Protocol (OSP).

    It is possible to start a shell like the python interactive
    mode where you could type things like "tasks = gmp.get_task".

    At the moment only these commands are support in the interactive shell:

    Example:
        gmp.authenticate('admin', 'admin')

        tasks = gmp.get_tasks()

        list = tasks.xpath('task')

        taskid = list[0].attrib

    Good introduction in working with XPath is well described here:
    https://www.w3schools.com/xml/xpath_syntax.asp

    To get out of the shell enter:
        Ctrl + D on Linux  or
        Ctrl + Z on Windows

    Further Information about the GMP Protocol can be found at:
    http://docs.greenbone.net/index.html#api_documentation
    Note: "GMP" was formerly known as "OMP".

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
    """.format(version=__version__)


class Help(object):
    """Help class to overwrite the help function from python itself.
    """

    def __call__(self):
        return print(HELP_TEXT)

    def __repr__(self):
        # do pwd command
        return HELP_TEXT


def main():
    parser = argparse.ArgumentParser(
        prog='gvm-pyshell',
        description=HELP_TEXT,
        formatter_class=argparse.RawTextHelpFormatter,
        add_help=False,
        epilog="""
usage: gvm-pyshell [-h] [--version] [connection_type] ...
   or: gvm-pyshell connection_type --help""")
    subparsers = parser.add_subparsers(metavar='[connection_type]')
    subparsers.required = True
    subparsers.dest = 'connection_type'

    parser.add_argument(
        '-h', '--help', action='help',
        help='Show this help message and exit.')

    parent_parser = argparse.ArgumentParser(add_help=False)

    parent_parser.add_argument(
        '-c', '--config', nargs='?', const='~/.config/gvm-tools.conf',
        help='Configuration file path. Default: ~/.config/gvm-tools.conf')
    args_before, remaining_args = parent_parser.parse_known_args()

    defaults = {
        'gmp_username': '',
        'gmp_password': ''
    }

    # Retrieve data from config file
    if args_before.config:
        try:
            config = configparser.SafeConfigParser()
            path = os.path.expanduser(args_before.config)
            config.read(path)
            defaults = dict(config.items('Auth'))
        except Exception as e: # pylint: disable=broad-except
            print(str(e), file=sys.stderr)

    parent_parser.set_defaults(**defaults)

    parent_parser.add_argument(
        '--timeout', required=False, default=DEFAULT_TIMEOUT, type=int,
        help='Wait <seconds> for response or if value -1, then wait '
             'continuously. Default: %(default)s')
    parent_parser.add_argument(
        '--log', nargs='?', dest='loglevel', const='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Activates logging. Default level: INFO.')
    parent_parser.add_argument(
        '-i', '--interactive', action='store_true', default=False,
        help='Start an interactive Python shell.')
    parent_parser.add_argument('--gmp-username', help='GMP username.')
    parent_parser.add_argument('--gmp-password', help='GMP password.')
    parent_parser.add_argument(
        'script', nargs='*',
        help='Preload gmp script. Example: myscript.gmp.')

    parser_ssh = subparsers.add_parser(
        'ssh', help='Use SSH connection for gmp service.',
        parents=[parent_parser])
    parser_ssh.add_argument('--hostname', required=True,
                            help='Hostname or IP-Address.')
    parser_ssh.add_argument('--port', required=False,
                            default=22, help='Port. Default: %(default)s.')
    parser_ssh.add_argument('--ssh-user', default='gmp',
                            help='SSH Username. Default: %(default)s.')

    parser_tls = subparsers.add_parser(
        'tls', help='Use TLS secured connection for gmp service.',
        parents=[parent_parser])
    parser_tls.add_argument('--hostname', required=True,
                            help='Hostname or IP-Address.')
    parser_tls.add_argument('--port', required=False,
                            default=DEFAULT_GVM_PORT,
                            help='Port. Default: %(default)s.')
    parser_tls.add_argument('--certfile', required=False, default=None,
                            help='Path to the client certificate file.')
    parser_tls.add_argument('--keyfile', required=False, default=None,
                            help='Path to key certificate file.')
    parser_tls.add_argument('--cafile', required=False, default=None,
                            help='Path to CA certificate file.')
    parser_tls.add_argument('--no-credentials', required=False, default=False,
                            help='Use only certificates.')

    parser_socket = subparsers.add_parser(
        'socket', help='Use UNIX-Socket connection for gmp service.',
        parents=[parent_parser])
    parser_socket.add_argument(
        '--sockpath', nargs='?',
        help='Depreacted. Use --socketpath instead')
    parser_socket.add_argument(
        '--socketpath', nargs='?', default=DEFAULT_UNIX_SOCKET_PATH,
        help='UNIX-Socket path. Default: %(default)s.')

    parser.add_argument(
        '-V', '--version', action='version',
        version='%(prog)s {version}'.format(version=__version__),
        help='Show program\'s version number and exit')

    args = parser.parse_args(remaining_args)

    # Sets the logging
    if args.loglevel is not None:
        level = logging.getLevelName(args.loglevel)
        logging.basicConfig(filename='gvm-pyshell.log', level=level)

    # If timeout value is -1, then the socket has no timeout for this session
    if args.timeout == -1:
        args.timeout = None

    # Open the right connection. SSH at last for default
    if 'socket' in args.connection_type:
        socketpath = args.sockpath
        if socketpath is None:
            socketpath = args.socketpath
        else:
            print('The --sockpath parameter has been deprecated. Please use '
                  '--socketpath instead', file=sys.stderr)

        connection = UnixSocketConnection(path=socketpath,
                                          timeout=args.timeout)
    elif 'tls' in args.connection_type:
        connection = TLSConnection(
            timeout=args.timeout,
            hostname=args.hostname,
            port=args.port,
            certfile=args.certfile,
            keyfile=args.keyfile,
            cafile=args.cafile,
        )
    else:
        connection = SSHConnection(hostname=args.hostname, port=args.port,
                                   timeout=args.timeout, username=args.ssh_user,
                                   password='')

    gmp = Gmp(connection, transform=EtreeCheckCommandTransform())

    with_script = args.script and len(args.script) > 0
    no_script_no_interactive = not args.interactive and not with_script
    script_and_interactive = args.interactive and with_script
    only_interactive = not with_script and args.interactive
    only_script = not args.interactive and with_script

    global_vars = get_globals_dict(gmp, args)

    if only_interactive or no_script_no_interactive:
        enter_interactive_mode(global_vars)

    if script_and_interactive or only_script:
        script_name = args.script[0]
        load(script_name, global_vars)

    if not only_script:
        enter_interactive_mode(global_vars)

    gmp.disconnect()


def get_globals_dict(gmp, args):
    return {
        'gmp': gmp,
        'help': Help(),
        'args': args,
    }

def enter_interactive_mode(global_vars):
    code.interact(
        banner='GVM Interactive Console. Type "help" to get information \
about functionality.',
        local=dict(global_vars, **locals()))


def load(path, global_vars):
    """Loads a file into the interactive console

    Loads a file into the interactive console and execute it.
    TODO: Needs some security checks.

    Arguments:
        path {str} -- Path of file
    """
    try:
        file = open(path, 'r', newline='').read()

        exec(file, global_vars) # pylint: disable=exec-used
    except OSError as e:
        print(str(e))


if __name__ == '__main__':
    main()