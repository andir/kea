# Copyright (C) 2011  Internet Systems Consortium.
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND INTERNET SYSTEMS CONSORTIUM
# DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL
# INTERNET SYSTEMS CONSORTIUM BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING
# FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
# NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION
# WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from bind10 import ProcessInfo, BoB

# XXX: environment tests are currently disabled, due to the preprocessor
#      setup that we have now complicating the environment

import unittest
import sys
import os
import signal
import socket
from isc.net.addr import IPAddr

class TestProcessInfo(unittest.TestCase):
    def setUp(self):
        # redirect stdout to a pipe so we can check that our
        # process spawning is doing the right thing with stdout
        self.old_stdout = os.dup(sys.stdout.fileno())
        self.pipes = os.pipe()
        os.dup2(self.pipes[1], sys.stdout.fileno())
        os.close(self.pipes[1])
        # note that we use dup2() to restore the original stdout
        # to the main program ASAP in each test... this prevents
        # hangs reading from the child process (as the pipe is only
        # open in the child), and also insures nice pretty output

    def tearDown(self):
        # clean up our stdout munging
        os.dup2(self.old_stdout, sys.stdout.fileno())
        os.close(self.pipes[0])

    def test_init(self):
        pi = ProcessInfo('Test Process', [ '/bin/echo', 'foo' ])
        pi.spawn()
        os.dup2(self.old_stdout, sys.stdout.fileno())
        self.assertEqual(pi.name, 'Test Process')
        self.assertEqual(pi.args, [ '/bin/echo', 'foo' ])
#        self.assertEqual(pi.env, { 'PATH': os.environ['PATH'],
#                                   'PYTHON_EXEC': os.environ['PYTHON_EXEC'] })
        self.assertEqual(pi.dev_null_stdout, False)
        self.assertEqual(os.read(self.pipes[0], 100), b"foo\n")
        self.assertNotEqual(pi.process, None)
        self.assertTrue(type(pi.pid) is int)

#    def test_setting_env(self):
#        pi = ProcessInfo('Test Process', [ '/bin/true' ], env={'FOO': 'BAR'})
#        os.dup2(self.old_stdout, sys.stdout.fileno())
#        self.assertEqual(pi.env, { 'PATH': os.environ['PATH'],
#                                   'PYTHON_EXEC': os.environ['PYTHON_EXEC'],
#                                   'FOO': 'BAR' })

    def test_setting_null_stdout(self):
        pi = ProcessInfo('Test Process', [ '/bin/echo', 'foo' ], 
                         dev_null_stdout=True)
        pi.spawn()
        os.dup2(self.old_stdout, sys.stdout.fileno())
        self.assertEqual(pi.dev_null_stdout, True)
        self.assertEqual(os.read(self.pipes[0], 100), b"")

    def test_respawn(self):
        pi = ProcessInfo('Test Process', [ '/bin/echo', 'foo' ])
        pi.spawn()
        # wait for old process to work...
        self.assertEqual(os.read(self.pipes[0], 100), b"foo\n")
        # respawn it
        old_pid = pi.pid
        pi.respawn()
        os.dup2(self.old_stdout, sys.stdout.fileno())
        # make sure the new one started properly
        self.assertEqual(pi.name, 'Test Process')
        self.assertEqual(pi.args, [ '/bin/echo', 'foo' ])
#        self.assertEqual(pi.env, { 'PATH': os.environ['PATH'],
#                                   'PYTHON_EXEC': os.environ['PYTHON_EXEC'] })
        self.assertEqual(pi.dev_null_stdout, False)
        self.assertEqual(os.read(self.pipes[0], 100), b"foo\n")
        self.assertNotEqual(pi.process, None)
        self.assertTrue(type(pi.pid) is int)
        self.assertNotEqual(pi.pid, old_pid)

class TestBoB(unittest.TestCase):
    def test_init(self):
        bob = BoB()
        self.assertEqual(bob.verbose, False)
        self.assertEqual(bob.msgq_socket_file, None)
        self.assertEqual(bob.cc_session, None)
        self.assertEqual(bob.ccs, None)
        self.assertEqual(bob.processes, {})
        self.assertEqual(bob.dead_processes, {})
        self.assertEqual(bob.runnable, False)
        self.assertEqual(bob.uid, None)
        self.assertEqual(bob.username, None)
        self.assertEqual(bob.nocache, False)
        self.assertEqual(bob.cfg_start_auth, True)
        self.assertEqual(bob.cfg_start_resolver, False)

    def test_init_alternate_socket(self):
        bob = BoB("alt_socket_file")
        self.assertEqual(bob.verbose, False)
        self.assertEqual(bob.msgq_socket_file, "alt_socket_file")
        self.assertEqual(bob.cc_session, None)
        self.assertEqual(bob.ccs, None)
        self.assertEqual(bob.processes, {})
        self.assertEqual(bob.dead_processes, {})
        self.assertEqual(bob.runnable, False)
        self.assertEqual(bob.uid, None)
        self.assertEqual(bob.username, None)
        self.assertEqual(bob.nocache, False)
        self.assertEqual(bob.cfg_start_auth, True)
        self.assertEqual(bob.cfg_start_resolver, False)

# Class for testing the BoB without actually starting processes.
# This is used for testing the start/stop components routines and
# the BoB commands.
#
# Testing that external processes start is outside the scope
# of the unit test, by overriding the process start methods we can check
# that the right processes are started depending on the configuration
# options.
class MockBob(BoB):
    def __init__(self):
        BoB.__init__(self)

        # Set flags as to which of the overridden methods has been run.
        self.msgq = False
        self.cfgmgr = False
        self.ccsession = False
        self.auth = False
        self.resolver = False
        self.xfrout = False
        self.xfrin = False
        self.zonemgr = False
        self.stats = False
        self.cmdctl = False
        self.c_channel_env = {}
        self.processes = { }

    def read_bind10_config(self):
        # Configuration options are set directly
        pass

    def start_msgq(self, c_channel_env):
        self.msgq = True
        self.processes[2] = ProcessInfo('b10-msgq', ['/bin/false'])

    def start_cfgmgr(self, c_channel_env):
        self.cfgmgr = True
        self.processes[3] = ProcessInfo('b10-cfgmgr', ['/bin/false'])

    def start_ccsession(self, c_channel_env):
        self.ccsession = True
        self.processes[4] = ProcessInfo('b10-ccsession', ['/bin/false'])

    def start_auth(self, c_channel_env):
        self.auth = True
        self.processes[5] = ProcessInfo('b10-auth', ['/bin/false'])

    def start_resolver(self, c_channel_env):
        self.resolver = True
        self.processes[6] = ProcessInfo('b10-resolver', ['/bin/false'])

    def start_xfrout(self, c_channel_env):
        self.xfrout = True
        self.processes[7] = ProcessInfo('b10-xfrout', ['/bin/false'])

    def start_xfrin(self, c_channel_env):
        self.xfrin = True
        self.processes[8] = ProcessInfo('b10-xfrin', ['/bin/false'])

    def start_zonemgr(self, c_channel_env):
        self.zonemgr = True
        self.processes[9] = ProcessInfo('b10-zonemgr', ['/bin/false'])

    def start_stats(self, c_channel_env):
        self.stats = True
        self.processes[10] = ProcessInfo('b10-stats', ['/bin/false'])

    def start_cmdctl(self, c_channel_env):
        self.cmdctl = True
        self.processes[11] = ProcessInfo('b10-cmdctl', ['/bin/false'])

    # We don't really use all of these stop_ methods. But it might turn out
    # someone would add some stop_ method to BoB and we want that one overriden
    # in case he forgets to update the tests.
    def stop_msgq(self):
        if self.msgq:
            del self.processes[2]
        self.msgq = False

    def stop_cfgmgr(self):
        if self.cfgmgr:
            del self.processes[3]
        self.cfgmgr = False

    def stop_ccsession(self):
        if self.ccssession:
            del self.processes[4]
        self.ccsession = False

    def stop_auth(self):
        if self.auth:
            del self.processes[5]
        self.auth = False

    def stop_resolver(self):
        if self.resolver:
            del self.processes[6]
        self.resolver = False

    def stop_xfrout(self):
        if self.xfrout:
            del self.processes[7]
        self.xfrout = False

    def stop_xfrin(self):
        if self.xfrin:
            del self.processes[8]
        self.xfrin = False

    def stop_zonemgr(self):
        if self.zonemgr:
            del self.processes[9]
        self.zonemgr = False

    def stop_stats(self):
        if self.stats:
            del self.processes[10]
        self.stats = False

    def stop_cmdctl(self):
        if self.cmdctl:
            del self.processes[11]
        self.cmdctl = False

class TestStartStopProcessesBob(unittest.TestCase):
    """
    Check that the start_all_processes method starts the right combination
    of processes and that the right processes are started and stopped
    according to changes in configuration.
    """
    def check_started(self, bob, core, auth, resolver):
        """
        Check that the right sets of services are started. The ones that
        should be running are specified by the core, auth and resolver parameters
        (they are groups of processes, eg. auth means b10-auth, -xfrout, -xfrin
        and -zonemgr).
        """
        self.assertEqual(bob.msgq, core)
        self.assertEqual(bob.cfgmgr, core)
        self.assertEqual(bob.ccsession, core)
        self.assertEqual(bob.auth, auth)
        self.assertEqual(bob.resolver, resolver)
        self.assertEqual(bob.xfrout, auth)
        self.assertEqual(bob.xfrin, auth)
        self.assertEqual(bob.zonemgr, auth)
        self.assertEqual(bob.stats, core)
        self.assertEqual(bob.cmdctl, core)

    def check_preconditions(self, bob):
        self.check_started(bob, False, False, False)

    def check_started_none(self, bob):
        """
        Check that the situation is according to configuration where no servers
        should be started. Some processes still need to be running.
        """
        self.check_started(bob, True, False, False)

    def check_started_both(self, bob):
        """
        Check the situation is according to configuration where both servers
        (auth and resolver) are enabled.
        """
        self.check_started(bob, True, True, True)

    def check_started_auth(self, bob):
        """
        Check the set of processes needed to run auth only is started.
        """
        self.check_started(bob, True, True, False)

    def check_started_resolver(self, bob):
        """
        Check the set of processes needed to run resolver only is started.
        """
        self.check_started(bob, True, False, True)

    # Checks the processes started when starting neither auth nor resolver
    # is specified.
    def test_start_none(self):
        # Create BoB and ensure correct initialization
        bob = MockBob()
        self.check_preconditions(bob)

        # Start processes and check what was started
        bob.cfg_start_auth = False
        bob.cfg_start_resolver = False

        bob.start_all_processes()
        self.check_started_none(bob)

    # Checks the processes started when starting only the auth process
    def test_start_auth(self):
        # Create BoB and ensure correct initialization
        bob = MockBob()
        self.check_preconditions(bob)

        # Start processes and check what was started
        bob.cfg_start_auth = True
        bob.cfg_start_resolver = False

        bob.start_all_processes()

        self.check_started_auth(bob)

    # Checks the processes started when starting only the resolver process
    def test_start_resolver(self):
        # Create BoB and ensure correct initialization
        bob = MockBob()
        self.check_preconditions(bob)

        # Start processes and check what was started
        bob.cfg_start_auth = False
        bob.cfg_start_resolver = True

        bob.start_all_processes()

        self.check_started_resolver(bob)

    # Checks the processes started when starting both auth and resolver process
    def test_start_both(self):
        # Create BoB and ensure correct initialization
        bob = MockBob()
        self.check_preconditions(bob)

        # Start processes and check what was started
        bob.cfg_start_auth = True
        bob.cfg_start_resolver = True

        bob.start_all_processes()

        self.check_started_both(bob)

    def test_config_start(self):
        """
        Test that the configuration starts and stops processes according
        to configuration changes.
        """

        # Create BoB and ensure correct initialization
        bob = MockBob()
        self.check_preconditions(bob)

        # Start processes (nothing much should be started, as in
        # test_start_none)
        bob.cfg_start_auth = False
        bob.cfg_start_resolver = False

        bob.start_all_processes()
        bob.runnable = True
        self.check_started_none(bob)

        # Enable both at once
        bob.config_handler({'start_auth': True, 'start_resolver': True})
        self.check_started_both(bob)

        # Not touched by empty change
        bob.config_handler({})
        self.check_started_both(bob)

        # Not touched by change to the same configuration
        bob.config_handler({'start_auth': True, 'start_resolver': True})
        self.check_started_both(bob)

        # Turn them both off again
        bob.config_handler({'start_auth': False, 'start_resolver': False})
        self.check_started_none(bob)

        # Not touched by empty change
        bob.config_handler({})
        self.check_started_none(bob)

        # Not touched by change to the same configuration
        bob.config_handler({'start_auth': False, 'start_resolver': False})
        self.check_started_none(bob)

        # Start and stop auth separately
        bob.config_handler({'start_auth': True})
        self.check_started_auth(bob)

        bob.config_handler({'start_auth': False})
        self.check_started_none(bob)

        # Start and stop resolver separately
        bob.config_handler({'start_resolver': True})
        self.check_started_resolver(bob)

        bob.config_handler({'start_resolver': False})
        self.check_started_none(bob)

        # Alternate
        bob.config_handler({'start_auth': True})
        self.check_started_auth(bob)

        bob.config_handler({'start_auth': False, 'start_resolver': True})
        self.check_started_resolver(bob)

        bob.config_handler({'start_auth': True, 'start_resolver': False})
        self.check_started_auth(bob)

    def test_config_start_once(self):
        """
        Tests that a process is started only once.
        """
        # Create BoB and ensure correct initialization
        bob = MockBob()
        self.check_preconditions(bob)

        # Start processes (both)
        bob.cfg_start_auth = True
        bob.cfg_start_resolver = True

        bob.start_all_processes()
        bob.runnable = True
        self.check_started_both(bob)

        bob.start_auth = lambda: self.fail("Started auth again")
        bob.start_xfrout = lambda: self.fail("Started xfrout again")
        bob.start_xfrin = lambda: self.fail("Started xfrin again")
        bob.start_zonemgr = lambda: self.fail("Started zonemgr again")
        bob.start_resolver = lambda: self.fail("Started resolver again")

        # Send again we want to start them. Should not do it, as they are.
        bob.config_handler({'start_auth': True})
        bob.config_handler({'start_resolver': True})

    def test_config_not_started_early(self):
        """
        Test that processes are not started by the config handler before
        startup.
        """
        bob = MockBob()
        self.check_preconditions(bob)

        bob.start_auth = lambda: self.fail("Started auth again")
        bob.start_xfrout = lambda: self.fail("Started xfrout again")
        bob.start_xfrin = lambda: self.fail("Started xfrin again")
        bob.start_zonemgr = lambda: self.fail("Started zonemgr again")
        bob.start_resolver = lambda: self.fail("Started resolver again")

        bob.config_handler({'start_auth': True, 'start_resolver': True})

class TestBossCmd(unittest.TestCase):
    def test_ping(self):
        """
        Confirm simple ping command works.
        """
        bob = MockBob()
        answer = bob.command_handler("ping", None)
        self.assertEqual(answer, {'result': [0, 'pong']})

    def test_show_processes(self):
        """
        Confirm getting a list of processes works.
        """
        bob = MockBob()
        answer = bob.command_handler("show_processes", None)
        self.assertEqual(answer, {'result': [0, []]})

    def test_show_processes_started(self):
        """
        Confirm getting a list of processes works.
        """
        bob = MockBob()
        bob.start_all_processes()
        answer = bob.command_handler("show_processes", None)
        processes = [[2, 'b10-msgq'],
                     [3, 'b10-cfgmgr'], 
                     [4, 'b10-ccsession'],
                     [5, 'b10-auth'],
                     [7, 'b10-xfrout'],
                     [8, 'b10-xfrin'], 
                     [9, 'b10-zonemgr'],
                     [10, 'b10-stats'], 
                     [11, 'b10-cmdctl']]
        self.assertEqual(answer, {'result': [0, processes]})

if __name__ == '__main__':
    unittest.main()
