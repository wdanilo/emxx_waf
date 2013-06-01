APPNAME = 'lunac'
VERSION = '0.1 alpha'

top = '.' 
out = 'build' 

from waflib.Configure import conf
from subprocess import Popen, PIPE
from waflib.Build import BuildContext, CleanContext, InstallContext, UninstallContext
from waflib import Logs
from waflib import ConfigSet, Options
import os

@conf
def recurse_all(ctx):
	cwd = ctx.path.abspath()
	for name in os.listdir(cwd):
		if os.path.isdir(os.path.join(cwd, name)):
			ctx.recurse(name)


import re
import os
@conf
def ant_regex(ctx, regex=r'*', exclude=r'_^'):
	files = []
	obj = re.compile(regex)
	obj_excl = re.compile(exclude)
	basepath = ctx.path.abspath()
	for path,_,filenames in os.walk(basepath):
		relpath = os.path.relpath(path,basepath)
		for filename in filenames:
			filerelpath = os.path.join(relpath,filename)
			if filerelpath[:2] == './':
				filerelpath = filerelpath[2:]
			if obj.match(filerelpath) and not obj_excl.match(filerelpath):
				files.append(filerelpath)
	return files


@conf
def register_tests(ctx, regex, **kwargs):
	files = ctx.ant_regex(regex)
	for file in files:
		output,_ = os.path.splitext(file)
		ctx.program(features = 'gtest',
		            source = [file],
		            includes = '.',
		            target = output,
					**kwargs)





def options(opt):
	opt.load('compiler_c compiler_cxx unittest_gtest flex')
	opt.load('eclipse')
	opt.load('msvs')
	#opt.add_option('--graph', action='store', default=None, help='gprof executables, which allows to generate gprof2dot graphs')
	opt.add_option('--default-variant', action='store', default=None, help='default build variant [auto, debug, release]')

def configure(cfg):
	def common_configure(cfg):
		from waflib.Tools.compiler_cxx import cxx_compiler
		cxx_compiler['linux'] = ['em++']
		#cfg.env.CC = 'gcc-4.7.2'
		#cfg.env.CXX = 'g++-4.7.2'
		cfg.env.FLEX = 'flex++'
		cfg.check_cfg(package='', path='llvm-config', args='--cppflags --ldflags --libs core jit native bitwriter bitreader asmparser linker', uselib_store='LLVM')
		cfg.load('compiler_c compiler_cxx unittest_gtest flex')
		cfg.env.append_value('CXXFLAGS', ['-g', '-std=c++11', '-Wall', '-D__GXX_EXPERIMENTAL_CXX0X__'])
		cfg.env.append_value('LINKFLAGS', ['-lprotobuf', '-rdynamic'])
		cfg.env.append_value('INCLUDES', ['include'])
		cfg.env.FLEXFLAGS.append('--header-file=include/lex.yy.hh')

	common_configure(cfg)
	
	cfg.setenv('release')
	common_configure(cfg)
	cfg.env.append_value('CXXFLAGS', ['-O3', '-fomit-frame-pointer', '-fPIC'])
	cfg.write_config_header('release/include/config.h')
	cfg.env.append_value('INCLUDES', ['build/release/include'])

	cfg.setenv('debug')
	common_configure(cfg)
	cfg.env.append_value('CXXFLAGS', ['-O0'])
	cfg.define('DEBUG', 1)
	cfg.write_config_header('debug/include/config.h')
	cfg.env.append_value('INCLUDES', ['../../include'])

	cfg.setenv('gprof')
	common_configure(cfg)
	#cfg.check_cc(lib='tcmalloc_and_profiler')
	cfg.env.append_value('CXXFLAGS', ['-O2', '-fno-omit-frame-pointer', '-fPIC', '-pg'])
	cfg.env.append_value('LINKFLAGS', ['-pg'])
	cfg.define('PROFILE', 1)
	cfg.write_config_header('gprof/include/config.h')
	cfg.env.append_value('INCLUDES', ['build/gprof/include'])


def build(bld):
	if not bld.variant:
		bld.fatal('No build variant specified. Exiting.')
	defaults = Defaults(bld)
	defaults['last_variant'] = bld.variant
	defaults.store()

	bld(export_includes = 'include')
	bld.recurse('tools')
	bld.recurse('lib')
	#bld.add_post_fun(post)

	import platform
	import datetime
	date = datetime.datetime.now()
	bld.define('BUILD_DATE', date.strftime("%Y-%m-%d %H:%M"))
	bld.define('BUILD_PLATFORM', platform.platform())
	bld.write_config_header('include/build_info.hpp')

class debug(BuildContext): 
        cmd = 'debug'
        variant = 'debug'

class release(BuildContext): 
        cmd = 'release'
        variant = 'release'

class gprof(BuildContext): 
        cmd = 'gprof'
        variant = 'gprof'


def init(ctx):
	from waflib.extras.eclipse import eclipse
	from waflib.extras.msvs import msvs_generator
	eclipse.variant = 'debug'
	msvs_generator.variant = 'debug'

	defaults = Defaults(ctx)
	if Options.options.default_variant is not None:
		defaults['default_variant'] = Options.options.default_variant
		ctx.msg('Default build variant', defaults['default_variant'])	
	

	if defaults['default_variant'] == 'auto':
		current_variant = defaults['last_variant']
	else:
		current_variant = defaults['default_variant']

	
	for y in (BuildContext, CleanContext, InstallContext, UninstallContext):
		class tmp(y):
			variant = current_variant
	defaults.store()

def defaults(ctx):
	d = Defaults(ctx)
	d.load()
	print(d)


class Defaults(object):
	def __init__(self, ctx, load=True):
		self.ctx = ctx
		self.path = 'build/c4che/defaults.py'
		self.env = ConfigSet.ConfigSet()
		if load:
			self.load()
	
	def init(self):
		self.env.default_variant = 'auto'
		self.env.last_variant = 'debug'

	def load(self):
		try:
			self.env.load(self.path)
		except:
			self.ctx.msg('Creating new defaults configuration', True)
			self.init()

	def store(self):
		self.env.store(self.path)

	def items(self):
		for key in self.env.keys():
			val = getattr(self.env, key)
			yield key, val

	def __getitem__(self, item):
		return self.env[item]

	def __setitem__(self, item, value):
		self.env[item] = value

	def __str__(self):
		return str(self.env)

def set(ctx):
	defaults(ctx)


'''
def post(ctx):
	if ctx.cmd == 'gprof':
		target = ctx.options.graph
		if not target:
			return
		raise Exception('NIE DZIALA NA RAZIE')
		Logs.pprint('GREEN','executing %s' % target)
		cwd = os.getcwd()
		path, filename = os.path.split(target)
		fullpath = os.path.join(cwd, out, 'gprof', path)
		fulltarget = os.path.join(fullpath, filename)
		os.chdir(fullpath)
		ctx.exec_command(fulltarget)

		Logs.pprint('GREEN','drawing graph')
		imagename = '%s.png'%filename
		#ctx.exec_command('gprof %s | gprof2dot | dot -Tpng -o %s'%(filename, imagename))
		#ctx.exec_command('gprof %s | gprof2dot | sfdp -Gsize=67! -Goverlap=prism -Tpng -o %s'%(filename, imagename))
		os.chdir(cwd)
'''

