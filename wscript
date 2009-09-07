VERSION = "9999"
APPNAME = "portato"

srcdir = "."
blddir = "build"

def configure (conf):
    import Options
    
    # disable .pyc/.pyo compilation if not in local mode
    if not Options.options.local:
        Options.options.pyc = False
        Options.options.pyo = False

    conf.check_tool("python")
    conf.check_tool("gcc")
    conf.check_tool("misc")
    conf.check_tool("cython", tooldir="./waf_tools")
    conf.check_tool("replace", tooldir="./waf_tools")
    conf.check_python_version((2,5))
    conf.check_python_headers()

def set_options (opt):
    from optparse import OptionGroup

    o = OptionGroup(opt.parser, "Package options")
    o.add_option("--with-eix", action = "store_true", default = True, help = "Enable the generation of the Eix-Parser (default).", dest = "eix")
    o.add_option("--without-eix", action = "store_false", help = "Disable the generation of the Eix-Parser.", dest="eix")
    o.add_option("--with-nls", action = "store_true", default = True, help = "Enable NLS support (default).", dest="nls")
    o.add_option("--without-nls", action = "store_false", help = "Disable NLS support.", dest="nls")
    o.add_option("--force-cython", action = "store_true", default = False, help = "Force the regeneration of cython code.", dest="cython")

    opt.add_option_group(o)

    opt.add_option("--local", "-l", action = "store_true", default = False, help = "Local build")

def build (bld):
    bld.add_subdirs("portato")

# vim: ft=python
