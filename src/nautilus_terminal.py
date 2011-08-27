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
    'term_on_top': True,
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
        self.swin.nt = self
        #Conf
        self._set_term_height(CONF['def_term_height'])
        self._visible = True

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


class Crowbar(object):
    """Modify the Nautilus' widget tree when the crowbar is inserted in it.

    Args:
        uri -- The URI of the current directory.
    """

    def __init__(self, uri):
        """The constructor."""
        self._uri = uri
        #Crowbar
        self._crowbar = Gtk.EventBox()
        self._crowbar.connect_after("parent-set", self._on_parent_set)
        #Lock
        self._lock = False

    def get_widget(self):
        """Returns the crowbar."""
        return self._crowbar

    def _on_parent_set(self, widget, old_parent):
        """Called when the crowbar is inserted in the Nautilus' widget tree.

        Args:
            widget -- The crowbar (self._crowbar)
            old_parent -- The previous parent of the crowbar (None...)
        """
        #Check if the work has already started
        if self._lock:
            return
        else:
            self._lock = True
        #Get the parents of the crowbar
        crowbar_p = self._crowbar.get_parent()
        crowbar_pp = crowbar_p.get_parent()
        crowbar_ppp = crowbar_pp.get_parent()
        #Get the childen of crowbar_pp
        crowbar_pp_children = crowbar_pp.get_children()
        #Check if our vpan is already there
        if type(crowbar_ppp) == Gtk.VPaned:
            #Find the Nautilus Terminal
            nterm = None
            for crowbar_ppp_child in crowbar_ppp.get_children():
                if type(crowbar_ppp_child) == Gtk.ScrolledWindow:
                    if hasattr(crowbar_ppp_child, "nt"):
                        nterm = crowbar_ppp_child.nt
                    break
            #Update the temrinal (cd,...)
            if nterm:
                nterm.change_directory(self._uri)
        #New tab/window/split
        else:
            #Create the vpan
            vpan = Gtk.VPaned()
            vpan.show()
            vbox = Gtk.VBox()
            vbox.show()
            if CONF['term_on_top']:
                vpan.add2(vbox)
            else:
                vpan.add1(vbox)
            #Add the vpan in Nautilus, and reparent some widgets
            if len(crowbar_pp_children) == 2:
                for crowbar_pp_child in crowbar_pp_children:
                    crowbar_pp.remove(crowbar_pp_child)
                crowbar_pp.pack_start(vpan, True, True, 0)
                vbox.pack_start(crowbar_pp_children[0], False, False, 0)
                vbox.pack_start(crowbar_pp_children[1], True, True, 0)
            #Create the terminal
            nt = NautilusTerminal(self._uri)
            if CONF['term_on_top']:
                vpan.add1(nt.get_widget())
            else:
                vpan.add2(nt.get_widget())


class NautilusTerminalProvider(GObject, Nautilus.LocationWidgetProvider):
    """Provides Nautilus Terminal in Nautilus."""

    def __init__(self):
        """The constructor."""
        print("Initializing nautilus-terminal extension")

    def get_widget(self, uri, window):
        """Returns a "crowbar" that will add a terminal in Nautilus.

        Args:
            uri -- The URI of the current directory.
            window -- The Nautilus' window.
        """
        #URI specific stuff
        if uri.startswith("x-nautilus-desktop:///"):
            return
        elif not uri.startswith("file:///"):
            uri = "file://%s" % os.environ["HOME"]
        #Return the crowbar
        return Crowbar(uri).get_widget()

    def _toggle_visible(self, window, event):
        """Toggle the visibility of Nautilus Terminal.

        This method is called on a "key-release-event" on the Nautilus'
        window.

        Args:
            window -- The Nautilus' window.
            event -- The detail of the event.
        """
        if event.keyval == 65473: #F4
            #TODO
            return True #Stop the event propagation


if __name__ == "__main__":
    #Code for testing Nautilus Terminal outside of Nautilus
    print("%s %s\nBy %s" % (__app_disp_name__, __version__, __author__))
    nterm = NautilusTerminal("file://%s" % os.environ["HOME"])
    nterm.get_widget().set_size_request(nterm.term.get_char_width() * 80 + 2,
            nterm.term.get_char_height() * 24 + 2)
    win = Gtk.Window()
    win.connect_after("destroy", Gtk.main_quit)
    win.add(nterm.get_widget())
    win.show_all()
    Gtk.main()