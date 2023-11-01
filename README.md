# Dynload wrapper

This program will generate a wrapper to make it easy to `dlopen()` shared objects on Linux without writing a ton of boilerplate code.

This is useful when shipping binaries to users which may or may not have some optional dependencies installed. Particularly pulseaudio can be an issue as there are some Linux users vehemently against using it. Using this tool to generate pulse wrappers allows the program to gracefully fall back on a different sound library without requiring libpulse to be available on the users' system. (Note that the actual fallback code is the domain of the program, the wrapper generation cannot do this for you)

The program works by parsing the header file(s) related to the binary and figuring out what functions exist. It will then generate a header which `#include`'s the orignal header, it renames all the function definitions in the orignal header to `_dylibloader_orig_<init-name>`, generate it's own `_dylibloader_wrap_<init-name>` definitions, and finally renames the original function as well. This means that for the code using the functions there is no difference, but we won't clash with the 'real' symbols if they manage to be loaded by a different dependency somewhere. These function pointers will be resolved by `dlsym()` when calling the `initialize_<init-name>()`.

Generally speaking all that should be required is generating the header and c file, replacing the `#include`s of the normal library with the generated ones, and calling the initialize function before starting to use the library. There are some examples in the examples/ directory which show how to do this.

# Caveats

Generally speaking this works fine, but if you link to libraries that themselves require the symbols of the dlopen()'d library you *must* call the initialize function *first* before using it. An example of this is alsa which on pulse-enabled systems will itself try to use pulse symbols. In this case you *must* initialize the pulse wrappers before using alsa.

# Tested libraries

 * Xlib
 * Alsa
 * PulseAudio
 * Udev

# Help
```
$ ./generate-wrapper.py --help
usage: generate-wrapper.py [-h] --include INCLUDE --sys-include SYS_INCLUDE --soname SONAME --init-name INIT_NAME --output-header OUTPUT_HEADER --output-implementation OUTPUT_IMPLEMENTATION [--omit-prefix OMIT_PREFIX]
                           [--ignore-headers IGNORE_HEADERS] [--ignore-other | --no-ignore-other]

A tool to generate wrappers for run-time dlopen()ing of libraries.

options:
  -h, --help            show this help message and exit
  --include INCLUDE     Include files to read (may appear more than once)
  --sys-include SYS_INCLUDE
                        Include as they appear inside a program (eg <pulse/pulseaudio.h>) (may appear more than once)
  --soname SONAME       Soname of the wrapped library (eg libpulse.so.0)
  --init-name INIT_NAME
                        Name to use for the initialize function. This will generate an initialize_<init-name> function. (eg pulse)
  --output-header OUTPUT_HEADER
                        Filename of the header to output
  --output-implementation OUTPUT_IMPLEMENTATION
                        Filename of the C file to output
  --omit-prefix OMIT_PREFIX
                        Omit functions that start with this prefix (eg _pa_) (may appear more than once)
  --ignore-headers IGNORE_HEADERS
                        Ignore the named headers, no function defintions from these headers will be included in the wrapper
  --ignore-other, --no-ignore-other
                        Ignore all header files not explicitly mentioned

Example usage for wrapping pulse:
generate-wrapper.py --include /usr/include/pulse/pulseaudio.h --sys-include '<pulse/pulseaudio.h>' --soname libpulse.so.0 --omit-prefix _pa_ --init-name pulse --output-header pulse.h --output-implementation pulse.c

Example usage for wrapping X:
generate-wrapper.py --include /usr/include/X11/Xlib.h --include /usr/include/X11/Xutil.h --include /usr/include/X11/XKBlib.h  --sys-include '<X11/Xlib.h>' --sys-include '<X11/Xutil.h>' --sys-include '<X11/XKBlib.h>' --soname libX11.so.6 --init-name xlib --omit-prefix XkbGetDeviceIndicatorState --omit-prefix XkbAddSymInterpret --output-header xlib.h --output-implementation xlib.c
```
