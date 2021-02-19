/* This program create and display a basic window. The window has a 
 * default white background.
 *
 * Coded by:	Ross Maloney
 * Date:	August 2006
 * Modified by:	Abdellah Chelli
 * Date:	January 2015
 */

#include <stdlib.h>
#include <stdio.h>

#include "xlib-wrap.h"

int error_handler(Display*, XErrorEvent*);
static int do_buttonpress(XButtonEvent*, int, int);

int main(int argc, char *argv [])
{
  if(initialize_xlib(0)) {
    printf("Error initializing Xlib\n");
    return 1;
  }

  Display *mydisplay;
  XSetWindowAttributes myat;
  Window mywindow;
  XSizeHints wmsize;
  XWMHints wmhints;
  XTextProperty windowName, iconName;
  XEvent myevent;
  char *window_name = "Basic";
  char *icon_name = "Ba";
  int screen_num, done;
  unsigned long valuemask;
  int x, y , w, h;

	/* 1. open connection to the server */
  if ((mydisplay = XOpenDisplay(""))==NULL)
  {
    fprintf(stderr, "Unable to open connection with X server!\n"); 
  };

  XSetErrorHandler(error_handler);

	/* 2. create a top-level window */
  screen_num = DefaultScreen(mydisplay);
  x = 100; y = 200;
  w = 350; h = 250;
  //myat.background_pixel = WhitePixel(mydisplay, screen_num);
  myat.background_pixel = 0xFFFF00; //yellow RGB
  myat.border_pixel = BlackPixel(mydisplay, screen_num);
  myat.event_mask = ButtonPressMask | StructureNotifyMask;
  valuemask = CWBackPixel | CWBorderPixel | CWEventMask;
  mywindow = XCreateWindow(mydisplay, RootWindow(mydisplay, screen_num),
    x, y, w, h, 2,
    DefaultDepth(mydisplay, screen_num), InputOutput,
    DefaultVisual(mydisplay, screen_num),
    valuemask, &myat);

	/* 3. give the window manager hints */
  wmsize.flags = USPosition | USSize;
  XSetWMNormalHints(mydisplay, mywindow, &wmsize);
  wmhints.initial_state = NormalState;
  wmhints.flags = StateHint;
  XSetWMHints(mydisplay, mywindow, &wmhints);
  //XStringToTextProperty(&window_name, 1, &windowName);
  if (XStringListToTextProperty(&window_name, 1, &windowName)==0)
  {
    fprintf(stderr, "unable to allocate space for windowName\n");
  };
  XSetWMName(mydisplay, mywindow, &windowName);
  //XStringToTextProperty(&icon_name, 1, &iconName);
  if (XStringListToTextProperty(&icon_name, 1, &iconName)==0)
  {
    fprintf(stderr, "unable to allocate space for iconName\n");
  };
  XSetWMIconName(mydisplay, mywindow, &iconName);
  
	/* 4. establish window resources */
	/* 5. create all the other windows needed */
	/* 6. select events for each window */
	/* 7. map the windows */
  XMapWindow(mydisplay, mywindow);

	/* 8. enter the event loop */
  done = 0;
  while(done == 0)
  {
    XNextEvent(mydisplay, &myevent);
    switch(myevent.type)
    {
    case ButtonPress:
        done=do_buttonpress((XButtonEvent*) &myevent, w, h);
      break;
    case ConfigureNotify:
        w=((XConfigureEvent*)&myevent)->width;
        h=((XConfigureEvent*)&myevent)->height;
      break;
    }
  }

	/* 9. clean up before exiting */
  XUnmapWindow(mydisplay, mywindow);
  XDestroyWindow(mydisplay, mywindow);
  XCloseDisplay(mydisplay);
}

int
error_handler(Display* d, XErrorEvent* e)
{
  fprintf(stderr, "error: %u\n", e->error_code);
}

static int
do_buttonpress(XButtonEvent* e, int w, int h)
{
  fprintf(stdout, "x: %u, y: %u\n", e->x, e->y);
  /* couldn't get it to work, by getting window size using XWindowAttributes
  XWindowAttributes *attr;
  XGetWindowAttributes(e->display, e->window, attr);
  if ((e->x<attr->width/5)||(e->x>4*attr->width/5)||(e->y<attr->height/5)||(e->y>4*attr->height/5))
  */
  if ((e->x<w/5)||(e->x>4*w/5)||(e->y<h/5)||(e->y>4*h/5))
  {
    return 1;
  } else
  {
    XBell(e->display, 20);
    //XkbBell(e->display, e->root, 100, (Atom) NULL);
  };
  return 0;
}
