# -*- Mode: python; coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
#
#   RatingFilters.py
#
#   Rating filters for the library browser.
#   Copyright (C) 2013 Donagh Horgan <donagh.horgan@gmail.com>
#
#   Preferences class code adapted from Magnatune plugin and CoverArt plugin
#   Copyright (C) 2006 Adam Zimmerman  <adam_zimmerman@sfu.ca>
#   Copyright (C) 2006 James Livingston  <doclivingston@gmail.com>
#   Copyright (C) 2012 - fossfreedom
#   Copyright (C) 2012 - Agustin Carrasco
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import GObject
from gi.repository import Peas
from gi.repository import RB
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import Gio
from gi.repository import PeasGtk

import rb

class RatingFiltersPlugin (GObject.Object, Peas.Activatable):
    '''
    Main class for the RatingFilters plugin. Contains functions for setting 
    up the UI, callbacks for user actions, and functions for filtering query 
    models and refreshing the display.
    '''
    object = GObject.property (type = GObject.Object)

    def __init__(self):
        GObject.Object.__init__(self)

    def log(self, function_name, message, error=False):
        '''
        Generic function for logging - will save Python 3 related slip ups.
        '''
        if error:
            message_type = 'ERROR'
        else:
            message_type = 'DEBUG'
        print(function_name + ': ' + message_type + ': ' + message)

    def do_activate(self):
        '''
        Creates and links UI elements and creates class variables.
        '''
        self.log(self.do_activate.__name__, 'Activating plugin...')

        self.settings = Gio.Settings(
            'org.gnome.rhythmbox.plugins.rating_filters'
            )
        self.settings.connect(
            'changed::favourites-threshold', 
            self.on_favourites_threshold_changed
            )
        
        app = Gio.Application.get_default()
        self.app_id = 'rating-filters'
        self.filter_names = ['All Ratings', 'Favourites', 'Unrated']
        self.target_values = {
            'All Ratings': GLib.Variant.new_string('rating-filters-all-ratings'),
            'Favourites': GLib.Variant.new_string('rating-filters-favourites'),
            'Unrated': GLib.Variant.new_string('rating-filters-unrated')
            }
        self.locations = ['library-toolbar', 'playlist-toolbar']
        self.visited_pages = {}
        self.active_filter = {}
        
        action_name = 'rating-filters'
        self.action = Gio.SimpleAction.new_stateful(
            action_name, GLib.VariantType.new('s'),
            self.target_values['All Ratings']
            )
        self.action.connect("activate", self.filter_change_cb)
        app.add_action(self.action)
        
        menu_item = Gio.MenuItem()
        section = Gio.Menu()
        menu = Gio.Menu()
        toolbar_item = Gio.MenuItem()
        for filter_name in self.filter_names:
            menu_item.set_label(filter_name)
            menu_item.set_action_and_target_value(
                'app.' + action_name, self.target_values[filter_name]
                )
            section.append_item(menu_item)
        menu.append_section(None, section)
        toolbar_item.set_label('Filter')
        toolbar_item.set_submenu(menu)
        for location in self.locations:
            app.add_plugin_menu_item(location, self.app_id, toolbar_item)

    def do_deactivate(self):
        '''
        Unlinks UI elements and resets entry views.
        '''
        self.log(self.do_deactivate.__name__, 'Deactivating plugin...')
        
        for page in self.visited_pages:
            [_, query_models, t] = self.visited_pages[page]
            self.visited_pages[page] = ['All Ratings', query_models, t]
            self.refresh(page)

        app = Gio.Application.get_default()
        for location in self.locations:
            app.remove_plugin_menu_item(location, self.app_id)

    def target_value_to_filter_name(self, target_value):
        '''
        Converts target values to filter names.
        '''
        filter_names = dict(zip(self.target_values.values(), self.target_values.keys()))
        return filter_names[target_value]
        
    def filter_change_cb(self, action, current):
        '''
        Called when the filter state on a page is changed. Sets the new 
        state and triggers a refresh of the entry view.
        '''
        action.set_state(current)
        
        shell = self.object
        page = shell.props.selected_page
        self.active_filter[page] = self.target_value_to_filter_name(current)
        
        self.change_filter()
    
    def change_filter(self):
        '''
        Changes the filter model on the selected page.
        '''        
        if len(self.visited_pages) == 0:
            self.set_callbacks() # set callbacks on first run
        
        shell = self.object
        page = shell.props.selected_page
        
        self.log(
            self.change_filter.__name__,
            'Changing filter on ' + page.props.name
            )

        t = self.get_favourites_threshold()
        active_filter = self.active_filter[page]
        if page in self.visited_pages:
            [_, query_models, t0] = self.visited_pages[page]
            if (active_filter not in query_models or 
                (active_filter == 'Favourites' and t0 != t)):
                query_models[active_filter] = self.filter_query_model(
                    active_filter, query_models['All Ratings']
                    )
            self.visited_pages[page] = [active_filter, query_models, t]
            self.refresh(page)
        else:
            query_models = {}
            query_model = page.get_entry_view().props.model
            query_models['All Ratings'] = self.filter_query_model(
                'All Ratings', query_model
                )
            query_models[active_filter] = self.filter_query_model(
                active_filter, query_model
                )

            self.visited_pages[page] = [active_filter, query_models, t]
            self.refresh(page)
    
    def set_callbacks(self):
        '''
        Sets callbacks to detect UI interactions, should be called only 
        after the rating filters are first activated.
        '''
        shell = self.object
        shell.props.display_page_tree.connect(
            "selected", self.on_page_change
            )
        shell.props.selected_page.connect(
            "filter-changed", self.on_browser_change
            )
        shell.props.db.connect(
            'entry-changed', self.on_entry_change
            )

    def get_favourites_threshold(self):
        '''
        Returns the current favourites threshold.
        '''
        return self.settings['favourites-threshold']

    def on_favourites_threshold_changed(self, settings, key):
        '''
        Refreshes the view when the favourites threshold preference is 
        changed.
        '''
        shell = self.object
        page = shell.props.selected_page
        
        self.log(
            self.on_favourites_threshold_changed.__name__, 
            'Favourites threshold changed on ' + page.props.name
            )        
        
        if page in self.active_filter:
            if self.active_filter[page] == 'Favourites':
                self.change_filter()

    def on_entry_change(self, db, entry, changes):
        '''
        Called when an entry in the current view is changed. If the user has 
        changed a track's rating, and the new rating should be filtered out, 
        then the page is refreshed.
        '''
        # This isn't working like it used to: the changes object no longer 
        # has a values property, so we can't check to see what was changed. 
        # For now, we'll just refresh everything each time something is 
        # changed, although this isn't ideal.
        
        #change = changes.values
        
        #if change.prop is RB.RhythmDBPropType.RATING:
        if True:
            for page in self.visited_pages:
                [active_filter, query_models, t] = self.visited_pages[page]
                query_model = query_models['All Ratings']
                entries = [row[0] for row in query_model]
                if entry in entries:
                    if "Favourites" in query_models:
                        del query_models["Favourites"]
                    if "Unrated" in query_models:
                        del query_models["Unrated"]
                    self.visited_pages[page] = [
                        active_filter,query_models, t
                        ]
                        
            shell = self.object
            self.on_page_change(None, shell.props.selected_page)

    def on_browser_change(self, action):
        '''
        Called when the library browser for a visited page changes. Reapplies 
        the active filter to the new query model.
        '''
        shell = self.object
        page = shell.props.selected_page

        self.log(
            self.on_browser_change.__name__, 
            "Browser changed on page " + page.props.name
            )

        query_models = {}
        query_model = page.get_entry_view().props.model

        active_filter = 'All Ratings'
        query_models[active_filter] = self.filter_query_model(
            active_filter, query_model
            )

        [active_filter, _, t] = self.visited_pages[page]
        query_models[active_filter] = self.filter_query_model(
            active_filter, query_model
            )

        self.visited_pages[page] = [active_filter, query_models, t]
        self.refresh(page)

    def on_page_change(self, display_page_tree, page):
        '''
        Called when the display page changes. Grabs query models and sets the 
        active filter.
        '''
        self.log(
            self.on_page_change.__name__, 
            "Page changed to " + page.props.name
            )

        shell = self.object
        t = self.get_favourites_threshold()
        if (type(page) == RB.PlaylistSource or 
            type(page) == RB.AutoPlaylistSource or 
            page == shell.props.library_source):
            if page in self.visited_pages:
                [active_filter, query_models, t0] = self.visited_pages[page]

                if ((active_filter == "Favourites" and t0 != t) or 
                    active_filter not in query_models):
                    query_models[active_filter] = self.filter_query_model(
                        active_filter, query_models['All Ratings']
                        )
                    self.visited_pages[page] = [
                        active_filter, query_models, t
                        ]
                    
                self.action.set_state(self.target_values[active_filter])
                self.refresh(page)
            else:
                query_models = {}
                query_model = page.get_entry_view().props.model

                active_filter = 'All Ratings'               
                query_models[active_filter] = self.filter_query_model(
                    active_filter, query_model
                    )

                self.visited_pages[page] = [active_filter, query_models, t]
                self.action.set_state(self.target_values[active_filter])
                page.connect("filter-changed", self.on_browser_change)

    def filter_query_model(self, active_filter, query_model):
        '''
        Applies the active filter to the supplied query model and returns 
        the result.
        '''
        self.log(
            self.filter_query_model.__name__, 
            "Creating new query model for " + active_filter
            )
            
        shell = self.object
        db = shell.props.db
        new_query_model = RB.RhythmDBQueryModel.new_empty(db)

        if active_filter == 'All Ratings':
            new_query_model = query_model
        else:
            if active_filter == "Favourites":
                ratings = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
                t = self.get_favourites_threshold()
                ratings = ratings[t:]
            else:
                ratings = [0.0]

            for row in query_model:
                entry = row[0]
                entry_rating = entry.get_double(RB.RhythmDBPropType.RATING)
                if entry_rating in ratings:
                    new_query_model.add_entry(entry, -1)

        return new_query_model

    def refresh(self, page):
        '''
        Refreshes the entry view on the specified page.
        '''
        [active_filter, query_models, t] = self.visited_pages[page]

        self.log(
            self.refresh.__name__, 
            "Applying '" + active_filter + "' to " + page.props.name
            )

        query_model = query_models[active_filter]
        entry_view = page.get_entry_view()
        sorting_type = entry_view.get_sorting_type()
        entry_view.set_model(query_model)
        entry_view.set_sorting_type(sorting_type)
        
        page.props.query_model = query_model


class Preferences(GObject.Object, PeasGtk.Configurable):
    '''
    Preferences for the RatingFilters plugin. It holds the settings for the 
    plugin and is also responsible for creating the preferences dialog.
    '''
    __gtype_name__ = 'RatingFiltersPreferences'
    object = GObject.property(type=GObject.Object)

    ratings = [5, 4, 3, 2, 1]

    def __init__(self):
        GObject.Object.__init__(self)

    def do_create_configure_widget(self):
        '''
        Creates the plugin's preferences dialog
        '''
        settings = Gio.Settings('org.gnome.rhythmbox.plugins.rating_filters')        
        
        def favourites_threshold_changed(button):
            settings['favourites-threshold'] = self.ratings[
                button.get_active()
                ]
            print('Changing favourites threshold to ' + str(settings['favourites-threshold']))

        self.configure_callback_dic = {
            "favourites_rating_threshold_combobox_changed_cb": favourites_threshold_changed
        }
    
        # Create dialog
        builder = Gtk.Builder()
        builder.add_from_file(
            rb.find_plugin_file(self, 'RatingFiltersPreferences.ui')
            )
    
        # Bind dialog to settings
        builder.get_object("favourites_threshold_combobox").set_active(
            self.ratings.index(settings['favourites-threshold'])
            )
        builder.connect_signals(self.configure_callback_dic)

        # Return dialog
        return builder.get_object('main')

