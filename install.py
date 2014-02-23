#!/usr/bin/python
# -*- Mode: python; coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
#
#    install.py
#
#    An RBPluginInstaller for RatingFilters.
#    Copyright (C) 2014 Donagh Horgan <donagh.horgan@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from rbpi import RBPluginInstaller

plugin_files_path = {
    '2.95': './release/2.97',
    '2.96': './release/2.97',
    '2.97': './release/2.97',
    '2.98': './release/2.98',
    '2.99': './release/2.99',
    '3.0': './release/3.0',
    '3.0.1': './release/3.0',
    'dev': './dev'
}
common_files = [
    'README', 'LICENSE', './common/RatingFiltersPreferences.ui'
]
glib_schema = './common/org.gnome.rhythmbox.plugins.rating_filters.gschema.xml'

if __name__ == "__main__":
    RBPluginInstaller('RatingFilters', plugin_files_path,
                      common_files=common_files, glib_schema=glib_schema)
