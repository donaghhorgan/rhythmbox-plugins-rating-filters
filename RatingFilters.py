# -*- coding: utf-8 -*-
#
#	RatingFilters.py
#
#	Rating filters for the library browser.
#	Copyright (C) 2013 Donagh Horgan <donagh.horgan@gmail.com>
#
#	Preferences class code adapted from Magnatune plugin and CoverArt plugin
#	Copyright (C) 2006 Adam Zimmerman  <adam_zimmerman@sfu.ca>
#	Copyright (C) 2006 James Livingston  <doclivingston@gmail.com>
#	Copyright (C) 2012 - fossfreedom
#	Copyright (C) 2012 - Agustin Carrasco
#
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import GObject, RB, Peas, Gtk, GLib, Gio, PeasGtk
import rb

ui_str = """
<ui>
  <toolbar name="LibrarySourceToolBar">
	<placeholder name="PluginPlaceholder"/>
	<toolitem name="FilterAll" action="FilterAll"/>
	<toolitem name="FilterFavourites" action="FilterFavourites"/>
	<toolitem name="FilterUnrated" action="FilterUnrated"/>
  </toolbar>

  <toolbar name="StaticPlaylistSourceToolBar">
	<placeholder name="PluginPlaceholder"/>
	<toolitem name="FilterAll" action="FilterAll"/>
	<toolitem name="FilterFavourites" action="FilterFavourites"/>
	<toolitem name="FilterUnrated" action="FilterUnrated"/>
  </toolbar>

  <toolbar name="AutoPlaylistSourceToolBar">
	<placeholder name="PluginPlaceholder"/>
	<toolitem name="FilterAll" action="FilterAll"/>
	<toolitem name="FilterFavourites" action="FilterFavourites"/>
	<toolitem name="FilterUnrated" action="FilterUnrated"/>
  </toolbar>
</ui>
"""

class RatingFilters (GObject.Object, Peas.Activatable):
	'''
	Main class for the RatingFilters plugin. Contains functions for setting up the UI, callbacks for user actions, and functions for filtering query models and refreshing the display.
	'''
	object = GObject.property (type = GObject.Object)


	def __init__(self):
		GObject.Object.__init__(self)


	def do_activate(self):
		"""Creates and links UI elements and creates class variables."""
		data = dict()
		shell = self.object
		manager = shell.props.ui_manager

		self.radioaction_all = Gtk.RadioAction('FilterAll', "All Ratings", "Show track(s) with any rating", 'gnome-mime-text-x-python', 0)
		self.radioaction_favourites = Gtk.RadioAction('FilterFavourites', "Favourites","Show favourite track(s)", 'gnome-mime-text-x-python', 1)
		self.radioaction_unrated = Gtk.RadioAction('FilterUnrated', "Unrated", "Show unrated track(s)",
'gnome-mime-text-x-python', 2)

		self.radioaction_all.set_active(True)
		self.radioaction_favourites.join_group(self.radioaction_all)
		self.radioaction_unrated.join_group(self.radioaction_all)

		data['action_group'] = Gtk.ActionGroup('RatingFiltersActions')
		data['action_group'].add_action(self.radioaction_all)
		data['action_group'].add_action(self.radioaction_favourites)
		data['action_group'].add_action(self.radioaction_unrated)

		self.radioaction_all.connect('changed', self.on_button_change)
				
		manager.insert_action_group(data['action_group'], 0)
		data['ui_id'] = manager.add_ui_from_string(ui_str)
		manager.ensure_update()

		shell.set_data('RatingFiltersInfo', data)

		# Class variables
		self.visited_pages = {}
		self.radioactions = {"All": self.radioaction_all, "Favourites": self.radioaction_favourites, "Unrated": self.radioaction_unrated}

		settings = Gio.Settings('org.gnome.rhythmbox.plugins.rating_filters')
		self.favourites_threshold = settings['favourites-threshold']


	def do_deactivate(self):
		"""Unlinks UI elements and resets entry views."""
		for page in self.visited_pages:
			[_, query_models] = self.visited_pages[page]
			self.visited_pages[page] = ["All", query_models]
			self.refresh(page)

		shell = self.object
		data = shell.get_data('RatingFiltersInfo')

		manager = shell.props.ui_manager
		manager.remove_ui(data['ui_id'])
		manager.remove_action_group(data['action_group'])
		manager.ensure_update()

		shell.set_data('RatingFiltersInfo', None)


	def on_button_change(self, action, current):
		"""Called when the UI is changed. Grabs query models and sets the active filter."""
		shell = self.object
		page = shell.props.selected_page

		active_filter = ("All", "Favourites", "Unrated")[action.get_current_value()]

		print "Button changed to " + active_filter + " on page " + page.props.name

		if page in self.visited_pages:
			settings = Gio.Settings('org.gnome.rhythmbox.plugins.rating_filters')
			t = settings['favourites-threshold']

			[_, query_models] = self.visited_pages[page]
			if active_filter not in query_models or (active_filter == "Favourites" and self.favourites_threshold != t):
				query_models[active_filter] = self.filter_query_model(active_filter, query_models["All"])
			self.visited_pages[page] = [active_filter, query_models]
			self.refresh(page)
		else:
			if len(self.visited_pages) == 0:
				shell.props.display_page_tree.connect("selected", self.on_page_change)
				page.connect("filter-changed", self.on_browser_change)

			query_models = {}
			query_model = page.get_entry_view().props.model

			query_models["All"] = self.filter_query_model("All", query_model)
			query_models[active_filter] = self.filter_query_model(active_filter, query_model)

			self.visited_pages[page] = [active_filter, query_models]
			self.refresh(page)


	def on_browser_change(self, action):
		"""Called when the library browser for a visited page changes. Reapplies the active filter to the new query model."""
		shell = self.object
		page = shell.props.selected_page

		print "Browser changed on page " + page.props.name

		query_models = {}
		query_model = page.get_entry_view().props.model

		active_filter = "All"
		query_models[active_filter] = query_models[active_filter] = self.filter_query_model(active_filter, query_model)

		[active_filter, _] = self.visited_pages[page]
		query_models[active_filter] = self.filter_query_model(active_filter, query_model)

		self.visited_pages[page] = [active_filter, query_models]
		self.refresh(page)


	def on_page_change(self, display_page_tree, page):
		"""Called when the display page changes. Grabs query models and sets the active filter."""
		print "Page changed to " + page.props.name
		shell = self.object
		if type(page) == RB.PlaylistSource or type(page) == RB.AutoPlaylistSource or page == shell.props.library_source:
			if page in self.visited_pages:
				[active_filter, query_models] = self.visited_pages[page]

				settings = Gio.Settings('org.gnome.rhythmbox.plugins.rating_filters')
				t = settings['favourites-threshold']

				if active_filter == "Favourites" and self.favourites_threshold != t:
					query_models[active_filter] = self.filter_query_model(active_filter, query_models["All"])
					self.visited_pages[page] = [active_filter, query_models]

				self.radioactions[active_filter].set_active(True)
				self.refresh(page)
			else:
				query_models = {}
				query_model = page.get_entry_view().props.model

				active_filter = "All"				
				query_models[active_filter] = self.filter_query_model(active_filter, query_model)

				self.visited_pages[page] = [active_filter, query_models]
				self.radioactions[active_filter].set_active(True)
				page.connect("filter-changed", self.on_browser_change)


	def filter_query_model(self, active_filter, query_model):
		"""Applies the active filter to the supplied query model and returns the result."""
		print "Creating new query model for " + active_filter

		shell = self.object
		db = shell.props.db
		new_query_model = RB.RhythmDBQueryModel.new_empty(db)

		if active_filter == "All":
			new_query_model = query_model
		else:
			if active_filter == "Favourites":
				ratings = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]	
				settings = Gio.Settings('org.gnome.rhythmbox.plugins.rating_filters')
				self.favourites_threshold = settings['favourites-threshold']
				ratings = ratings[self.favourites_threshold:]
			else:
				ratings = [0.0]

			for row in query_model:
				entry = row[0]
				entry_rating = entry.get_double(RB.RhythmDBPropType.RATING)
				if entry_rating in ratings:
					new_query_model.add_entry(entry, -1)

		return new_query_model


	def refresh(self, page):
		"""Refreshes the entry view on the specified page."""
		[active_filter, query_models] = self.visited_pages[page]

		print "Applying '" + active_filter + "' to " + page.props.name

		query_model = query_models[active_filter]
		entry_view = page.get_entry_view()
		[column_name, sort_order] = entry_view.get_sorting_order()
		entry_view.set_model(query_model)
		entry_view.set_sorting_order(column_name, sort_order)
		
		page.props.query_model = query_model



class Preferences(GObject.Object, PeasGtk.Configurable):
	'''
	Preferences for the RatingFilters plugin. It holds the settings for
	the plugin and also is the responsible of creating the preferences dialog.
	'''
	__gtype_name__ = 'RatingFiltersPreferences'
	object = GObject.property(type=GObject.Object)

	ratings = [5, 4, 3, 2, 1]

	def __init__(self):
		'''
		Initialises the preferences, getting an instance of the settings saved
		by Gio.
		'''
		GObject.Object.__init__(self)
		self.settings = Gio.Settings('org.gnome.rhythmbox.plugins.rating_filters')

	def do_create_configure_widget(self):
		'''
		Creates the plugin's preferences dialog
		'''
	
		def favourites_threshold_changed(button):
			self.settings['favourites-threshold'] = self.ratings[button.get_active()]

		self.configure_callback_dic = {
			"favourites_rating_threshold_combobox_changed_cb" : favourites_threshold_changed
		}
	
		# Create dialog
		builder = Gtk.Builder()
		builder.add_from_file(rb.find_plugin_file(self, 'RatingFiltersPreferences.ui'))
	
		# Bind dialog to settings
		builder.get_object("favourites_threshold_combobox").set_active(self.ratings.index(self.settings['favourites-threshold']))
		builder.connect_signals(self.configure_callback_dic)

		# Return dialog
		return builder.get_object('main')

