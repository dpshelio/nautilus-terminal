#!/usr/bin/python
# -*- coding: UTF-8 -*-

############################################################################
##                                                                        ##
## Nautilus Terminal - A terminal embedded in Nautilus                    ##
##                                                                        ##
## Copyright (C) 2010-2011  Fabien LOISON <flo at flogisoft dot com>      ##
##                                                                        ##
## This program is free software: you can redistribute it and/or modify   ##
## it under the terms of the GNU General Public License as published by   ##
## the Free Software Foundation, either version 3 of the License, or      ##
## (at your option) any later version.                                    ##
##                                                                        ##
## This program is distributed in the hope that it will be useful,        ##
## but WITHOUT ANY WARRANTY; without even the implied warranty of         ##
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          ##
## GNU General Public License for more details.                           ##
##                                                                        ##
## You should have received a copy of the GNU General Public License      ##
## along with this program.  If not, see <http://www.gnu.org/licenses/>.  ##
##                                                                        ##
##                                                                        ##
## WEB SITE: http://software.flogisoft.com/nautilus-terminal/             ##
##                                                                        ##
############################################################################


"""A terminal embedded in Nautilus."""

__author__ = "Fabien LOISON <flo at flogisoft dot com>"
__version__ = "1.0"
__appname__ = "nautilus-terminal"
__app_disp_name__ = "Nautilus Terminal"


import os
import urllib

from gobject import GObject
from gi.repository import Nautilus, Gtk, Vte, GLib


CONF = {
    'shell': Vte.get_user_shell(),
    'def_term_height': 5, #lines
    'def_visible': True,
    }


class NautilusTerminal(object):
    """Nautilus Terminal itself.

    Args:
        uri -- The URI of the folder where the terminal will be created.
    """

    def __init__(self, uri):
        """The constructor."""
        #Term
        self.shell_pid = -1
        self.term = Vte.Terminal()
        self.shell_pid = self.term.fork_command_full(Vte.PtyFlags.DEFAULT,
                self._uri_to_path(uri), [CONF['shell']], None,
                GLib.SpawnFlags.SEARCH_PATH, None, self.shell_pid)[1]
        #Swin
        self.swin = Gtk.ScrolledWindow()
        #Conf
        self._set_term_height(CONF['def_term_height'])
        self._visible = True

    def has_parent(self):
        """Check if Nautilus Terminal has a parent gtk container"""
        if self.swin.get_parent():
            return True
        else:
            return False

    def change_directory(self, uri):
        """Change the current directory in the shell if it is not busy.

        Args:
            uri -- The URI of the destination directory.
        """
        if uri[:7] == "file://" and not self._shell_is_busy():
            cdcmd = " cd '%s'\n" % self._uri_to_path(uri).replace("'", r"'\''")
            #self.term.feed("\033[8m", len("\033[8m"))
            self.term.feed_child(cdcmd, len(cdcmd))

    def get_widget(self):
        """Return the top-level widget of Nautilus Terminal."""
        if not self.term.get_parent():
            self.swin.add(self.term)
        if self._visible:
            self.swin.show_all()
        return self.swin

    def set_visible(self, visible):
        """Change the visibility of Nautilus Terminal

        Args:
            visible -- True for showing Nautilus Terminal, False for hiding.
        """
        self._visible = visible
        if visible:
            self.swin.show_all()
        else:
            self.swin.hide()

    def _shell_is_busy(self):
        """Check if the shell is waiting for a command or not."""
        wchan_path = "/proc/%i/wchan" % self.shell_pid
        wchan = open(wchan_path, "r").read()
        if wchan != "n_tty_read":
            return True
        else:
            return False

    def _uri_to_path(self, uri):
        """Returns the path corresponding of the given URI.

        Args:
            uri -- The URI to convert."""
        return urllib.url2pathname(uri[7:])

    def _set_term_height(self, height):
        """Change the terminal height.

        Args:
            height -- The new height (in lines).
        """
        self.swin.set_size_request(-1,
                height * self.term.get_char_height() + 2)


class NautilusTerminalProvider(GObject, Nautilus.LocationWidgetProvider):
    """Provides Nautilus Terminal in Nautilus."""

    def __init__(self):
        """The constructor."""
        print("Initializing nautilus-terminal extension")

    def get_widget(self, uri, window):
        """Return the top-level widget of a Nautilus Terminal.

        Args:
            uri -- The URI of the current directory.
            window -- The Nautilus' window.
        """
        #Init
        if not hasattr(window, "terms"):
            window.terms = []
        if not hasattr(window, "visible"):
            window.visible = CONF['def_visible']
        #URI specific stuff
        if uri.startswith("x-nautilus-desktop:///"):
            return
        elif not uri.startswith("file:///"):
            uri = "file://%s" % os.environ["HOME"]
        #Try to re-use an existing terminal
        nt = None
        for item in window.terms:
            if not item.has_parent():
                nt = item
                break #FIXME: remove unused terms
        #New terminal
        if not nt:
            nt = NautilusTerminal(uri)
            nt.set_visible(window.visible)
            window.terms.append(nt)
        else:
            nt.change_directory(uri)
        window.connect_after("key-release-event", self._toggle_visible)
        return nt.get_widget()

    def _toggle_visible(self, window, event):
        """Toggle the visibility of Nautilus Terminal.

        This method is called on a "key-release-event" on the Nautilus'
        window.

        Args:
            window -- The Nautilus' window.
            event -- The detail of the event.
        """
        if event.keyval == 65473: #F4
            window.visible = not window.visible
            for nt in window.terms:
                nt.set_visible(window.visible)
            return True #Stop the event propagation


if __name__ == "__main__":
    #Code for testing nautilus terminal outside of Nautilus
    print("%s %s\nBy %s" % (__app_disp_name__, __version__, __author__))
    nterm = NautilusTerminal("file://%s" % os.environ["HOME"])
    nterm.get_widget().set_size_request(nterm.term.get_char_width() * 80 + 2,
            nterm.term.get_char_height() * 24 + 2)
    win = Gtk.Window()
    win.connect_after("destroy", Gtk.main_quit)
    win.add(nterm.get_widget())
    win.show_all()
    Gtk.main()
