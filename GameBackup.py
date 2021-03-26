import PySimpleGUI as sg
from json import (load as jsonload, dump as jsondump)
import os
import subprocess
from distutils.dir_util import copy_tree
import threading
from itertools import count, filterfalse

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), r'settings_file.cfg')
DEFAULT_SETTINGS = {'1': {'game_name': 'add name here', 'source_folder': 'Please select', 'output_folder': 'please select'}}
ADD_WINDOW = 1
WINDOW_LIST = []
FILEBROWSER_PATH = os.path.join(os.getenv('WINDIR'), 'explorer.exe')


##################### Load/Save Settings File #####################


def load_settings(settings_file, default_settings):
    try:
        with open(settings_file, 'r') as f:
            settings = jsonload(f)
    except Exception as e:
        sg.popup_quick_message(f'exception {e}', 'No settings file found... will create one for you', keep_on_top=True, background_color='red', text_color='white')
        settings = default_settings
        save_settings('new game', settings_file, settings, None, None)
    return settings


def save_settings(item_number, settings_file, settings, values, window):
    if values:      # if there are stuff specified by another window, fill in those values
        for element in [[(item_number, 0, 0), 'game_name'], [(item_number, 1, 1), 'source_folder'], [(item_number, 2, 1), 'output_folder']]:  # update window with the values read from settings file
            try:
                settings[item_number][element[1]] = values[element[0]]
            except Exception as e:
                print(f'Problem updating settings from window values. Key = {element}')

    save_file(settings_file, settings, 1, window)


def save_file(settings_file, settings, pop, window):
    with open(settings_file, 'w') as f:
        jsondump(settings, f)
    if pop and window is not None:
        sg.popup_quick_message('Settings Saved', location=window.current_location())


def list_files(startpath, window):
    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        window.update(window.get() + f'{indent}{os.path.basename(root)}/')
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            window.update(window.get() + f'{subindent}{f}')
    window.update(window.get() + f'Copy Size: {get_size_format(get_directory_size(startpath))}')


def get_size_format(b, factor=1024, suffix="B"):
    """
    Scale bytes to its proper byte format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if b < factor:
            return f"{b:.2f}{unit}{suffix}"
        b /= factor
    return f"{b:.2f}Y{suffix}"


def get_directory_size(directory):
    """Returns the `directory` size in bytes."""
    total = 0
    try:
        # print("[+] Getting the size of", directory)
        for entry in os.scandir(directory):
            if entry.is_file():
                # if it's a file, use stat() function
                total += entry.stat().st_size
            elif entry.is_dir():
                # if it's a directory, recursively call this function
                total += get_directory_size(entry.path)
    except NotADirectoryError:
        # if `directory` isn't a directory, get the file size then
        return os.path.getsize(directory)
    except PermissionError:
        # if for whatever reason we can't open the folder, return 0
        return 0
    return total


def explore(path):
    # explorer would choke on forward slashes
    path = os.path.normpath(path)

    if os.path.isdir(path):
        subprocess.run([FILEBROWSER_PATH, path])
    elif os.path.isfile(path):
        subprocess.run([FILEBROWSER_PATH, '/select,', os.path.normpath(path)])


def backup_thread(source, destination, window, event):
    copy_tree(source, destination)
    window.write_event_value('-THREAD-', (destination, event))


def create_layout(settings):
    new_layout = []
    ordered_keys = sorted(settings.keys())
    for key in ordered_keys:
        new_layout += [sg.Frame(key, create_frame_layout(key))],
    return new_layout


def create_frame_layout(index):
    frame_layout = [[sg.Text('Game: ', size=(16, 1), justification='right'),
                     sg.InputText(key=(index, 0, 0), enable_events=True, size=(20, 1)),
                     sg.Button(key=(index, 0, 1), button_text='Save Details', enable_events=True, size=(12, 1)),
                     sg.Button(key=(index, 0, 2), button_text='Backup Now', enable_events=True, size=(12, 1),
                               button_color='green'),
                     sg.Button(key=(index, 0, 3), button_text='Remove Game', enable_events=True, size=(12, 1),
                               button_color='indian red')],
                    [sg.FolderBrowse(button_text='Pick Game Folder',
                                     key=(index, 1, 0), enable_events=True,
                                     size=(14, 1), ),
                     sg.InputText(key=(index, 1, 1), size=(54, 1)),
                     sg.Button(button_text='< Open folder', key=(index, 1, 2), enable_events=True, size=(12, 1))],
                    [sg.FolderBrowse(button_text='Pick Backup Folder',
                                     key=(index, 2, 0),
                                     enable_events=True,
                                     size=(14, 1), ),
                     sg.InputText(key=(index, 2, 1), size=(54, 1)),
                     sg.Button(button_text='< Open folder', key=(index, 2, 2), enable_events=True, size=(12, 1))],
                    ]

    return frame_layout


def create_main_window(settings, window, location):
    sg.theme('DarkBrown')
    column1 = create_layout(settings)
    column2 = []
    column2 += [[sg.Multiline(key='-OUTPUT_TEXT-', enable_events=True, size=(38, 41), autoscroll=True)]]
    column2 += [[sg.Button(key='-ADD_GAME-', button_text='Add Game', enable_events=True, size=(12,1))]]
    layout = [[sg.Column(column1, size=(670,700), scrollable=True), sg.Column(column2, size=(300, 700), scrollable=False)]]

    return sg.Window('Backup Save Games  -DontDoDeath 2021- 1.2', layout, location=location)


def populate_window(settings, window):
    for key in settings:
        for element in [[(key, 0, 0), 'game_name'], [(key, 1, 1), 'source_folder'], [(key, 2, 1), 'output_folder']]:
            try:
                window[element[0]].update(value=settings[key][element[1]])
            except Exception as e:
                print(f'Problem updating PySimpleGUI window from settings. Key = {key}')


def main():
    window, settings = None, load_settings(SETTINGS_FILE, DEFAULT_SETTINGS)

    while True:
        if window is None:
            w, h = sg.Window.get_screen_size()
            window = create_main_window(settings, window, ((w/2)-490, 200))
            window.finalize()
            populate_window(settings, window)

        event, values = window.read()
        if event == sg.WIN_CLOSED or event == 'Cancel':
            break

        # select source folder event
        elif event[1] == 1 and event[2] == 0:
            file_name = values[(event[0], 1, 0)]
            window[(event[0], 1, 1)].update(file_name)

        # select output folder event
        elif event[1] == 2 and event[2] == 0:
            file_name = values[(event[0], 1, 0)]
            window[(event[0], 1, 1)].update(file_name)

        # Open folder
        elif (event[1] == 1 or event[1] == 2) and event[2] == 2:
            file_name = values[(event[0], event[1], 1)]
            print('opening folder ', file_name)
            explore(file_name)

        # save details event
        elif event[1] == 0 and event[2] == 1:
            save_settings(event[0], SETTINGS_FILE, settings, values, window)

        # Backup event
        elif event[1] == 0 and event[2] == 2:
            name = values[(event[0], 0, 0)]
            window[event].update(button_color='indian red')
            window['-OUTPUT_TEXT-'].update(window['-OUTPUT_TEXT-'].get() + f'{name} copy started')
            threading.Thread(target=backup_thread,
                             args=(values[(event[0], 1, 1)], values[(event[0], 2, 1)], window, event), daemon=True).start()

        elif event == '-THREAD-':
            list_files(values[event][0], window['-OUTPUT_TEXT-'])
            window[values[event][1]].update(button_color='green')

        elif event == '-ADD_GAME-':
            key_list = []
            for keys in settings:
                key_list.append(int(keys))
            new_key = next(filterfalse(set(key_list).__contains__, count(1)))
            settings[str(new_key)] = DEFAULT_SETTINGS['1']
            save_file(SETTINGS_FILE, settings, 0, window)
            location = window.CurrentLocation()
            window2 = create_main_window(settings, window, location)
            window2.finalize()
            populate_window(settings, window2)
            window.close()
            window = window2

        # event remove game
        elif event[1] == 0 and event[2] == 3:
            location = window.current_location()
            w, h = location
            sg.theme('DarkRed2')
            if sg.popup_yes_no('Are you Sure?', location=(w+500, h+300), ) == 'Yes':
                del settings[event[0]]
                save_file(SETTINGS_FILE, settings, 0, window)
                window2 = create_main_window(settings, window, location)
                window2.finalize()
                populate_window(settings, window2)
                window.close()
                window = window2

    window.close()


main()
