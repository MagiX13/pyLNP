#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Configuration and raw manipulation for Dwarf Fortress."""
from __future__ import print_function, unicode_literals

import os, re, shutil

# Markers to read certain settings correctly

class _DisableValues(object):
    """Marker class for DFConfiguration. Value is disabled by replacing [ and ]
    with !."""
    pass

_disabled = _DisableValues()

class _ForceBool(object):
    """Marker class for DFConfiguration. Values other than YES or NO are
    interpreted as YES."""
    pass

_force_bool = _ForceBool()

class DFConfiguration(object):
    """Reads and modifies Dwarf Fortress configuration textfiles."""
    def __init__(self, base_dir):
        """
        Constructor for DFConfiguration.

        Params:
            base_dir
                Path containing the Dwarf Fortress instance to operate on.
        """
        self.base_dir = base_dir
        self.settings = dict()
        self.options = dict()
        self.field_names = dict()
        self.inverse_field_names = dict()
        self.files = dict()
        self.in_files = dict()
        #init.txt
        boolvals = ("YES", "NO")
        init = (os.path.join(base_dir, 'data', 'init', 'init.txt'),)
        self.create_option("truetype", "TRUETYPE", "YES", _force_bool, init)
        self.create_option("sound", "SOUND", "YES", boolvals, init)
        self.create_option("volume", "VOLUME", "255", None, init)
        self.create_option("introMovie", "INTRO", "YES", boolvals, init)
        self.create_option("startWindowed", "WINDOWED", "YES", boolvals, init)
        self.create_option("fpsCounter", "FPS", "NO", boolvals, init)
        self.create_option("fpsCap", "FPS_CAP", "100", None, init)
        self.create_option("gpsCap", "G_FPS_CAP", "50", None, init)
        self.create_option(
            "procPriority", "PRIORITY", "NORMAL", (
                "REALTIME", "HIGH", "ABOVE_NORMAL", "NORMAL", "BELOW_NORMAL",
                "IDLE"), init)
        self.create_option(
            "compressSaves", "COMPRESSED_SAVES", "YES", boolvals, init)
        #d_init.txt
        dinit = (os.path.join(base_dir, 'data', 'init', 'd_init.txt'),)
        self.create_option("popcap", "POPULATION_CAP", "200", None, dinit)
        self.create_option(
            "childcap", "BABY_CHILD_CAP", "100:1000", None, dinit)
        self.create_option("invaders", "INVADERS", "YES", boolvals, dinit)
        self.create_option(
            "temperature", "TEMPERATURE", "YES", boolvals, dinit)
        self.create_option("weather", "WEATHER", "YES", boolvals, dinit)
        self.create_option("caveins", "CAVEINS", "YES", boolvals, dinit)
        self.create_option(
            "liquidDepth", "SHOW_FLOW_AMOUNTS", "YES", boolvals, dinit)
        self.create_option(
            "variedGround", "VARIED_GROUND_TILES", "YES", boolvals, dinit)
        self.create_option("laborLists", "SET_LABOR_LISTS", "SKILLS", (
            "NO", "SKILLS", "BY_UNIT_TYPE"), dinit)
        self.create_option("autoSave", "AUTOSAVE", "SEASONAL", (
            "NONE", "SEASONAL", "YEARLY"), dinit)
        self.create_option("autoBackup", "AUTOBACKUP", "YES", boolvals, dinit)
        self.create_option(
            "autoSavePause", "AUTOSAVE_PAUSE", "YES", boolvals, dinit)
        self.create_option(
            "initialSave", "INITIAL_SAVE", "YES", boolvals, dinit)
        self.create_option(
            "pauseOnLoad", "PAUSE_ON_LOAD", "YES", boolvals, dinit)
        #special
        self.create_option("aquifers", "AQUIFER", "YES", _disabled, tuple(
            os.path.join(base_dir, 'raw', 'objects', a) for a in [
                'inorganic_stone_layer.txt', 'inorganic_stone_mineral.txt',
                'inorganic_stone_soil.txt']))

    def create_option(self, name, field_name, default, values, files):
        """
        Register an option to write back for changes. If the field_name has
        been registered before, no changes are made.

        Params:
          name
            The name you want to use to refer to this field (becomes available
            as an attribute on this class).
          field_name
            The field name used in the file. If this is different from the name
            argument, this will also become available as an attribute.
          default
            The value to initialize this setting to.
          values
            An iterable of valid values for this field. Used in cycle_list.
            Special values defined in this file:
              None
                Unspecified value; cycling has no effect.
              disabled:
                Boolean option toggled by replacing the [] around the field
                name with !!.
              force_bool:
                Values other than "YES" and "NO" are interpreted as "YES".
          files
            A tuple of files this value is read from. Used for e.g. aquifer
            toggling, which requires editing multiple files.
        """

        # Don't allow re-registration of a known field
        if name in self.settings or name in self.inverse_field_names:
            return
        self.settings[name] = default
        self.options[name] = values
        self.field_names[name] = field_name
        if field_name != name:
            self.inverse_field_names[field_name] = name
        self.files[name] = files
        self.in_files.setdefault(files, [])
        self.in_files[files].append(name)

    def __iter__(self):
        for key, value in list(self.settings.items()):
            yield key, value

    def set_value(self, name, value):
        """
        Sets the setting <name> to <value>.

        Params:
            name
                Name of the setting to alter.
            value
                New value for the setting.
        """
        self.settings[name] = value

    def cycle_item(self, name):
        """
        Cycle the setting <name>.

        Params:
            name
                Name of the setting to cycle.
        """

        self.settings[name] = self.cycle_list(
            self.settings[name], self.options[name])

    @staticmethod
    def cycle_list(current, items):
        """Cycles setting between a list of items.

        Params:
            current
                Current value.
            items
                List of possible values (optionally a special value).

        Returns:
            If no list of values is given, returns current.
            If the current value is the last value in the list, returns the
            first value in the list.
            Otherwise, returns the value from items immediately following the
            current value.
        """
        if items is None:
            return current
        if items is _disabled or items is _force_bool:
            items = ("YES", "NO")
        return items[(items.index(current) + 1) % len(items)]

    def read_settings(self):
        """Read settings from known filesets. If fileset only contains one
        file, all options will be registered automatically."""
        for files in self.in_files.keys():
            for filename in files:
                self.read_file(filename, self.in_files[files], len(files) == 1)

    def read_file(self, filename, fields, auto_add):
        """
        Reads DF settings from the file <filename>.

        Params:
          filename
            The file to read from.
          fields:
            An iterable containing the field names to read.
          auto_add
            Whether to automatically register all unknown fields for changes by
            calling create_option(field_name, field_name, value, None,
            (filename,)).
        """
        settings_file = open(filename)
        text = settings_file.read()
        if auto_add:
            for match in re.findall(r'\[(.+?):(.+?)\]', text):
                self.create_option(
                    match[0], match[0], match[1], None, (filename,))
        for field in fields:
            if field in self.inverse_field_names:
                field = self.inverse_field_names[field]
            if self.options[field] is _disabled:
                #Assume option is disabled unless there is a single match
                self.settings[field] = "NO"
                if "[{0}]".format(self.field_names[field]) in text:
                    self.settings[field] = "YES"
            else:
                match = re.search(r'\[{0}:(.+?)\]'.format(
                    self.field_names[field]), text)
                if (
                        self.options[field] is _force_bool and
                        match.group(1) != "NO"):
                    #Interpret everything other than "NO" as "YES"
                    self.settings[field] = "YES"
                else:
                    self.settings[field] = match.group(1)

    def write_settings(self):
        """Write all settings to their respective files."""
        for files in self.in_files:
            for filename in files:
                self.write_file(filename, self.in_files[files])

    def write_file(self, filename, fields):
        """
        Write settings to a specific file.

        Params:
            filename
                Name of the file to write.
            fields
                List of all field names to change.
        """
        oldfile = open(filename, 'r')
        text = oldfile.read()
        for field in fields:
            if self.options[field] is _disabled:
                replace_from = None
                replace_to = None
                if self.settings[field] == "NO":
                    replace_from = "[{0}]"
                    replace_to = "!{0}!"
                else:
                    replace_from = "!{0}!"
                    replace_to = "[{0}]"
                text = text.replace(
                    replace_from.format(self.field_names[field]),
                    replace_to.format(self.field_names[field]))
            else:
                text = re.sub(
                    r'\[{0}:(.+?)\]'.format(self.field_names[field]),
                    '[{0}:{1}]'.format(
                        self.field_names[field], self.settings[field]), text)
        oldfile.close()
        #Backup old file
        backup = filename+'.bak'
        shutil.copyfile(filename, backup)
        newfile = open(filename, 'w')
        newfile.write(text)
        newfile.close()

    def __str__(self):
        return (
            "base_dir = {0}\nsettings = {1}\noptions = {2}\n"
            "field_names ={3}\ninverse_field_names = {4}\nfiles = {5}\n"
            "in_files = {6}").format(
                self.base_dir, self.settings, self.options, self.field_names,
                self.inverse_field_names, self.files, self.in_files)

    def __getattr__(self, name):
        """Exposes all registered options through both their internal and
        registered names."""
        if name in self.inverse_field_names:
            return self.settings[self.inverse_field_names[name]]
        return self.settings[name]

# vim:expandtab
