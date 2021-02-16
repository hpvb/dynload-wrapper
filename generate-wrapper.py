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

try:
    from pycparser import c_parser, c_ast, parse_file, c_generator
    from pycparser.c_ast import Decl, FuncDecl, IdentifierType, TypeDecl, Struct, PtrDecl, EllipsisParam, ArrayDecl, Typedef, Enum
except:
    print("pycparser not found.")
    print("Try installing it with pip install pycparser or using your distributions package manager.")
    sys.exit(1)

VERSION="0.1"
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
            return(f"{stringify_declaration(ext, t.type)} {' '.join(t.type.quals)} [{t.dim.value}]")
        else:
            return(f"{stringify_declaration(ext, t.type)} {' '.join(t.type.quals)} []")
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
    elif isinstance(t.type, PtrDecl):
        return(f"{stringify_declaration(ext, t.type.type)}*")
    elif isinstance(t.type, ArrayDecl):
        if t.type.dim:
            return(f"{stringify_declaration(ext, t.type.type)} {' '.join(t.quals)} [{t.type.dim.value}]")
        else:
            return(f"{stringify_declaration(ext, t.type.type)} {' '.join(t.quals)} []")
    else:
        print(t)
        print(type(t.type))
        print(f"Unknown t type? {ext.name}")
        sys.exit(1)

def parse_header(filename, omit_prefix):
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

            if skip:
                continue

            for param in ext.type.args.params:
                params_anon.append(stringify_declaration(ext, param))

            sym_definitions.append(f"{stringify_declaration(ext, ext.type.type)} (*{ext.name})({','.join(params_anon)});".strip())
            functions.append(ext.name)

    return (functions, sym_definitions)

def generate_header(sysincludes, functions):
    retval = []
    retval.append("// clang-format off")
    retval.append("// This file is generated. Do not edit!")
    retval.append(f"// see {URL} for details")
    retval.append(f"// generated by {PROGNAME} {VERSION} on {NOW}")
    retval.append(f"// flags: {FLAGS}")
    retval.append("//")
    retval.append("#include <dlfcn.h>")
    retval.append("#include <stdio.h>")

    for function in functions:
        retval.append(f"#define {function} {function}_orig")

    for include in sysincludes:
        retval.append(f"#include {include}")

    for function in functions:
        retval.append(f"#undef {function}")

    retval.append("")
    return "\n".join(retval)

def write_implementation(filename, soname, sysincludes, initname, functions, sym_definitions):
    with open(filename, 'w') as file:
        file.write(generate_header(sysincludes, functions))
        file.write("\n".join(sym_definitions))

        file.write(f"int initialize_{initname}() {{\n")
        file.write("  void *handle;\n")
        file.write("  char *error;\n")
        file.write(f"  handle = dlopen(\"{soname}\", RTLD_NOW | RTLD_DEEPBIND);\n")
        file.write("  if (!handle) {\n")
        file.write("    fprintf(stderr, \"%s\\n\", dlerror());\n")
        file.write("    return(1);\n")
        file.write("  }\n")
        file.write("  dlerror();\n")

        for function in functions:
            file.write(f"// {function}\n")
            #file.write(f"  *(void **) (&_sym_{function}) = dlsym(handle, \"{function}\");")
            file.write(f"  *(void **) (&{function}) = dlsym(handle, \"{function}\");\n")
            file.write("  error = dlerror();\n")
            file.write("  if (error != NULL) {\n")
            file.write("    fprintf(stderr, \"%s\\n\", error);\n")
            #file.write("    return(1);\n")
            file.write("  }\n")

        file.write("return 0;\n");
        file.write("}\n")

def write_header(filename, sysincludes, initname, functions, sym_definitions):
    with open(filename, 'w') as file:
        file.write(generate_header(sysincludes, functions))
        file.write("#ifdef __cplusplus\n")
        file.write("extern \"C\" {\n")
        file.write("#endif\n")

        for sym_definition in sym_definitions:
            file.write(f"extern {sym_definition}\n")
        file.write(f"int initialize_{initname}();\n")

        file.write("#ifdef __cplusplus\n")
        file.write("}\n")
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
    parser.add_argument('--omit-prefix', action='append', help='Function prefixes to omit (eg _pa_) (may appear more than once)', required=False)
    
    args = parser.parse_args()
    FLAGS = " ".join(sys.argv)

    functions = []
    sym_definitions = []

    for filename in args.include:
        f, s = parse_header(filename, args.omit_prefix)
        for item in f:
            if item not in functions:
                functions.append(item)

        for item in s: 
            if item not in sym_definitions:
                sym_definitions.append(item)


    write_implementation(args.output_implementation, args.soname, args.sys_include, args.init_name, functions, sym_definitions)
    write_header(args.output_header, args.sys_include, args.init_name, functions, sym_definitions)
