# Dartmouth Name Directory Client

* N.B.: The Dartmouth Name Directory and the systems it served have been
  decommissioned, so the code here is primarily of historical interest.  Some
  of the links below are broken.

Copyright (C) 2004-2007 Michael J. Fromberger, All Rights Reserved.

The file "dnd.py" implements a client for the Dartmouth Name Directory (DND), a
central database of public user information used by the BlitzMail system
developed at Dartmouth College.

Information about BlitzMail and the DND can be obtained from the following
locations:

 1. BlitzMail    http://tinyurl.com/d44ut
 2. DND          http://tinyurl.com/aqzce
 3. Protocols    ftp://ftp.dartmouth.edu/pub/software/mac/BlitzMail/Export/
    - doc/server-doc.sea.hqx    : protocol documentation
    - doc/BlitzManual.sea.hqx   : software manual

## INSTALLATION

This library requires the Crypto.Cipher.DES library from PyCrypto,

    http://www.amk.ca/python/code/crypto.html

Once you have that installed, simply copy "dnd.py" to someplace in your Python
installation's module path (e.g., site-packages).

## USAGE

To use the library,

    import dnd

To communicate with the DND, create an instance of the DNDSession class,
optionally providing the host name and port where the server is
located.  The default is to use the name "dnd" and port 902.  

    d = dnd.DNDSession()

The constructor understands keyword arguments to let you specify certain
parameters:

*  `server`   -- the hostname of the DND to talk to (str)
*  `port`     -- the port number of the DND (int)
*  `default_fields` --  default query fields (sequence) [see below]

Once you have a DNDSession object, you can issue queries using the `.lookup()`,
`.lookup_unique()`, and `.validate()` methods.  The first parameter to each
method is the query string, usually a name or nickname to be resolved.  For
`.lookup()` and `.lookup_unique()`, any subsequent parameters should be the
names of DND fields you want to retrieve for each of the matching records.

The `DNDSession` object also understands the context manager protocol, so you
can use it in a "with" statement, e.g.,

```python
with dnd.DNDSession(server = 'dnd.mydomain.org') as db:
    result = db.lookup_unique('some user', 'name', 'uid')
```

To obtain a list of available fields, use the `.fieldinfo()` or `.fieldnames()`
methods.  The `.fieldinfo()` method returns a set of `DNDField` objects, which
know about the names and access permissions of each field supported by the DND.
The `.fieldnames()` method returns a set of just the names (it is a wrapper
around a call to `.fieldinfo()`).  A `DNDField` object supports the following
properties and methods:

*  `.name`  -- returns the name of the field
*  `.read`  -- returns the read-permission code
*  `.write` -- returns the write-permission code

*  `.is_readable(bywhom)`  -- True iff field is readable to bywhom
*  `.is_writable(bywhom)`  -- True iff field is writable to bywhom

The permission codes are:

```
  'T'  - trusted (certain trusted users)
  'U'  - user (the user who "owns" the record)
  'N'  - nobody (only database administrators)
  'A'  - anyone
```

You can get a list of field names readable or writable by a certain
constituency using queries like the following:

```python
  d.readable_fields('all')           #  Fields readable by anyone
  d.readable_fieldS(('all', 'user')) #  Fields readable by user or anyone
  d.writable_fields('none')          #  Fields writable only by DBA
  d.writable_fields('trusted')       #  Fields writable by trusted users
```

To change passwords, use the `.change_pw()` method:

    d.change_pw('user', '<oldpassword>', '<newpassword>')

To edit a field, use the `.change_record()` method:

    d.change_record('user', 'pw', 
                    ('field1', '<newvalue>'), ('field2', '<newvalue>'))

You can edit and query "group" memberships using the methods:

```python
  d.group_add('user', 'group', 'group-pw')
  d.group_remove('user', 'group', 'group-pw')
  d.group_list('group', 'group-pw', 'field1', 'field2', 'field3')
```

When you're done with the session, call `d.close()` to shut down the network
connexion.  The `__del__` method of the object will call this for you when it
gets garbage collected, if necessary.

Records are returned as `DNDRecord` objects.  A `DNDRecord` behaves just like a
dictionary, except that you can also access query fields as if they were class
members, and keys are case-insensitive:

```python
  rec = d.lookup_unique('your name', 'NAME', "NICKNAME", "UID")
  print rec.uid, rec.name, rec.nickname
  print rec['uid'], rec['name'], rec['nickname']
```

An abbreviated version of `.lookup_unique()` is provided if you treat the
DNDSession object as a dictionary and pass it a string query,

    d['query string']

By default, this returns True if there is a unique match for the query string
in the DND, False if there is an ambiguous match, and raises a DNDProtocolError
if there is no match.  You can specify that such a query should return a record
instead, by setting default fields for the session object:

    d.set_default_fields('name', 'uid', 'url')
    print d['query string']

Saying `d.set_default_fields()`, with no field names, deletes the default
fields and restores the original behaviour.  You can also specify a
`default_fields` keyword argument to the `DNDSession` constructor to get the
same effect when the session starts up.

The DND supports a notion of "trusted connexions," which allows users with
administrative privileges to perform edits to DND records without having to
know user passwords.  This is supported by two methods:

*  `d.enable_privs("name", "password")`
     -- enable privileges for the specified user.  Requires that the
	user have AUTH, DBA, or TRUST permission in the PERM field.

*  `d.disable_privs()`
     -- disable privileges on this connexion.

Once you have enabled privileges for a connexion, you can pass the special
constant `DNDSession.TRUST` as the password for any operation which requires
one (e.g., `.change_record()`, `.validate()`, `.group_add()`, `.group_list()`,
etc.).  This causes the `TRUST` command to be used in place of the normal
`PASE` command for authentication.

The `.add_record()` command allows you to add a new record to the DND if
privileges are enabled.  The new record is specified as a dictionary whose keys
are the field names and whose values are the field data for those fields.  All
required fields must be supplied.  You must enable privileges before you can
add new records in this manner.  This method has not been tested, since I do
not have a privileged record in a DND server.  Probably I should set up a test
server to try it out.

## TOOLS

The following command-line tools are implemented using the dnd package
described above:

* `dndedit`   -- Edit the fields of a DND entry.
* `dndquery`  -- Look up records in a DND server.
* `groupedit` -- Edit DND group membership.
* `makelist`  -- Manipulate lists of DND user info.
