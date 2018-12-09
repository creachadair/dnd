#!/usr/bin/env python
##
## Name:     test_dnd.py
## Purpose:  Unit tests for dnd.py
##
## Copyright (C) 2006 Michael J. Fromberger, All Rights Reserved.
##

import dnd, errno, inspect, random, socket, sys, thread, unittest

# {{ class PseudoDND


class PseudoDND(object):
    """Simulates a primitive DND server for testing purposes.  Only
    one client at a time can be handled.  To customize the behaviour
    of this object for different tests, each client command is given
    to a method which may be overridden; the protocol is:

      h_COMMAND(self, key, data)
        key   -- the command name
        data  -- the rest of the command line

    Commands for which no method is defined are passed to h_default(),
    which sends a default response to the client.  Your method may
    call .h_default() explicitly if desired for the default behaviour.
    """

    def __init__(self, port):
        """Creates a new PseudoDND listening at the specified port.

        Use .run() to start a client session.
        Use .close() to explicitly destroy the listener.
        """
        self._conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._conn.bind(('localhost', port))
        self._conn.listen(1)
        self._client = None
        self._input = None
        self._caddr = None
        self._debug = True

    def run(self):
        """Accept a single client session and process its commands.
        Each command is passed to the appropriate handler until either
        an error is encountered, or until one of the handlers sets the
        _more attribute of this object to a false value.
        """
        self._client = self._conn.accept()[0]
        self._caddr = self._client.getpeername()
        self._input = self._client.makefile()
        self._diag('- client connected: %s', self._caddr)

        self._writelines(220, 'DND server here.')
        self._more = True
        while self._more:
            try:
                cmd, data = self._readline()
            except ValueError, e:
                self._diag('- error: %s', e)
                break

            self._diag('  >> %s %s', cmd, data)

            tag = 'h_%s' % cmd.upper()
            handler = getattr(self, tag, None)
            try:
                if inspect.ismethod(handler):
                    self._diag('    sending to %s', tag)
                    handler(cmd, data)
                else:
                    self.h_default(cmd, data)
            except ValueError, e:
                self._diag('- error: %s', e)
                break

        self._diag('- server loop ended')
        self._cclient()
        self._diag('- client disconnected')

    def h_QUIT(self, cmd, data):
        """Default QUIT command handler; say OK and stop the client loop."""
        self._writelines(200, 'Ok')
        self._more = False  # Tell server loop to exit

    def h_NOOP(self, cmd, data):
        """Default NOOP command handler; just say OK."""
        self._writelines(200, 'Ok')

    def h_default(self, cmd, data):
        """Default command handler; report a syntax error."""
        self._writelines(500, 'Syntax error, command unknown.')

    def __del__(self):
        try:
            self._diag('[disposing of %s]', self)
            self._close()
        except:
            pass

    def _diag(self, msg, *args):
        if self._debug:
            print >> sys.stderr, msg % args

    def _cclient(self):
        try:
            self._client.shutdown(2)
        except (socket.error, AttributeError):
            pass

        self._client = None
        self._caddr = None
        self._input = None

    def _close(self):
        self._cclient()
        try:
            self._conn.shutdown(2)
        except (socket.error, AttributeError):
            pass

        self._conn = None

    def _readline(self):
        try:
            line = self._input.readline()
        except socket.error, e:
            if e[0] == errno.ECONNRESET:
                self._close()
                raise ValueError("connection closed by remote host")
            else:
                raise
        except AttributeError:
            raise ValueError("no client is connected")

        if line == '':
            self._close()
            raise ValueError("connection closed by remote host")

        out = line.rstrip().split(' ', 1)
        if len(out) == 1:
            out.append('')
        return out

    def _rawsend(self, data):
        try:
            self._client.send(data)
        except socket.error, e:
            if e[0] == errno.EPIPE:
                self._close()
                raise ValueError("broken pipe")
            else:
                raise
        except AttributeError:
            raise ValueError("no client is connected")

    def _writelines(self, code, *specs):
        for elt in specs:
            if isinstance(elt, (int, long)):
                code = elt
            else:
                msg = '%03d %s\n' % (code, elt)
                self._rawsend(msg)


# }}

fake_fields = set()
for wr in 'AUNT':
    for rd in 'AUNT':
        fake_fields.add(
            dnd.DNDField('field%d' % (len(fake_fields) + 1), rd, wr))

# {{ class TestDND


class TestDND(PseudoDND):
    def __init__(self, *args):
        super(TestDND, self).__init__(*args)

        self._privs = None  # Indicates special privileges
        self._vdata = None  # Indicates open validation

    def check_validate(self):
        if self._vdata is None:
            return True

        self._writelines(502, 'Bad sequence of commands')
        self._vdata = None
        return False

    def h_FIELDS(self, cmd, data):
        if not self.check_validate():
            return

        self._writelines(102, '%d' % len(fake_fields))
        for fld in fake_fields:
            self._writelines(120, '%s %s %s' % (fld.name, fld.write, fld.read))
        self._writelines(200, 'Done')

    def h_UNPRIV(self, cmd, data):
        if not self.check_validate():
            return

        self._writelines(200, 'Permissions removed')
        self._privs = None

    def h_LOOKUP(self, cmd, data):
        if not self.check_validate():
            return

        if ',' not in data:
            query = data
            fields = ()
        else:
            query, data = data.split(',', 1)
            fields = data.split(' ')

        if query == 'missing':
            self._writelines(520, 'No match for that name.')
            return
        elif query == 'unique':
            numrec = 1
        elif query == 'excessive':
            numrec = 30
        else:
            numrec = 2

        for fld in fields:
            for elt in fake_fields:
                if elt == fld:
                    break
            else:
                self._writelines(501, 'No such field: %s' % fld)
                return

            if not elt.is_readable('any'):
                self._writelines(521, 'Field access denied: %s' % fld)
                return

        outrec = min(25, numrec)
        self._writelines(101, '%d %d' % (outrec, len(fields)))
        for i in xrange(outrec):
            for j in xrange(len(fields)):
                self._writelines(110,
                                 'Data for user %s %s' % (i + 1, fields[j]))
        if outrec < numrec:
            self._writelines(201, 'Additional matching records not returned.')
        else:
            self._writelines(200, 'Ok.')

    def h_VALIDATE(self, cmd, data):
        if not self.check_validate():
            return

        if ',' not in data:
            name = data
            fields = ()
        else:
            name, data = data.split(',', 1)
            fields = data.split(' ')

        if name == 'missing':
            self._writelines(520, 'Invalid name.')
            return
        elif name in ('ambiguous', 'excessive'):
            self._writelines(522, 'Ambiguous name.')
            return

        for fld in fields:
            for elt in fake_fields:
                if elt == fld:
                    break
            else:
                self._writelines(501, 'No such field: %s' % fld)
                return

            if not elt.is_readable(('user', 'any')):
                self._writelines(521, 'Field access denied: %s' % fld)
                return

        self._vdata = {
            'name': name,
            'fields': fields,
            'pw': 'testpass',
            'challenge': '240147326165005023201134'
        }
        self._writelines(300, self._vdata['challenge'])

    def h_PASS(self, cmd, data):
        if self._vdata is None:
            self._writelines(502, 'Bad sequence of commands')
            return

        if data <> self._vdata['pw']:
            self._writelines(530, 'Incorrect password.')
        else:
            self._writelines(101, '1 %d' % len(self._vdata['fields']))
            for elt in self._vdata['fields']:
                self._writelines(110, 'Data for %s' % elt)
            self._writelines(200, 'Validation ok.')

        self._vdata = None

    def h_PASE(self, cmd, data):
        if self._vdata is None:
            self._writelines(502, 'Bad sequence of commands')
            return

        enc = dnd.encrypt_challenge(self._vdata['challenge'],
                                    self._vdata['pw'])
        if enc <> data:
            self._writelines(530, 'Incorrect password.')
        else:
            self._writelines(101, '1 %d' % len(self._vdata['fields']))
            for elt in self._vdata['fields']:
                self._writelines(110, 'Data for %s' % elt)
            self._writelines(200, 'Validation ok.')

        self._vdata = None


# }}

# {{ class DNDSessionSmokeTest


class DNDSessionSmokeTest(unittest.TestCase):
    """A test case that verifies that some basic functionality of the
    DNDSession object works properly.  Tested here are:

    .fieldinfo()
    .readable_by()
    .writable_by()
    .lookup()
    .lookup_unique()
    .validate()
    .begin_validate()
    .keep_alive()

    There are many other methods that are NOT tested here.
    """
    host_name = 'localhost'
    host_port = random.randint(2000, 50000)

    def __init__(self, *args, **kwargs):
        super(DNDSessionSmokeTest, self).__init__(*args, **kwargs)

    def setUp(self):
        self._pd = TestDND(self.host_port)
        thread.start_new_thread(self.run_pseudo, ())
        self._dnd = None

    def run_pseudo(self):
        self._pd.run()
        thread.exit()

    def tearDown(self):
        if self._dnd is not None:
            self._dnd.close()

        self._pd._close()

    def runTest(self):
        try:
            self._dnd = dnd.DNDSession(
                server=self.host_name, port=self.host_port)
            d = self._dnd
        except dnd.DNDError, e:
            self.fail('unable to create test DNDSession: %s' % e)

        # Look up all the field keys
        try:
            fld = d.fieldinfo()
        except dnd.DNDError, e:
            self.fail('error in fieldinfo: %s' % e)

        self.assertEquals(len(fld), 16)

        # Make sure they're the same as the ones we sent out, modulo
        # case sensitivity
        fld = set(s.upper() for s in d.fieldnames())
        cmp = set(s.name.upper() for s in fake_fields)
        self.assertEquals(fld, cmp)

        # Make sure the permission wrangling looks reasonable...
        fld = d.readable_fields('any')
        self.assertEquals(len(fld), 4)

        fld = d.writable_fields('any')
        self.assertEquals(len(fld), 4)

        fld = d.readable_fields(('user', 'any'))
        self.assertEquals(len(fld), 8)

        # Make sure a missing user generates an exception...
        try:
            d.lookup('missing')
            self.fail('missing user did not raise DNDProtocolError')
        except dnd.DNDProtocolError:
            pass
        except dnd.DNDError, e:
            self.fail('missing user raised an unexpected error: %s' % e)

        # Make sure the 'additional records' message is handled...
        try:
            rec = d.lookup('excessive', 'field1', 'field9')
        except dnd.DNDError, e:
            self.fail('error in lookup: %s' % e)

        self.assertEquals(len(rec), 25)
        self.assertTrue(rec.more)
        for elt in rec:
            self.assertEqual(len(elt), 2)

        # Make sure a unique user is really unique...
        try:
            rec = d.lookup('unique', 'field1', 'field13', 'field9')
        except dnd.DNDError, e:
            self.fail('error in lookup: %s' % e)

        self.assertEquals(len(rec), 1)
        self.assertFalse(rec.more)
        elt = rec.pop()
        self.assertEqual(len(elt), 3)

        self.assertFalse(d.lookup_unique('ambiguous'))
        self.assertEquals(d.lookup('ambiguous'), 2)
        self.assertEquals(d.lookup('excessive'), 25)
        self.assertEquals(d.lookup('unique'), 1)

        # Make sure validation works correctly
        try:
            chal, resp = d.begin_validate('unique', 'field1', 'field2')
        except dnd.DNDError, e:
            self.fail('error in begin_validate: %s' % e)

        try:
            rec = resp('testpass', False)
            self.assertEqual(len(rec), 2)
        except dnd.DNDError, e:
            self.fail('error in validate responder: %s' % e)

        try:
            chal, resp = d.begin_validate('unique')
        except dnd.DNDError, e:
            self.fail('error in begin_validate: %s' % e)

        try:
            rec = resp('testpass', False)
            self.assertTrue(rec)
        except dnd.DNDError, e:
            self.fail('error in validate responder: %s' % e)

        try:
            d.begin_validate('missing')
            self.fail('missing user did not generate DNDProtocolError')
        except dnd.DNDProtocolError:
            pass
        except dnd.DNDError, e:
            self.fail('error in begin_validate: %s' % e)

        try:
            d.validate('ambiguous', 'irrelevant password')
            self.fail('ambiguous user did not generate DNDProtocolError')
        except dnd.DNDProtocolError:
            pass
        except dnd.DNDError, e:
            self.fail('error in validation: %s' % e)

        try:
            d.validate('unique', 'wrongpw', 'field1')
            self.fail('wrong password did not generate DNDProtocolError')
        except dnd.DNDProtocolError:
            pass
        except dnd.DNDError, e:
            self.fail('error in validation: %s' % e)

        try:
            d.lookup('ambiguous', 'field1', 'nosuchfield')
            self.fail('unknown field did not generate DNDProtocolError')
        except dnd.DNDProtocolError:
            pass
        except dnd.DNDError, e:
            self.fail('error in lookup: %s' % e)

        try:
            d.lookup('ambiguous', 'field1', 'field13', 'field7')
            self.fail('inaccessible field did not generate DNDProtocolError')
        except dnd.DNDProtocolError:
            pass
        except dnd.DNDError, e:
            self.fail('error in lookup: %s' % e)

        try:
            d.keep_alive()
        except dnd.DNDError, e:
            self.fail('error in keep_alive: %s' % e)


# }}

if __name__ == "__main__":
    suite = unittest.TestSuite((DNDSessionSmokeTest(), ))

    unittest.main()

# Here there be dragons
