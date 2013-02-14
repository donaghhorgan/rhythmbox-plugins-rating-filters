#!/bin/bash
SCRIPT_NAME=`basename "$0"`
SCRIPT_PATH=${0%`basename "$0"`}
PLUGIN_PATH="/home/${USER}/.local/share/rhythmbox/plugins/RatingFilters/"
GLIB_SCHEME="org.gnome.rhythmbox.plugins.rating_filters.gschema.xml"
GLIB_PATH="/usr/share/glib-2.0/schemas/"

rm -rf $PLUGIN_PATH

mkdir -p $PLUGIN_PATH
cp -r "${SCRIPT_PATH}"* "$PLUGIN_PATH"
rm "${PLUGIN_PATH}${SCRIPT_NAME}"
sudo cp "${PLUGIN_PATH}${GLIB_SCHEME}" "${GLIB_PATH}"
rm "${PLUGIN_PATH}${GLIB_SCHEME}"
sudo glib-compile-schemas "$GLIB_PATH"
