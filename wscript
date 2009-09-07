VERSION = "9999"
APPNAME = "portato"

srcdir = "."
blddir = "build"

def configure (conf):
    conf.check_tool("python")
    conf.check_tool("gcc")
    conf.check_tool("cython", tooldir="./waf_tools")
    conf.check_python_version((2,5))
    conf.check_python_headers()

def set_options (opt):
    from optparse import OptionGroup

    o = OptionGroup(opt.parser, "Package options")
    o.add_option("--with-eix", action = "store_true", default = True, help = "Enable the generation of the Eix-Parser (default).", dest = "eix")
    o.add_option("--without-eix", action = "store_false", default = True, help = "Disable the generation of the Eix-Parser.", dest="eix")
    o.add_option("--generate-cython", action = "store_true", default = False, help = "Force the regeneration of cython code.", dest="cython")

    opt.add_option_group(o)

# vim: ft=python
