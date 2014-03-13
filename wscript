#! /usr/bin/env python
# encoding: utf-8
#

import sys, os, platform
from waflib.Configure import conf
from waflib import Options

top = '.'
out = 'wbuild'

ZMQ_VERSION = "4.1.0"

def options(opt):
	opt.load('compiler_c compiler_cxx')
	
	opt.add_option('--poller', action='store', default='', help='Choose polling system. valid values are kqueue, epoll, devpoll, poll or select [default=autodetect]"', dest='POLLER')
	opt.add_option('--tests', action='store_true', default=False, help='Build and launch all tests', dest='tests')
	opt.add_option('--disable-shared', action='store_true', default=False, help='Disable build of shared library', dest='shared')
	opt.add_option('--enable-static', action='store_true', default=False, help='Enable build of static library', dest='static')
	
def configure(conf):	
	conf.load('compiler_c')
	conf.load('compiler_cxx')

	#override windows lib pattern to lib%s.dll instead of %s.dll
	if platform.system() == "Windows":
		conf.env.cshlib_PATTERN = 'lib%s.dll'
		conf.env.cxxshlib_PATTERN = 'lib%s.dll'

	conf.env['STATIC'] = Options.options.static
	conf.env['SHARED'] = not Options.options.shared
	
	#Name of package
	conf.define('PACKAGE', "zeromq")
	#Define to the address where bug reports for this package should be sent.
	conf.define('PACKAGE_BUGREPORT', "zeromq-dev@lists.zeromq.org")
	#Define to the full name of this package. 
	conf.define('PACKAGE_NAME', "zeromq")
	#Define to the full name and version of this package.
	conf.define('PACKAGE_STRING', "zeromq %s", ZMQ_VERSION)
	#Define to the one symbol short name of this package. 
	conf.define('PACKAGE_TARNAME', "zeromq")
	#Define to the home page for this package. 
	conf.define('PACKAGE_URL', "")
	#Define to the version of this package.
	conf.define('PACKAGE_VERSION', ZMQ_VERSION)
	conf.define('VERSION', ZMQ_VERSION)
	
	if Options.options.POLLER == '':
		if not conf.check_cc(function_name='kqueue', header_name=['sys/event.h'], mandatory=False, define_name='ZMQ_USE_KQUEUE'):
			if not conf.check_cc(function_name='epoll_create', header_name=['sys/epoll.h'], mandatory=False, define_name='ZMQ_USE_EPOLL'):
				if not conf.check_cc(type_name='struct pollfd', header_name=['ssys/devpoll.h'], mandatory=False, define_name='ZMQ_USE_DEVPOLL'):
					if not conf.check_cc(function_name='poll', header_name=['poll.h'], mandatory=False, define_name='ZMQ_USE_POLL'):
						if platform.system() == "Windows":
							ret = conf.check_cc(function_name='select', header_name=['winsock2.h'], mandatory=False, define_name='ZMQ_USE_SELECT')
						else:
							ret = conf.check_cc(function_name='select', header_name=['sys/select.h'], mandatory=False, define_name='ZMQ_USE_SELECT')
						if not ret:
							conf.fatal("Could not autodetect polling method")
	
	conf.check(header_name='ifaddrs.h', mandatory=False, define_name='ZMQ_HAVE_IFADDRS')
	conf.check(header_name='windows.h', mandatory=False, define_name='ZMQ_HAVE_WINDOWS')
	conf.check(header_name='sys/uio.h', mandatory=False, define_name='ZMQ_HAVE_UIO')
	conf.check(header_name='sys/eventfd.h', mandatory=False, define_name='ZMQ_HAVE_EVENTFD')
	
	if platform.system() == "Windows":
		conf.check(lib='ws2_32', defines='HAVE_WS2_32')
		conf.check(lib='ws2', defines='HAVE_WS2')
		conf.check(lib='rpcrt4', defines='HAVE_RPCRT4')
		conf.check(lib='iphlpapi', defines='HAVE_IPHLPAPI')
	
	conf.check(lib='rt')
	conf.check(lib='pthread')
	
	conf.env.LIBS = ['IPHLPAPI', 'NSL', 'PTHREAD', 'RPCRT4', 'RT', 'SOCKET', 'WS2_32']
	
	conf.check_cc(function_name='clock_gettime', header_name="time.h", mandatory=False, define_name='HAVE_CLOCK_GETTIME')
	conf.check_cc(function_name='gethrtime', header_name="sys/time.h", mandatory=False, define_name='HAVE_GETHRTIME')
		
		
	#check compiler flags
	conf.env.CXXFLAGS = ['-g', '-O2']
	if conf.check(cxxflags='-Wall', mandatory=False):
		conf.env.CXXFLAGS += ['-Wall']
	if conf.check(cxxflags='-Wextra', mandatory=False):
		conf.env.CXXFLAGS += ['-Wextra']
	if conf.check(cxxflags='-Wno-long-long', mandatory=False):
		conf.env.CXXFLAGS += ['-Wno-long-long']
	if conf.check(cxxflags='-Wno-uninitialized', mandatory=False):
		conf.env.CXXFLAGS += ['-Wno-uninitialized']
	if conf.check(cxxflags='-pedantic', mandatory=False):
		conf.env.CXXFLAGS += ['-pedantic']
	
	conf.check_fragment()
	conf.check_platform()
		
	conf.write_config_header('platform.hpp')
	conf.defines = {}

	conf.env.DEFINES = ['_GNU_SOURCE', '_REENTRANT', '_THREAD_SAFE']
	if platform.system() == "Windows":
		conf.env.DEFINES += ['DLL_EXPORT']
		

def build(bld):
	#########################################################
	# build zmq
	#########################################################
	zmq_include = bld.path.ant_glob(['include/*.h', 'include/*.hpp'])
	zmq_sources = bld.path.ant_glob(['src/*.cpp'])

	if bld.env['STATIC'] == True:
		bld.stlib(
			source          = zmq_sources,
			name            = 'zmqa',
			target          = 'zmq',
			includes        = ['.', 'include'],
			#cxxflags        = [''],
			use				= bld.env.LIBS,
			install_path    = '${PREFIX}/lib'
		)

	if bld.env['SHARED'] == True:
		bld.shlib(
			source          = zmq_sources,
			name            = 'zmq',
			target          = 'zmq',
			includes        = ['.', 'include'],
			defines			= bld.env.DEFINES + (['DLL_EXPORT'] if platform.system() == "Windows" else []),
			#cxxflags        = [''],
			use				= bld.env.LIBS,
			install_path    = '${PREFIX}/lib'
		)
	
	bld.install_files('${PREFIX}/include', zmq_include)

	#########################################################
	# build and run tests
	#########################################################
	if Options.options.tests == True:
		test(bld)

def test(bld):
	bld.add_group()
	zmq_tests = bld.path.ant_glob(['tests/*.cpp'])
	for test in zmq_tests:
		testname = os.path.splitext(os.path.basename(test.abspath()))[0]
		bld(
			features='cxx cxxprogram test',
			source          = [test],
			name            = testname,
			target          = testname,
			includes        = ['.', 'include'],
			use				= ['zmq'] + bld.env.LIBS,
			install_path    = None,
		)
		#todo : add_group -> need to run test sequentially for now
		bld.add_group()

	from waflib.Tools import waf_unit_test
	bld.add_post_fun(waf_unit_test.summary)


@conf
def check_platform(conf):
	if platform.system() == "Windows":
		conf.define('ZMQ_HAVE_WINDOWS', 1)
		conf.define('ZMQ_HAVE_MINGW32', 1)
		
	if platform.system().startswith("CYGWIN"):	
		conf.define('ZMQ_HAVE_CYGWIN', 1)
		
	if platform.system() == "Linux":
		conf.define('ZMQ_HAVE_LINUX', 1)
	
	#todo : handle other OS
	"""
	Have AIX OS : ZMQ_HAVE_AIX
	Have Android OS : ZMQ_HAVE_ANDROID
	Have FreeBSD OS : ZMQ_HAVE_FREEBSD
	Have HPUX OS : ZMQ_HAVE_HPUX
	Have NetBSD OS : ZMQ_HAVE_NETBSD
	Have OpenBSD OS : ZMQ_HAVE_OPENBSD
	Have DarwinOSX OS : ZMQ_HAVE_OSX
	Have QNX Neutrino OS : ZMQ_HAVE_QNXNTO
	Have Solaris OS : ZMQ_HAVE_SOLARIS
	"""

@conf
def check_fragment(conf):
	#Whether SOCK_CLOEXEC is defined and functioning.
	#define ZMQ_HAVE_SOCK_CLOEXEC 1
	LIBZMQ_CHECK_SOCK_CLOEXEC = '''#include <sys/types.h>
#include <sys/socket.h>

int main (int argc, char *argv [])
{
    int s = socket (PF_INET, SOCK_STREAM | SOCK_CLOEXEC, 0);
    return (s == -1);
}'''
	conf.check(fragment=LIBZMQ_CHECK_SOCK_CLOEXEC, define_name='ZMQ_HAVE_SOCK_CLOEXEC', mandatory=False, \
		execute     = True, \
		msg="Checking for SOCK_CLOEXEC")

	#Whether SO_KEEPALIVE is supported.
	#define ZMQ_HAVE_SO_KEEPALIVE 1
	LIBZMQ_CHECK_SO_KEEPALIVE = '''#include <sys/types.h>
#include <sys/socket.h>
int main (int argc, char *argv []){
	int s, rc, opt = 1;
	return (
		((s = socket (PF_INET, SOCK_STREAM, 0)) == -1) ||
		((rc = setsockopt (s, SOL_SOCKET, SO_KEEPALIVE, (char*) &opt, sizeof (int))) == -1)
	);
}'''
	conf.check(fragment=LIBZMQ_CHECK_SO_KEEPALIVE, define_name='ZMQ_HAVE_SO_KEEPALIVE', mandatory=False, \
		execute     = True, \
		msg="Checking for SO_KEEPALIVE")

	#Whether TCP_KEEPCNT is supported.
	#define ZMQ_HAVE_TCP_KEEPCNT 1
	LIBZMQ_CHECK_TCP_KEEPCNT = '''#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/tcp.h>

int main (int argc, char *argv [])
{
    int s, rc, opt = 1;
    return (
        ((s = socket (PF_INET, SOCK_STREAM, 0)) == -1) ||
        ((rc = setsockopt (s, SOL_SOCKET, SO_KEEPALIVE, (char*) &opt, sizeof (int))) == -1) ||
        ((rc = setsockopt (s, IPPROTO_TCP, TCP_KEEPCNT, (char*) &opt, sizeof (int))) == -1)
    );
}'''
	conf.check(fragment=LIBZMQ_CHECK_TCP_KEEPCNT, define_name='ZMQ_HAVE_TCP_KEEPCNT', mandatory=False, \
		execute     = True, \
		msg="Checking for TCP_KEEPCNT")
		
	#Whether TCP_KEEPIDLE is supported.
	#define ZMQ_HAVE_TCP_KEEPIDLE 1
	LIBZMQ_CHECK_TCP_KEEPIDLE = '''#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/tcp.h>

int main (int argc, char *argv [])
{
    int s, rc, opt = 1;
    return (
        ((s = socket (PF_INET, SOCK_STREAM, 0)) == -1) ||
        ((rc = setsockopt (s, SOL_SOCKET, SO_KEEPALIVE, (char*) &opt, sizeof (int))) == -1) ||
        ((rc = setsockopt (s, IPPROTO_TCP, TCP_KEEPIDLE, (char*) &opt, sizeof (int))) == -1)
    );
}'''
	conf.check(fragment=LIBZMQ_CHECK_TCP_KEEPIDLE, define_name='ZMQ_HAVE_TCP_KEEPIDLE', mandatory=False, \
		execute     = True, \
		msg="Checking for TCP_KEEPIDLE")

	#Whether TCP_KEEPINTVL is supported.
	#define ZMQ_HAVE_TCP_KEEPINTVL 1
	LIBZMQ_CHECK_TCP_KEEPINTVL = '''#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/tcp.h>

int main (int argc, char *argv [])
{
    int s, rc, opt = 1;
    return (
        ((s = socket (PF_INET, SOCK_STREAM, 0)) == -1) ||
        ((rc = setsockopt (s, SOL_SOCKET, SO_KEEPALIVE, (char*) &opt, sizeof (int))) == -1) ||
        ((rc = setsockopt (s, IPPROTO_TCP, TCP_KEEPINTVL, (char*) &opt, sizeof (int))) == -1)
    );
}'''
	conf.check(fragment=LIBZMQ_CHECK_TCP_KEEPINTVL, define_name='ZMQ_HAVE_TCP_KEEPINTVL', mandatory=False, \
		execute     = True, \
		msg="Checking for TCP_KEEPINTVL")

	#Whether TCP_KEEPALIVE is supported.
	#define ZMQ_HAVE_TCP_KEEPALIVE 1
	LIBZMQ_CHECK_TCP_KEEPALIVE = '''#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/tcp.h>

int main (int argc, char *argv [])
{
    int s, rc, opt = 1;
    return (
        ((s = socket (PF_INET, SOCK_STREAM, 0)) == -1) ||
        ((rc = setsockopt (s, SOL_SOCKET, SO_KEEPALIVE, (char*) &opt, sizeof (int))) == -1) ||
        ((rc = setsockopt (s, IPPROTO_TCP, TCP_KEEPALIVE, (char*) &opt, sizeof (int))) == -1)
    );
}'''
	conf.check(fragment=LIBZMQ_CHECK_TCP_KEEPALIVE, define_name='ZMQ_HAVE_TCP_KEEPALIVE', mandatory=False, \
		execute     = True, \
		msg="Checking for TCP_KEEPALIVE")
