#!/usr/local/bin/python
##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
# All Rights Reserved.
# 
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
# 
##############################################################################

# Zope External Editor Helper Application by Casey Duncan

__version__ = '0.1'

import sys, os, stat
from time import sleep
from ConfigParser import ConfigParser
from httplib import HTTPConnection, HTTPSConnection

class Configuration:
    
    default_configuration = """\
# Zope External Editor helper application configuration

[general]
# General configuration options

# Uncomment and specify an editor value to override the editor
# specified in the environment
#editor = 

# Automatic save interval, in seconds. Set to zero for
# no auto save (save to Zope only on exit).
save_interval = 1

# Temporary file cleanup. Set to false for debugging or
# to waste disk space. Note: setting this to false is a
# security risk to the zope server
cleanup_files = 1

# Use WebDAV locking to prevent concurrent editing by
# different users. Disable for single user use for
# better performance
use_locks = 1

# Specific settings by content-type or meta-type. Specific
# settings override general options above. Content-type settings
# override meta-type settings for the same option.

[meta-type:DTML Document]
extension=.dtml

[meta-type:DTML Method]
extension=.dtml

[meta-type:Script (Python)]
extension=.py

[meta-type:Page Template]
extension=.pt

[meta-type:Image]
editor=gimp

[content-type:text/*]
extension=.txt

[content-type:text/html]
extension=.html"""
    
    def __init__(self, path):
        # Create/read config file on instantiation
        self.path = path
        if not os.path.exists(path):
            f = open(path, 'w')
            f.write(self.default_configuration)
            f.close()
        self.changed = 0
        self.config = ConfigParser()
        self.config.readfp(open(path))
        
        
    def __del__(self):
        # Save changes on destruction
        if self.changed:
            self.save()
            
    def save(self):
        """Save config options to disk"""
        self.config.write(open(self.path, 'w'))
        self.changed = 0
        
            
    def set(self, section, option, value):
        self.config.set(section, option, value)
        self.changed = 1
    
    def __getattr__(self, name):
        # Delegate to the ConfigParser instance'
        return getattr(self.config, name)
        
    def getAllOptions(self, meta_type, content_type):
        """Return a dict of all applicable options for the
           given meta_type and content_type
        """
        opt = {}
        sep = content_type.find('/')
        general_type = '%s/*' % content_type[:sep]
        sections = ('general', 
                    'meta-type:%s' % meta_type,
                    'content-type:%s' % general_type,
                    'content-type:%s' % content_type)
        for section in sections:
            if self.config.has_section(section):
                for option in self.config.options(section):
                    opt[option] = self.config.get(section, option)
        return opt
                     
        
class ExternalEditor:
    
    clean_up = 0
    saved = 1
    
    def __init__(self, input_file):
        # Read the configuration file output any errors to the user
        config_path = os.path.expanduser('~/.zope-external-edit')
        self.config = Configuration(config_path)
        
        # Open the input file and read the metadata headers
        in_f = open(input_file, 'rb')
        metadata = {}

        while 1:
            line = in_f.readline()[:-1]
            if not line: break
            sep = line.find(':')
            key = line[:sep]
            val = line[sep+1:]
            metadata[key] = val
        self.metadata = metadata
        
        self.options = self.config.getAllOptions(metadata['meta_type'],
                           metadata.get('content_type',''))
            
        # Write the body of the input file to a separate file
        body_file = self.metadata['url'][7:].replace('/',',')
        body_file = '%s-%s' % (os.tmpnam(), body_file)
        ext = self.options.get('extension')
        if ext and not body_file.endswith(ext):
            body_file = body_file + ext
        body_f = open(body_file, 'wb')
        body_f.write(in_f.read())
        in_f.close()
        body_f.close()
        self.clean_up = int(self.options.get('cleanup_files', 1))
        if self.clean_up: os.remove(input_file)
        self.body_file = body_file
        
        # Get the host and path from the URL
        self.ssl = self.metadata['url'].startswith('https:')
        url = self.metadata['url'][7:]
        path_start = url.find('/')
        if path_start == -1:
            self.host = url
            self.path = '/'
        else:
            self.host = url[:path_start]
            self.path = url[path_start:]
        
    def __del__(self):
        if self.clean_up:
            os.remove(self.body_file)
            
    def getEditorPath(self):
        """Return the absolute path to the editor"""
        path = self.options.get('editor')
        
        if path:
            path = whereIs(path)
        elif has_tk():
            from tkSimpleDialog import askstring
            path = askstring('Zope External Editor', 
                             'Enter the default editor name')
            if not path: sys.exit(0)
            path = whereIs(path)
            if os.path.exists(path):
                self.config.set('general', 'editor', path)
                self.config.save()
                
        if not path:
            # Try some sensible default
            if sys.platform == 'win32':
                path = whereIs('notepad')
            else:
                editors = ['xedit', 'gvim', 'emacs']
                while not path:
                    path = whereIs(editors.pop())
                
        if path is not None:            
            return path
        else:
            self.fatalError('Editor not found at "%s"' % path)
        
    def launch(self):
        """Launch external editor"""
        editor = self.getEditorPath()
        file = self.body_file
        last_fstat = os.stat(file)
        pid = os.spawnl(os.P_NOWAIT, editor, editor, file)
        use_locks = int(self.options.get('use_locks'))
        
        if use_locks:
            self.lock()
            
        exit_pid = 0
        save_interval = self.config.getfloat('general', 'save_interval')
        launched = 0
        
        while exit_pid != pid:
            sleep(save_interval or 2)
            
            try:
                exit_pid, exit_status = os.waitpid(pid, os.WNOHANG)
                if not exit_pid: launched = 1
            except OSError:
                exit_pid = pid
            
            fstat = os.stat(file)
            if (exit_pid == pid or save_interval) \
               and fstat[stat.ST_MTIME] != last_fstat[stat.ST_MTIME]:
                # File was modified
                self.saved = self.putChanges()
                last_fstat = fstat
                
        if not launched:
            fatalError(('Editor "%s" did not launch.\n'
                        'It may not be a graphical editor.') % editor)
         
        if use_locks:
            self.unlock()
        
        if not self.saved and has_tk():
            from tkMessageBox import askyesno
            if askyesno('Zope External Editor',
                        'File not saved to Zope.\nReopen local copy?'):
                has_tk() # ugh, keeps tk happy
                self.launch()
            else:
                self.clean_up = 0 # Keep temp file
                has_tk() # ugh
        
    def putChanges(self):
        """Save changes to the file back to Zope"""
        f = open(self.body_file, 'rb')
        body = f.read()
        f.close()
        headers = {'Content-Type': 
                   self.metadata.get('content_type', 'text/plain')}
        
        if hasattr(self, 'lock_token'):
            headers['If'] = '<%s> (<%s>)' % (self.path,
                                             self.lock_token)
        
        response = self.zope_request('PUT', headers, body)
        del body # Don't keep the body around longer then we need to

        if response.status / 100 != 2:
            # Something went wrong
            sys.stderr.write('Error occurred during HTTP put:\n%d %s\n' \
                             % (response.status, response.reason))
            sys.stderr.write('\n----\n%s\n----' % response.read())
            
            message = response.getheader('Bobo-Exception-Type','')
            if has_tk():
                from tkMessageBox import askretrycancel
                if askretrycancel('Zope External Editor',
                                  ('Could not save to Zope.\nError '
                                   'occurred during HTTP put:\n%d %s\n%s') \
                                  % (response.status, response.reason,
                                     message)):
                    has_tk() # ugh, keeps tk happy
                    self.putChanges()
                else:
                    has_tk() # ugh
                    return 0
        return 1
    
    def lock(self):
        """Apply a webdav lock to the object in Zope"""
        
        headers = {'Content-Type':'text/xml; charset="utf-8"',
                   'Timeout':'infinite',
                   'Depth':'infinity',
                  }
        body = ('<?xml version="1.0" encoding="utf-8"?>\n'
                '<d:lockinfo xmlns:d="DAV:">\n'
                '  <d:lockscope><d:exclusive/></d:lockscope>\n'
                '  <d:locktype><d:write/></d:locktype>\n'
                '  <d:depth>infinity</d:depth>\n'
                '  <d:owner>\n' 
                '  <d:href>Zope External Editor</d:href>\n'
                '  </d:owner>\n'
                '</d:lockinfo>'
                )
        
        response = self.zope_request('LOCK', headers, body)
        
        if response.status / 100 == 2:
            # We got our lock, extract the lock token and return it
            reply = response.read()
            token_start = reply.find('>opaquelocktoken:')
            token_end = reply.find('<', token_start)
            if token_start > 0 and token_end > 0:
               self.lock_token = reply[token_start+1:token_end]
        else:
            # We can't lock her sir!
            if response.status == 423:
                message = '\n(Object already locked)'
            else:
                message = response.getheader('Bobo-Exception-Type','')

            sys.stderr.write('Error occurred during lock request:\n%d %s\n' \
                             % (response.status, response.reason))
            sys.stderr.write('\n----\n%s\n----' % response.read())
            if has_tk():
                from tkMessageBox import askretrycancel
                if askretrycancel('Zope External Editor',
                                  ('Lock request failed:\n%d %s\n%s') \
                                  % (response.status, response.reason, message)):
                    has_tk() # ugh, keeps tk happy
                    return self.lock()
                else:
                    has_tk() # ugh
                    return 0
        return 1
                    
    def unlock(self):
        """Remove webdav lock from edited zope object"""
        if not hasattr(self, 'lock_token'): 
            return 0
            
        headers = {'Lock-Token':self.lock_token}
        
        response = self.zope_request('UNLOCK', headers)
        
        if response.status / 100 != 2:
            # Captain, she's still locked!
            message = response.getheader('Bobo-Exception-Type','')
            sys.stderr.write('Error occurred during lock request:\n%d %s\n%s' \
                             % (response.status, response.reason, message))
            sys.stderr.write('\n----\n%s\n----' % response.read())
            if has_tk():
                from tkMessageBox import askretrycancel
                if askretrycancel('Zope External Editor',
                                  ('Unlock request failed:\n%d %s') \
                                  % (response.status, response.reason)):
                    has_tk() # ugh, keeps tk happy
                    return self.unlock(token)
                else:
                    has_tk() # ugh
                    return 0
        return 1
        
    def zope_request(self, method, headers={}, body=''):
        """Send a request back to Zope"""
        try:
            if self.ssl:
                h = HTTPSConnection(self.host)
            else:
                h = HTTPConnection(self.host)

            h.putrequest(method, self.path)
            #h.putheader("Host", self.host)  # required by HTTP/1.1
            h.putheader('User-Agent', 'Zope External Editor/%s' % __version__)
            h.putheader('Connection', 'close')

            for header, value in headers.items():
                h.putheader(header, value)

            h.putheader("Content-Length", str(len(body)))

            if self.metadata.get('auth','').startswith('Basic'):
                h.putheader("Authorization", self.metadata['auth'])

            if self.metadata.get('cookie'):
                h.putheader("Cookie", self.metadata['cookie'])

            h.endheaders()
            h.send(body)
            return h.getresponse()
        except:
            # On error return a null response with error info
            class NullResponse:
                def getheader(n,d): return d
                def read(): return ''
            
            response = NullResponse()
            response.reason = sys.exc_info()[1]
            try:
                response.status, response.reason = response.reason
            except:
                response.status = 0
            return response

def has_tk():
    """Sets up a suitable tk root window if one has not
       already been setup. Returns true if tk is happy,
       false if tk throws an error (like its not available)"""
    if not hasattr(globals(), 'tk_root'):
        # create a hidden root window to make Tk happy
        try:
            global tk_root
            from Tkinter import Tk
            tk_root = Tk()
            tk_root.withdraw()
            return 1
        except:
            return 0
    return 1
        
def fatalError(message, exit=1):
    """Show error message and exit"""
    message = 'FATAL ERROR:\n%s\n' % message
    try:
        if has_tk():
            from tkMessageBox import showerror
            showerror('Zope External Editor', message)
    finally:
        sys.stderr.write(message)
        if exit: sys.exit(0)

def whereIs(filename): 
    """Given a filename, returns the full path to it based
       on the PATH environment variable. If no file was found, None is returned
    """
    pathExists = os.path.exists
    
    if pathExists(filename):
        return filename
        
    pathJoin = os.path.join
    paths = os.environ['PATH'].split(os.pathsep)
    
    for path in paths:
        file_path = pathJoin(path, filename)
        if pathExists(file_path):
            return file_path

if __name__ == '__main__':
    try:
        ExternalEditor(sys.argv[1]).launch()
    except KeyboardInterrupt:
        pass
    except SystemExit:
        pass
    except:
        fatalError(sys.exc_info()[1],0)
        raise
