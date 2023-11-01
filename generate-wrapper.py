#! /usr/bin/env python3
# MIT License
#
# Copyright (c) 2021 Hein-Pieter van Braam-Stewart <hp@tmm.cx>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import sys
import string
import argparse
import textwrap
from datetime import datetime
from subprocess import check_output

try:
    from pycparser import c_parser, c_ast, parse_file, c_generator
    from pycparser.c_ast import Decl, FuncDecl, IdentifierType, TypeDecl, Struct, Union, PtrDecl, EllipsisParam, ArrayDecl, Typedef, Enum
except:
    print("pycparser not found.")
    print("Try installing it with pip install pycparser or using your distributions package manager.")
    sys.exit(1)

VERSION="0.4"
URL="https://github.com/hpvb/dynload-wrapper"
NOW=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
PROGNAME=sys.argv[0]
FLAGS=""

def stringify_declaration(ext, t):
    pointer=""

    while isinstance(t, PtrDecl):
        pointer+="*"
        t = t.type
    if isinstance(t, Decl):
        return stringify_declaration(ext, t.type)
    if isinstance(t, EllipsisParam):
        return "..."

    if isinstance(t.type, IdentifierType):
        return(f"{' '.join(t.quals)} {' '.join(t.type.names)}{pointer}")
    elif isinstance(t, ArrayDecl):
        if t.dim:
            return(f"{stringify_declaration(ext, t.type)} [{t.dim.value}]")
        else:
            return(f"{stringify_declaration(ext, t.type)} []")
    elif isinstance(t.type, TypeDecl):
        return(f"{' '.join(t.type.quals)} {' '.join(t.type.type.names)}{pointer}")
    elif isinstance(t.type, FuncDecl):
        params = []
        for param in t.type.args.params:
            params.append(stringify_declaration(ext, param, names))
        return(f"{' '.join(t.type.type.type.names)} (*{(t.type.type.declname)})({', '.join(params)})")
    elif isinstance(t.type, Enum):
        return(f"enum {t.type.name}")
    elif isinstance(t.type, Struct):
        return(f"struct {t.type.name}{pointer}")
    elif isinstance(t.type, Union):
        return(f"union {t.type.name}")
    elif isinstance(t.type, PtrDecl):
        return(f"{stringify_declaration(ext, t.type.type)}*")
    elif isinstance(t.type, ArrayDecl):
        if t.type.dim:
            return(f"{stringify_declaration(ext, t.type.type)} [{t.type.dim.value}]")
        else:
            return(f"{stringify_declaration(ext, t.type.type)} []")
    else:
        print(t)
        print(type(t.type))
        print(f"Unknown t type? {ext.name}")
        sys.exit(1)

def parse_header(filename, omit_prefix, initname, ignore_headers = [], ignore_all = False, include_headers = []):
    mydir = os.path.dirname(os.path.abspath(__file__))

    ast = parse_file(filename, use_cpp=True, cpp_path='gcc', cpp_args=['-E', '-include', f'{mydir}/attributes.h', '-I', f'{mydir}/fake_libc_include'])

    functions = []
    sym_definitions = []

    for ext in ast.ext:
        if isinstance(ext, Decl):
            params = []
            params_anon = []
            used_params = []
            if not isinstance(ext.type, FuncDecl):
                continue

            skip = False
            if omit_prefix:
                for o in omit_prefix:
                    if ext.name.startswith(o):
                        skip = True
                        break

            if ignore_headers:
                for h in ignore_headers:
                    if ext.coord.file.find(h) >= 0:
                        skip = True
                        break

            if not skip and ignore_all:
                skip = True
                for h in include_headers:
                    if ext.coord.file.find(h) >= 0:
                        skip = False
                        break

            if skip:
                continue

            for param in ext.type.args.params:
                params_anon.append(stringify_declaration(ext, param))

            sym_definitions.append(f"{stringify_declaration(ext, ext.type.type)} (*{ext.name}_dylibloader_wrapper_{initname})({','.join(params_anon)});".strip())
            functions.append(ext.name)

    return (functions, sym_definitions)

def generate_header(sysincludes, functions, initname):
    retval = []
    retval.append("// This file is generated. Do not edit!")
    retval.append(f"// see {URL} for details")
    retval.append(f"// generated by {PROGNAME} {VERSION} on {NOW}")
    retval.append(f"// flags: {FLAGS}")
    retval.append("//")
    retval.append("#include <stdint.h>\n")

    for function in functions:
        retval.append(f"#define {function} {function}_dylibloader_orig_{initname}")

    for include in sysincludes:
        if include.startswith("<"):
            retval.append(f"#include {include}")
        else:
            retval.append(f"#include \"{include}\"")

    for function in functions:
        retval.append(f"#undef {function}")

    retval.append("")
    return "\n".join(retval)

def write_implementation(filename, soname, sysincludes, initname, functions, sym_definitions):
    with open(filename, 'w') as file:
        file.write(generate_header(sysincludes, functions, initname))
        file.write("#include <dlfcn.h>\n")
        file.write("#include <stdio.h>\n")

        for sym_definition in sym_definitions:
            file.write(f"{sym_definition}\n")

        file.write(f"int initialize_{initname}(int verbose) {{\n")
        file.write("  void *handle;\n")
        file.write("  char *error;\n")
        file.write(f"  handle = dlopen(\"{soname}\", RTLD_LAZY);\n")
        file.write("  if (!handle) {\n")
        file.write("    if (verbose) {\n")
        file.write("      fprintf(stderr, \"%s\\n\", dlerror());\n")
        file.write("    }\n")
        file.write("    return(1);\n")
        file.write("  }\n")
        file.write("  dlerror();\n")

        for function in functions:
            file.write(f"// {function}\n")
            file.write(f"  *(void **) (&{function}_dylibloader_wrapper_{initname}) = dlsym(handle, \"{function}\");\n")
            file.write("  if (verbose) {\n")
            file.write("    error = dlerror();\n")
            file.write("    if (error != NULL) {\n")
            file.write("      fprintf(stderr, \"%s\\n\", error);\n")
            #file.write("     return(1);\n")
            file.write("    }\n")
            file.write("  }\n")

        file.write("return 0;\n");
        file.write("}\n")

def write_header(filename, sysincludes, initname, functions, sym_definitions):
    with open(filename, 'w') as file:
        file.write(f"#ifndef DYLIBLOAD_WRAPPER_{initname.upper()}\n")
        file.write(f"#define DYLIBLOAD_WRAPPER_{initname.upper()}\n")
        file.write(generate_header(sysincludes, functions, initname))
        file.write("#ifdef __cplusplus\n")
        file.write("extern \"C\" {\n")
        file.write("#endif\n")

        for function in functions:
            file.write(f"#define {function} {function}_dylibloader_wrapper_{initname}\n")

        for sym_definition in sym_definitions:
            file.write(f"extern {sym_definition}\n")

        file.write(f"int initialize_{initname}(int verbose);\n")

        file.write("#ifdef __cplusplus\n")
        file.write("}\n")
        file.write("#endif\n")
        file.write("#endif\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description = "A tool to generate wrappers for run-time dlopen()ing of libraries.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''
            Example usage for wrapping pulse:
            %(prog)s --include /usr/include/pulse/pulseaudio.h --sys-include '<pulse/pulseaudio.h>' --soname libpulse.so.0 --omit-prefix _pa_ --init-name pulse --output-header pulse.h --output-implementation pulse.c

            Example usage for wrapping X:
            %(prog)s --include /usr/include/X11/Xlib.h --include /usr/include/X11/Xutil.h --include /usr/include/X11/XKBlib.h  --sys-include '<X11/Xlib.h>' --sys-include '<X11/Xutil.h>' --sys-include '<X11/XKBlib.h>' --soname libX11.so.6 --init-name xlib --omit-prefix XkbGetDeviceIndicatorState --omit-prefix XkbAddSymInterpret --output-header xlib.h --output-implementation xlib.c
        ''')
    )
    parser.add_argument('--include', action='append', help='Include files to read (may appear more than once)', required=True)
    parser.add_argument('--sys-include', action='append', help='Include as they appear inside a program (eg <pulse/pulseaudio.h>) (may appear more than once)', required=True)
    parser.add_argument('--soname', help='Soname of the wrapped library (eg libpulse.so.0)', required=True)
    parser.add_argument('--init-name', help='Name to use for the initialize function. This will generate an initialize_<init-name> function. (eg pulse)', required=True)
    parser.add_argument('--output-header', help='Filename of the header to output', required=True)
    parser.add_argument('--output-implementation', help='Filename of the C file to output', required=True)
    parser.add_argument('--omit-prefix', action='append', help='Omit functions that start with this prefix (eg _pa_) (may appear more than once)', required=False)
    parser.add_argument('--ignore-headers', action='append', help='Ignore the named headers, no function defintions from these headers will be included in the wrapper', required=False)
    parser.add_argument('--ignore-other', action=argparse.BooleanOptionalAction, help='Ignore all header files not explicitly mentioned', required=False)
    
    args = parser.parse_args()
    FLAGS = " ".join(sys.argv)

    functions = []
    sym_definitions = []

    for filename in args.include:
        f, s = parse_header(filename, args.omit_prefix, args.init_name, args.ignore_headers, args.ignore_other, args.include)
        for item in f:
            if item not in functions:
                functions.append(item)

        for item in s: 
            if item not in sym_definitions:
                sym_definitions.append(item)

    write_implementation(args.output_implementation, args.soname, args.sys_include, args.init_name, functions, sym_definitions)
    write_header(args.output_header, args.sys_include, args.init_name, functions, sym_definitions)
