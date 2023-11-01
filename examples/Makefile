all: alsa xlib paplay

pulse-wrap.o: pulse-wrap.c
	$(CC) -c -o pulse-wrap.o pulse-wrap.c

sndfile-wrap.o: sndfile-wrap.c
	$(CC) -c -o sndfile-wrap.o sndfile-wrap.c

paplay.o: paplay.c pulse-wrap.h sndfile-wrap.h
	$(CC) -c -o paplay.o paplay.c

pulse-wrap.c pulse-wrap.h:
	../generate-wrapper.py --include /usr/include/pulse/pulseaudio.h --sys-include '<pulse/pulseaudio.h>' --soname libpulse.so.0 --omit-prefix _pa_ --init-name pulse --output-header pulse-wrap.h --output-implementation pulse-wrap.c

sndfile-wrap.c sndfile-wrap.h:
	../generate-wrapper.py --include /usr/include/sndfile.h --sys-include '<sndfile.h>' --soname libsndfile.so.1 --init-name sndfile --output-header sndfile-wrap.h --output-implementation sndfile-wrap.c

paplay: paplay.o sndfile-wrap.o pulse-wrap.o
	$(CC) paplay.o pulse-wrap.o sndfile-wrap.o -o paplay -ldl

xlib-wrap.o: xlib-wrap.c
	$(CC) -c -o xlib-wrap.o xlib-wrap.c

xlib.o: xlib.c xlib-wrap.h
	$(CC) -c -o xlib.o xlib.c

xlib-wrap.c xlib-wrap.h:
	../generate-wrapper.py --ignore-other --include /usr/include/X11/Xlib.h --include /usr/include/X11/Xutil.h --include /usr/include/X11/XKBlib.h  --sys-include '<X11/Xlib.h>' --sys-include '<X11/Xutil.h>' --sys-include '<X11/XKBlib.h>' --soname libX11.so.6 --init-name xlib --omit-prefix XkbGetDeviceIndicatorState --omit-prefix XkbAddSymInterpret --output-header xlib-wrap.h --output-implementation xlib-wrap.c

xlib: xlib.o xlib-wrap.o
	$(CC) xlib.o xlib-wrap.o -o xlib -ldl

alsa-wrap.o: alsa-wrap.c
	$(CC) -c -o alsa-wrap.o alsa-wrap.c

alsa.o: alsa.c alsa-wrap.h
	$(CC) -c -o alsa.o alsa.c

alsa-wrap.c alsa-wrap.h:
	../generate-wrapper.py --include /usr/include/alsa/asoundlib.h --sys-include '<alsa/asoundlib.h>' --soname libasound.so.2 --init-name asound --output-header alsa-wrap.h --output-implementation alsa-wrap.c

alsa: alsa.o alsa-wrap.o
	$(CC) alsa.o alsa-wrap.o -o alsa -ldl

clean:
	rm -f *-wrap* *.o alsa xlib paplay
