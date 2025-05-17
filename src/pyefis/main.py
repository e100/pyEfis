#!/usr/bin/env python3

#  Copyright (c) 2013 Phil Birkelbach
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
import time
import sys, os

import logging
import logging.config
import argparse
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

import yaml
import importlib
from os import environ
import shutil
import hashlib 

from pyefis import cfg
from pyefis import __version__

if "pyAvTools" not in ''.join(sys.path):
    neighbor_tools = os.path.join('..', 'pyAvTools')
    if os.path.isdir(neighbor_tools):
        sys.path.append(neighbor_tools)
    elif 'TOOLS_PATH' in os.environ:
        sys.path.append(os.environ['TOOLS_PATH'])

if "pyAvMap" not in ''.join(sys.path):
    neighbor_map = os.path.join('..', 'pyAvMap')
    if os.path.isdir(neighbor_map):
        sys.path.append(neighbor_map)
    elif 'MAP_PATH' in os.environ:
        sys.path.append(os.environ['MAP_PATH'])

import pyavtools.fix as fix

import pyefis.hooks as hooks
import pyefis.hmi as hmi
import pyefis.gui as gui


config_filename = "default.yaml"
user_home = environ.get('SNAP_REAL_HOME', os.path.expanduser("~"))
os.environ["HOME"] = user_home
prefix_path = sys.prefix
path_options = ['{USER}/makerplane/pyefis/config',
                '{PREFIX}/local/etc/pyefis',
                '{PREFIX}/etc/pyefis',
                '/etc/pyefis',
                '.']

config_path = None

# This function recursively walks the given directory in the installed
# package and creates a mirror of it in basedir.
def create_config_dir(basedir):
    # Look in the package for the configuration
    import importlib.resources as ir
    package = 'pyefis'
    def sha256sum(file):
        sha256 = hashlib.sha256()
        with open(file, 'rb') as f:
            while True:
                data = f.read(65536)
                if not data:
                    break
                sha256.update(data)
        return sha256.hexdigest()

    def copy_file(source,dest,extension=""):
        print(f"Replacing file: {dest}{extension}")
        shutil.copy(source,dest + extension)
        # Set timestamp
        os.utime(dest + extension,(350039106.789,350039106.789))

    def copy_dir(module,path=None):
        if not path: path = module
        os.makedirs(basedir + "/" + path, exist_ok=True)
        for each in ir.files(package + '.'+ module).iterdir():
            filename = path + "/" + each.name
            filepath = basedir + "/" + filename
            modulename = module + "." + each.name
            if each.is_dir():
                copy_dir(modulename,filename)
            else:
                # If file does not exist, copy it
                if not os.path.exists(filepath): 
                    copy_file(each.as_posix(), filepath)
                    continue
                # If file has specific timestamp, it has not been edited by the user
                if os.path.getmtime(filepath) == 350039106.789:
                    # If the file is not identical to the one in this version, replace it
                    if not sha256sum(filepath) == sha256sum(each.as_posix()):
                        copy_file(each.as_posix(), filepath) 
                else:
                    # Copy file but with .dist added to the filename.
                    copy_file(each.as_posix(), filepath, ".dist")

    copy_dir('config')


def merge_dict(dest,override):
    for k, v in override.items():
        if (k in dest and isinstance(dest[k], dict) and isinstance(override[k], dict)):
            merge_dict(dest[k], override[k])
        else:
            dest[k] = override[k]

def main():
    global config_path
    global preferences
    app = QApplication(sys.argv)
    parser = argparse.ArgumentParser(description='pyEfis')
    parser.add_argument('-m', '--mode', choices=['test', 'normal'],
        default='normal', help='Run pyEFIS in specific mode')
    parser.add_argument('--debug', action='store_true',
                        help='Run in debug mode')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Run in verbose mode')
    parser.add_argument('--config-file', type=argparse.FileType('r'),
                        help='Alternate configuration file')
    parser.add_argument('--log-config', type=argparse.FileType('r'),
                        help='Alternate logger configuration file')

    args = parser.parse_args()

    # Look for our configuration file in the list of directories
    for directory in path_options:
        # store the first match that we find
        d = directory.format(USER=user_home, PREFIX=prefix_path)
        if os.path.isfile("{}/{}".format(d, config_filename)):
            config_path = d
            break

    config_file = "{}/{}".format(config_path, config_filename)

    #config_file = args.config_file if args.config_file else os.path.join(os.path.dirname(__file__), 'config/default.yaml')

    # if we passed in a configuration file on the command line...
    if args.config_file:
        cf = args.config_file
        config_file = cf.name
    else:
        # If all else fails or update the configuration from the package
        # to ~/makerplane/fixgw/config
        create_config_dir("{USER}/makerplane/pyefis".format(USER=user_home))
        # Reset this stuff like we found it
        config_file = "{USER}/makerplane/pyefis/config/{FILE}".format(USER=user_home, FILE=config_filename)
    config_path = os.path.dirname(config_file)
    preference_file = f"{config_path}/preferences.yaml"
    with open(preference_file) as cf:
       preferences = yaml.safe_load(cf)
    preference_file = preference_file + ".custom"
    # override preferecnes with customizations
    if os.path.exists(preference_file):
        with open(preference_file) as cf:
            custom = yaml.safe_load(cf)
        merge_dict(preferences,custom)

    config = cfg.from_yaml(config_file,preferences=preferences)

    # If running under systemd
    if environ.get('INVOCATION_ID', False):
        # and autostart is not true, exit
        auto = config.get('auto start', False)
        print(auto)
        if isinstance(auto, str):
            # Check preferecnes
            if 'enabled' in preferences:
                if not preferences['enabled'].get('AUTO_START', False):
                    os._exit(0)
            else:
                # It is a string and we we cannot lookup enabled keys in preferences
                # Assume false
                os._exit(0)
        elif not auto:
            os._exit(0)


    log_config_file = args.log_config if args.log_config else config_file

    # Either load the config file given as a command line argument or
    # look in the configuration for the logging object
    if args.log_config:
        logging.config.fileConfig(args.log_config)
    elif 'logging' in config:
        # If running in snap write to $SNAP_USER_COMMON directory
        snap_dir = os.environ.get('SNAP_USER_COMMON','')
        if len(snap_dir) > 0: snap_dir = snap_dir + "/"
        log_yaml = yaml.dump(config['logging']).format(SNAP_USER_COMMON = snap_dir)
        logging.config.dictConfig(yaml.load(log_yaml, Loader=yaml.SafeLoader))
    else:
        logging.basicConfig()

    log = logging.getLogger()
    if args.verbose:
        log.setLevel(logging.INFO)
    if args.debug:
        log.setLevel(logging.DEBUG)
    log.info("Starting pyEFIS")

    fix.initialize(config)
    loaded = False
    while not loaded:
        try:
            fix.db.get_item("ZZLOADER")
            loaded = True
        except:
            log.critical("fix database not fully Initialized yet, ensure you have 'ZZLOADER' created in fixgateway database.yaml")
            time.sleep(2)
    pyefis_ver = fix.db.get_item('PYEFIS_VERSION')
    pyefis_ver.value = __version__
    pyefis_ver.output_value()

    hmi.initialize(config)

    if 'FMS' in config:
        sys.path.insert(0, config["FMS"]["module_dir"])
        fms = importlib.import_module ("FixIntf")
        fms.start(config["FMS"]["aircraft_config"])

    gui.initialize(config,config_path,preferences)
    if "keybindings" in config:
        hmi.keys.initialize(gui.mainWindow, config["keybindings"])
    hooks.initialize(config['hooks'])

    # Main program loop
    result = app.exec()

    # Clean up and get out
    fix.stop()
    if 'FMS' in config:
        fms.stop()
    log.info("PyEFIS Exiting Normally")
    sys.exit(result)


if __name__ == "__main__":
    main()
