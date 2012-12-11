#!/usr/bin/env python

import os, sys, re
from configobj import ConfigObj, ConfigObjError, get_extra_values, flatten_errors, Section
from validate import Validator
from print_cfg import print_cfg
from mkdir_p import mkdir_p
from copy import deepcopy
import atexit
import shutil
from tempfile import mkdtemp

try:
    any
except NameError:
    # any() appeared in Python 2.5
    def any(iterable):
        for entry in iterable:
            if entry:
                return True
        return False

class globalcfg( object ):
    """Global (non suite-specific) site/user cylc configuration. See the
    configspec file conf/siterc/cfgspec for all primary item names and
    default values. """

    def __init__( self ):

        cfgspec = os.path.join( os.environ['CYLC_DIR'], 'conf', 'siterc', 'cfgspec' )

        self.rcfiles = {}
        self.rcfiles['site'] = os.path.join( os.environ['CYLC_DIR'], 'conf', 'siterc', 'site.rc' )
        self.rcfiles['user'] = os.path.join( os.environ['HOME'], '.cylc', 'user.rc' )

        self.sepcfg= {}

        rc = self.rcfiles['site']
        try:
            self.sepcfg['site'] = ConfigObj( infile=rc, configspec=cfgspec, _inspec=False )
        except ConfigObjError, x:
            print >> sys.stderr, x
            raise SystemExit( "ERROR, failed to load site config file: " + rc )

        # validate site file and load defaults for anything not set
        self.validate( self.sepcfg['site'] )

        rc = self.rcfiles['user']
        try:
            self.sepcfg['user'] = ConfigObj( infile=rc, configspec=cfgspec )
        except ConfigObjError, x:
            print >> sys.stderr, x
            raise SystemExit( "ERROR, failed to load user config file: " + rc )

        # validate user file without loading defaults for anything not set
        self.validate( deepcopy( self.sepcfg['user'] ) )

        self.block_user_cfg( self.sepcfg['user'], self.sepcfg['site'], self.sepcfg['site'].comments )

        # combined site and user configs (user takes precedence)
        self.cfg = {}
        self.inherit( self.cfg, self.sepcfg['site'] )
        self.inherit( self.cfg, self.sepcfg['user'] )

        # expand out environment variables etc.
        self.process()

    def write_rc( self, ftype=None ):
        if ftype not in [ 'site', 'user' ]:
            raise SystemExit( "ERROR, illegal file type for write_rc(): " + ftype )

        target = self.rcfiles[ ftype ] 

        if os.path.exists( target ):
            raise SystemExit( "ERROR, file already exists: " + target )

        # cfgobj.write() will write a config file directly, but we want
        # add a file header, filter out some lines, and comment out all
        # the default settings ... so read into a string and process.

        if target == 'site':
            preamble = """
#_______________________________________________________________________
#       This is your cylc site configuration file, generated by:
#               'cylc get-global-config --write-site'
#-----------------------------------------------------------------------
#    Users can override these settings in $HOME/.cylc/user.rc, see:
#               'cylc get-global-config --write-user'
#-----------------------------------------------------------------------
# At the time of writing this file contained all available config items,
# commented out with '#==>', with initial values determined by the cylc
# system defaults in $CYLC_DIR/conf/site/cfgspec.
#-----------------------------------------------------------------------
# ** TO CUSTOMIZE, UNCOMMENT AND MODIFY SPECIFIC SETTINGS AS REQUIRED **
#          (just the items whose values you need to change)
#-----------------------------------------------------------------------
"""
        else:
            preamble = """
#_______________________________________________________________________
#       This is your cylc user configuration file, generated by:
#               'cylc get-global-config --write-user'
#-----------------------------------------------------------------------
# At the time of writing this file contained all available config items,
# commented out with '#==>', with initial values determined by the local
# site config file $CYLC_DIR/conf/site/siter.rc, or by the cylc system
# defaults in $CYLC_DIR/conf/site/cfgspec.
#-----------------------------------------------------------------------
# ** TO CUSTOMIZE, UNCOMMENT AND MODIFY SPECIFIC SETTINGS AS REQUIRED **
#          (just the items whose values you need to change)
#-----------------------------------------------------------------------
"""
        cfg = deepcopy( self.sepcfg['site'] )

        outlines = preamble.split('\n')
        cfg.filename = None
        for line in cfg.write():
            if line.startswith( "#>" ):
                # omit comments specific to the spec file
                continue
            line = re.sub( '^(\s*)([^[#]+)$', '\g<1>#==> \g<2>', line )
            outlines.append(line)

        f = open( target, 'w' )
        for line in outlines:
            print >> f, line
        f.close()

        print "File written:", target
        print "See inside the file for usage instructions."

    def process( self ):
        # process temporary directory
        cylc_tmpdir = self.cfg['temporary directory']
        if not cylc_tmpdir:
            # use tempfile.mkdtemp() to create a new temp directory
            cylc_tmpdir = mkdtemp(prefix="cylc-")
            # self-cleanup
            atexit.register(lambda: shutil.rmtree(cylc_tmpdir))
            # now replace the original item
            self.cfg['temporary directory'] = cylc_tmpdir
        else:
            self.cfg['temporary directory'] = self.proc_dir( self.cfg['temporary directory'] )

        # expand environment variables and ~user in file paths
        for key,val in self.cfg['documentation']['files'].items():
            self.cfg['documentation']['files'][key] = os.path.expanduser( os.path.expandvars( val ))

        # expand variables in local directory paths, and create if necessary.
        self.cfg['hosts']['local']['run directory'] = self.proc_dir( self.cfg['hosts']['local']['run directory'] )
        self.cfg['hosts']['local']['workspace directory'] = self.proc_dir( self.cfg['hosts']['local']['workspace directory'] )
        self.cfg['pyro']['ports directory'] = self.proc_dir( self.cfg['pyro']['ports directory'] )

        # propagate host section defaults from the 'local' section
        for host in self.cfg['hosts']:
            for key,val in self.cfg['hosts'][host].items():
                if not val:
                    self.cfg['hosts'][host][key] = self.cfg['hosts']['local'][key]

    def proc_dir( self, path ):
        # expand environment variables and create dir if necessary.
        path = os.path.expandvars( os.path.expanduser( path ))
        try:
            mkdir_p( path )
        except Exception, x:
            print >> sys.stderr, x
            raise SystemExit( 'ERROR, illegal path? ' + dir )
        return path

    def validate( self, cfg ):
        # validate against the cfgspec and load defaults
        val = Validator()
        test = cfg.validate( val, preserve_errors=False, copy=True )
        if test != True:
            # Validation failed
            failed_items = flatten_errors( cfg, test )
            # Always print reason for validation failure
            for item in failed_items:
                sections, key, result = item
                print >> sys.stderr, ' ',
                for sec in sections:
                    print >> sys.stderr, sec, ' / ',
                print >> sys.stderr, key
                if result == False:
                    print >> sys.stderr, "ERROR, required item missing."
                else:
                    print >> sys.stderr, result
            raise SystemExit( "ERROR global config validation failed")
        extras = []
        for sections, name in get_extra_values( cfg ):
            extra = ' '
            for sec in sections:
                extra += sec + ' / '
            extras.append( extra + name )
        if len(extras) != 0:
            for extra in extras:
                print >> sys.stderr, '  ERROR, illegal entry:', extra 
            raise SystemExit( "ERROR illegal global config entry(s) found" )

    def inherit( self, target, source ):
        for item in source:
            if isinstance( source[item], dict ):
                if item not in target:
                    target[item] = {}
                self.inherit( target[item], source[item] )
            else:
                target[item] = source[item]

    def block_user_cfg( self, usercfg, sitecfg, comments={}, sec_blocked=False ):
        for item in usercfg:
            # iterate through sparse user config and check for attempts
            # to override any items marked '# SITE ONLY' in the spec.
            if isinstance( usercfg[item], dict ):
                if any( re.match( '^\s*# SITE ONLY\s*$', mem ) for mem in comments[item]):
                    # section blocked, but see if user actually attempts
                    # to set any items in it before aborting.
                    sb = True
                else:
                    sb = False
                self.block_user_cfg( usercfg[item], sitecfg[item], sitecfg[item].comments, sb )
            else:
                if any( re.match( '^\s*# SITE ONLY\s*$', mem ) for mem in comments[item]):
                    raise SystemExit( 'ERROR, item blocked from user override: ' + item )
                elif sec_blocked:
                    raise SystemExit( 'ERROR, section blocked from user override, item: ' + item )

    def dump( self, cfg_in=None ):
        if cfg_in:
            print_cfg( cfg_in, prefix='   ' )
        else:
            print_cfg( self.cfg, prefix='   ' )

    def get_task_work_dir( self, suite, task, host=None, owner=None ):
        # this goes under the top level workspace directory; it is
        # created on the fly, if necessary, by task job scripts.
        if host:
            work_root = self.cfg['hosts'][host]['workspace directory']
        else:
            work_root = self.cfg['hosts']['local']['workspace directory']
        if host or owner:
            # remote account: replace local home directory with '$HOME' 
            work_root  = re.sub( os.environ['HOME'], '$HOME', work_root )
        return os.path.join( work_root, suite, 'work', task )

    def get_suite_share_dir( self, suite, host=None, owner=None ):
        # this goes under the top level workspace directory; it is
        # created on the fly, if necessary, by task job scripts.
        if host:
            share_root = self.cfg['hosts'][host]['workspace directory']
        else:
            share_root = self.cfg['hosts']['local']['workspace directory']
        if host or owner:
            # remote account: replace local home directory, if present, with '$HOME' 
            share_root  = re.sub( os.environ['HOME'], '$HOME', share_root )
        return os.path.join( share_root, suite, 'share' )

    def get_suite_log_dir( self, suite, ext='suite', create=False ):
        path = os.path.join( self.cfg['hosts']['local']['run directory'], suite, 'log', ext )
        if create:
            self.proc_dir( path )
        return path

    def get_task_log_dir( self, suite, host=None, owner=None, create=False ):
        log_root = None
        if host:
            log_root = self.cfg['hosts'][host]['run directory']
        else:
            log_root = self.cfg['hosts']['local']['run directory']
        if host or owner:
            # remote account: replace local home directory, if present, with '$HOME' 
            log_root  = re.sub( os.environ['HOME'], '$HOME', log_root )
        path = os.path.join( log_root, suite, 'log', 'job' )
        if create:
            self.proc_dir( path )
        return path

